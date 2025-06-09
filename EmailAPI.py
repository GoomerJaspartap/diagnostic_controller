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

# Load environment variables
load_dotenv()

def format_datetime(dt):
    if not dt:
        return ''
    if isinstance(dt, str):
        try:
            dt = datetime.datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime('%d %B, %Y %H:%M:%S')

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

    # Read and attach the logo
    with open('static/logo.png', 'rb') as f:
        logo = MIMEImage(f.read())
        logo.add_header('Content-ID', '<logo>')
        msg.attach(logo)

    # HTML content with enhanced professional styling
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>{subject}</title>
</head>
<body style=\"background: #f4f6fa; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #222; margin: 0; padding: 0;\">
    <div style=\"max-width: 600px; margin: 40px auto; background: #fff; border-radius: 16px; box-shadow: 0 4px 24px rgba(30, 42, 80, 0.10); border: 1px solid #e0e6ed; overflow: hidden;\">
        <div style=\"background: #f8fafc; padding: 32px 32px 16px 32px; text-align: center; border-bottom: 1px solid #e0e6ed;\">
            <a href=\"https://ace.ontariotechu.ca\" target=\"_blank\" style=\"display: inline-block;\">
                <img src=\"cid:logo\" alt=\"Company Logo\" style=\"height: 48px; margin-bottom: 8px;\">
            </a>
            <div style=\"font-size: 18px; color: #1a2a44; font-weight: 600; margin-bottom: 4px;\">Automotive Center of Excellence</div>
            <div style=\"font-size: 13px; color: #7f8c8d; letter-spacing: 1px;\">Automated Diagnostics Report</div>
        </div>
        <div style=\"padding: 32px;\">
            <h1 style=\"color: #1a2a44; font-size: 28px; margin-bottom: 18px; text-align: center; letter-spacing: 0.5px;\">Status Report</h1>
            <p style=\"font-size: 16px; margin-bottom: 24px; text-align: center;\">{message}</p>
            <div style=\"background: #f4f6fa; padding: 18px 20px; border-radius: 8px; margin-bottom: 28px; border: 1px solid #e0e6ed; display: flex; justify-content: space-between;\">
                <span style=\"font-size: 15px;\"><strong>Last Read Time:</strong> {format_datetime(current_time)}</span>
                <span style=\"font-size: 15px;\"><strong>Refresh Time:</strong> {refresh_time} seconds</span>
            </div>
"""
    
    # Create a table for each diagnostic type
    for dtype, diagnostics in table_data.items():
        html += f"""
            <h2 style=\"color: #1a2a44; font-size: 20px; margin: 30px 0 15px 0; border-left: 4px solid #1a2a44; padding-left: 12px;\">{dtype} Diagnostics</h2>
            <table style=\"width: 100%; border-collapse: separate; border-spacing: 0; font-size: 15px; margin-bottom: 32px; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(30,42,80,0.04);\">
                <thead>
                    <tr style=\"background: #1a2a44; color: #fff;\">
                        <th style=\"padding: 14px 10px; border-right: 1px solid #e0e6ed; text-align: left;\">Code</th>
                        <th style=\"padding: 14px 10px; border-right: 1px solid #e0e6ed; text-align: left;\">Description</th>
                        <th style=\"padding: 14px 10px; border-right: 1px solid #e0e6ed; text-align: left;\">State</th>
                        <th style=\"padding: 14px 10px; border-right: 1px solid #e0e6ed; text-align: left;\">Last Failure</th>
                        <th style=\"padding: 14px 10px; text-align: left;\">History Count</th>
                    </tr>
                </thead>
                <tbody>
