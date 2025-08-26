import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from xhtml2pdf import pisa
import os
from dotenv import load_dotenv
import io
import datetime
import threading
import queue
import time

# Load environment variables
load_dotenv()

# Global email queue and worker thread
email_queue = queue.Queue()
email_worker_running = False
email_worker_thread = None

# Start the email worker thread automatically when module is imported
def _auto_start_worker():
    """Automatically start the email worker when module is imported"""
    try:
        start_email_worker()
    except Exception as e:
        print(f"[EMAIL WARNING] Could not auto-start email worker: {e}")

# Start worker thread automatically
_auto_start_worker()

def start_email_worker():
    """Start the email worker thread if it's not already running"""
    global email_worker_running, email_worker_thread
    
    if not email_worker_running:
        email_worker_running = True
        email_worker_thread = threading.Thread(target=email_worker, daemon=True)
        email_worker_thread.start()
        print("[EMAIL DEBUG] Email worker thread started")
    else:
        print("[EMAIL DEBUG] Email worker thread already running")

def stop_email_worker():
    """Gracefully stop the email worker thread"""
    global email_worker_running
    
    if email_worker_running:
        print("[EMAIL DEBUG] Stopping email worker thread...")
        email_worker_running = False
        
        # Wait for the worker to finish processing current emails
        if email_worker_thread and email_worker_thread.is_alive():
            email_worker_thread.join(timeout=10)  # Wait up to 10 seconds
            
            if email_worker_thread.is_alive():
                print("[EMAIL WARNING] Email worker thread did not stop gracefully")
            else:
                print("[EMAIL DEBUG] Email worker thread stopped gracefully")
    else:
        print("[EMAIL DEBUG] Email worker thread not running")

def email_worker():
    """Background worker thread that processes email queue"""
    global email_worker_running
    
    print("[EMAIL DEBUG] Email worker thread started and running")
    
    while email_worker_running:
        try:
            # Get email task from queue with timeout
            try:
                email_task = email_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            
            # Process the email
            recipients, subject, message, table_data, text, current_time = email_task
            
            print(f"[EMAIL DEBUG] Processing email for {recipients}...")
            
            # Send email synchronously in this thread
            success = _send_status_email_sync(recipients, subject, message, table_data, text, current_time)
            
            if success:
                print(f"[EMAIL DEBUG] Email sent successfully to {recipients}")
            else:
                print(f"[EMAIL ERROR] Failed to send email to {recipients}")
                
            # Mark task as done
            email_queue.task_done()
            
        except Exception as e:
            print(f"[EMAIL ERROR] Error in email worker: {e}")
            # Mark task as done even if it failed
            try:
                email_queue.task_done()
            except:
                pass
    
    print("[EMAIL DEBUG] Email worker thread stopped")

def get_email_queue_status():
    """Get current status of the email queue"""
    return {
        'queue_size': email_queue.qsize(),
        'worker_running': email_worker_running,
        'worker_alive': email_worker_thread.is_alive() if email_worker_thread else False
    }

def format_datetime(dt):
    if not dt:
        return ''
    if isinstance(dt, str):
        try:
            dt = datetime.datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime('%d %B, %Y %H:%M:%S')

def send_status_email(recipients, subject, message, table_data, text, current_time):
    """
    Asynchronous email sending - adds email to queue and returns immediately
    """
    # Start email worker if not running
    start_email_worker()
    
    # Add email task to queue
    email_task = (recipients, subject, message, table_data, text, current_time)
    email_queue.put(email_task)
    
    print(f"[EMAIL DEBUG] Email queued for {recipients} - will be sent asynchronously")
    return True

