from EmailAPI import send_status_email
from TwilioAPI import send_message

def send_alert(emails, phone_numbers, subject, message, table_data):
    # Group diagnostics by type
    grouped_data = {}
    for row in table_data:
        if row['type'] not in grouped_data:
            grouped_data[row['type']] = []
        grouped_data[row['type']].append(row)
    
    # Create separate text messages for each type
    text = f"{message}\n\n"
    for dtype, diagnostics in grouped_data.items():
        text += f"{dtype} Diagnostics:\n"
        for row in diagnostics:
            text += f"{row['code']} - {row['description']} {row['state']} {row['last_failure']} (History: {row['history_count']})\n"
        text += "\n"
    
    # Send emails
    for email in emails:
        print(f"[ALERT LOG] Attempting to send email to {email}")
        result = send_status_email(email, subject, message, grouped_data, text)
        print(f"[ALERT LOG] Email sent to {email}: {result}")
    
    # Send SMS
    for number in phone_numbers:
        print(f"[ALERT LOG] Attempting to send SMS to {number}")
        try:
            sid = send_message(number, text)
            print(f"[ALERT LOG] Message sent to {number} with SID: {sid}")
        except Exception as e:
            print(f"[ALERT LOG] Failed to send SMS to {number}: {e}") 