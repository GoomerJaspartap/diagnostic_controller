# Industrial Diagnostics Monitoring System

A comprehensive web-based system for monitoring and managing industrial diagnostic codes through Modbus communication. This system provides real-time monitoring, alerting, and management of various industrial parameters like temperature and humidity.

## Features

### Core Functionality
- Real-time monitoring of industrial diagnostic codes via Modbus TCP
- Support for multiple data types (int16, int32, float32, int64, float64)
- Configurable upper and lower limits for each diagnostic code
- Automatic state determination (Pass/Fail/No Status)
- History tracking of failures and readings
- Configurable refresh rates for data polling

### User Interface
- Modern, responsive web dashboard
- Real-time updates of diagnostic status
- Separate views for temperature and humidity monitoring
- Notification center for failed or problematic diagnostics
- User authentication and authorization system

### Alert System
- Email notifications for diagnostic failures
- SMS alerts via Twilio integration
- Configurable contact management
- Multiple notification channels support

### Diagnostic Code Management
- Add, edit, and delete diagnostic codes
- Enable/disable individual diagnostics
- Configure Modbus parameters:
  - IP address and port
  - Unit ID
  - Register type (Holding/Input)
  - Register address
  - Data type and byte order
  - Scaling and offset values
  - Upper and lower limits

### User Management
- Multi-user support
- Secure password hashing
- User role management
- Session-based authentication

## Technical Details

### Architecture
- Built with Flask (Python web framework)
- SQLite database for data storage
- Modbus TCP client for industrial communication
- RESTful API endpoints for data access

### Database Schema
- Users table for authentication
- Diagnostic codes table for monitoring configuration
- Contacts table for alert recipients
- App settings table for system configuration

### Security Features
- Password hashing using Werkzeug
- Session-based authentication
- Input validation and sanitization
- Protected API endpoints

## Setup Instructions

1. Install Python dependencies:
```bash
pip install flask pymodbus werkzeug
```

2. Initialize the database:
```bash
python app.py
```

3. Configure the system:
   - Set up Modbus device connections
   - Add diagnostic codes
   - Configure alert contacts
   - Set refresh rates

4. Start the application:
```bash
python main.py
```

## Default Credentials
- Username: user
- Password: password

**Note:** Change these credentials immediately after first login.

## File Structure
- `app.py`: Main Flask application and routes
- `read_modbus_data.py`: Modbus communication and data processing
- `EmailAPI.py`: Email notification system
- `TwilioAPI.py`: SMS notification system
- `AlertAPI.py`: Alert management system
- `update_diagnostic.py`: Diagnostic code update logic
- `templates/`: HTML templates for the web interface
- `static/`: Static assets (CSS, JavaScript, images)
- `diagnostics.db`: SQLite database file

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details. 