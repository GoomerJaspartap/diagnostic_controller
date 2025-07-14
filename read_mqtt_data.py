import paho.mqtt.client as mqtt
import psycopg2
import time
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json
import logging

from AlertAPI import send_alert

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s')

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

def is_value_within_bounds_realtime(start_time, time_to_achieve, current_time,
                                    threshold, start_value, target_value, current_value):
    """
    Checks if current_value at current_time is within threshold of expected value on linear ramp.
    
    Params:
    - start_time: datetime.datetime — enabled time
    - time_to_achieve:  — duration in seconds to reach target
    - current_time: datetime.datetime —time when data is received
    - threshold: float — max deviation allowed
    - start_value: float — initial value at start_time
    - target_value: float — final target value
    - current_value: float — data received. 
    
    Returns:
    - (bool, float): (True if in bounds, expected_value)
    """
    # Convert datetime objects to seconds for calculation
    start_time_seconds = start_time.timestamp()
    current_time_seconds = current_time.timestamp()
    
    # Calculate slope and intercept (matching trial.py logic)
    m = (target_value - start_value) / time_to_achieve
    b = start_value - m * start_time_seconds
    
    # Calculate expected value
    print(f"[DEBUG] Time calculations: start_time_seconds={start_time_seconds}, current_time_seconds={current_time_seconds}, time_to_achieve={time_to_achieve}")
    print(f"[DEBUG] Slope calculations: m={m}, b={b}")
    
    if current_time_seconds < start_time_seconds:
        expected_value = start_value
        print(f"[DEBUG] Before start time, using start_value: {expected_value}")
    elif current_time_seconds >= start_time_seconds + time_to_achieve:
        expected_value = target_value
        print(f"[DEBUG] After end time, using target_value: {expected_value}")
    else:
        expected_value = m * current_time_seconds + b
        print(f"[DEBUG] During ramp, calculated: {expected_value}")
    
    # Clamp expected value to bounds
    expected_value = max(min(expected_value, target_value), start_value)
    print(f"[DEBUG] After clamping: {expected_value}")

    # Check if current value is within bounds
    deviation = abs(current_value - expected_value)
    in_bounds = deviation <= threshold and current_value <= target_value
    print(f"[DEBUG] Final check: deviation={deviation}, threshold={threshold}, current_value={current_value}, target_value={target_value}, in_bounds={in_bounds}")

    return in_bounds, expected_value

def check_limits(value, start_value, target_value, threshold, time_to_achieve=None, enabled_time=None):
    """Check if value is within diagnostic parameters using real-time strategy"""
    if value is None or start_value is None or target_value is None or threshold is None:
        return "No Status", None
    
    try:
        value_float = float(value)
        start_float = float(start_value)
        target_float = float(target_value)
        threshold_float = float(threshold)
        
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
                
                in_bounds, expected_value = is_value_within_bounds_realtime(
                    enabled_time, time_to_achieve, current_time,
                    threshold_float, start_float, target_float, value_float
                )
                
                print(f"[DEBUG] Real-time check: current={value_float}, expected={expected_value}, in_bounds={in_bounds}")
                
                if in_bounds:
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
        if deviation <= threshold_float and value_float <= target_float:
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

def update_last_error_event():
    conn = init_db()
    c = conn.cursor()
    now_str = format_datetime(datetime.now())
    c.execute('UPDATE app_settings SET last_error_event = %s WHERE id = 1', (now_str,))
    conn.commit()
    conn.close()

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

def init_db():
    """Initialize database connection"""
    logging.debug(f"Connecting to database with config: {DB_CONFIG}")
    return psycopg2.connect(**DB_CONFIG)

def get_active_mqtt_diagnostics():
    """Get all active MQTT diagnostic codes from the database"""
    conn = init_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, code, description, type, mqtt_broker, mqtt_port, 
               mqtt_topic, mqtt_username, mqtt_password, mqtt_qos,
               start_value, target_value, threshold, time_to_achieve, enabled_at
        FROM diagnostic_codes 
        WHERE enabled = 1 AND data_source_type = 'mqtt'
    ''')
    diagnostics = c.fetchall()
    logging.debug(f"Found {len(diagnostics)} active MQTT diagnostics")
    for diag in diagnostics:
        logging.debug(f"Diagnostic: {diag}")
    conn.close()
    return diagnostics

def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the broker"""
    if rc == 0:
        print("Connected to MQTT broker")
        # Subscribe to all topics from active diagnostics
        diagnostics = get_active_mqtt_diagnostics()
        for diag in diagnostics:
            topic = diag[6]  # mqtt_topic
            client.subscribe(topic, qos=diag[9])  # mqtt_qos
    else:
        print(f"Failed to connect to MQTT broker, return code: {rc}")

def on_message(client, userdata, msg):
    """Callback for when a message is received"""
    try:
        # Get diagnostic code for this topic
        conn = init_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, code, description, type, start_value, target_value, threshold, state, time_to_achieve, enabled_at
            FROM diagnostic_codes 
            WHERE mqtt_topic = %s AND enabled = 1 AND data_source_type = 'mqtt'
        ''', (msg.topic,))
        diagnostic = c.fetchone()
        
        if not diagnostic:
            print(f"[DEBUG] No diagnostic found for topic: {msg.topic}")
            return

        # Parse the message payload
        try:
            payload_str = msg.payload.decode().strip()
            print(f"[DEBUG] Received payload for {diagnostic[1]} (topic: {msg.topic}): {payload_str}")
            
            try:
                # Try to parse as JSON first
                payload = json.loads(payload_str)
                if isinstance(payload, dict):
                    value = payload.get('value')
                    if value is None:
                        for v in payload.values():
                            if isinstance(v, (int, float)):
                                value = v
                                break
                elif isinstance(payload, (int, float)):
                    value = payload
                else:
                    value = None
            except json.JSONDecodeError:
                try:
                    value = float(payload_str.strip())
                except ValueError:
                    print(f"[DEBUG] Could not parse value from payload: {payload_str}")
                    value = None

            print(f"[DEBUG] Parsed value for {diagnostic[1]}: {value}")

        except Exception as e:
            print(f"[DEBUG] Error parsing payload: {str(e)}")
            value = None

        # Log data to data_logs table
        if value is not None:
            conn_data = init_db()
            c_data = conn_data.cursor()
            c_data.execute('INSERT INTO data_logs (code, value, data_source) VALUES (%s, %s, %s)', (diagnostic[1], value, 'mqtt'))
            conn_data.commit()
            conn_data.close()

        # Check limits using the same logic as Modbus
        status, fault_type = check_limits(value, diagnostic[4], diagnostic[5], diagnostic[6], diagnostic[8], diagnostic[9])
        
        print(f"[DEBUG] Status for {diagnostic[1]}: {status}")

        # Create status update for batch processing
        status_update = {
            'code': diagnostic[1],
            'state': status,
            'value': value,
            'fault_type': fault_type
        }

        # Update diagnostic status using batch processing
        successful, errors = update_diagnostics_batch([status_update])
        
        if successful:
            print(f"[DEBUG] Successfully updated diagnostic {diagnostic[1]} to {status}")
        if errors:
            print(f"[DEBUG] Failed to update diagnostic {diagnostic[1]}: {errors}")

        # Send alert if status is Fail or No Status
        if status in ('Fail', 'No Status'):
            details = get_diagnostic_details(diagnostic[1])
            if details:
                emails, phone_numbers = get_contacts()
                subject = "Fault Detected"
                message = "Fault Detected"
                current_time = format_datetime(datetime.now())
                refresh_time = get_refresh_time()
                send_alert(emails, phone_numbers, subject, message, [details], current_time, refresh_time)

        conn.close()

    except Exception as e:
        print(f"[DEBUG] Error processing MQTT message: {str(e)}")

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

