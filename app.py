from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import psycopg2
import os
from werkzeug.security import generate_password_hash, check_password_hash
import re
from functools import wraps
from dotenv import load_dotenv
import datetime

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
            refresh_time INTEGER DEFAULT 5,
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
            last_read_time TIMESTAMP
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
    
    # Check if default user exists
    c.execute('SELECT 1 FROM users WHERE username = %s', ('user',))
    if not c.fetchone():
        c.execute('INSERT INTO users (username, password, name) VALUES (%s, %s, %s)',
                  ('user', generate_password_hash('password'), 'Admin'))
    
    # Check if default refresh time exists
    c.execute('SELECT 1 FROM app_settings WHERE id = 1')
    if not c.fetchone():
        c.execute('INSERT INTO app_settings (id, refresh_time, last_error_event) VALUES (1, 5, NULL)')
    
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
    # Fetch enabled diagnostic codes for temperature and humidity
    c.execute('SELECT code, description, state, last_failure, history_count, type FROM diagnostic_codes WHERE enabled=1')
    all_codes = c.fetchall()
    temp_codes = [code for code in all_codes if code[5] == 'Temperature']
    humidity_codes = [code for code in all_codes if code[5] == 'Humidity']
    # Notification center: codes with state 'No Status' or 'Fail'
    notifications = [code for code in all_codes if code[2] in ('No Status', 'Fail')]
    conn.close()
    
    # Get contact statistics
    total_contacts, email_enabled, sms_enabled = get_contact_stats()
    
    return render_template('dashboard.html', 
                         user=name, 
                         temp_codes=temp_codes, 
                         humidity_codes=humidity_codes, 
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
        # Create search pattern for SQL LIKE
        search_pattern = f'%{search_query}%'
        
        # Search in temperature codes
        c.execute('''
            SELECT * FROM diagnostic_codes 
            WHERE type = 'Temperature'
            AND (
                code ILIKE %s OR
                description ILIKE %s OR
                state ILIKE %s OR
                last_failure ILIKE %s OR
                modbus_ip ILIKE %s OR
                modbus_register_type ILIKE %s OR
                modbus_data_type ILIKE %s OR
                modbus_byte_order ILIKE %s OR
                modbus_units ILIKE %s
            )
        ''', (search_pattern,) * 9)
        temp_codes = c.fetchall()
        
        # Search in humidity codes
        c.execute('''
            SELECT * FROM diagnostic_codes 
            WHERE type = 'Humidity'
            AND (
                code ILIKE %s OR
                description ILIKE %s OR
                state ILIKE %s OR
                last_failure ILIKE %s OR
                modbus_ip ILIKE %s OR
                modbus_register_type ILIKE %s OR
                modbus_data_type ILIKE %s OR
                modbus_byte_order ILIKE %s OR
                modbus_units ILIKE %s
            )
        ''', (search_pattern,) * 9)
        humidity_codes = c.fetchall()
    else:
        # If no search query, get all codes
        c.execute('SELECT * FROM diagnostic_codes WHERE type = %s', ('Temperature',))
        temp_codes = c.fetchall()
        c.execute('SELECT * FROM diagnostic_codes WHERE type = %s', ('Humidity',))
        humidity_codes = c.fetchall()
    
    conn.close()
    return render_template('diagnostic_codes.html', 
                         temp_codes=temp_codes, 
                         humidity_codes=humidity_codes,
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
        
        # Get common fields
        upper_limit = request.form['upper_limit']
        lower_limit = request.form['lower_limit']
        
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
        
        if not all([code, description, type, data_source_type, upper_limit, lower_limit]):
            flash('All required fields must be filled.', 'danger')
        else:
            conn = psycopg2.connect(**DB_CONFIG)
            c = conn.cursor()
            try:
                c.execute('''INSERT INTO diagnostic_codes 
                    (code, description, type, state, last_failure, history_count,
                    data_source_type, modbus_ip, modbus_port, modbus_unit_id, modbus_register_type,
                    modbus_register_address, modbus_data_type, modbus_byte_order,
                    modbus_scaling, modbus_units, modbus_offset, modbus_function_code,
                    mqtt_broker, mqtt_port, mqtt_topic, mqtt_username, mqtt_password, mqtt_qos,
                    upper_limit, lower_limit, enabled)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (code, description, type, 'No Status', '', 0,
                    data_source_type, modbus_ip, modbus_port, modbus_unit_id, modbus_register_type,
                    modbus_register_address, modbus_data_type, modbus_byte_order,
                    modbus_scaling, modbus_units, modbus_offset, modbus_function_code,
                    mqtt_broker, mqtt_port, mqtt_topic, mqtt_username, mqtt_password, mqtt_qos,
                    upper_limit, lower_limit, 1))
                conn.commit()
                flash('Diagnostic code added successfully!', 'success')
                return redirect(url_for('diagnostic_codes'))
            except psycopg2.IntegrityError:
                flash('Code already exists.', 'danger')
            finally:
                conn.close()
    return render_template('add_diagnostic_code.html')

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
        
        # Get common fields
        upper_limit = request.form['upper_limit']
        lower_limit = request.form['lower_limit']
        enabled = 1 if request.form.get('enabled') == 'on' else 0
        
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
        
        if not all([code, description, type, data_source_type, upper_limit, lower_limit]):
            flash('All required fields must be filled.', 'danger')
        else:
            # Check for uniqueness of code (excluding current record)
            c.execute('SELECT id FROM diagnostic_codes WHERE code = %s AND id != %s', (code, code_id))
            if c.fetchone():
                flash('Code already exists.', 'danger')
            else:
                try:
                    c.execute('''UPDATE diagnostic_codes SET 
                        code=%s, description=%s, type=%s, data_source_type=%s,
                        modbus_ip=%s, modbus_port=%s, modbus_unit_id=%s, modbus_register_type=%s,
                        modbus_register_address=%s, modbus_data_type=%s, modbus_byte_order=%s,
                        modbus_scaling=%s, modbus_units=%s, modbus_offset=%s, modbus_function_code=%s,
                        mqtt_broker=%s, mqtt_port=%s, mqtt_topic=%s, mqtt_username=%s,
                        mqtt_password=%s, mqtt_qos=%s, upper_limit=%s, lower_limit=%s, enabled=%s
                        WHERE id=%s''',
                        (code, description, type, data_source_type,
                        modbus_ip, modbus_port, modbus_unit_id, modbus_register_type,
                        modbus_register_address, modbus_data_type, modbus_byte_order,
                        modbus_scaling, modbus_units, modbus_offset, modbus_function_code,
                        mqtt_broker, mqtt_port, mqtt_topic, mqtt_username,
                        mqtt_password, mqtt_qos, upper_limit, lower_limit, enabled, code_id))
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
        
    return render_template('edit_diagnostic_code.html', code=code)

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
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('SELECT enabled FROM diagnostic_codes WHERE id=%s', (code_id,))
    current = c.fetchone()
    if current:
        new_status = 0 if current[0] else 1
        c.execute('UPDATE diagnostic_codes SET enabled=%s WHERE id=%s', (new_status, code_id))
        conn.commit()
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
        # Get humidity codes
        humidity_codes = get_humidity_codes()
        # Get temperature codes
        temp_codes = get_temp_codes()
        # Get notifications
        notifications = get_notifications()
        # Get contact statistics
        total_contacts, email_enabled, sms_enabled = get_contact_stats()
        
        return jsonify({
            'humidity_codes': humidity_codes,
            'temp_codes': temp_codes,
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

@app.route('/api/refresh_time', methods=['GET', 'POST'])
@login_required
def manage_refresh_time():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute('SELECT refresh_time, last_updated FROM app_settings WHERE id = 1')
        result = c.fetchone()
        conn.close()
        if result:
            return jsonify({
                'refresh_time': result[0],
                'last_updated': result[1]
            })
        return jsonify({'error': 'Settings not found'}), 404
    
    elif request.method == 'POST':
        try:
            new_time = int(request.json.get('refresh_time', 5))
            if new_time < 1:
                return jsonify({'error': 'Refresh time must be at least 1 second'}), 400
            
            c.execute('''
                UPDATE app_settings 
                SET refresh_time = %s, last_updated = CURRENT_TIMESTAMP 
                WHERE id = 1
            ''', (new_time,))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'refresh_time': new_time})
        except ValueError:
            return jsonify({'error': 'Invalid refresh time value'}), 400

@app.route('/api/read_now', methods=['POST'])
@login_required
def trigger_read_now():
    try:
        # Import here to avoid circular imports
        from read_modbus_data import main as read_modbus_main
        
        
        # Run both Modbus and MQTT reads
        read_modbus_main()
        
        
        return jsonify({
            'success': True,
            'message': 'Data read triggered successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/logs')
@login_required
def logs():
    return render_template('logs.html')

def format_datetime(dt):
    if not dt:
        return ''
    if isinstance(dt, str):
        try:
            dt = datetime.datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime('%d %B, %Y %H:%M:%S')

@app.route('/api/logs')
@login_required
def api_logs():
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
            'event_time': format_datetime(r[7]) if r[7] else ''
        } for r in rows
    ]
    return jsonify({'logs': logs})

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
    
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    
    try:
        # Get the original code
        c.execute('''
            SELECT code, description, type, data_source_type,
                   modbus_ip, modbus_port, modbus_unit_id,
                   modbus_register_type, modbus_register_address, modbus_data_type,
                   modbus_byte_order, modbus_scaling, modbus_units, modbus_offset,
                   modbus_function_code, mqtt_broker, mqtt_port, mqtt_topic,
                   mqtt_username, mqtt_password, mqtt_qos,
                   upper_limit, lower_limit
            FROM diagnostic_codes 
            WHERE id = %s
        ''', (code_id,))
        original = c.fetchone()
        
        if not original:
            flash('Diagnostic code not found.', 'danger')
            return redirect(url_for('diagnostic_codes'))
        
        # Create a new code with a unique _copy suffix
        base_code = original[0] + "_copy"
        new_code = base_code
        counter = 2
        while True:
            c.execute('SELECT 1 FROM diagnostic_codes WHERE code = %s', (new_code,))
            if not c.fetchone():
                break
            new_code = f"{base_code}{counter}"
            counter += 1
        new_description = original[1] + " (Copy)"
        
        # Insert the duplicated code
        c.execute('''
            INSERT INTO diagnostic_codes 
            (code, description, type, data_source_type, state, last_failure, history_count,
             modbus_ip, modbus_port, modbus_unit_id, modbus_register_type,
             modbus_register_address, modbus_data_type, modbus_byte_order,
             modbus_scaling, modbus_units, modbus_offset, modbus_function_code,
             mqtt_broker, mqtt_port, mqtt_topic, mqtt_username, mqtt_password, mqtt_qos,
             upper_limit, lower_limit, enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (new_code, new_description, original[2], original[3], 'No Status', '', 0,
              original[4], original[5], original[6], original[7], original[8],
              original[9], original[10], original[11], original[12], original[13],
              original[14], original[15], original[16], original[17], original[18],
              original[19], original[20], original[21], original[22], 1))
        
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
    row = c.fetchone()
    conn.close()
    return jsonify({'last_error_event': row[0] if row else None})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 