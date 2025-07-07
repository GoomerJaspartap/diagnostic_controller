# Diagnostic Controller

A comprehensive web-based diagnostics and alerting system for industrial devices, supporting both Modbus and MQTT data sources. Features real-time monitoring, automated alerts, professional reporting capabilities, and **room-based organization** for better facility management.

## 🚀 Features

- **Multi-Protocol Support**: Monitor devices via Modbus TCP and MQTT
- **Room Management**: Organize diagnostic codes by rooms/locations for better facility oversight
- **Real-time Dashboard**: Live diagnostic status with auto-refresh, grouped by room
- **Comprehensive Logging**: Persistent, filterable logs of all state changes
- **Smart Alerting**: Email and SMS notifications for fault conditions
- **Professional Reports**: PDF generation with branded templates
- **User Management**: Secure authentication and user administration
- **Contact Management**: Manage emergency contacts with SMS/email preferences
- **Docker Ready**: Complete containerized deployment with Docker Compose

## 🏗️ Architecture

The system consists of several microservices:

- **Web Application**: Flask-based dashboard and management interface
- **PostgreSQL Database**: Persistent storage for diagnostics, logs, configuration, and room management
- **MQTT Broker**: Eclipse Mosquitto for MQTT device communication
- **MQTT Reader**: Service that processes MQTT sensor data
- **Modbus Reader**: Service that polls Modbus devices

## 🏢 Room Management

The system now supports organizing diagnostic codes by rooms or locations:

- **Room CRUD Operations**: Create, read, update, and delete rooms through the web interface
- **Diagnostic Assignment**: Assign diagnostic codes to specific rooms during creation or editing
- **Room-based Dashboard**: View diagnostics grouped by room for better facility oversight
- **Search by Room**: Filter diagnostic codes by room name in the diagnostic codes page

### Migration from Existing Installations

If you're upgrading from a previous version, run the migration script to add room management:

```bash
# Run the migration script
python migrate_rooms.py
```

