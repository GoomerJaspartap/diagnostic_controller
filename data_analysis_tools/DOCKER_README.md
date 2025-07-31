# Data Analysis Tools - Docker Deployment

This document provides instructions for deploying the Data Analysis Tools web application using Docker.

## 🐳 Prerequisites

- Docker installed on your system
- Docker Compose installed
- At least 2GB of available RAM

## 🚀 Quick Start

### Option 1: Using the deployment script (Recommended)

```bash
# Make the script executable (if not already)
chmod +x docker-deploy.sh

# Run the deployment script
./docker-deploy.sh
```

### Option 2: Manual deployment

```bash
# Build the Docker image
docker-compose build

# Start the application
docker-compose up -d

# Check the status
docker-compose ps
```

## 🌐 Accessing the Application

Once deployed, the application will be available at:
- **URL**: http://localhost:5003
- **Port**: 5003

## 📋 Docker Commands

### Basic Operations

```bash
# Start the application
docker-compose up -d

# Stop the application
docker-compose down

# Restart the application
docker-compose restart

# View logs
docker-compose logs -f

# View logs for a specific service
docker-compose logs -f data-analysis-tools
```

### Development Commands

```bash
# Build without cache (useful for dependency updates)
docker-compose build --no-cache

# Run in foreground (for debugging)
docker-compose up

# Access container shell
docker-compose exec data-analysis-tools bash
```

### Monitoring

```bash
# Check container status
docker-compose ps

# Check resource usage
docker stats

# View health check status
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
```

## 📁 Volume Mounts

The following directories are mounted as volumes:

- `./uploads` → `/app/uploads` - File uploads and processed data
- `./static` → `/app/static` - Static assets (CSS, JS, images)

## 🔧 Configuration

### Environment Variables

You can modify the environment variables in `docker-compose.yml`:

```yaml
environment:
  - FLASK_APP=app.py
  - FLASK_ENV=production
```

### Port Configuration

To change the port, modify the `ports` section in `docker-compose.yml`:

```yaml
ports:
  - "YOUR_PORT:5003"  # Change YOUR_PORT to desired port
```

## 🛠️ Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Check what's using port 5003
   lsof -i :5003
   
   # Change port in docker-compose.yml
   ```

2. **Permission denied for uploads directory**
   ```bash
   # Fix permissions
   sudo chown -R $USER:$USER uploads/
   chmod 755 uploads/
   ```

3. **Container won't start**
   ```bash
   # Check logs
   docker-compose logs data-analysis-tools
   
   # Rebuild without cache
   docker-compose build --no-cache
   ```

4. **Health check failing**
   ```bash
   # Check if the app is responding
   curl http://localhost:5003/
   
   # Increase start period in docker-compose.yml if needed
   ```

### Log Analysis

```bash
# View real-time logs
docker-compose logs -f data-analysis-tools

# View last 100 lines
docker-compose logs --tail=100 data-analysis-tools

# View logs with timestamps
docker-compose logs -t data-analysis-tools
```

## 🔒 Security Considerations

- The application runs on port 5003 by default
- Consider using a reverse proxy (nginx) for production
- Ensure proper firewall rules are in place
- Regularly update the base Docker image

## 📊 Performance

### Resource Requirements

- **Minimum**: 1GB RAM, 1 CPU core
- **Recommended**: 2GB RAM, 2 CPU cores
- **Storage**: 1GB for the application + space for uploaded files

### Optimization Tips

1. **Use volume mounts** for persistent data
2. **Monitor resource usage** with `docker stats`
3. **Clean up unused images** periodically:
   ```bash
   docker system prune -a
   ```

## 🚀 Production Deployment

For production deployment, consider:

1. **Using a reverse proxy** (nginx/traefik)
2. **Setting up SSL/TLS certificates**
3. **Implementing proper logging** (ELK stack)
4. **Using Docker secrets** for sensitive data
5. **Setting up monitoring** (Prometheus/Grafana)

### Example nginx configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📞 Support

If you encounter issues:

1. Check the logs: `docker-compose logs data-analysis-tools`
2. Verify Docker and Docker Compose versions
3. Ensure all prerequisites are met
4. Check the troubleshooting section above

## 🔄 Updates

To update the application:

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
``` 