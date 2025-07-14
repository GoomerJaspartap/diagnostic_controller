# Windows Setup Guide for Diagnostic Controller

## Prerequisites

1. **Docker Desktop for Windows**
   - Download from: https://www.docker.com/products/docker-desktop
   - Install and start Docker Desktop
   - Ensure Docker is running (check system tray icon)

2. **Git for Windows** (optional)
   - Download from: https://git-scm.com/download/win
   - Or use GitHub Desktop

## Quick Setup

### Option 1: Using the Setup Script (Recommended)
```cmd
# Run the batch file
setup_windows.bat
```

### Option 2: Using PowerShell
```powershell
# Run the PowerShell script
.\setup_windows.ps1
```

### Option 3: Manual Setup
```cmd
# 1. Create .env file
copy .env.example .env

# 2. Create necessary directories
mkdir mosquitto\data
mkdir mosquitto\log

# 3. Start services
docker-compose up -d --build
```

## Common Windows Issues and Solutions

### Issue 1: "Docker is not running"
**Solution:**
- Open Docker Desktop
- Wait for it to fully start (green icon in system tray)
- Restart Docker Desktop if needed

### Issue 2: "Permission denied" errors
**Solution:**
```cmd
# Run Command Prompt as Administrator
# Then run:
docker-compose up -d
```

### Issue 3: Port conflicts (5001, 1883, 5432)
**Solution:**
- Check if other services are using these ports
- Stop conflicting services or change ports in docker-compose.yml

### Issue 4: "Volume mount" errors
**Solution:**
- Ensure mosquitto directories exist:
```cmd
mkdir mosquitto\data
mkdir mosquitto\log
```

### Issue 5: "Environment variables not found"
**Solution:**
- Create .env file with required variables
- See the .env template in this guide

### Issue 6: "Build failed" errors
**Solution:**
```cmd
# Clean and rebuild
docker-compose down
docker system prune -f
docker-compose up -d --build
```

## Environment Variables (.env file)

Create a `.env` file in the project root:

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

## Verification Steps

1. **Check if services are running:**
```cmd
docker-compose ps
```

2. **View logs:**
```cmd
docker-compose logs -f
```

3. **Access the web interface:**
   - Open browser: http://localhost:5001
   - Default login: `user` / `password`

4. **Test MQTT:**
```cmd
python test_mqtt_sensor.py
```

## Troubleshooting Commands

```cmd
# Stop all services
docker-compose down

# Remove all containers and volumes
docker-compose down -v

# Clean Docker cache
docker system prune -f

# Rebuild everything
docker-compose up -d --build

# View specific service logs
docker-compose logs -f webapp
docker-compose logs -f mqtt-broker
docker-compose logs -f mqtt-reader
```

## Windows-Specific Notes

1. **Line Endings**: Git may change line endings. Use:
```cmd
git config --global core.autocrlf true
```

2. **Antivirus**: Some antivirus software may block Docker. Add exceptions for:
   - Docker Desktop
   - Project directory

3. **Windows Defender**: May block port 1883. Add firewall exception:
```cmd
netsh advfirewall firewall add rule name="MQTT" dir=in action=allow protocol=TCP localport=1883
```

4. **WSL2**: If using WSL2 backend, ensure it's properly configured in Docker Desktop settings.

## Getting Help

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Ensure Docker Desktop is running
3. Try restarting Docker Desktop
4. Check Windows Event Viewer for system errors
5. Verify all prerequisites are installed

## Support

For additional help, check:
- Docker Desktop logs
- Windows Event Viewer
- Project README.md for general setup instructions 