This will:
- Add the `room_id` column to the `diagnostic_codes` table
- Create the `rooms` table
- Add sample rooms (Lab 101, Control Room, Server Room, etc.)
- Preserve all existing diagnostic codes (they'll be marked as "Unassigned")

## 🐳 Docker Setup

### Prerequisites

- Docker and Docker Compose installed
- Git (to clone the repository)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd diagnostic_controller
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   # Database Configuration
   DB_NAME=diagnostics
   DB_USER=diagnostics_user
   DB_PASSWORD=your_secure_password
   
   # Email Configuration (Gmail recommended)
   SENDER_EMAIL=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password
   
   # Twilio Configuration (for SMS alerts)
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_MESSAGING_SERVICE_SID=your_twilio_messaging_service_sid
   
   # Flask Secret Key
   FLASK_SECRET_KEY=your_secure_secret_key_here
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Web Dashboard: http://localhost:5001
   - Default credentials: `user` / `password`

### Service Details

| Service | Port | Description |
|---------|------|-------------|
| Web App | 5001 | Main dashboard and management interface |
| PostgreSQL | 5432 | Database (internal access only) |
| MQTT Broker | 1883 | MQTT message broker |

### Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f webapp
docker-compose logs -f mqtt-reader
docker-compose logs -f modbus-reader

# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes all data)
docker-compose down -v

# Rebuild containers
docker-compose up -d --build

# Access database directly
docker-compose exec db psql -U diagnostics_user -d diagnostics
```

## 📊 Configuration

### Adding Diagnostic Codes

1. **Access the web interface** at http://localhost:5001
2. **Navigate to "Diagnostic Codes"**
3. **Click "Add Diagnostic Code"**
4. **Configure based on your data source:**

#### MQTT Configuration
- **Data Source Type**: MQTT
- **Broker**: `mqtt-broker` (internal Docker network)
- **Port**: 1883
- **Topic**: Your MQTT topic (e.g., `sensors/temperature/1`)
- **QoS**: 0 (default)
- **Limits**: Set upper/lower limits for alerts

#### Modbus Configuration
- **Data Source Type**: Modbus
- **IP Address**: Your Modbus device IP
- **Port**: Usually 502
- **Unit ID**: Modbus device ID
- **Register Type**: Holding/Input Register
- **Register Address**: Register number to read
- **Data Type**: int16, int32, float32, etc.
- **Byte Order**: big-endian, little-endian, or word-swapped

### Email Setup (Gmail)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. **Use the app password** in your `.env` file

### SMS Setup (Twilio)

1. **Create Twilio account** at https://www.twilio.com
2. **Get credentials** from Twilio Console
3. **Create Messaging Service** for better delivery rates
4. **Add credentials** to your `.env` file

## 🧪 Testing

### MQTT Testing

1. **Start the system**: `docker-compose up -d`
2. **Add MQTT diagnostic code** in web interface
3. **Install MQTT client**
   ```bash
   pip install paho-mqtt
   ```
4. **Run test sensor**
   ```bash
   python test_mqtt_sensor.py
   ```
5. **Monitor dashboard** for real-time updates

### Modbus Testing

1. **Configure Modbus diagnostic code** in web interface
2. **Ensure Modbus device** is accessible from Docker network
3. **Monitor logs**: `docker-compose logs -f modbus-reader`

## 📁 Project Structure

```
diagnostic_controller/
├── app.py                 # Main Flask application
├── read_modbus_data.py    # Modbus polling service
├── read_mqtt_data.py      # MQTT data processing
├── EmailAPI.py           # Email and PDF generation
├── AlertAPI.py           # Alert management
├── TwilioAPI.py          # SMS functionality
├── migrate_rooms.py      # Room management migration script
├── docker-compose.yml    # Docker orchestration
├── Dockerfile.webapp     # Web app container
├── Dockerfile.mqtt       # MQTT reader container
├── Dockerfile.modbus     # Modbus reader container
├── requirements.txt      # Python dependencies
├── templates/            # HTML templates
│   ├── rooms.html        # Room management interface
│   ├── add_room.html     # Add room form
│   ├── edit_room.html    # Edit room form
│   └── ...               # Other templates
├── static/              # CSS, JS, images
├── mosquitto/           # MQTT broker config
│   ├── config/
│   ├── data/
│   └── log/
└── db/                  # Database files
```

## 🔧 Troubleshooting

### Common Issues

1. **Database connection errors**
   ```bash
   # Check if database is running
   docker-compose ps
   
   # View database logs
   docker-compose logs db
   ```

2. **MQTT connection issues**
   ```bash
   # Check MQTT broker status
   docker-compose logs mqtt-broker
   
   # Test MQTT connectivity
   docker-compose exec mqtt-broker mosquitto_pub -h localhost -t test -m "hello"
   ```

3. **Modbus connection issues**
   ```bash
   # Check Modbus reader logs
   docker-compose logs modbus-reader
   
   # Verify network connectivity
   docker-compose exec modbus-reader ping <modbus-device-ip>
   ```

4. **Email/SMS not working**
   - Verify credentials in `.env` file
   - Check service logs for authentication errors
   - Ensure proper network access for external services

5. **Room management issues**
   - Run migration script: `python migrate_rooms.py`
   - Check database schema: `docker-compose exec db psql -U diagnostics_user -d diagnostics -c "\d rooms"`
   - Verify room assignments in diagnostic codes

### Log Locations

- **Application logs**: `docker-compose logs -f webapp`
- **MQTT logs**: `docker-compose logs -f mqtt-reader`
- **Modbus logs**: `docker-compose logs -f modbus-reader`
- **Database logs**: `docker-compose logs -f db`
- **MQTT broker logs**: `docker-compose logs -f mqtt-broker`

## 🔒 Security Considerations

- **Change default passwords** immediately after first login
- **Use strong database passwords** in production
- **Secure your `.env` file** - never commit to version control
- **Configure firewall rules** for production deployments
- **Use HTTPS** in production environments
- **Regular security updates** for Docker images

## 📈 Production Deployment

For production deployment, consider:

1. **Reverse proxy** (nginx/traefik) for HTTPS termination
2. **Database backups** and monitoring
3. **Log aggregation** (ELK stack, etc.)
4. **Monitoring** (Prometheus, Grafana)
5. **Container orchestration** (Kubernetes, Docker Swarm)
6. **Secrets management** (Docker Secrets, HashiCorp Vault)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review service logs
3. Create an issue in the repository
4. Contact the development team 