from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
import re
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production
DB_PATH = 'diagnostics.db'

# --- DB Initialization ---
def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE users (username TEXT PRIMARY KEY, password TEXT, name TEXT)''')
        c.execute('''CREATE TABLE contacts (id INTEGER PRIMARY KEY AUTOINCREMENT, fullname TEXT, phone TEXT UNIQUE, email TEXT UNIQUE)''')
        c.execute('''CREATE TABLE app_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            refresh_time INTEGER DEFAULT 5,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE diagnostic_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            description TEXT,
            type TEXT,
            state TEXT,
            last_failure TEXT,
            history_count INTEGER,
            modbus_ip TEXT,
            modbus_port INTEGER,
            modbus_unit_id INTEGER,
            modbus_register_type TEXT,
            modbus_register_address INTEGER,
            modbus_data_type TEXT,
            modbus_byte_order TEXT,
            modbus_scaling TEXT,
            modbus_units TEXT,
            modbus_offset TEXT,
            modbus_function_code TEXT,
            upper_limit REAL,
            lower_limit REAL,
            enabled INTEGER,
            current_value REAL,
            last_read_time TIMESTAMP
        )''')
        # Add default user
        c.execute('''INSERT INTO users (username, password, name) VALUES (?, ?, ?)''',
                  ('user', generate_password_hash('password'), 'Admin'))
        # Insert default refresh time
        c.execute('''INSERT INTO app_settings (id, refresh_time) VALUES (1, 5)''')
        conn.commit()
        conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS diagnostic_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            description TEXT,
            type TEXT,
            state TEXT,
            last_failure TEXT,
            history_count INTEGER,
            modbus_ip TEXT,
            modbus_port INTEGER,
            modbus_unit_id INTEGER,
            modbus_register_type TEXT,
            modbus_register_address INTEGER,
            modbus_data_type TEXT,
            modbus_byte_order TEXT,
            modbus_scaling TEXT,
            modbus_units TEXT,
            modbus_offset TEXT,
            modbus_function_code TEXT,
            upper_limit REAL,
            lower_limit REAL,
            enabled INTEGER,
            current_value REAL,
            last_read_time TIMESTAMP
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT,
            phone TEXT UNIQUE,
            email TEXT UNIQUE
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            refresh_time INTEGER DEFAULT 5,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # Insert default refresh time if not exists
        c.execute("INSERT OR IGNORE INTO app_settings (id, refresh_time) VALUES (1, 5)")
        conn.commit()
        conn.close()

init_db()

# --- Helper: Check login ---
def validate_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username=?', (username,))
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name FROM users WHERE username=?', (username,))
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
    return render_template('dashboard.html', user=name, temp_codes=temp_codes, humidity_codes=humidity_codes, notifications=notifications)

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
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            try:
                c.execute('INSERT INTO users (username, password, name) VALUES (?, ?, ?)',
                          (username, generate_password_hash(password), name))
                conn.commit()
                flash('User added successfully!', 'success')
            except sqlite3.IntegrityError:
                flash('Username already exists.', 'danger')
            finally:
                conn.close()
    return render_template('add_user.html')

@app.route('/contacts')
def contacts():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM contacts')
    contacts = c.fetchall()
    conn.close()
    return render_template('contacts.html', contacts=contacts)

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
        if not fullname or not phone or not email:
            flash('All fields are required.', 'danger')
        elif not is_valid_phone(phone):
            flash('Phone number must start with country code (e.g., +1) and be followed by exactly 10 digits.', 'danger')
        elif not is_valid_email(email):
            flash('Invalid email address format.', 'danger')
        else:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            # Check for existing phone or email
            c.execute('SELECT 1 FROM contacts WHERE phone=?', (phone,))
            if c.fetchone():
                flash('Phone number already exists.', 'danger')
            else:
                c.execute('SELECT 1 FROM contacts WHERE email=?', (email,))
                if c.fetchone():
                    flash('Email address already exists.', 'danger')
                else:
                    try:
                        c.execute('INSERT INTO contacts (fullname, phone, email) VALUES (?, ?, ?)',
                                  (fullname, phone, email))
                        conn.commit()
                        flash('Contact added successfully!', 'success')
                        conn.close()
                        return redirect(url_for('contacts'))
                    except sqlite3.IntegrityError:
                        flash('Duplicate entry.', 'danger')
            conn.close()
    return render_template('add_contact.html', fullname=fullname, phone=phone, email=email)

@app.route('/edit_contact/<int:contact_id>', methods=['GET', 'POST'])
def edit_contact(contact_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        fullname = request.form['fullname']
        phone = request.form['phone']
        email = request.form['email']
        if not fullname or not phone or not email:
            flash('All fields are required.', 'danger')
        else:
            c.execute('UPDATE contacts SET fullname=?, phone=?, email=? WHERE id=?',
                      (fullname, phone, email, contact_id))
            conn.commit()
            conn.close()
            flash('Contact updated successfully!', 'success')
            return redirect(url_for('contacts'))
    else:
        c.execute('SELECT * FROM contacts WHERE id=?', (contact_id,))
        contact = c.fetchone()
        conn.close()
        if not contact:
            flash('Contact not found.', 'danger')
            return redirect(url_for('contacts'))
        return render_template('edit_contact.html', contact=contact)

@app.route('/delete_contact/<int:contact_id>', methods=['POST'])
def delete_contact(contact_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM contacts WHERE id=?', (contact_id,))
    conn.commit()
    conn.close()
    flash('Contact deleted successfully!', 'success')
    return redirect(url_for('contacts'))

@app.route('/diagnostic_codes')
def diagnostic_codes():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '').strip()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if search_query:
        # Create search pattern for SQL LIKE
        search_pattern = f'%{search_query}%'
        
        # Search in temperature codes
        c.execute('''
            SELECT * FROM diagnostic_codes 
            WHERE type = "Temperature" 
            AND (
                code LIKE ? OR
                description LIKE ? OR
                state LIKE ? OR
                last_failure LIKE ? OR
                modbus_ip LIKE ? OR
                modbus_register_type LIKE ? OR
                modbus_data_type LIKE ? OR
                modbus_byte_order LIKE ? OR
                modbus_units LIKE ?
            )
        ''', (search_pattern,) * 9)
        temp_codes = c.fetchall()
        
        # Search in humidity codes
        c.execute('''
            SELECT * FROM diagnostic_codes 
            WHERE type = "Humidity" 
            AND (
                code LIKE ? OR
                description LIKE ? OR
                state LIKE ? OR
                last_failure LIKE ? OR
                modbus_ip LIKE ? OR
                modbus_register_type LIKE ? OR
                modbus_data_type LIKE ? OR
                modbus_byte_order LIKE ? OR
                modbus_units LIKE ?
            )
        ''', (search_pattern,) * 9)
        humidity_codes = c.fetchall()
    else:
        # If no search query, get all codes
        c.execute('SELECT * FROM diagnostic_codes WHERE type = "Temperature"')
        temp_codes = c.fetchall()
        c.execute('SELECT * FROM diagnostic_codes WHERE type = "Humidity"')
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
        modbus_ip = request.form['modbus_ip']
        modbus_port = request.form['modbus_port']
        modbus_unit_id = request.form['modbus_unit_id']
        modbus_register_type = request.form['modbus_register_type']
        modbus_register_address = request.form['modbus_register_address']
        modbus_data_type = request.form['modbus_data_type']
        modbus_byte_order = request.form['modbus_byte_order']
        modbus_scaling = request.form['modbus_scaling']
        modbus_units = request.form['modbus_units']
        modbus_offset = request.form['modbus_offset']
        modbus_function_code = request.form['modbus_function_code']
        upper_limit = request.form['upper_limit']
        lower_limit = request.form['lower_limit']
        
        if not all([code, description, type, modbus_ip, modbus_port, modbus_unit_id, 
                   modbus_register_type, modbus_register_address, modbus_data_type, 
                   modbus_byte_order, modbus_scaling, modbus_units, modbus_offset, 
                   modbus_function_code, upper_limit, lower_limit]):
            flash('All fields are required.', 'danger')
        else:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            try:
                c.execute('''INSERT INTO diagnostic_codes 
                    (code, description, type, state, last_failure, history_count,
                    modbus_ip, modbus_port, modbus_unit_id, modbus_register_type,
                    modbus_register_address, modbus_data_type, modbus_byte_order,
                    modbus_scaling, modbus_units, modbus_offset, modbus_function_code,
                    upper_limit, lower_limit, enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (code, description, type, 'No Status', '', 0,
                    modbus_ip, modbus_port, modbus_unit_id, modbus_register_type,
                    modbus_register_address, modbus_data_type, modbus_byte_order,
                    modbus_scaling, modbus_units, modbus_offset, modbus_function_code,
                    upper_limit, lower_limit, 1))
                conn.commit()
                flash('Diagnostic code added successfully!', 'success')
                return redirect(url_for('diagnostic_codes'))
            except sqlite3.IntegrityError:
                flash('Code already exists.', 'danger')
            finally:
                conn.close()
    return render_template('add_diagnostic_code.html')

