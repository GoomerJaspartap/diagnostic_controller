# Diagnostic Controller

A web-based diagnostics and alerting system for Modbus-connected devices, featuring:
- Real-time dashboard and logs
- Email and SMS alerts
- PDF report generation
- User and contact management
- PostgreSQL backend

## Features
- **Dashboard**: View live diagnostic status for all codes
- **Logs**: Persistent, filterable log of all diagnostic state changes (Pass, Fail, No Status)
- **Email & SMS Alerts**: Automated notifications for faults
- **PDF Reports**: Branded, professional email and PDF status reports
- **User & Contact Management**: Add/edit users and emergency contacts
- **Modbus Polling**: Reads and updates diagnostics from Modbus devices

## Setup

### 1. Clone the repository
```bash
git clone <repo-url>
cd Diagnostics
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
Create a `.env` file in the root directory with:
```
SENDER_EMAIL=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth
TWILIO_MESSAGING_SERVICE_SID=your_twilio_msg_sid
```

### 4. PostgreSQL Setup
- Ensure PostgreSQL is running and a database named `diagnostics` exists.
- The app will auto-create all required tables on first run.

### 5. Run the Application
```bash
python app.py
```
- The web app will be available at `http://localhost:5001`

### 6. Modbus Polling
- To start Modbus polling and logging, run:
```bash
python read_modbus_data.py
```

## Directory Structure
- `app.py` - Main Flask app
- `read_modbus_data.py` - Modbus polling and logging
- `EmailAPI.py` - Email and PDF logic
- `AlertAPI.py` - Alert logic (email/SMS)
- `TwilioAPI.py` - SMS sending
- `templates/` - HTML templates
- `static/` - CSS and logo

## Notes
- All logs (Pass, Fail, No Status) are stored in the `logs` table and viewable in the web UI.
- The app supports real-time log updates and filtering.
- Email and SMS require valid credentials and configuration.

## License
MIT 