"""
        for i, row in enumerate(diagnostics):
            state_color = {'Pass': '#2ecc71', 'Fail': '#e74c3c', 'NoStatus': '#7f8c8d'}.get(row['state'], '#7f8c8d')
            state_bg = {'Pass': '#eafaf1', 'Fail': '#fdeaea', 'NoStatus': '#f4f6fa'}.get(row['state'], '#f4f6fa')
            bg_color = '#f9f9f9' if i % 2 == 0 else '#fff'
            html += f"""                    <tr style=\"background: {bg_color}; transition: background-color 0.2s;\">
                        <td style=\"padding: 12px 10px; border-bottom: 1px solid #e0e6ed;\">{row['code']}</td>
                        <td style=\"padding: 12px 10px; border-bottom: 1px solid #e0e6ed;\">{row['description']}</td>
                        <td style=\"padding: 12px 10px; border-bottom: 1px solid #e0e6ed;\">
                            <span style=\"display: inline-block; min-width: 64px; padding: 4px 14px; border-radius: 16px; background: {state_bg}; color: {state_color}; font-weight: 600; font-size: 14px; text-align: center;\">{row['state']}</span>
                        </td>
                        <td style=\"padding: 12px 10px; border-bottom: 1px solid #e0e6ed;\">{row['last_failure']}</td>
                        <td style=\"padding: 12px 10px; border-bottom: 1px solid #e0e6ed;\">{row['history_count']}</td>
                    </tr>
"""
        html += """                </tbody>
            </table>
"""
    html += f"""            <div style=\"margin-top: 32px; padding-top: 24px; border-top: 1px solid #e0e6ed; text-align: center; color: #7f8c8d; font-size: 13px;\">
                <div style=\"margin-bottom: 6px;\">Generated on {format_datetime(current_time)}. Do not reply to this email.</div>
            </div>
        </div>
    </div>
    <style>
        tr:hover {{ background-color: #f1f3f5 !important; }}
        @media only screen and (max-width: 600px) {{
            body {{ padding: 0 !important; }}
            .container {{ padding: 0 !important; }}
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

    # Generate PDF from PDF-optimized HTML
    pdf_html = generate_pdf_html(subject, message, table_data, current_time, refresh_time)
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(pdf_html), dest=pdf_buffer)
    if not pisa_status.err:
        pdf_buffer.seek(0)
        pdf_attachment = MIMEApplication(pdf_buffer.read(), _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename='diagnostics_report.pdf')
        msg.attach(pdf_attachment)

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
    for dtype, diagnostics in table_data.items():
        pdf_html += f"""
                    <h2 style='color:#1a2a44; font-size:18px; margin:24px 0 10px 0; border-left:4px solid #1a2a44; padding-left:10px;'>{dtype} Diagnostics</h2>
                    <table width='100%' border='0' cellpadding='0' cellspacing='0' style='border-collapse:collapse; font-size:14px; margin-bottom:24px;'>
                        <tr style='background:#1a2a44; color:#fff;'>
                            <th style='padding:10px; border:1px solid #e0e6ed;'>Code</th>
                            <th style='padding:10px; border:1px solid #e0e6ed;'>Description</th>
                            <th style='padding:10px; border:1px solid #e0e6ed;'>State</th>
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
                            <td style='padding:8px; border:1px solid #e0e6ed; color:{state_color}; font-weight:bold;'>{row['state']}</td>
                            <td style='padding:8px; border:1px solid #e0e6ed;'>{row['last_failure']}</td>
                            <td style='padding:8px; border:1px solid #e0e6ed;'>{row['history_count']}</td>
                        </tr>
            """
        pdf_html += "</table>"
    pdf_html += f"""
                    <div style='margin-top:24px; text-align:center; color:#7f8c8d; font-size:12px;'>
                        Generated on {format_datetime(current_time)}. Do not reply to this email.<br>
                        &copy; {format_datetime(current_time)[:4]} Automotive Center of Excellence. All rights reserved.<br>
                        <a href='https://ace.ontariotechu.ca' style='color:#1a2a44; text-decoration:none;'>ace.ontariotechu.ca</a>
                    </div>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return pdf_html 