@app.route('/edit_diagnostic_code/<int:code_id>', methods=['GET', 'POST'])
def edit_diagnostic_code(code_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if request.method == 'POST':
        code = request.form['code']
        description = request.form['description']
        type = request.form['type']
        modbus_ip = request.form['modbus_ip']
        modbus_port = request.form['modbus_port']
        modbus_unit_id = request.form['modbus_unit_id']
        modbus_register_type = request.form['modbus_register_type']
        modbus_register_address = request.form['modbus_register_address']
        modbus_data_type = request.form['modbus_data_type']
        modbus_byte_order = request.form['modbus_byte_order']
        modbus_scaling = request.form['modbus_scaling']
        modbus_units = request.form['modbus_units']
        modbus_offset = request.form['modbus_offset']
        modbus_function_code = request.form['modbus_function_code']
        upper_limit = request.form['upper_limit']
        lower_limit = request.form['lower_limit']
        enabled = 1 if request.form.get('enabled') == 'on' else 0
        
        if not all([code, description, type, modbus_ip, modbus_port, modbus_unit_id, 
                   modbus_register_type, modbus_register_address, modbus_data_type, 
                   modbus_byte_order, modbus_scaling, modbus_units, modbus_offset, 
                   modbus_function_code, upper_limit, lower_limit]):
            flash('All fields are required.', 'danger')
        else:
            try:
                c.execute('''UPDATE diagnostic_codes SET 
                    code=?, description=?, type=?, modbus_ip=?, modbus_port=?,
                    modbus_unit_id=?, modbus_register_type=?, modbus_register_address=?,
                    modbus_data_type=?, modbus_byte_order=?, modbus_scaling=?,
                    modbus_units=?, modbus_offset=?, modbus_function_code=?,
                    upper_limit=?, lower_limit=?, enabled=?
                    WHERE id=?''',
                    (code, description, type, modbus_ip, modbus_port,
                    modbus_unit_id, modbus_register_type, modbus_register_address,
                    modbus_data_type, modbus_byte_order, modbus_scaling,
                    modbus_units, modbus_offset, modbus_function_code,
                    upper_limit, lower_limit, enabled, code_id))
                conn.commit()
                flash('Diagnostic code updated successfully!', 'success')
                return redirect(url_for('diagnostic_codes'))
            except sqlite3.IntegrityError:
                flash('Code already exists.', 'danger')
    
    c.execute('SELECT * FROM diagnostic_codes WHERE id=?', (code_id,))
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM diagnostic_codes WHERE id=?', (code_id,))
    conn.commit()
    conn.close()
    flash('Diagnostic code deleted successfully!', 'success')
    return redirect(url_for('diagnostic_codes'))

@app.route('/toggle_diagnostic_code/<int:code_id>', methods=['POST'])
def toggle_diagnostic_code(code_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT enabled FROM diagnostic_codes WHERE id=?', (code_id,))
    current = c.fetchone()
    if current:
        new_status = 0 if current[0] else 1
        c.execute('UPDATE diagnostic_codes SET enabled=? WHERE id=?', (new_status, code_id))
        conn.commit()
    conn.close()
    return redirect(url_for('diagnostic_codes'))

def get_humidity_codes():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT code, description, state, last_failure, history_count, type,
               modbus_units, current_value, last_read_time 
        FROM diagnostic_codes 
        WHERE type="Humidity" AND enabled=1
    ''')
    codes = c.fetchall()
    conn.close()
    return codes

def get_temp_codes():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT code, description, state, last_failure, history_count, type,
               modbus_units, current_value, last_read_time 
        FROM diagnostic_codes 
        WHERE type="Temperature" AND enabled=1
    ''')
    codes = c.fetchall()
    conn.close()
    return codes

def get_notifications():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT code, description, state, last_failure, current_value, modbus_units 
        FROM diagnostic_codes 
        WHERE state IN ("No Status", "Fail") AND enabled=1
    ''')
    notifications = c.fetchall()
    conn.close()
    return notifications

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
        
        return jsonify({
            'humidity_codes': humidity_codes,
            'temp_codes': temp_codes,
            'notifications': notifications
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset_history', methods=['POST'])
@login_required
def reset_history():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            UPDATE diagnostic_codes 
            SET history_count = 0,
                last_failure = NULL,
                state = 'Pass'
            WHERE enabled = 1
        ''')
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
    
    conn = sqlite3.connect(DB_PATH)
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
                SET refresh_time = ?, last_updated = CURRENT_TIMESTAMP 
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
        
        # Run the Modbus read
        read_modbus_main()
        
        return jsonify({
            'success': True,
            'message': 'Modbus read triggered successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 