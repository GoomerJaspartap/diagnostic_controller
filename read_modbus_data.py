from pymodbus.client import ModbusTcpClient
import sqlite3
import time
from datetime import datetime
import struct
from update_diagnostic import update_diagnostics_batch
from AlertAPI import send_alert

def init_db():
    """Initialize database connection"""
    return sqlite3.connect('diagnostics.db')

def get_active_diagnostics():
    """Get all active diagnostic codes from the database"""
    conn = init_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, code, description, type, modbus_ip, modbus_port, 
               modbus_unit_id, modbus_register_type, modbus_register_address,
               modbus_data_type, modbus_byte_order, modbus_scaling,
               modbus_units, modbus_offset, modbus_function_code,
               upper_limit, lower_limit
        FROM diagnostic_codes 
        WHERE enabled = 1
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

def check_limits(value, upper_limit, lower_limit):
    """Check if value is within limits"""
    if value is None:
        return "No Status"
    try:
        if float(value) > float(upper_limit) or float(value) < float(lower_limit):
            return "Fail"
        return "Pass"
    except (ValueError, TypeError):
        return "No Status"

def get_refresh_time():
    """Get the current refresh time from the database"""
    conn = init_db()
    c = conn.cursor()
    c.execute('SELECT refresh_time FROM app_settings WHERE id = 1')
    result = c.fetchone()
    conn.close()
    return result[0] if result else 5  # Default to 5 seconds if not found

def update_diagnostics_batch(status_updates):
    """Update multiple diagnostic codes in a batch"""
    conn = init_db()
    c = conn.cursor()
    successful = []
    errors = []
    
    for update in status_updates:
        try:
            if update['state'] in ('Fail', 'No Status'):
                c.execute('''
                    UPDATE diagnostic_codes 
                    SET state = ?,
                        current_value = ?,
                        last_read_time = CURRENT_TIMESTAMP,
                        last_failure = CURRENT_TIMESTAMP,
                        history_count = COALESCE(history_count, 0) + 1
                    WHERE code = ?
                ''', (update['state'], update.get('value'), update['code']))
            else:
                c.execute('''
                    UPDATE diagnostic_codes 
                    SET state = ?,
                        current_value = ?,
                        last_read_time = CURRENT_TIMESTAMP
                    WHERE code = ?
                ''', (update['state'], update.get('value'), update['code']))
            successful.append(update['code'])
        except Exception as e:
            errors.append((update['code'], str(e)))
    
    conn.commit()
    conn.close()
    return successful, errors

def get_contacts():
    conn = init_db()
    c = conn.cursor()
    c.execute('SELECT email, phone FROM contacts')
    contacts = c.fetchall()
    emails = [c[0] for c in contacts]
    phone_numbers = [c[1] for c in contacts]
    conn.close()
    return emails, phone_numbers

def get_diagnostic_details(code):
    conn = init_db()
    c = conn.cursor()
    c.execute('SELECT code, description, state, last_failure, history_count, type FROM diagnostic_codes WHERE code = ? AND enabled = 1', (code,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'code': row[0],
            'description': row[1],
            'state': row[2],
            'last_failure': row[3],
            'history_count': row[4],
            'type': row[5]
        }
    return None

def main():
    # Get active diagnostics
    diagnostics = get_active_diagnostics()
    
    # Group diagnostics by (IP, port) to minimize connections
    ip_port_groups = {}
    for diag in diagnostics:
        ip = diag[4]
        port = diag[5]
        key = (ip, port)
        if key not in ip_port_groups:
            ip_port_groups[key] = []
        ip_port_groups[key].append(diag)

    # Store all status updates
    status_updates = []

    # Process each (IP, port)
    for (ip, port), diag_list in ip_port_groups.items():
        print(f"\nConnecting to {ip}:{port}...")
        try:
            # Create Modbus client
            client = ModbusTcpClient(ip, port=port)
            
            if not client.connect():
                print(f"Failed to connect to {ip}:{port}")
                # Mark all diagnostics for this (IP, port) as No Status
                for diag in diag_list:
                    status_updates.append({
                        'code': diag[1],
                        'state': 'No Status',
                        'value': None
                    })
                continue

            # Read values for each diagnostic
            for diag in diag_list:
                value, error = read_modbus_value(client, diag)
                
                # Print results
                print(f"\nDiagnostic: {diag[1]} ({diag[2]})")
                print(f"Type: {diag[3]}")
                if error:
                    print(f"Error: {error}")
                    status = "No Status"
                    value = None
                else:
                    print(f"Value: {value} {diag[12]}")
                    print(f"Limits: {diag[15]} - {diag[16]} {diag[12]}")
                    status = check_limits(value, diag[15], diag[16])
                
                # Add to status updates
                status_updates.append({
                    'code': diag[1],
                    'state': status,
                    'value': value
                })

            # Close connection
            client.close()

        except Exception as e:
            print(f"Error processing {ip}:{port}: {str(e)}")
            # Mark all diagnostics for this (IP, port) as No Status
            for diag in diag_list:
                status_updates.append({
                    'code': diag[1],
                    'state': 'No Status',
                    'value': None
                })

    # Batch update all statuses
    if status_updates:
        print("\nUpdating diagnostic statuses...")
        successful, errors = update_diagnostics_batch(status_updates)
        if successful:
            print(f"Successfully updated {len(successful)} diagnostics")
        if errors:
            print(f"Failed to update {len(errors)} diagnostics")

        # ALERT LOGIC: send alert for any Fail or No Status
        alert_updates = []
        for update in status_updates:
            if update['state'] in ['Fail', 'No Status']:
                details = get_diagnostic_details(update['code'])
                if details:
                    alert_updates.append(details)
        if alert_updates:
            emails, phone_numbers = get_contacts()
            subject = "Fault Detected"
            message = "Fault Detected"
            send_alert(emails, phone_numbers, subject, message, alert_updates)

if __name__ == "__main__":
    while True:
        print("\n" + "="*50)
        print(f"Reading Modbus data at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)
        
        main()
        
        # Get refresh time from database
        refresh_time = get_refresh_time()
        print(f"\nWaiting {refresh_time} seconds before next reading...")
        time.sleep(refresh_time) 