def _send_status_email_sync(recipients, subject, message, table_data, text, current_time):
    """
    Internal synchronous email sending function used by the worker thread
    """
    # Get email credentials from environment variables
    sender_email = os.getenv('SENDER_EMAIL')
    password = os.getenv('EMAIL_PASSWORD')
    
    print(f"[EMAIL DEBUG] Sending email from {sender_email} to {recipients}")
    
    if not sender_email or not password:
        error_msg = "Email credentials not found in environment variables"
        print(f"[EMAIL ERROR] {error_msg}")
        return False

    # Convert single recipient to list
    if isinstance(recipients, str):
        recipients = [recipients]
    
    # Create the email
    msg = MIMEMultipart('alternative')
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = subject

    # Read and attach the logo
    try:
        with open('static/logo.png', 'rb') as f:
            logo = MIMEImage(f.read())
            logo.add_header('Content-ID', '<logo>')
            msg.attach(logo)
    except FileNotFoundError:
        print("Warning: Logo file 'static/logo.png' not found. Email will be sent without logo.")
    except Exception as e:
        print(f"Warning: Error reading logo file: {e}. Email will be sent without logo.")

    # HTML content with enhanced professional styling
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>{subject}</title>
</head>
<body style=\"background: #f4f6fa; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #222; margin: 0; padding: 0;\">
    <div style=\"max-width: 700px; margin: 40px auto; background: #fff; border-radius: 14px; border: 1px solid #e0e6ed; overflow: hidden;\">
        <div style=\"background: #f8fafc; padding: 28px 32px 12px 32px; text-align: center; border-bottom: 1px solid #e0e6ed;\">
            <a href=\"https://ace.ontariotechu.ca\" target=\"_blank\" style=\"display: inline-block;\">
                <img src=\"cid:logo\" alt=\"Company Logo\" style=\"height: 44px; margin-bottom: 8px;\">
            </a>
            <div style=\"font-size: 19px; color: #1a2a44; font-weight: 700; margin-bottom: 4px; letter-spacing: 0.5px;\">Automotive Center of Excellence</div>
            <div style=\"font-size: 13px; color: #7f8c8d; letter-spacing: 1px;\">Automated Diagnostics Report</div>
        </div>
        <div style=\"padding: 32px 24px 28px 24px;\">
            <h1 style=\"color: #1a2a44; font-size: 27px; margin-bottom: 16px; text-align: center; letter-spacing: 0.5px;\">Status Report</h1>
            <p style=\"font-size: 16px; margin-bottom: 22px; text-align: center; color: #444;\">{message}</p>
            <div style=\"background: #f4f6fa; padding: 14px 18px; border-radius: 8px; margin-bottom: 28px; border: 1px solid #e0e6ed; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px; font-size: 15px;\">
                <span><strong>Last Read Time:</strong> {format_datetime(current_time)}</span>
            </div>
"""
    for room, diagnostics in table_data.items():
        html += f"""
            <h2 style=\"color: #1a2a44; font-size: 19px; margin: 28px 0 12px 0; border-left: 3px solid #1a2a44; padding-left: 12px; letter-spacing: 0.2px;\">Room: {room}</h2>
            <div style=\"overflow-x: auto;\">
            <table style=\"width: 100%; border-collapse: collapse; font-size: 15px; background: #fff; border-radius: 6px;\">
                <thead>
                    <tr style=\"background: #1a2a44; color: #fff;\">
                        <th style=\"padding: 13px 8px; border-right: 1px solid #e0e6ed; text-align: left; font-weight: 600;\">Code</th>
                        <th style=\"padding: 13px 8px; border-right: 1px solid #e0e6ed; text-align: left; font-weight: 600;\">Description</th>
                        <th style=\"padding: 13px 8px; border-right: 1px solid #e0e6ed; text-align: left; font-weight: 600;\">Type</th>
                        <th style=\"padding: 13px 8px; border-right: 1px solid #e0e6ed; text-align: left; font-weight: 600;\">State</th>
                        <th style=\"padding: 13px 8px; border-right: 1px solid #e0e6ed; text-align: left; font-weight: 600;\">Fault Type</th>
                        <th style=\"padding: 13px 8px; border-right: 1px solid #e0e6ed; text-align: left; font-weight: 600;\">Current Value</th>
                        <th style=\"padding: 13px 8px; border-right: 1px solid #e0e6ed; text-align: left; font-weight: 600;\">Start Value</th>
                        <th style=\"padding: 13px 8px; border-right: 1px solid #e0e6ed; text-align: left; font-weight: 600;\">Target Value</th>
                        <th style=\"padding: 13px 8px; border-right: 1px solid #e0e6ed; text-align: left; font-weight: 600;\">Threshold</th>
                        <th style=\"padding: 13px 8px; border-right: 1px solid #e0e6ed; text-align: left; font-weight: 600;\">Time to Achieve</th>
                        <th style=\"padding: 13px 8px; border-right: 1px solid #e0e6ed; text-align: left; font-weight: 600;\">Enabled At</th>
                        <th style=\"padding: 13px 8px; border-right: 1px solid #e0e6ed; text-align: left; font-weight: 600;\">Last Read Time</th>
                        <th style=\"padding: 13px 8px; border-right: 1px solid #e0e6ed; text-align: left; font-weight: 600;\">Last Failure</th>
                        <th style=\"padding: 13px 8px; text-align: left; font-weight: 600;\">History</th>
                    </tr>
                </thead>
                <tbody>