def get_refresh_time():
    """Get the current refresh time from the database"""
    conn = init_db()
    c = conn.cursor()
    c.execute('SELECT refresh_time FROM app_settings WHERE id = 1')
    result = c.fetchone()
    conn.close()
    return result[0] if result else 5  # Default to 5 seconds if not found

def format_datetime(dt):
    """Format datetime object to string"""
    if not dt:
        return ''
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime('%d %B, %Y %H:%M:%S')

def check_parameter_changes(active_clients, broker_groups):
    """Check if MQTT parameters have changed and update connections accordingly"""
    current_brokers = set(broker_groups.keys())
    existing_brokers = set(active_clients.keys())

    # Remove clients for brokers that no longer have diagnostics
    for broker in existing_brokers - current_brokers:
        print(f"Removing connection to broker: {broker}")
        client = active_clients[broker]
        client.loop_stop()
        client.disconnect()
        del active_clients[broker]

    # Add or update clients for current brokers
    for broker, diag_list in broker_groups.items():
        if broker not in active_clients:
            try:
                # Create MQTT client
                client = mqtt.Client()
                
                # Set credentials if provided
                username = diag_list[0][7]  # mqtt_username
                password = diag_list[0][8]  # mqtt_password
                if username and password:
                    client.username_pw_set(username, password)
                
                # Set callbacks
                client.on_connect = on_connect
                client.on_message = on_message
                
                # Connect to broker
                port = diag_list[0][5]  # mqtt_port
                client.connect(broker, port=port)
                
                # Start the loop
                client.loop_start()
                active_clients[broker] = client
                
                print(f"Connected to MQTT broker: {broker}:{port}")
                
            except Exception as e:
                print(f"Error connecting to MQTT broker {broker}: {str(e)}")
        else:
            # Update subscriptions for existing client
            client = active_clients[broker]
            # Unsubscribe from all topics first
            client.unsubscribe([diag[6] for diag in get_active_mqtt_diagnostics() if diag[4] == broker])
            # Subscribe to new topics
            for diag in diag_list:
                topic = diag[6]  # mqtt_topic
                client.subscribe(topic, qos=diag[9])  # mqtt_qos
            print(f"Updated subscriptions for broker: {broker}")

def main():
    """Main function to start MQTT client"""
    logging.info("\n" + "="*50)
    logging.info(f"Starting MQTT data reader at {format_datetime(datetime.now())}")
    logging.info("="*50)

    # Dictionary to keep track of active clients
    active_clients = {}
    last_check_time = time.time()
    CHECK_INTERVAL = 30  # Check for parameter changes every 30 seconds

    while True:
        try:
            current_time = time.time()
            
            # Get active MQTT diagnostics
            diagnostics = get_active_mqtt_diagnostics()
            
            if not diagnostics:
                logging.info("No active MQTT diagnostics found. Checking again in 5 seconds...")
                time.sleep(5)
                continue

            # Group diagnostics by broker
            broker_groups = {}
            for diag in diagnostics:
                broker = diag[4]  # mqtt_broker
                if broker not in broker_groups:
                    broker_groups[broker] = []
                broker_groups[broker].append(diag)

            logging.debug(f"Broker groups: {broker_groups}")

            # Check for parameter changes periodically
            if current_time - last_check_time >= CHECK_INTERVAL:
                check_parameter_changes(active_clients, broker_groups)
                last_check_time = current_time

            # Small sleep to prevent CPU overuse
            time.sleep(1)

        except KeyboardInterrupt:
            logging.info("\nStopping MQTT clients...")
            for client in active_clients.values():
                client.loop_stop()
                client.disconnect()
            break
        except Exception as e:
            logging.error(f"Error in main loop: {str(e)}")
            time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    main() 