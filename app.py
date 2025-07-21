from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import psycopg2
import os
from werkzeug.security import generate_password_hash, check_password_hash
import re
from functools import wraps
from dotenv import load_dotenv
import datetime
from datetime import datetime
from datetime import timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from pytz import timezone as ZoneInfo

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# PostgreSQL configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

# --- DB Initialization ---
def init_db():
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    
    # Create tables if they don't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username VARCHAR(255) PRIMARY KEY,
            password VARCHAR(255),
            name VARCHAR(255)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            refresh_time INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id SERIAL PRIMARY KEY,
            fullname VARCHAR(255),
            phone VARCHAR(255) UNIQUE,
            email VARCHAR(255) UNIQUE,
            enable_sms INTEGER DEFAULT 1,
            enable_email INTEGER DEFAULT 1
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS app_settings (
            id SERIAL PRIMARY KEY,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_error_event TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS diagnostic_codes (
            id SERIAL PRIMARY KEY,
            code VARCHAR(255) UNIQUE,
            description TEXT,
            type VARCHAR(255),
            state VARCHAR(255),
            last_failure TEXT,
            history_count INTEGER,
            room_id INTEGER REFERENCES rooms(id),
            data_source_type VARCHAR(50) DEFAULT 'modbus',
            modbus_ip VARCHAR(255),
            modbus_port INTEGER,
            modbus_unit_id INTEGER,
            modbus_register_type VARCHAR(255),
            modbus_register_address INTEGER,
            modbus_data_type VARCHAR(255),
            modbus_byte_order VARCHAR(255),
            modbus_scaling VARCHAR(255),
            modbus_units VARCHAR(255),
            modbus_offset VARCHAR(255),
            modbus_function_code VARCHAR(255),
            mqtt_broker VARCHAR(255),
            mqtt_port INTEGER,
            mqtt_topic VARCHAR(255),
            mqtt_username VARCHAR(255),
            mqtt_password VARCHAR(255),
            mqtt_qos INTEGER DEFAULT 0,
            upper_limit REAL,
            lower_limit REAL,
            enabled INTEGER,
            current_value REAL,
            last_read_time TIMESTAMP,
            start_value REAL,
            target_value REAL,
            threshold REAL,
            time_to_achieve INTEGER,
            enabled_at TIMESTAMP,
            fault_type VARCHAR(255)
        )
    ''')
    
    # Ensure code is unique if table already exists
    try:
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS unique_code_idx ON diagnostic_codes (code)')
    except Exception:
        pass
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            code VARCHAR(255),
            description TEXT,
            state VARCHAR(255),
            last_failure TEXT,
            history_count INTEGER,
            type VARCHAR(255),
            value REAL,
            event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS data_logs (
            id SERIAL PRIMARY KEY,
            code VARCHAR(255),
            value REAL,
            data_source VARCHAR(50),
            event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if default user exists
    c.execute('SELECT 1 FROM users WHERE username = %s', ('user',))
    if not c.fetchone():
        c.execute('INSERT INTO users (username, password, name) VALUES (%s, %s, %s)',
                  ('user', generate_password_hash('password'), 'Admin'))
    
    # Check if default refresh time exists
    c.execute('SELECT 1 FROM app_settings WHERE id = 1')
    if not c.fetchone():
        c.execute('INSERT INTO app_settings (id, last_error_event) VALUES (1, NULL)')
    
    conn.commit()
    conn.close()

init_db()

# --- Helper: Check login ---
def validate_user(username, password):
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username=%s', (username,))
    row = c.fetchone()
    conn.close()
    if row and check_password_hash(row[0], password):
        return True
    return False

# --- Helper: Email and Phone Validation ---
def is_valid_email(email):
    # Simple regex for email validation
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)

def is_valid_phone(phone):
    # Must start with +, then 1-3 digits (country code), then exactly 10 digits
    return re.match(r"^\+[0-9]{1,3}[0-9]{10}$", phone)

# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if validate_user(username, password):
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    username = session['user']
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('SELECT name FROM users WHERE username=%s', (username,))
    row = c.fetchone()
    name = row[0] if row else username
    
    # Fetch enabled diagnostic codes with room information
    c.execute('''
        SELECT dc.code, dc.description, dc.state, dc.last_failure, dc.history_count, 
               dc.type, dc.modbus_units, dc.current_value, dc.last_read_time,
               r.name as room_name, r.id as room_id
        FROM diagnostic_codes dc
        LEFT JOIN rooms r ON dc.room_id = r.id
        WHERE dc.enabled=1
        ORDER BY r.name NULLS FIRST, dc.type, dc.code
    ''')
    all_codes = c.fetchall()
    
    # Group codes by room
    codes_by_room = {}
    for code in all_codes:
        room_name = code[9] if code[9] else 'Unassigned'
        if room_name not in codes_by_room:
            codes_by_room[room_name] = {'temp': [], 'humidity': [], 'room_id': code[10]}
        
        if code[5] == 'Temperature':
            codes_by_room[room_name]['temp'].append(code)
        elif code[5] == 'Humidity':
            codes_by_room[room_name]['humidity'].append(code)
    
    # Notification center: codes with state 'No Status' or 'Fail'
    notifications = [code for code in all_codes if code[2] in ('No Status', 'Fail')]
    conn.close()
    
    # Get contact statistics
    total_contacts, email_enabled, sms_enabled = get_contact_stats()
    
    return render_template('dashboard.html', 
                         user=name, 
                         codes_by_room=codes_by_room,
                         notifications=notifications,
                         total_contacts=total_contacts,
                         email_enabled=email_enabled,
                         sms_enabled=sms_enabled)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        if not username or not password or not name:
            flash('All fields are required.', 'danger')
        else:
            conn = psycopg2.connect(**DB_CONFIG)
            c = conn.cursor()
            try:
                c.execute('INSERT INTO users (username, password, name) VALUES (%s, %s, %s)',
                          (username, generate_password_hash(password), name))
                conn.commit()
                flash('User added successfully!', 'success')
            except psycopg2.IntegrityError:
                flash('Username already exists.', 'danger')
            finally:
                conn.close()
    return render_template('add_user.html')

@app.route('/contacts')
def contacts():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '').strip()
    
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    
    if search_query:
        search_pattern = f'%{search_query}%'
        c.execute('''
            SELECT * FROM contacts 
            WHERE fullname ILIKE %s 
            OR phone ILIKE %s 
            OR email ILIKE %s
        ''', (search_pattern, search_pattern, search_pattern))
    else:
        c.execute('SELECT * FROM contacts')
    
    contacts = c.fetchall()
    conn.close()
    return render_template('contacts.html', contacts=contacts, search_query=search_query)

@app.route('/toggle_contact_sms/<int:contact_id>', methods=['POST'])
def toggle_contact_sms(contact_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    # Toggle the SMS enabled status
    c.execute('UPDATE contacts SET enable_sms = CASE WHEN enable_sms = 1 THEN 0 ELSE 1 END WHERE id = %s', (contact_id,))
    conn.commit()
    conn.close()
    flash('Contact SMS status updated successfully', 'success')
    return redirect(url_for('contacts'))

@app.route('/toggle_contact_email/<int:contact_id>', methods=['POST'])
def toggle_contact_email(contact_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    # Toggle the email enabled status
    c.execute('UPDATE contacts SET enable_email = CASE WHEN enable_email = 1 THEN 0 ELSE 1 END WHERE id = %s', (contact_id,))
    conn.commit()
    conn.close()
    flash('Contact email status updated successfully', 'success')
    return redirect(url_for('contacts'))

@app.route('/add_contact', methods=['GET', 'POST'])
def add_contact():
    if 'user' not in session:
        return redirect(url_for('login'))
    fullname = ''
    phone = '+1'
    email = ''
    if request.method == 'POST':
        fullname = request.form['fullname']
        phone = request.form['phone'] or '+1'
        email = request.form['email']
        enable_sms = 1 if request.form.get('enable_sms') == 'on' else 0
        enable_email = 1 if request.form.get('enable_email') == 'on' else 0
        
        if not fullname or not phone or not email:
            flash('All fields are required.', 'danger')
        elif not is_valid_phone(phone):
            flash('Invalid phone number format. Must be in format: +[country code][10 digits]', 'danger')
        elif not is_valid_email(email):
            flash('Invalid email format.', 'danger')
        else:
            conn = psycopg2.connect(**DB_CONFIG)
            c = conn.cursor()
            try:
                c.execute('INSERT INTO contacts (fullname, phone, email, enable_sms, enable_email) VALUES (%s, %s, %s, %s, %s)',
                          (fullname, phone, email, enable_sms, enable_email))
                conn.commit()
                flash('Contact added successfully!', 'success')
                return redirect(url_for('contacts'))
            except psycopg2.IntegrityError:
                flash('Phone number or email already exists.', 'danger')
            finally:
                conn.close()
    return render_template('add_contact.html', fullname=fullname, phone=phone, email=email)

@app.route('/edit_contact/<int:contact_id>', methods=['GET', 'POST'])
def edit_contact(contact_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    
    if request.method == 'POST':
        fullname = request.form['fullname']
        phone = request.form['phone']
        email = request.form['email']
        enable_sms = 1 if request.form.get('enable_sms') == 'on' else 0
        enable_email = 1 if request.form.get('enable_email') == 'on' else 0
        
        if not fullname or not phone or not email:
            flash('All fields are required.', 'danger')
        elif not is_valid_phone(phone):
            flash('Invalid phone number format. Must be in format: +[country code][10 digits]', 'danger')
        elif not is_valid_email(email):
            flash('Invalid email format.', 'danger')
        else:
            try:
                c.execute('UPDATE contacts SET fullname=%s, phone=%s, email=%s, enable_sms=%s, enable_email=%s WHERE id=%s',
                          (fullname, phone, email, enable_sms, enable_email, contact_id))
                conn.commit()
                flash('Contact updated successfully!', 'success')
                return redirect(url_for('contacts'))
            except psycopg2.IntegrityError:
                flash('Phone number or email already exists.', 'danger')
    
    c.execute('SELECT * FROM contacts WHERE id=%s', (contact_id,))
    contact = c.fetchone()
    conn.close()
    
    if contact is None:
        flash('Contact not found.', 'danger')
        return redirect(url_for('contacts'))
        
    return render_template('edit_contact.html', contact=contact)

@app.route('/delete_contact/<int:contact_id>', methods=['POST'])
def delete_contact(contact_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('DELETE FROM contacts WHERE id=%s', (contact_id,))
    conn.commit()
    conn.close()
    flash('Contact deleted successfully!', 'success')
    return redirect(url_for('contacts'))

@app.route('/diagnostic_codes')
def diagnostic_codes():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '').strip()
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    
    if search_query:
        c.execute('''
            SELECT dc.*, r.name as room_name 
            FROM diagnostic_codes dc
            LEFT JOIN rooms r ON dc.room_id = r.id
            WHERE dc.code ILIKE %s OR dc.description ILIKE %s OR r.name ILIKE %s
            ORDER BY r.name NULLS FIRST, dc.code
        ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
        all_codes = c.fetchall()
        
        # Group by room
        codes_by_room = {}
        for code in all_codes:
            room_name = code[-1] if code[-1] else 'Unassigned'
            if room_name not in codes_by_room:
                codes_by_room[room_name] = []
            codes_by_room[room_name].append(code)
    else:
        # Get all codes grouped by room
        c.execute('''
            SELECT dc.*, r.name as room_name 
            FROM diagnostic_codes dc
            LEFT JOIN rooms r ON dc.room_id = r.id
            ORDER BY r.name NULLS FIRST, dc.code
        ''')
        all_codes = c.fetchall()
        
        # Group by room
        codes_by_room = {}
        for code in all_codes:
            room_name = code[-1] if code[-1] else 'Unassigned'
            if room_name not in codes_by_room:
                codes_by_room[room_name] = []
            codes_by_room[room_name].append(code)
    
    conn.close()
    rooms = get_rooms()
    return render_template('diagnostic_codes.html', 
                         codes_by_room=codes_by_room,
                         rooms=rooms,
                         search_query=search_query)

@app.route('/add_diagnostic_code', methods=['GET', 'POST'])
def add_diagnostic_code():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        code = request.form['code']
        description = request.form['description']
        type = request.form['type']
        data_source_type = request.form['data_source_type']
        room_id = request.form.get('room_id') or None
        
        # Get Modbus fields
        modbus_ip = request.form.get('modbus_ip')
        modbus_port = request.form.get('modbus_port') or None
        modbus_unit_id = request.form.get('modbus_unit_id') or None
        modbus_register_type = request.form.get('modbus_register_type')
        modbus_register_address = request.form.get('modbus_register_address') or None
        modbus_data_type = request.form.get('modbus_data_type')
        modbus_byte_order = request.form.get('modbus_byte_order')
        modbus_scaling = request.form.get('modbus_scaling')
        modbus_units = request.form.get('modbus_units')
        modbus_offset = request.form.get('modbus_offset')
        modbus_function_code = request.form.get('modbus_function_code')
        
        # Get MQTT fields
        mqtt_broker = request.form.get('mqtt_broker')
        mqtt_port = request.form.get('mqtt_port') or None
        mqtt_topic = request.form.get('mqtt_topic')
        mqtt_username = request.form.get('mqtt_username')
        mqtt_password = request.form.get('mqtt_password')
        mqtt_qos = request.form.get('mqtt_qos') or 0
        
        if not all([code, description, type, data_source_type]):
            flash('All required fields must be filled.', 'danger')
        else:
            conn = psycopg2.connect(**DB_CONFIG)
            c = conn.cursor()
            try:
                c.execute('''INSERT INTO diagnostic_codes 
                    (code, description, type, state, last_failure, history_count, room_id,
                    data_source_type, modbus_ip, modbus_port, modbus_unit_id, modbus_register_type,
                    modbus_register_address, modbus_data_type, modbus_byte_order,
                    modbus_scaling, modbus_units, modbus_offset, modbus_function_code,
                    mqtt_broker, mqtt_port, mqtt_topic, mqtt_username, mqtt_password, mqtt_qos,
                    enabled)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (code, description, type, 'No Status', '', 0, room_id,
                    data_source_type, modbus_ip, modbus_port, modbus_unit_id, modbus_register_type,
                    modbus_register_address, modbus_data_type, modbus_byte_order,
                    modbus_scaling, modbus_units, modbus_offset, modbus_function_code,
                    mqtt_broker, mqtt_port, mqtt_topic, mqtt_username, mqtt_password, mqtt_qos,
                    0))
                conn.commit()
                flash('Diagnostic code added successfully!', 'success')
                return redirect(url_for('diagnostic_codes'))
            except psycopg2.IntegrityError:
                flash('Code already exists.', 'danger')
            finally:
                conn.close()
    
    rooms = get_rooms()
    return render_template('add_diagnostic_code.html', rooms=rooms)

@app.route('/edit_diagnostic_code/<int:code_id>', methods=['GET', 'POST'])
def edit_diagnostic_code(code_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    
    if request.method == 'POST':
        code = request.form['code']
        description = request.form['description']
        type = request.form['type']
        data_source_type = request.form['data_source_type']
        room_id = request.form.get('room_id') or None
        
        enabled = 1 if request.form.get('enabled') == 'on' else 0
        
        # Get current enabled status to check if we're enabling for the first time
        c.execute('SELECT enabled FROM diagnostic_codes WHERE id = %s', (code_id,))
        current_enabled = c.fetchone()
        was_enabled = current_enabled[0] if current_enabled else False
        
        # Set enabled_at timestamp if we're enabling for the first time
        enabled_at = None
        if enabled and not was_enabled:
            try:
                enabled_at = datetime.now(ZoneInfo('America/New_York'))
            except Exception:
                import pytz
                enabled_at = datetime.now(pytz.timezone('America/New_York'))
        
        # Get Modbus fields
        modbus_ip = request.form.get('modbus_ip')
        modbus_port = request.form.get('modbus_port') or None
        modbus_unit_id = request.form.get('modbus_unit_id') or None
        modbus_register_type = request.form.get('modbus_register_type')
        modbus_register_address = request.form.get('modbus_register_address') or None
        modbus_data_type = request.form.get('modbus_data_type')
        modbus_byte_order = request.form.get('modbus_byte_order')
        modbus_scaling = request.form.get('modbus_scaling')
        modbus_units = request.form.get('modbus_units')
        modbus_offset = request.form.get('modbus_offset')
        modbus_function_code = request.form.get('modbus_function_code')
        
        # Get MQTT fields
        mqtt_broker = request.form.get('mqtt_broker')
        mqtt_port = request.form.get('mqtt_port') or None
        mqtt_topic = request.form.get('mqtt_topic')
        mqtt_username = request.form.get('mqtt_username')
        mqtt_password = request.form.get('mqtt_password')
        mqtt_qos = request.form.get('mqtt_qos') or 0
        
        if not all([code, description, type, data_source_type]):
            flash('All required fields must be filled.', 'danger')
        else:
            # Check for uniqueness of code (excluding current record)
            c.execute('SELECT id FROM diagnostic_codes WHERE code = %s AND id != %s', (code, code_id))
            if c.fetchone():
                flash('Code already exists.', 'danger')
            else:
                try:
                    if enabled_at:
                        # Update with enabled_at timestamp
                        c.execute('''UPDATE diagnostic_codes SET 
                            code=%s, description=%s, type=%s, data_source_type=%s, room_id=%s,
                            modbus_ip=%s, modbus_port=%s, modbus_unit_id=%s, modbus_register_type=%s,
                            modbus_register_address=%s, modbus_data_type=%s, modbus_byte_order=%s,
                            modbus_scaling=%s, modbus_units=%s, modbus_offset=%s, modbus_function_code=%s,
                            mqtt_broker=%s, mqtt_port=%s, mqtt_topic=%s, mqtt_username=%s,
                            mqtt_password=%s, mqtt_qos=%s, enabled=%s, enabled_at=%s
                            WHERE id=%s''',
                            (code, description, type, data_source_type, room_id,
                            modbus_ip, modbus_port, modbus_unit_id, modbus_register_type,
                            modbus_register_address, modbus_data_type, modbus_byte_order,
                            modbus_scaling, modbus_units, modbus_offset, modbus_function_code,
                            mqtt_broker, mqtt_port, mqtt_topic, mqtt_username,
                            mqtt_password, mqtt_qos, enabled, enabled_at, code_id))
                    else:
                        # Update without changing enabled_at
                        c.execute('''UPDATE diagnostic_codes SET 
                            code=%s, description=%s, type=%s, data_source_type=%s, room_id=%s,
                            modbus_ip=%s, modbus_port=%s, modbus_unit_id=%s, modbus_register_type=%s,
                            modbus_register_address=%s, modbus_data_type=%s, modbus_byte_order=%s,
                            modbus_scaling=%s, modbus_units=%s, modbus_offset=%s, modbus_function_code=%s,
                            mqtt_broker=%s, mqtt_port=%s, mqtt_topic=%s, mqtt_username=%s,
                            mqtt_password=%s, mqtt_qos=%s, enabled=%s
                            WHERE id=%s''',
                            (code, description, type, data_source_type, room_id,
                            modbus_ip, modbus_port, modbus_unit_id, modbus_register_type,
                            modbus_register_address, modbus_data_type, modbus_byte_order,
                            modbus_scaling, modbus_units, modbus_offset, modbus_function_code,
                            mqtt_broker, mqtt_port, mqtt_topic, mqtt_username,
                            mqtt_password, mqtt_qos, enabled, code_id))
                    conn.commit()
                    flash('Diagnostic code updated successfully!', 'success')
                    return redirect(url_for('diagnostic_codes'))
                except psycopg2.IntegrityError:
                    flash('Code already exists.', 'danger')
    
    c.execute('SELECT * FROM diagnostic_codes WHERE id=%s', (code_id,))
    code = c.fetchone()
    conn.close()
    
    if code is None:
        flash('Diagnostic code not found.', 'danger')
        return redirect(url_for('diagnostic_codes'))
        
    rooms = get_rooms()
    return render_template('edit_diagnostic_code.html', code=code, rooms=rooms)

@app.route('/delete_diagnostic_code/<int:code_id>', methods=['POST'])
def delete_diagnostic_code(code_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('DELETE FROM diagnostic_codes WHERE id=%s', (code_id,))
    conn.commit()
    conn.close()
    flash('Diagnostic code deleted successfully!', 'success')
    return redirect(url_for('diagnostic_codes'))

@app.route('/toggle_diagnostic_code/<int:code_id>', methods=['POST'])
def toggle_diagnostic_code(code_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Check if this is a request to enable or disable
    action = request.form.get('action', 'toggle')
    
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    
    if action == 'enable':
        # This will be handled by the frontend popup and API call
        # Just redirect back to the diagnostic codes page
        conn.close()
        return redirect(url_for('diagnostic_codes'))
    elif action == 'disable':
        # Clear diagnostic parameters and disable the code
        c.execute('''
            UPDATE diagnostic_codes 
            SET start_value = NULL, target_value = NULL, threshold = NULL, 
                time_to_achieve = NULL, enabled = 0, enabled_at = NULL
            WHERE id = %s
        ''', (code_id,))
        conn.commit()
        flash('Diagnostic code disabled and parameters cleared.', 'info')
    else:
        # Legacy toggle behavior - check current status
        c.execute('SELECT enabled FROM diagnostic_codes WHERE id=%s', (code_id,))
        current = c.fetchone()
        if current:
            if current[0]:  # Currently enabled, so disable
                c.execute('''
                    UPDATE diagnostic_codes 
                    SET start_value = NULL, target_value = NULL, threshold = NULL, 
                        time_to_achieve = NULL, enabled = 0, enabled_at = NULL
                    WHERE id = %s
                ''', (code_id,))
                flash('Diagnostic code disabled and parameters cleared.', 'info')
            else:  # Currently disabled, redirect to enable via popup
                conn.close()
                return redirect(url_for('diagnostic_codes'))
    
    conn.close()
    return redirect(url_for('diagnostic_codes'))

def get_humidity_codes():
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('''
        SELECT code, description, state, last_failure, history_count, type,
               modbus_units, current_value, last_read_time 
        FROM diagnostic_codes 
        WHERE type=%s AND enabled=1
    ''', ('Humidity',))
    codes = c.fetchall()
    conn.close()
    # Format last_read_time
    formatted_codes = []
    for code in codes:
        code = list(code)
        code[8] = format_datetime(code[8])
        formatted_codes.append(tuple(code))
    return formatted_codes

def get_temp_codes():
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('''
        SELECT code, description, state, last_failure, history_count, type,
               modbus_units, current_value, last_read_time 
        FROM diagnostic_codes 
        WHERE type=%s AND enabled=1
    ''', ('Temperature',))
    codes = c.fetchall()
    conn.close()
    # Format last_read_time
    formatted_codes = []
    for code in codes:
        code = list(code)
        code[8] = format_datetime(code[8])
        formatted_codes.append(tuple(code))
    return formatted_codes

def get_notifications():
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('''
        SELECT code, description, state, last_failure, current_value, modbus_units 
        FROM diagnostic_codes 
        WHERE state IN (%s, %s) AND enabled=1
    ''', ('No Status', 'Fail'))
    notifications = c.fetchall()
    conn.close()
    return notifications

def get_contact_stats():
    """Get contact statistics"""
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM contacts')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM contacts WHERE enable_email = 1')
    email_enabled = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM contacts WHERE enable_sms = 1')
    sms_enabled = c.fetchone()[0]
    conn.close()
    return total, email_enabled, sms_enabled

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/diagnostics')
@login_required
def get_diagnostics():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        c = conn.cursor()
        
        # Fetch enabled diagnostic codes with room information
        c.execute('''
            SELECT dc.code, dc.description, dc.state, dc.last_failure, dc.history_count, 
                   dc.type, dc.modbus_units, dc.current_value, dc.last_read_time,
                   r.name as room_name, r.id as room_id, dc.fault_type
            FROM diagnostic_codes dc
            LEFT JOIN rooms r ON dc.room_id = r.id
            WHERE dc.enabled=1
            ORDER BY r.name NULLS FIRST, dc.type, dc.code
        ''')
        all_codes = c.fetchall()
        
        # Group codes by room
        codes_by_room = {}
        for code in all_codes:
            room_name = code[9] if code[9] else 'Unassigned'
            if room_name not in codes_by_room:
                codes_by_room[room_name] = {'temp': [], 'humidity': [], 'room_id': code[10]}
            
            if code[5] == 'Temperature':
                codes_by_room[room_name]['temp'].append(code)
            elif code[5] == 'Humidity':
                codes_by_room[room_name]['humidity'].append(code)
        
        # Get notifications
        notifications = [code for code in all_codes if code[2] in ('No Status', 'Fail')]
        
        conn.close()
        
        # Get contact statistics
        total_contacts, email_enabled, sms_enabled = get_contact_stats()
        
        return jsonify({
            'codes_by_room': codes_by_room,
            'notifications': notifications,
            'contact_stats': {
                'total': total_contacts,
                'email_enabled': email_enabled,
                'sms_enabled': sms_enabled
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset_history', methods=['POST'])
@login_required
def reset_history():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        c = conn.cursor()
        c.execute('''
            UPDATE diagnostic_codes 
            SET history_count = 0,
                last_failure = NULL,
                state = %s
            WHERE enabled = 1
        ''', ('No Status',))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'History reset successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/read_now', methods=['POST'])
@login_required
def trigger_read_now():
    try:
        # Import here to avoid circular imports
        from read_modbus_data import main as read_modbus_main
        
        # Get room_id from request data
        data = request.get_json()
        room_id = data.get('room_id') if data else None
        
        # Convert room_id to int if it's not None and not 'all'
        if room_id and room_id != 'all':
            try:
                room_id = int(room_id)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'Invalid room_id'
                }), 400
        
        # If room_id is 'all' or None, set it to None to read all rooms
        if room_id == 'all':
            room_id = None
        
        # Run Modbus read for specific room or all rooms
        read_modbus_main(room_id)
        
        return jsonify({
            'success': True,
            'message': f'Data read triggered successfully for {"all rooms" if room_id is None else f"room {room_id}"}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/read_live_modbus/<int:code_id>', methods=['POST'])
@login_required
def read_live_modbus_value(code_id):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        c = conn.cursor()
        
        # Get the diagnostic code configuration
        c.execute('''
            SELECT data_source_type, modbus_ip, modbus_port, modbus_unit_id, 
                   modbus_register_type, modbus_register_address, modbus_data_type,
                   modbus_byte_order, modbus_scaling, modbus_units, modbus_offset,
                   modbus_function_code
            FROM diagnostic_codes WHERE id = %s
        ''', (code_id,))
        
        code_config = c.fetchone()
        conn.close()
        
        if not code_config:
            return jsonify({'success': False, 'error': 'Diagnostic code not found'}), 404
        
        if code_config[0] != 'modbus':
            return jsonify({'success': False, 'error': 'This diagnostic code is not configured for Modbus'}), 400
        
        # Import and use the modbus reading function
        from read_modbus_data import read_single_modbus_value
        
        try:
            value = read_single_modbus_value(
                ip=code_config[1],
                port=code_config[2],
                unit_id=code_config[3],
                register_type=code_config[4],
                register_address=code_config[5],
                data_type=code_config[6],
                byte_order=code_config[7],
                scaling=code_config[8],
                units=code_config[9],
                offset=code_config[10],
                function_code=code_config[11]
            )
            
            return jsonify({
                'success': True,
                'value': value,
                'units': code_config[9] or ''
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to read Modbus value: {str(e)}'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update_diagnostic_params/<int:code_id>', methods=['POST'])
@login_required
def update_diagnostic_params(code_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        start_value = data.get('start_value')
        target_value = data.get('target_value')
        threshold = data.get('threshold')
        time_to_achieve = data.get('time_to_achieve')
        if None in [start_value, target_value, threshold, time_to_achieve]:
            return jsonify({'success': False, 'error': 'All parameters are required'}), 400
        conn = psycopg2.connect(**DB_CONFIG)
        c = conn.cursor()
        # Get current time in America/New_York timezone
        try:
            now_est = datetime.now(ZoneInfo('America/New_York'))
        except Exception:
            import pytz
            now_est = datetime.now(pytz.timezone('America/New_York'))
        # Update the diagnostic parameters and enable the code (no upper/lower limit)
        c.execute('''
            UPDATE diagnostic_codes 
            SET start_value = %s, target_value = %s, threshold = %s, 
                time_to_achieve = %s, enabled = 1, enabled_at = %s
            WHERE id = %s
        ''', (start_value, target_value, threshold, time_to_achieve, now_est, code_id))
        if c.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Diagnostic code not found'}), 404
        conn.commit()
        conn.close()
        return jsonify({
            'success': True,
            'message': 'Diagnostic parameters updated and code enabled successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clear_diagnostic_params/<int:code_id>', methods=['POST'])
@login_required
def clear_diagnostic_params(code_id):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        c = conn.cursor()
        
        # Clear diagnostic parameters and disable the code
        c.execute('''
            UPDATE diagnostic_codes 
            SET start_value = NULL, target_value = NULL, threshold = NULL, 
                time_to_achieve = NULL, enabled = 0, enabled_at = NULL
            WHERE id = %s
        ''', (code_id,))
        
        if c.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Diagnostic code not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Diagnostic parameters cleared and code disabled successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/status_log')
def status_log():
    return render_template('status_log.html')

def format_datetime(dt):
    if not dt:
        return ''
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime('%d %B, %Y %H:%M:%S')

@app.route('/api/status_log')
def api_status_log():
    try:
        code = request.args.get('code', '').strip()
        state = request.args.get('state', '').strip()
        dtype = request.args.get('type', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()

        query = 'SELECT code, description, state, last_failure, history_count, type, value, event_time FROM logs WHERE 1=1'
        params = []
        if code:
            query += ' AND code ILIKE %s'
            params.append(f'%{code}%')
        if state:
            query += ' AND state = %s'
            params.append(state)
        if dtype:
            query += ' AND type = %s'
            params.append(dtype)
        if start_date:
            query += ' AND event_time >= %s'
            params.append(start_date)
        if end_date:
            query += ' AND event_time <= %s'
            params.append(end_date)
        query += ' ORDER BY event_time DESC LIMIT 1000'

        conn = psycopg2.connect(**DB_CONFIG)
        c = conn.cursor()
        c.execute(query, tuple(params))
        rows = c.fetchall()
        conn.close()
        logs = [
            {
                'code': r[0],
                'description': r[1],
                'state': r[2],
                'last_failure': format_datetime(r[3]),
                'history_count': r[4],
                'type': r[5],
                'value': r[6],
                'event_time': (r[7] - timedelta(hours=4)).strftime('%Y-%m-%dT%H:%M:%S') if r[7] else ''
            } for r in rows
        ]
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/toggle_all_contacts', methods=['POST'])
def toggle_all_contacts():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    action = request.form.get('action')
    if action not in ['enable', 'disable']:
        flash('Invalid action', 'danger')
        return redirect(url_for('contacts'))
    
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    try:
        # Update all contacts to the specified state
        c.execute('UPDATE contacts SET enable_sms = %s, enable_email = %s', (1 if action == 'enable' else 0, 1 if action == 'enable' else 0))
        conn.commit()
        flash(f'All contacts have been {action}d successfully', 'success')
    except Exception as e:
        flash(f'Error updating contacts: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('contacts'))

@app.route('/duplicate_diagnostic_code/<int:code_id>', methods=['POST'])
@login_required
def duplicate_diagnostic_code(code_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        c = conn.cursor()
        # Fetch all columns except id
        c.execute('SELECT * FROM diagnostic_codes WHERE id = %s', (code_id,))
        original = c.fetchone()
        if not original:
            flash('Diagnostic code not found.', 'danger')
            return redirect(url_for('diagnostic_codes'))
        # Get column names
        c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'diagnostic_codes' ORDER BY ordinal_position")
        columns = [row[0] for row in c.fetchall()]
        # Remove id column
        id_index = columns.index('id')
        columns_wo_id = columns[:id_index] + columns[id_index+1:]
        # Prepare new values
        original = list(original)
        # Remove id value
        del original[id_index]
        # Update code and description
        base_code = original[columns_wo_id.index('code')] + "_copy"
        new_code = base_code
        counter = 2
        while True:
            c.execute('SELECT 1 FROM diagnostic_codes WHERE code = %s', (new_code,))
            if not c.fetchone():
                break
            new_code = f"{base_code}{counter}"
            counter += 1
        original[columns_wo_id.index('code')] = new_code
        original[columns_wo_id.index('description')] += " (Copy)"
        # Set state to 'No Status', last_failure to '', history_count to 0
        if 'state' in columns_wo_id:
            original[columns_wo_id.index('state')] = 'No Status'
        if 'last_failure' in columns_wo_id:
            original[columns_wo_id.index('last_failure')] = ''
        if 'history_count' in columns_wo_id:
            original[columns_wo_id.index('history_count')] = 0
        # Insert new row
        placeholders = ', '.join(['%s'] * len(columns_wo_id))
        c.execute(f'''INSERT INTO diagnostic_codes ({', '.join(columns_wo_id)}) VALUES ({placeholders})''', tuple(original))
        conn.commit()
        flash('Diagnostic code duplicated successfully!', 'success')
    except psycopg2.IntegrityError:
        flash('A code with this name already exists.', 'danger')
    except Exception as e:
        flash(f'Error duplicating code: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('diagnostic_codes'))

@app.route('/reset_diagnostic_code/<int:code_id>', methods=['POST'])
@login_required
def reset_diagnostic_code(code_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        c = conn.cursor()
        c.execute('''
            UPDATE diagnostic_codes
            SET history_count = 0,
                last_failure = NULL,
                state = %s
            WHERE id = %s
        ''', ('No Status', code_id))
        conn.commit()
        conn.close()
        flash('Diagnostic code history reset successfully!', 'success')
    except Exception as e:
        flash(f'Error resetting code: {str(e)}', 'danger')
    return redirect(url_for('diagnostic_codes'))

@app.route('/api/last_error_event')
def api_last_error_event():
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('SELECT last_error_event FROM app_settings WHERE id = 1')
    result = c.fetchone()
    conn.close()
    return jsonify({'last_error_event': result[0] if result else None})

# --- Room Management Routes ---
@app.route('/rooms')
@login_required
def rooms():
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('SELECT id, name, description, created_at, refresh_time FROM rooms ORDER BY name')
    rooms = c.fetchall()
    conn.close()
    return render_template('rooms.html', rooms=rooms)

@app.route('/add_room', methods=['GET', 'POST'])
@login_required
def add_room():
    if request.method == 'POST':
        name = request.form['name'].strip()
        description = request.form['description'].strip()
        refresh_time = request.form.get('refresh_time')
        refresh_time = int(refresh_time) if refresh_time else None
        if not name:
            flash('Chamber name is required', 'danger')
            return render_template('add_room.html')
        conn = psycopg2.connect(**DB_CONFIG)
        c = conn.cursor()
        try:
            c.execute('INSERT INTO rooms (name, description, refresh_time) VALUES (%s, %s, %s)', (name, description, refresh_time))
            conn.commit()
            flash('Chamber added successfully', 'success')
            return redirect(url_for('rooms'))
        except psycopg2.IntegrityError:
            flash('Chamber name already exists', 'danger')
        except Exception as e:
            flash(f'Error adding chamber: {str(e)}', 'danger')
        finally:
            conn.close()
    return render_template('add_room.html')

@app.route('/edit_room/<int:room_id>', methods=['GET', 'POST'])
@login_required
def edit_room(room_id):
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        description = request.form['description'].strip()
        refresh_time = request.form.get('refresh_time')
        refresh_time = int(refresh_time) if refresh_time else None
        if not name:
            flash('Chamber name is required', 'danger')
            c.execute('SELECT name, description, refresh_time FROM rooms WHERE id = %s', (room_id,))
            room = c.fetchone()
            conn.close()
            return render_template('edit_room.html', room=room, room_id=room_id)
        try:
            c.execute('UPDATE rooms SET name = %s, description = %s, refresh_time = %s WHERE id = %s', (name, description, refresh_time, room_id))
            conn.commit()
            flash('Chamber updated successfully', 'success')
            return redirect(url_for('rooms'))
        except psycopg2.IntegrityError:
            flash('Chamber name already exists', 'danger')
        except Exception as e:
            flash(f'Error updating chamber: {str(e)}', 'danger')
        finally:
            conn.close()
    
    c.execute('SELECT name, description, refresh_time FROM rooms WHERE id = %s', (room_id,))
    room = c.fetchone()
    conn.close()
    
    if not room:
        flash('Chamber not found', 'danger')
        return redirect(url_for('rooms'))
    
    return render_template('edit_room.html', room=room, room_id=room_id)

@app.route('/delete_room/<int:room_id>', methods=['POST'])
@login_required
def delete_room(room_id):
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    
    # Check if room has associated diagnostic codes
    c.execute('SELECT COUNT(*) FROM diagnostic_codes WHERE room_id = %s', (room_id,))
    count = c.fetchone()[0]
    
    if count > 0:
        flash(f'Cannot delete room: {count} diagnostic code(s) are associated with this room', 'danger')
        conn.close()
        return redirect(url_for('rooms'))
    
    try:
        c.execute('DELETE FROM rooms WHERE id = %s', (room_id,))
        conn.commit()
        flash('Room deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting room: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('rooms'))

# --- Helper function to get rooms for dropdowns ---
def get_rooms():
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('SELECT id, name, refresh_time FROM rooms ORDER BY name')
    rooms = c.fetchall()
    conn.close()
    return rooms

@app.route('/data_log')
def data_log():
    return render_template('data_log.html')

@app.route('/api/data_log')
def api_data_log():
    code = request.args.get('code', '').strip()
    data_source = request.args.get('data_source', '').strip()
    query = 'SELECT code, value, data_source, event_time FROM data_logs WHERE 1=1'
    params = []
    if code:
        query += ' AND code = %s'
        params.append(code)
    if data_source:
        query += ' AND data_source = %s'
        params.append(data_source)
    query += ' ORDER BY event_time DESC LIMIT 500'
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute(query, tuple(params))
    logs = [
        {
            'code': row[0],
            'value': row[1],
            'data_source': row[2],
            'event_time': (row[3] - timedelta(hours=4)).strftime('%Y-%m-%dT%H:%M:%S') if row[3] else ''
        }
        for row in c.fetchall()
    ]
    conn.close()
    return jsonify({'logs': logs})

@app.route('/api/diagnostic_graph/<code>')
@login_required
def diagnostic_graph(code):
    """Get diagnostic graph data for a specific code"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        c = conn.cursor()
        
        # Get diagnostic parameters
        c.execute('''
            SELECT start_value, target_value, threshold, time_to_achieve, enabled_at
            FROM diagnostic_codes 
            WHERE code = %s AND enabled = 1
        ''', (code,))
        diagnostic = c.fetchone()
        
        if not diagnostic:
            return jsonify({'success': False, 'error': 'Diagnostic not found or not enabled'})
        
        start_value, target_value, threshold, time_to_achieve, enabled_at = diagnostic
        
        # Get data points from data_logs
        c.execute('''
            SELECT value, event_time 
            FROM data_logs 
            WHERE code = %s 
            ORDER BY event_time ASC
        ''', (code,))
        data_points = c.fetchall()
        
        conn.close()
        
        # Format data points
        formatted_points = []
        for point in data_points:
            formatted_points.append({
                'value': point[0],
                'timestamp': point[1].isoformat() if point[1] else None
            })
        
        return jsonify({
            'success': True,
            'data': {
                'start_value': start_value,
                'target_value': target_value,
                'threshold': threshold,
                'time_to_achieve': time_to_achieve,
                'enabled_time': enabled_at.isoformat() if enabled_at else None,
                'data_points': formatted_points
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bulk_update_diagnostic_params', methods=['POST'])
@login_required
def bulk_update_diagnostic_params():
    try:
        data = request.get_json()
        if not data or 'codes' not in data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        codes = data['codes']
        conn = psycopg2.connect(**DB_CONFIG)
        c = conn.cursor()
        try:
            now_est = datetime.now(ZoneInfo('America/New_York'))
        except Exception:
            import pytz
            now_est = datetime.now(pytz.timezone('America/New_York'))
        for code in codes:
            code_id = code.get('code_id')
            start_value = code.get('start_value')
            target_value = code.get('target_value')
            threshold = code.get('threshold')
            time_to_achieve = code.get('time_to_achieve')
            if None in [code_id, start_value, target_value, threshold, time_to_achieve]:
                continue  # skip incomplete
            c.execute('''
                UPDATE diagnostic_codes 
                SET start_value = %s, target_value = %s, threshold = %s, 
                    time_to_achieve = %s, enabled = 1, enabled_at = %s
                WHERE id = %s
            ''', (start_value, target_value, threshold, time_to_achieve, now_est, code_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Bulk diagnostic parameters updated and codes enabled successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bulk_delete_diagnostic_codes', methods=['POST'])
@login_required
def bulk_delete_diagnostic_codes():
    try:
        data = request.get_json()
        if not data or 'code_ids' not in data:
            return jsonify({'success': False, 'error': 'No code_ids provided'}), 400
        code_ids = data['code_ids']
        if not isinstance(code_ids, list) or not code_ids:
            return jsonify({'success': False, 'error': 'Invalid code_ids'}), 400
        conn = psycopg2.connect(**DB_CONFIG)
        c = conn.cursor()
        c.execute('DELETE FROM diagnostic_codes WHERE id = ANY(%s)', (code_ids,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Selected diagnostic codes deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bulk_disable_diagnostic_codes', methods=['POST'])
@login_required
def bulk_disable_diagnostic_codes():
    try:
        data = request.get_json()
        if not data or 'code_ids' not in data:
            return jsonify({'success': False, 'error': 'No code_ids provided'}), 400
        code_ids = data['code_ids']
        if not isinstance(code_ids, list) or not code_ids:
            return jsonify({'success': False, 'error': 'Invalid code_ids'}), 400
        code_ids = list(map(int, code_ids))
        conn = psycopg2.connect(**DB_CONFIG)
        c = conn.cursor()
        c.execute('''
            UPDATE diagnostic_codes
            SET enabled = 0, enabled_at = NULL, start_value = NULL, target_value = NULL, threshold = NULL, time_to_achieve = NULL
            WHERE id = ANY(%s)
        ''', (code_ids,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Selected diagnostic codes disabled successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 