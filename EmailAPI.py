import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_status_email(recipients, subject, message, table_data, text, current_time, refresh_time):
    # Get email credentials from environment variables
    sender_email = os.getenv('SENDER_EMAIL')
    password = os.getenv('EMAIL_PASSWORD')
    
    if not sender_email or not password:
        raise ValueError("Email credentials not found in environment variables")

    # Convert single recipient to list
    if isinstance(recipients, str):
        recipients = [recipients]
    
    # Create the email
    msg = MIMEMultipart('alternative')
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = subject

    # HTML content with inline CSS
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>{subject}</title>
</head>
<body style=\"font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;\">
    <div style=\"background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 30px;\">
        <h1 style=\"color: #1a2a44; font-size: 24px; margin-bottom: 20px; text-align: center;\">Status Report</h1>
        <p style=\"font-size: 16px; margin-bottom: 20px;\">{message}</p>
        
        <div style=\"background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;\">
            <p style=\"margin: 5px 0;\"><strong>Last Read Time:</strong> {current_time}</p>
            <p style=\"margin: 5px 0;\"><strong>Refresh Time:</strong> {refresh_time} seconds</p>
        </div>
"""
    
    # Create a table for each diagnostic type
    for dtype, diagnostics in table_data.items():
        html += f"""
        <h2 style=\"color: #1a2a44; font-size: 20px; margin: 30px 0 15px 0;\">{dtype} Diagnostics</h2>
        <table style=\"width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 30px;\">
            <thead>
                <tr style=\"background-color: #1a2a44; color: #ffffff;\">
                    <th style=\"padding: 12px; border: 1px solid #e0e0e0; text-align: left;\">Code</th>
                    <th style=\"padding: 12px; border: 1px solid #e0e0e0; text-align: left;\">Description</th>
                    <th style=\"padding: 12px; border: 1px solid #e0e0e0; text-align: left;\">State</th>
                    <th style=\"padding: 12px; border: 1px solid #e0e0e0; text-align: left;\">Last Failure</th>
                    <th style=\"padding: 12px; border: 1px solid #e0e0e0; text-align: left;\">History Count</th>
                </tr>
            </thead>
            <tbody>
"""
        for i, row in enumerate(diagnostics):
            state_color = {'Pass': '#2ecc71', 'Fail': '#e74c3c', 'NoStatus': '#7f8c8d'}.get(row['state'], '#7f8c8d')
            bg_color = '#f9f9f9' if i % 2 == 0 else '#ffffff'
            html += f"""                <tr style=\"background-color: {bg_color}; transition: background-color 0.2s;\">
                    <td style=\"padding: 12px; border: 1px solid #e0e0e0;\">{row['code']}</td>
                    <td style=\"padding: 12px; border: 1px solid #e0e0e0;\">{row['description']}</td>
                    <td style=\"padding: 12px; border: 1px solid #e0e0e0; color: {state_color}; font-weight: bold;\">{row['state']}</td>
                    <td style=\"padding: 12px; border: 1px solid #e0e0e0;\">{row['last_failure']}</td>
                    <td style=\"padding: 12px; border: 1px solid #e0e0e0;\">{row['history_count']}</td>
                </tr>
"""
        html += """            </tbody>
        </table>
"""
    
    html += f"""        <p style=\"font-size: 12px; color: #7f8c8d; text-align: center; margin-top: 20px;\">Generated on {current_time}. Do not reply to this email.</p>
    </div>

    <!-- Inline CSS for hover and responsiveness -->
    <style>
        tr:hover {{ background-color: #f1f3f5 !important; }}
        @media only screen and (max-width: 600px) {{
            table, thead, tbody, th, td, tr {{ display: block; }}
            thead tr {{ position: absolute; top: -9999px; left: -9999px; }}
            tr {{ border: 1px solid #e0e0e0; margin-bottom: 10px; }}
            td {{ 
                border: none; 
                border-bottom: 1px solid #e0e0e0; 
                position: relative; 
                padding-left: 50%; 
                text-align: right; 
            }}
            td:before {{ 
                position: absolute; 
                left: 12px; 
                content: attr(data-label); 
                font-weight: bold; 
                white-space: nowrap; 
            }}
            td:nth-of-type(1):before {{ content: \"Code\"; }}
            td:nth-of-type(2):before {{ content: \"Description\"; }}
            td:nth-of-type(3):before {{ content: \"State\"; }}
            td:nth-of-type(4):before {{ content: \"Last Failure\"; }}
            td:nth-of-type(5):before {{ content: \"History Count\"; }}
        }}
    </style>
</body>
</html>"""

    # Attach plain text and HTML versions
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))

    # Connect to Gmail's SMTP server
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Enable TLS
        server.login(sender_email, password)  # Login with email and App Password
        server.sendmail(sender_email, recipients, msg.as_string())  # Send email
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        server.quit() 