"""
        for i, row in enumerate(diagnostics):
            state_color = {'Pass': '#2ecc71', 'Fail': '#e74c3c', 'NoStatus': '#7f8c8d'}.get(row['state'], '#7f8c8d')
            state_bg = {'Pass': '#eafaf1', 'Fail': '#fdeaea', 'NoStatus': '#f4f6fa'}.get(row['state'], '#f4f6fa')
            border_style = 'border-bottom: 1px solid #e0e6ed;' if i < len(diagnostics)-1 else ''
            # Format enabled_at with -4 hours if present
            enabled_at = row.get('enabled_at', 'N/A')
            if enabled_at and enabled_at != 'N/A':
                try:
                    from datetime import datetime, timedelta
                    if isinstance(enabled_at, str):
                        enabled_at_dt = datetime.fromisoformat(enabled_at)
                    else:
                        enabled_at_dt = enabled_at
                    enabled_at_shifted = (enabled_at_dt - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    enabled_at_shifted = enabled_at
            else:
                enabled_at_shifted = 'N/A'
            html += f"""                    <tr style=\"background: {state_bg}; {border_style}\">
                        <td style=\"padding: 11px 8px;\">{row['code']}</td>
                        <td style=\"padding: 11px 8px;\">{row['description']}</td>
                        <td style=\"padding: 11px 8px;\">{row['type']}</td>
                        <td style=\"padding: 11px 8px;\">
                            <span style=\"display: inline-block; min-width: 54px; padding: 2px 10px; border-radius: 12px; background: {state_bg}; color: {state_color}; font-weight: 600; font-size: 14px; text-align: center;\">{row['state']}</span>
                        </td>
                        <td style=\"padding: 11px 8px;\">
                            <span style=\"display: inline-block; padding: 2px 8px; border-radius: 8px; background: {state_bg}; color: {state_color}; font-weight: 600; font-size: 12px; text-align: center;\">{row.get('fault_type', 'N/A')}</span>
                        </td>
                        <td style=\"padding: 11px 8px;\">{row.get('value', 'N/A')}</td>
                        <td style=\"padding: 11px 8px;\">{row.get('start_value', 'N/A')}</td>
                        <td style=\"padding: 11px 8px;\">{row.get('target_value', 'N/A')}</td>
                        <td style=\"padding: 11px 8px;\">{row.get('threshold', 'N/A')}</td>
                        <td style=\"padding: 11px 8px;\">{row.get('time_to_achieve', 'N/A')}</td>
                        <td style=\"padding: 11px 8px;\">{enabled_at_shifted}</td>
                        <td style=\"padding: 11px 8px;\">{row.get('last_read_time', 'N/A')}</td>
                        <td style=\"padding: 11px 8px;\">{row['last_failure']}</td>
                        <td style=\"padding: 11px 8px;\">{row.get('history_count', 'N/A')}</td>
                    </tr>
