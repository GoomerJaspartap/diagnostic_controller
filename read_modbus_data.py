from pymodbus.client import ModbusTcpClient
import psycopg2
import time
from datetime import datetime, timedelta
import struct
import os
from dotenv import load_dotenv
import threading

from AlertAPI import send_alert

# Load environment variables
load_dotenv()

# PostgreSQL configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

def init_db():
    """Initialize database connection"""
    return psycopg2.connect(**DB_CONFIG)

def get_active_diagnostics():
    """Get all active Modbus diagnostic codes from the database"""
    conn = init_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, code, description, type, modbus_ip, modbus_port, 
               modbus_unit_id, modbus_register_type, modbus_register_address,
               modbus_data_type, modbus_byte_order, modbus_scaling,
               modbus_units, modbus_offset, modbus_function_code,
               start_value, target_value, threshold, time_to_achieve, enabled_at, upper_limit, lower_limit
        FROM diagnostic_codes 
        WHERE enabled = 1 AND data_source_type = 'modbus'
    ''')
    diagnostics = c.fetchall()
    conn.close()
    return diagnostics

def read_modbus_value(client, diagnostic):
    """Read a value from Modbus device based on diagnostic configuration"""
    try:
        # Extract Modbus configuration
        unit_id = diagnostic[6]
        register_type = diagnostic[7]
        register_address = diagnostic[8]
        data_type = diagnostic[9]
        byte_order = diagnostic[10]
        scaling = float(diagnostic[11])
        offset = float(diagnostic[13])
        function_code = int(diagnostic[14])

        # Determine number of registers to read
        if data_type == 'int16':
            reg_count = 1
        elif data_type in ['int32', 'float32']:
            reg_count = 2
        elif data_type in ['int64', 'float64']:
            reg_count = 4
        else:
            return None, "Unsupported data type"

        # Read based on register type and function code
        if register_type == 'Holding Register':
            result = client.read_holding_registers(register_address, reg_count, unit=unit_id)
        elif register_type == 'Input Register':
            result = client.read_input_registers(register_address, reg_count, unit=unit_id)
        else:
            return None, "Unsupported register type"

        if result.isError():
            return None, f"Modbus error: {result}"

        # Process the value based on data type
        if data_type == 'int16':
            value = result.registers[0]
        elif data_type == 'int32':
            if byte_order == 'big-endian':
                value = struct.unpack('>i', struct.pack('>HH', result.registers[0], result.registers[1]))[0]
            elif byte_order == 'little-endian':
                value = struct.unpack('<i', struct.pack('<HH', result.registers[0], result.registers[1]))[0]
            else:  # word-swapped
                value = struct.unpack('>i', struct.pack('>HH', result.registers[1], result.registers[0]))[0]
        elif data_type == 'float32':
            if byte_order == 'big-endian':
                value = struct.unpack('>f', struct.pack('>HH', result.registers[0], result.registers[1]))[0]
            elif byte_order == 'little-endian':
                value = struct.unpack('<f', struct.pack('<HH', result.registers[0], result.registers[1]))[0]
            else:  # word-swapped
                value = struct.unpack('>f', struct.pack('>HH', result.registers[1], result.registers[0]))[0]
        elif data_type == 'int64':
            regs = result.registers[:4]
            if byte_order == 'big-endian':
                value = struct.unpack('>q', struct.pack('>HHHH', *regs))[0]
            elif byte_order == 'little-endian':
                value = struct.unpack('<q', struct.pack('<HHHH', *regs))[0]
            else:  # word-swapped
                value = struct.unpack('>q', struct.pack('>HHHH', regs[2], regs[3], regs[0], regs[1]))[0]
        elif data_type == 'float64':
            regs = result.registers[:4]
            if byte_order == 'big-endian':
                value = struct.unpack('>d', struct.pack('>HHHH', *regs))[0]
            elif byte_order == 'little-endian':
                value = struct.unpack('<d', struct.pack('<HHHH', *regs))[0]
            else:  # word-swapped
                value = struct.unpack('>d', struct.pack('>HHHH', regs[2], regs[3], regs[0], regs[1]))[0]
        else:
            return None, "Unsupported data type"

        # Apply scaling and offset
        scaled_value = (value * scaling) + offset
        return scaled_value, None

    except Exception as e:
        return None, f"Error reading value: {str(e)}"

def read_single_modbus_value(ip, port, unit_id, register_type, register_address, data_type, byte_order, scaling, units, offset, function_code):
    """Read a single modbus value with the given configuration"""
    try:
        # Create Modbus client
        client = ModbusTcpClient(ip, port)
        
        if not client.connect():
            raise Exception(f"Failed to connect to Modbus device at {ip}:{port}")
        
        try:
            # Determine number of registers to read
            if data_type == 'int16':
                reg_count = 1
            elif data_type in ['int32', 'float32']:
                reg_count = 2
            elif data_type in ['int64', 'float64']:
                reg_count = 4
            else:
                raise Exception("Unsupported data type")

            # Read based on register type
            if register_type == 'Holding Register':
                result = client.read_holding_registers(register_address, reg_count, unit=unit_id)
            elif register_type == 'Input Register':
                result = client.read_input_registers(register_address, reg_count, unit=unit_id)
            else:
                raise Exception("Unsupported register type")

            if result.isError():
                raise Exception(f"Modbus error: {result}")

            # Process the value based on data type
            if data_type == 'int16':
                value = result.registers[0]
            elif data_type == 'int32':
                if byte_order == 'big-endian':
                    value = struct.unpack('>i', struct.pack('>HH', result.registers[0], result.registers[1]))[0]
                elif byte_order == 'little-endian':
                    value = struct.unpack('<i', struct.pack('<HH', result.registers[0], result.registers[1]))[0]
                else:  # word-swapped
                    value = struct.unpack('>i', struct.pack('>HH', result.registers[1], result.registers[0]))[0]
            elif data_type == 'float32':
                if byte_order == 'big-endian':
                    value = struct.unpack('>f', struct.pack('>HH', result.registers[0], result.registers[1]))[0]
                elif byte_order == 'little-endian':
                    value = struct.unpack('<f', struct.pack('<HH', result.registers[0], result.registers[1]))[0]
                else:  # word-swapped
                    value = struct.unpack('>f', struct.pack('>HH', result.registers[1], result.registers[0]))[0]
            elif data_type == 'int64':
                regs = result.registers[:4]
                if byte_order == 'big-endian':
                    value = struct.unpack('>q', struct.pack('>HHHH', *regs))[0]
                elif byte_order == 'little-endian':
                    value = struct.unpack('<q', struct.pack('<HHHH', *regs))[0]
                else:  # word-swapped
                    value = struct.unpack('>q', struct.pack('>HHHH', regs[2], regs[3], regs[0], regs[1]))[0]
            elif data_type == 'float64':
                regs = result.registers[:4]
                if byte_order == 'big-endian':
                    value = struct.unpack('>d', struct.pack('>HHHH', *regs))[0]
                elif byte_order == 'little-endian':
                    value = struct.unpack('<d', struct.pack('<HHHH', *regs))[0]
                else:  # word-swapped
                    value = struct.unpack('>d', struct.pack('>HHHH', regs[2], regs[3], regs[0], regs[1]))[0]
            else:
                raise Exception("Unsupported data type")

            # Apply scaling and offset
            scaling = float(scaling) if scaling else 1.0
            offset = float(offset) if offset else 0.0
            scaled_value = (value * scaling) + offset
            
            return scaled_value

        finally:
            client.close()
            
    except Exception as e:
        raise Exception(f"Error reading Modbus value: {str(e)}")

def is_value_within_bounds_realtime(start_time, time_to_achieve, current_time,
                                    threshold, start_value, target_value, current_value):
    """
    Checks if current_value at current_time is within threshold of expected value on linear ramp.
x    Works for both positive and negative slopes.
    """
    # Convert datetime objects to seconds for calculation
    start_time_seconds = start_time.timestamp()
    current_time_seconds = current_time.timestamp()
    
    # Calculate slope and intercept (matching trial.py logic)
    m = (target_value - start_value) / time_to_achieve
    b = start_value - m * start_time_seconds
    
    # Calculate expected value
    if current_time_seconds < start_time_seconds:
        expected_value = start_value
    elif current_time_seconds >= start_time_seconds + time_to_achieve:
        expected_value = target_value
    else:
        expected_value = m * current_time_seconds + b
    
    # Clamp expected value to bounds (works for both positive and negative slope)
    min_bound = min(start_value, target_value)
    max_bound = max(start_value, target_value)
    expected_value = max(min(expected_value, max_bound), min_bound)
    
    # Check if current value is within bounds
    deviation = abs(current_value - expected_value)
    if start_value < target_value:
        in_bounds = deviation <= threshold and current_value <= target_value
    else:
        in_bounds = deviation <= threshold and current_value >= target_value
    
    return in_bounds, expected_value

def check_limits(value, start_value, target_value, threshold, time_to_achieve=None, enabled_time=None, upper_limit=None, lower_limit=None):
    """Check if value is within diagnostic parameters using real-time strategy"""
    if value is None or start_value is None or target_value is None or threshold is None:
        return "No Status", None
    
    try:
        value_float = float(value)
        start_float = float(start_value)
        target_float = float(target_value)
        threshold_float = float(threshold)
        
        # Use upper_limit if provided, otherwise use target_value as the maximum bound
        max_limit = float(upper_limit) if upper_limit is not None else target_float
        min_limit = float(lower_limit) if lower_limit is not None else start_float
        
        # Use real-time strategy if we have all required parameters
        if time_to_achieve is not None and enabled_time is not None:
            try:
                # Handle different types of enabled_time
                if isinstance(enabled_time, str):
                    enabled_time = datetime.fromisoformat(enabled_time)
                elif isinstance(enabled_time, (int, float)):
                    # enabled_at should be the actual timestamp, not a relative offset
                    # If it's a small number, it's likely an old/invalid value
                    if enabled_time < 1000000:  # Less than ~11 days in seconds
                        print(f"[DEBUG] Warning: enabled_at={enabled_time} appears to be invalid. Using current time as fallback.")
                        enabled_time = datetime.now()
                    else:
                        # Assume it's a Unix timestamp in seconds
                        enabled_time = datetime.fromtimestamp(enabled_time)
                # else: assume it's already a datetime object
                
                # Use UTC time consistently to match the database timestamps
                current_time = datetime.utcnow()
                
                # Use the new real-time diagnostic strategy
                print(f"[DEBUG] Time info: enabled_time={enabled_time}, time_to_achieve={time_to_achieve}, current_time={current_time}")
                print(f"[DEBUG] Value info: start_value={start_float}, target_value={target_float}, current_value={value_float}, threshold={threshold_float}")
                print(f"[DEBUG] Limits: upper_limit={max_limit}, lower_limit={min_limit}")
                
                in_bounds, expected_value = is_value_within_bounds_realtime(
                    enabled_time, time_to_achieve, current_time,
                    threshold_float, start_float, target_float, value_float
                )
                
                print(f"[DEBUG] Real-time check: current={value_float}, expected={expected_value}, in_bounds={in_bounds}")
                
                # Additional check for upper and lower limits
                if value_float > max_limit:
                    print(f"[DEBUG] Value {value_float} exceeds upper limit {max_limit}")
                    return "Fail", "Over Upper Limit"
                elif value_float < min_limit:
                    print(f"[DEBUG] Value {value_float} below lower limit {min_limit}")
                    return "Fail", "Under Lower Limit"
                elif in_bounds:
                    return "Pass", None
                else:
                    # Determine fault type for real-time strategy
                    if value_float > expected_value + threshold_float:
                        fault_type = "Over Threshold"
                    elif value_float < expected_value - threshold_float:
                        fault_type = "Under Threshold"
                    elif value_float > target_float:
                        fault_type = "Over Target"
                    else:
                        fault_type = "Out of Bounds"
                    return "Fail", fault_type
                    
            except Exception as e:
                print(f"[DEBUG] Error in real-time calculation: {str(e)}")
                # Fall back to simple threshold check
        
        # Fallback to simple threshold check (matching trial.py logic)
        deviation = abs(value_float - target_float)
        
        # Check upper and lower limits first
        if value_float > max_limit:
            return "Fail", "Over Upper Limit"
        elif value_float < min_limit:
            return "Fail", "Under Lower Limit"
        elif deviation <= threshold_float and value_float <= target_float:
            return "Pass", None
        else:
            # Determine fault type for simple threshold check
            if value_float > target_float + threshold_float:
                fault_type = "Over Threshold"
            elif value_float < target_float - threshold_float:
                fault_type = "Under Threshold"
            elif value_float > target_float:
                fault_type = "Over Target"
            else:
                fault_type = "Out of Bounds"
            return "Fail", fault_type
    except (ValueError, TypeError):
        return "No Status", None

def get_refresh_time():
    """Get the current refresh time from the database"""
    conn = init_db()
    c = conn.cursor()
    c.execute('SELECT refresh_time FROM app_settings WHERE id = 1')
    result = c.fetchone()
    conn.close()
    return result[0] if result else 5  # Default to 5 seconds if not found

def update_last_error_event():
    conn = init_db()
    c = conn.cursor()
    now_str = format_datetime(datetime.now())
    c.execute('UPDATE app_settings SET last_error_event = %s WHERE id = 1', (now_str,))
    conn.commit()
    conn.close()

def update_diagnostics_batch(status_updates):
    """Update multiple diagnostic codes in a batch"""
    conn = init_db()
    c = conn.cursor()
    successful = []
    errors = []
    now_str = format_datetime(datetime.now())
    error_triggered = False
    for update in status_updates:
        try:
            if update['state'] in ('Fail', 'No Status'):
                error_triggered = True
                c.execute('''
                    UPDATE diagnostic_codes 
                    SET state = %s,
                        current_value = %s,
                        last_read_time = %s,
                        last_failure = %s,
                        history_count = COALESCE(history_count, 0) + 1,
                        fault_type = %s
                    WHERE code = %s
                ''', (update['state'], update.get('value'), now_str, now_str, update.get('fault_type'), update['code']))
            else:
                c.execute('''
                    UPDATE diagnostic_codes 
                    SET state = %s,
                        current_value = %s,
                        last_read_time = %s,
                        fault_type = NULL
                    WHERE code = %s
                ''', (update['state'], update.get('value'), now_str, update['code']))
            # Always log to logs for 'Fail' and 'No Status'
            if update['state'] in ('Fail', 'No Status'):
                c.execute('''SELECT description, last_failure, history_count, type, current_value FROM diagnostic_codes WHERE code = %s''', (update['code'],))
                row = c.fetchone()
                c.execute('''
                    INSERT INTO logs (code, description, state, last_failure, history_count, type, value)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    update['code'],
                    row[0] if row else '',
                    update['state'],
                    row[1] if row else '',
                    row[2] if row else 0,
                    row[3] if row else '',
                    row[4] if row else None
                ))
            successful.append(update['code'])
        except Exception as e:
            errors.append((update['code'], str(e)))
    conn.commit()
    conn.close()
    if error_triggered:
        update_last_error_event()
    return successful, errors

