@echo off
echo Setting up Diagnostic Controller for Windows...
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running!
    echo Please install Docker Desktop for Windows from: https://www.docker.com/products/docker-desktop
    echo Make sure Docker Desktop is running before continuing.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    echo Creating .env file...
    echo # Database Configuration > .env
    echo DB_NAME=diagnostics >> .env
    echo DB_USER=diagnostics_user >> .env
    echo DB_PASSWORD=your_secure_password >> .env
    echo. >> .env
    echo # Email Configuration >> .env
    echo SENDER_EMAIL=your_email@gmail.com >> .env
    echo EMAIL_PASSWORD=your_app_password >> .env
    echo. >> .env
    echo # Twilio Configuration >> .env
    echo TWILIO_ACCOUNT_SID=your_twilio_sid >> .env
    echo TWILIO_AUTH_TOKEN=your_twilio_auth_token >> .env
    echo TWILIO_MESSAGING_SERVICE_SID=your_twilio_messaging_service_sid >> .env
    echo. >> .env
    echo # Flask Secret Key >> .env
    echo FLASK_SECRET_KEY=your_secure_secret_key_here >> .env
    echo.
    echo .env file created! Please edit it with your actual credentials.
    echo.
)

REM Create necessary directories if they don't exist
if not exist "mosquitto\data" mkdir mosquitto\data
if not exist "mosquitto\log" mkdir mosquitto\log

REM Set proper permissions for mosquitto directories
echo Setting up mosquitto directories...

REM Build and start the services
echo.
echo Building and starting Docker services...
docker-compose up -d --build

echo.
echo Setup complete! 
echo.
echo Next steps:
echo 1. Edit the .env file with your actual credentials
echo 2. Restart services: docker-compose down && docker-compose up -d
echo 3. Access the web interface at: http://localhost:5001
echo 4. Default login: user / password
echo.
pause 