"""
        html += """                </tbody>
            </table>
            </div>
"""
    html += f"""            <div style=\"margin-top: 30px; padding-top: 18px; border-top: 1px solid #e0e6ed; text-align: center; color: #7f8c8d; font-size: 13px;\">
                <div style=\"margin-bottom: 6px;\">Generated on {format_datetime(current_time)}. Do not reply to this email.</div>
                <div style=\"font-size: 12px;\">&copy; {datetime.now().year} Automotive Center of Excellence. All rights reserved.</div>
                <div style=\"margin-top: 4px;\"><a href=\"https://ace.ontariotechu.ca\" style=\"color: #1a2a44; text-decoration: none;\">ace.ontariotechu.ca</a></div>
            </div>
        </div>
    </div>
    <style>
        @media only screen and (max-width: 800px) {{{{
            .container-table-wrap {{{{ overflow-x: auto; }}}}
            table {{{{ min-width: 600px; }}}}
        }}}}
    </style>
</body>
</html>"""

    # Attach plain text and HTML versions
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))

    # Use only the working method: SMTP_SSL on port 465
    server = None
    try:
        print(f"[EMAIL DEBUG] Connecting to smtp.gmail.com:465 using SSL...")
        
        # Create SSL connection with proper timeouts
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30)
        print(f"[EMAIL DEBUG] SSL connection created successfully")
        
        # Login
        print(f"[EMAIL DEBUG] Logging in...")
        server.login(sender_email, password)
        
        # Send email
        print(f"[EMAIL DEBUG] Sending email...")
        server.sendmail(sender_email, recipients, msg.as_string())
        
        print(f"[EMAIL DEBUG] Email sent successfully!")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL ERROR] Authentication failed: {e}")
        print("  Check if your Gmail App Password is correct and 2FA is enabled")
        return False
    except smtplib.SMTPConnectError as e:
        print(f"[EMAIL ERROR] Connection failed: {e}")
        print("  Check network connectivity and firewall settings")
        return False
    except smtplib.SMTPException as e:
        print(f"[EMAIL ERROR] SMTP error: {e}")
        return False
    except Exception as e:
        print(f"[EMAIL ERROR] Unexpected error: {e}")
        return False
    finally:
        if server:
            try:
                print(f"[EMAIL DEBUG] Closing SMTP connection...")
                server.quit()
                print(f"[EMAIL DEBUG] SMTP connection closed")
            except Exception as e:
                print(f"[EMAIL WARNING] Error closing SMTP connection: {e}")

def generate_pdf_html(subject, message, table_data, current_time, refresh_time):
    # Use table-based layout and inline styles for xhtml2pdf compatibility
    pdf_html = f"""
    <html>
    <head>
        <meta charset='UTF-8'>
        <title>{subject}</title>
    </head>
    <body style='font-family: Arial, Helvetica, sans-serif; color: #222; background: #fff;'>
        <table width='600' align='center' cellpadding='0' cellspacing='0' style='border:1px solid #e0e6ed; border-radius:12px; box-shadow:0 4px 24px #1e2a501a;'>
            <tr>
                <td style='background:#f8fafc; text-align:center; padding:24px 0 8px 0; border-bottom:1px solid #e0e6ed;'>
                    <img src='static/logo.png' alt='Company Logo' style='height:48px; margin-bottom:8px;'><br>
                    <div style='font-size:18px; color:#1a2a44; font-weight:600; margin-bottom:4px;'>Automotive Center of Excellence</div>
                    <div style='font-size:13px; color:#7f8c8d; letter-spacing:1px;'>Automated Diagnostics Report</div>
                </td>
            </tr>
            <tr>
                <td style='padding:24px;'>
                    <h1 style='color:#1a2a44; font-size:24px; text-align:center; margin-bottom:16px;'>Status Report</h1>
                    <p style='font-size:15px; text-align:center; margin-bottom:18px;'>{message}</p>
                    <table width='100%' style='background:#f4f6fa; border-radius:8px; border:1px solid #e0e6ed; margin-bottom:24px;'>
                        <tr>
                            <td style='padding:10px 16px; font-size:14px;'><b>Last Read Time:</b> {format_datetime(current_time)}</td>
                            <td style='padding:10px 16px; font-size:14px;'><b>Refresh Time:</b> {refresh_time} seconds</td>
                        </tr>
                    </table>
    """
    for room, diagnostics in table_data.items():
        pdf_html += f"""
                    <h2 style='color:#1a2a44; font-size:18px; margin:24px 0 10px 0; border-left:4px solid #1a2a44; padding-left:10px;'>Room: {room}</h2>
                    <table width='100%' border='0' cellpadding='0' cellspacing='0' style='border-collapse:collapse; font-size:14px; margin-bottom:24px;'>
                        <tr style='background:#1a2a44; color:#fff;'>
                            <th style='padding:10px; border:1px solid #e0e6ed;'>Code</th>
                            <th style='padding:10px; border:1px solid #e0e6ed;'>Description</th>
                            <th style='padding:10px; border:1px solid #e0e6ed;'>Type</th>
                            <th style='padding:10px; border:1px solid #e0e6ed;'>State</th>
                            <th style='padding:10px; border:1px solid #e0e6ed;'>Fault Type</th>
                            <th style='padding:10px; border:1px solid #e0e6ed;'>Value</th>
                            <th style='padding:10px; border:1px solid #e0e6ed;'>Last Read Time</th>
                            <th style='padding:10px; border:1px solid #e0e6ed;'>Last Failure</th>
                            <th style='padding:10px; border:1px solid #e0e6ed;'>History Count</th>
                        </tr>
        """
        for i, row in enumerate(diagnostics):
            state_color = {'Pass': '#2ecc71', 'Fail': '#e74c3c', 'NoStatus': '#7f8c8d'}.get(row['state'], '#7f8c8d')
            bg_color = '#f9f9f9' if i % 2 == 0 else '#fff'
            pdf_html += f"""
                        <tr style='background:{bg_color};'>
                            <td style='padding:8px; border:1px solid #e0e6ed;'>{row['code']}</td>
                            <td style='padding:8px; border:1px solid #e0e6ed;'>{row['description']}</td>
                            <td style='padding:8px; border:1px solid #e0e6ed;'>{row['type']}</td>
                            <td style='padding:8px; border:1px solid #e0e6ed; color:{state_color}; font-weight:bold;'>{row['state']}</td>
                            <td style='padding:8px; border:1px solid #e0e6ed; color:{state_color}; font-weight:bold;'>{row.get('fault_type', 'N/A')}</td>
                            <td style='padding:8px; border:1px solid #e0e6ed;'>{row.get('value', 'N/A')}</td>
                            <td style='padding:8px; border:1px solid #e0e6ed;'>{row.get('last_read_time', 'N/A')}</td>
                            <td style='padding:8px; border:1px solid #e0e6ed;'>{row['last_failure']}</td>
                            <td style='padding:8px; border:1px solid #e0e6ed;'>{row['history_count']}</td>
                        </tr>
            """
        pdf_html += "</table>"
    pdf_html += f"""
                    <div style='margin-top:24px; text-align:center; color:#7f8c8d; font-size:12px;'>
                        Generated on {format_datetime(current_time)}. Do not reply to this email.<br>
                        &copy; {datetime.now().year} Automotive Center of Excellence. All rights reserved.<br>
                        <a href='https://ace.ontariotechu.ca' style='color:#1a2a44; text-decoration:none;'>ace.ontariotechu.ca</a>
                    </div>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return pdf_html 