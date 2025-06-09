import paho.mqtt.client as mqtt
import psycopg2
import time
from datetime import datetime
import os
from dotenv import load_dotenv
import json

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

def get_active_mqtt_diagnostics():
    """Get all active MQTT diagnostic codes from the database"""
    conn = init_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, code, description, type, mqtt_broker, mqtt_port, 
               mqtt_topic, mqtt_username, mqtt_password, mqtt_qos,
               upper_limit, lower_limit
        FROM diagnostic_codes 
        WHERE enabled = 1 AND data_source_type = 'mqtt'
    ''')
    diagnostics = c.fetchall()
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
            SELECT id, code, description, type, upper_limit, lower_limit, state
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

        # Check limits and update status
        if value is None:
            status = "No Status"
        else:
            try:
                value_float = float(value)
                upper_limit = float(diagnostic[4]) if diagnostic[4] is not None else float('inf')
                lower_limit = float(diagnostic[5]) if diagnostic[5] is not None else float('-inf')
                if value_float > upper_limit or value_float < lower_limit:
                    status = "Fail"
                else:
                    status = "Pass"
            except (ValueError, TypeError) as e:
                print(f"[DEBUG] Error comparing values: {str(e)}")
                status = "No Status"

        print(f"[DEBUG] Status for {diagnostic[1]}: {status}")

        # Only update if status has changed or it's the first reading
        current_state = diagnostic[6]  # Get current state from database
        now_str = format_datetime(datetime.now())
        
        if current_state != status or current_state == "No Status":
            if status in ('Fail', 'No Status'):
                c.execute('''
                    UPDATE diagnostic_codes 
                    SET state = %s,
                        current_value = %s,
                        last_read_time = %s,
                        last_failure = %s,
                        history_count = COALESCE(history_count, 0) + 1
                    WHERE id = %s
                ''', (status, value, now_str, now_str, diagnostic[0]))
                
                # Log the failure
                c.execute('''
                    INSERT INTO logs (code, description, state, last_failure, history_count, type, value)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    diagnostic[1],
                    diagnostic[2],
                    status,
                    now_str,
                    1,
                    diagnostic[3],
                    value
                ))
                
                # Send alert
                emails, phone_numbers = get_contacts()
                subject = "Fault Detected"
                message = "Fault Detected"
                current_time = format_datetime(datetime.now())
                refresh_time = get_refresh_time()
                send_alert(emails, phone_numbers, subject, message, [{
                    'code': diagnostic[1],
                    'description': diagnostic[2],
                    'state': status,
                    'last_failure': now_str,
                    'history_count': 1,
                    'type': diagnostic[3]
                }], current_time, refresh_time)
            else:
                c.execute('''
                    UPDATE diagnostic_codes 
                    SET state = %s,
                        current_value = %s,
                        last_read_time = %s
                    WHERE id = %s
                ''', (status, value, now_str, diagnostic[0]))

            conn.commit()
            print(f"[DEBUG] Updated diagnostic {diagnostic[1]} ({diagnostic[2]}) to {status} with value {value}")

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
    print("\n" + "="*50)
    print(f"Starting MQTT data reader at {format_datetime(datetime.now())}")
    print("="*50)

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
                print("No active MQTT diagnostics found. Checking again in 5 seconds...")
                time.sleep(5)
                continue

            # Group diagnostics by broker
            broker_groups = {}
            for diag in diagnostics:
                broker = diag[4]  # mqtt_broker
                if broker not in broker_groups:
                    broker_groups[broker] = []
                broker_groups[broker].append(diag)

            # Check for parameter changes periodically
            if current_time - last_check_time >= CHECK_INTERVAL:
                check_parameter_changes(active_clients, broker_groups)
                last_check_time = current_time

            # Small sleep to prevent CPU overuse
            time.sleep(1)

        except KeyboardInterrupt:
            print("\nStopping MQTT clients...")
            for client in active_clients.values():
                client.loop_stop()
                client.disconnect()
            break
        except Exception as e:
            print(f"Error in main loop: {str(e)}")
            time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    main() 