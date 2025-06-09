from EmailAPI import send_status_email
from TwilioAPI import send_message
import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

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
            dt = datetime.datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime('%d %B, %Y %H:%M:%S')

def send_alert(emails, phone_numbers, subject, message, table_data, current_time=None, refresh_time=None):
    # Get refresh time if not provided
    if refresh_time is None:
        refresh_time = get_refresh_time()
    
    # Get current time if not provided
    if current_time is None:
        current_time = format_datetime(datetime.datetime.now())
    else:
        current_time = format_datetime(current_time)
    
    # Group diagnostics by type
    grouped_data = {}
    for row in table_data:
        if row['type'] not in grouped_data:
            grouped_data[row['type']] = []
        grouped_data[row['type']].append(row)
    
    # Create separate text messages for each type
    text = f"{message}\n\n"
    text += f"Last Read Time: {current_time}\n"
    text += f"Refresh Time: {refresh_time} seconds\n\n"
    
    for dtype, diagnostics in grouped_data.items():
        text += f"{dtype} Diagnostics:\n"
        for row in diagnostics:
            text += f"{row['code']} - {row['description']} {row['state']} {row['last_failure']} (History: {row['history_count']})\n"
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