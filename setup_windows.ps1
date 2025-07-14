# Windows PowerShell Setup Script for Diagnostic Controller
Write-Host "Setting up Diagnostic Controller for Windows..." -ForegroundColor Green
Write-Host ""

# Check if Docker is installed
try {
    $dockerVersion = docker --version
    Write-Host "Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not installed or not running!" -ForegroundColor Red
    Write-Host "Please install Docker Desktop for Windows from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    Write-Host "Make sure Docker Desktop is running before continuing." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    @"
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
"@ | Out-File -FilePath ".env" -Encoding UTF8
    
    Write-Host ".env file created! Please edit it with your actual credentials." -ForegroundColor Yellow
    Write-Host ""
}

# Create necessary directories if they don't exist
if (-not (Test-Path "mosquitto\data")) {
    New-Item -ItemType Directory -Path "mosquitto\data" -Force
}
if (-not (Test-Path "mosquitto\log")) {
    New-Item -ItemType Directory -Path "mosquitto\log" -Force
}

Write-Host "Setting up mosquitto directories..." -ForegroundColor Green

# Build and start the services
Write-Host ""
Write-Host "Building and starting Docker services..." -ForegroundColor Green
docker-compose up -d --build

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Edit the .env file with your actual credentials" -ForegroundColor White
Write-Host "2. Restart services: docker-compose down && docker-compose up -d" -ForegroundColor White
Write-Host "3. Access the web interface at: http://localhost:5001" -ForegroundColor White
Write-Host "4. Default login: user / password" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to continue" 