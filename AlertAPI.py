from EmailAPI import send_status_email
from TwilioAPI import send_message
import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv
from datetime import timedelta

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

def get_refresh_time():
    """Get the current refresh time from the database"""
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('SELECT refresh_time FROM app_settings WHERE id = 1')
    result = c.fetchone()
    conn.close()
    return result[0] if result else 5  # Default to 5 seconds if not found

def format_datetime(dt):
    if not dt:
        return ''
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime('%d %B, %Y %H:%M:%S')

def send_alert(emails, phone_numbers, subject, message, table_data, current_time=None, refresh_time=None):
    # Get refresh time if not provided
    if refresh_time is None:
        refresh_time = get_refresh_time()
    
    # Get current time if not provided
    if current_time is None:
        current_time = format_datetime(datetime.now())
    else:
        current_time = format_datetime(current_time)
    
    # Group diagnostics by room_name
    grouped_data = {}
    for row in table_data:
        room = row.get('room_name', 'Unassigned')
        if room not in grouped_data:
            grouped_data[room] = []
        grouped_data[room].append(row)
    
    # Create more detailed text messages for each room
    text = f"{message}\n\n"
    text += f"Last Read Time: {current_time}\n"
    text += f"Refresh Time: {refresh_time} seconds\n\n"
    for room, diagnostics in grouped_data.items():
        text += f"Room: {room}\n"
        for row in diagnostics:
            enabled_at = row.get('enabled_at', 'N/A')
            if enabled_at and enabled_at != 'N/A':
                try:
                    if isinstance(enabled_at, str):
                        from datetime import datetime
                        enabled_at_dt = datetime.fromisoformat(enabled_at)
                    else:
                        enabled_at_dt = enabled_at
                    enabled_at_shifted = (enabled_at_dt - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    enabled_at_shifted = enabled_at
            else:
                enabled_at_shifted = 'N/A'
            text += (
                f"Code: {row.get('code', '')}\n"
                f"Description: {row.get('description', '')}\n"
                f"Type: {row.get('type', '')}\n"
                f"State: {row.get('state', '')}\n"
                f"Current Value: {row.get('value', 'N/A')}\n"
                f"Start Value: {row.get('start_value', 'N/A')}\n"
                f"Target Value: {row.get('target_value', 'N/A')}\n"
                f"Threshold: {row.get('threshold', 'N/A')}\n"
                f"Time to Achieve: {row.get('time_to_achieve', 'N/A')}\n"
                f"Enabled At: {enabled_at_shifted}\n"
                f"Last Read Time: {row.get('last_read_time', 'N/A')}\n"
                f"Last Failure: {row.get('last_failure', 'N/A')}\n"
                f"History: {row.get('history_count', 'N/A')}\n"
                "-----------------------------\n"
            )
        text += "\n"
    
    # Send emails
    for email in emails:
        print(f"[ALERT LOG] Attempting to send email to {email}")
        result = send_status_email(email, subject, message, grouped_data, text, current_time, refresh_time)
        print(f"[ALERT LOG] Email sent to {email}: {result}")
    
    # Send SMS
    for number in phone_numbers:
        print(f"[ALERT LOG] Attempting to send SMS to {number}")
        try:
            sid = send_message(number, text)
            print(f"[ALERT LOG] Message sent to {number} with SID: {sid}")
        except Exception as e:
            print(f"[ALERT LOG] Failed to send SMS to {number}: {e}")

def get_contacts():
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute('SELECT email, phone FROM contacts WHERE enabled = 1')
    contacts = c.fetchall()
    emails = [c[0] for c in contacts]
    phone_numbers = [c[1] for c in contacts]
    conn.close()
    return emails, phone_numbers 