def get_contacts():
    """Get contact information for alerts"""
    conn = init_db()
    c = conn.cursor()
    c.execute('SELECT email, phone, enable_email, enable_sms FROM contacts')
    contacts = c.fetchall()
    emails = [c[0] for c in contacts if c[2] == 1]  # Only get emails where enable_email is 1
    phone_numbers = [c[1] for c in contacts if c[3] == 1]  # Only get phones where enable_sms is 1
    conn.close()
    return emails, phone_numbers

def get_diagnostic_details(code):
    """Get diagnostic details for alerts, including room name and all diagnostic parameters"""
    conn = init_db()
    c = conn.cursor()
    c.execute('''
        SELECT d.id, d.code, d.description, d.type, d.state, d.current_value, d.last_read_time, d.last_failure, d.history_count, r.name as room_name,
               d.start_value, d.target_value, d.threshold, d.time_to_achieve, d.enabled_at, d.fault_type
        FROM diagnostic_codes d
        LEFT JOIN rooms r ON d.room_id = r.id
        WHERE d.code = %s
    ''', (code,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'code': row[1],
            'description': row[2],
            'type': row[3],
            'state': row[4],
            'value': row[5],
            'last_read_time': row[6],
            'last_failure': row[7],
            'history_count': row[8],
            'room_name': row[9] or 'Unassigned',
            'start_value': row[10],
            'target_value': row[11],
            'threshold': row[12],
            'time_to_achieve': row[13],
            'enabled_at': row[14],
            'fault_type': row[15]
        }
    return None

def format_datetime(dt):
    if not dt:
        return ''
    if isinstance(dt, str):
        try:
            dt = datetime.datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime('%d %B, %Y %H:%M:%S')

def get_chambers_with_refresh():
    """Get all chambers with their id, name, and refresh_time"""
    conn = init_db()
    c = conn.cursor()
    c.execute('SELECT id, name, refresh_time FROM rooms')
    chambers = c.fetchall()
    conn.close()
    return chambers

def get_chamber_diagnostics(chamber_id):
    """Get all active Modbus diagnostics for a given chamber"""
    conn = init_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, code, description, type, modbus_ip, modbus_port, 
               modbus_unit_id, modbus_register_type, modbus_register_address,
               modbus_data_type, modbus_byte_order, modbus_scaling,
               modbus_units, modbus_offset, modbus_function_code,
               start_value, target_value, threshold, time_to_achieve, enabled_at
        FROM diagnostic_codes 
        WHERE enabled = 1 AND data_source_type = 'modbus' AND room_id = %s
    ''', (chamber_id,))
    diagnostics = c.fetchall()
    conn.close()
    return diagnostics

def chamber_modbus_loop(chamber_id, chamber_name, refresh_time):
    while True:
        print(f"\n{'='*50}\nReading Modbus data for chamber: {chamber_name} at {format_datetime(datetime.now())}\n{'='*50}")
        diagnostics = get_chamber_diagnostics(chamber_id)
        if diagnostics:
            # Group by (ip, port) for efficiency
            ip_port_groups = {}
            for diag in diagnostics:
                ip = diag[4]
                port = diag[5]
                key = (ip, port)
                if key not in ip_port_groups:
                    ip_port_groups[key] = []
                ip_port_groups[key].append(diag)
            status_updates = []
            for (ip, port), diag_list in ip_port_groups.items():
                print(f"Connecting to {ip}:{port} for chamber {chamber_name}...")
                try:
                    client = ModbusTcpClient(ip, port=port)
                    if not client.connect():
                        print(f"Failed to connect to {ip}:{port}")
                        for diag in diag_list:
                            status_updates.append({'code': diag[1], 'state': 'No Status', 'value': None})
                        continue
                    for diag in diag_list:
                        value, error = read_modbus_value(client, diag)
                        print(f"Diagnostic: {diag[1]} ({diag[2]})")
                        print(f"Type: {diag[3]}")
                        if error:
                            print(f"Error: {error}")
                            status = "No Status"
                            value = None
                        else:
                            print(f"Value: {value} {diag[12]}")
                            print(f"Diagnostic Params: Start={diag[15]}, Target={diag[16]}, Threshold={diag[17]}, Time={diag[18]}")
                            enabled_at = diag[19] if len(diag) > 19 else None
                            print(f"[DEBUG] Params: start={diag[15]}, target={diag[16]}, threshold={diag[17]}, time={diag[18]}, enabled_at={enabled_at}")
                            status, fault_type = check_limits(value, diag[15], diag[16], diag[17], diag[18], enabled_at, diag[20], diag[21])
                        status_updates.append({'code': diag[1], 'state': status, 'value': value, 'fault_type': fault_type})
                        if error is None and value is not None:
                            conn_data = init_db()
                            c_data = conn_data.cursor()
                            c_data.execute('INSERT INTO data_logs (code, value, data_source) VALUES (%s, %s, %s)', (diag[1], value, 'modbus'))
                            conn_data.commit()
                            conn_data.close()
                    client.close()
                except Exception as e:
                    print(f"Error processing {ip}:{port}: {str(e)}")
                    for diag in diag_list:
                        status_updates.append({'code': diag[1], 'state': 'No Status', 'value': None})
            if status_updates:
                print("Updating diagnostic statuses...")
                successful, errors = update_diagnostics_batch(status_updates)
                if successful:
                    print(f"Successfully updated {len(successful)} diagnostics for chamber {chamber_name}")
                if errors:
                    print(f"Failed to update {len(errors)} diagnostics for chamber {chamber_name}")
                # ALERT LOGIC: send alert for any Fail or No Status
                alert_updates = []
                for update in status_updates:
                    if update['state'] in ['Fail', 'No Status']:
                        details = get_diagnostic_details(update['code'])
                        if details:
                            alert_updates.append(details)
                if alert_updates:
                    emails, phone_numbers = get_contacts()
                    subject = f"Fault Detected in {chamber_name}"
                    message = "Fault Detected"
                    current_time = format_datetime(datetime.now())
                    send_alert(emails, phone_numbers, subject, message, alert_updates, current_time, refresh_time)
        else:
            print(f"No active Modbus diagnostics for chamber {chamber_name}")
        print(f"Waiting {refresh_time} seconds before next reading for chamber {chamber_name}...")
        time.sleep(refresh_time)

def main(room_id=None):
    """Main function to read modbus data for specific room or all rooms"""
    if room_id:
        # Read for specific room
        conn = init_db()
        c = conn.cursor()
        c.execute('SELECT id, name, refresh_time FROM rooms WHERE id = %s', (room_id,))
        chamber = c.fetchone()
        conn.close()
        
        if chamber:
            chamber_id, chamber_name, chamber_refresh = chamber
            refresh_time = chamber_refresh if chamber_refresh and chamber_refresh > 0 else 5
            print(f"Reading Modbus data for chamber: {chamber_name}")
            
            diagnostics = get_chamber_diagnostics(chamber_id)
            if diagnostics:
                # Group by (ip, port) for efficiency
                ip_port_groups = {}
                for diag in diagnostics:
                    ip = diag[4]
                    port = diag[5]
                    key = (ip, port)
                    if key not in ip_port_groups:
                        ip_port_groups[key] = []
                    ip_port_groups[key].append(diag)
                
                status_updates = []
                for (ip, port), diag_list in ip_port_groups.items():
                    print(f"Connecting to {ip}:{port} for chamber {chamber_name}...")
                    try:
                        client = ModbusTcpClient(ip, port=port)
                        if not client.connect():
                            print(f"Failed to connect to {ip}:{port}")
                            for diag in diag_list:
                                status_updates.append({'code': diag[1], 'state': 'No Status', 'value': None})
                            continue
                        for diag in diag_list:
                            value, error = read_modbus_value(client, diag)
                            print(f"Diagnostic: {diag[1]} ({diag[2]})")
                            print(f"Type: {diag[3]}")
                            if error:
                                print(f"Error: {error}")
                                status = "No Status"
                                value = None
                            else:
                                print(f"Value: {value} {diag[12]}")
                                print(f"Diagnostic Params: Start={diag[15]}, Target={diag[16]}, Threshold={diag[17]}, Time={diag[18]}")
                                enabled_at = diag[19] if len(diag) > 19 else None
                                print(f"[DEBUG] Params: start={diag[15]}, target={diag[16]}, threshold={diag[17]}, time={diag[18]}, enabled_at={enabled_at}")
                                status, fault_type = check_limits(value, diag[15], diag[16], diag[17], diag[18], enabled_at)
                            status_updates.append({'code': diag[1], 'state': status, 'value': value})
                            if error is None and value is not None:
                                conn_data = init_db()
                                c_data = conn_data.cursor()
                                c_data.execute('INSERT INTO data_logs (code, value, data_source) VALUES (%s, %s, %s)', (diag[1], value, 'modbus'))
                                conn_data.commit()
                                conn_data.close()
                        client.close()
                    except Exception as e:
                        print(f"Error processing {ip}:{port}: {str(e)}")
                        for diag in diag_list:
                            status_updates.append({'code': diag[1], 'state': 'No Status', 'value': None})
                
                if status_updates:
                    print("Updating diagnostic statuses...")
                    successful, errors = update_diagnostics_batch(status_updates)
                    if successful:
                        print(f"Successfully updated {len(successful)} diagnostics for chamber {chamber_name}")
                    if errors:
                        print(f"Failed to update {len(errors)} diagnostics for chamber {chamber_name}")
                    
                    # ALERT LOGIC: send alert for any Fail or No Status
                    alert_updates = []
                    for update in status_updates:
                        if update['state'] in ['Fail', 'No Status']:
                            details = get_diagnostic_details(update['code'])
                            if details:
                                alert_updates.append(details)
                    if alert_updates:
                        emails, phone_numbers = get_contacts()
                        subject = f"Fault Detected in {chamber_name}"
                        message = "Fault Detected"
                        current_time = format_datetime(datetime.now())
                        send_alert(emails, phone_numbers, subject, message, alert_updates, current_time, refresh_time)
                else:
                    print(f"No active Modbus diagnostics for chamber {chamber_name}")
            else:
                print(f"No active Modbus diagnostics for chamber {chamber_name}")
        else:
            print(f"Room with ID {room_id} not found")
    else:
        # Read for all rooms
        chambers = get_chambers_with_refresh()
        for chamber in chambers:
            chamber_id, chamber_name, chamber_refresh = chamber
            refresh_time = chamber_refresh if chamber_refresh and chamber_refresh > 0 else 5
            print(f"Reading Modbus data for chamber: {chamber_name}")
            
            diagnostics = get_chamber_diagnostics(chamber_id)
            if diagnostics:
                # Group by (ip, port) for efficiency
                ip_port_groups = {}
                for diag in diagnostics:
                    ip = diag[4]
                    port = diag[5]
                    key = (ip, port)
                    if key not in ip_port_groups:
                        ip_port_groups[key] = []
                    ip_port_groups[key].append(diag)
                
                status_updates = []
                for (ip, port), diag_list in ip_port_groups.items():
                    print(f"Connecting to {ip}:{port} for chamber {chamber_name}...")
                    try:
                        client = ModbusTcpClient(ip, port=port)
                        if not client.connect():
                            print(f"Failed to connect to {ip}:{port}")
                            for diag in diag_list:
                                status_updates.append({'code': diag[1], 'state': 'No Status', 'value': None})
                            continue
                        for diag in diag_list:
                            value, error = read_modbus_value(client, diag)
                            print(f"Diagnostic: {diag[1]} ({diag[2]})")
                            print(f"Type: {diag[3]}")
                            if error:
                                print(f"Error: {error}")
                                status = "No Status"
                                value = None
                            else:
                                print(f"Value: {value} {diag[12]}")
                                print(f"Diagnostic Params: Start={diag[15]}, Target={diag[16]}, Threshold={diag[17]}, Time={diag[18]}")
                                enabled_at = diag[19] if len(diag) > 19 else None
                                print(f"[DEBUG] Params: start={diag[15]}, target={diag[16]}, threshold={diag[17]}, time={diag[18]}, enabled_at={enabled_at}")
                                status, fault_type = check_limits(value, diag[15], diag[16], diag[17], diag[18], enabled_at)
                            status_updates.append({'code': diag[1], 'state': status, 'value': value})
                            if error is None and value is not None:
                                conn_data = init_db()
                                c_data = conn_data.cursor()
                                c_data.execute('INSERT INTO data_logs (code, value, data_source) VALUES (%s, %s, %s)', (diag[1], value, 'modbus'))
                                conn_data.commit()
                                conn_data.close()
                        client.close()
                    except Exception as e:
                        print(f"Error processing {ip}:{port}: {str(e)}")
                        for diag in diag_list:
                            status_updates.append({'code': diag[1], 'state': 'No Status', 'value': None})
                
                if status_updates:
                    print("Updating diagnostic statuses...")
                    successful, errors = update_diagnostics_batch(status_updates)
                    if successful:
                        print(f"Successfully updated {len(successful)} diagnostics for chamber {chamber_name}")
                    if errors:
                        print(f"Failed to update {len(errors)} diagnostics for chamber {chamber_name}")
                    
                    # ALERT LOGIC: send alert for any Fail or No Status
                    alert_updates = []
                    for update in status_updates:
                        if update['state'] in ['Fail', 'No Status']:
                            details = get_diagnostic_details(update['code'])
                            if details:
                                alert_updates.append(details)
                    if alert_updates:
                        emails, phone_numbers = get_contacts()
                        subject = f"Fault Detected in {chamber_name}"
                        message = "Fault Detected"
                        current_time = format_datetime(datetime.now())
                        send_alert(emails, phone_numbers, subject, message, alert_updates, current_time, refresh_time)
                else:
                    print(f"No active Modbus diagnostics for chamber {chamber_name}")
            else:
                print(f"No active Modbus diagnostics for chamber {chamber_name}")

if __name__ == "__main__":
    threads = {}
    while True:
        chambers = get_chambers_with_refresh()
        for chamber in chambers:
            chamber_id, chamber_name, chamber_refresh = chamber
            # Only start a thread if this chamber has at least one Modbus diagnostic
            diagnostics = get_chamber_diagnostics(chamber_id)
            if diagnostics and chamber_id not in threads:
                refresh_time = chamber_refresh if chamber_refresh and chamber_refresh > 0 else 5
                t = threading.Thread(target=chamber_modbus_loop, args=(chamber_id, chamber_name, refresh_time), daemon=True)
                t.start()
                threads[chamber_id] = t
        time.sleep(30) 