#!/bin/bash

# Data Analysis Tools Docker Deployment Script

echo "🚀 Starting Data Analysis Tools Docker Deployment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose and try again."
    exit 1
fi

# Create uploads directory if it doesn't exist
mkdir -p uploads

echo "📦 Building Docker image..."
docker-compose build

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully!"
    
    echo "🌐 Starting the application..."
    docker-compose up -d
    
    if [ $? -eq 0 ]; then
        echo "✅ Application started successfully!"
        echo ""
        echo "🎉 Data Analysis Tools is now running!"
        echo "📱 Access the application at: http://localhost:5003"
        echo ""
        echo "📋 Useful commands:"
        echo "   View logs: docker-compose logs -f"
        echo "   Stop app:  docker-compose down"
        echo "   Restart:   docker-compose restart"
        echo ""
    else
        echo "❌ Failed to start the application."
        exit 1
    fi
else
    echo "❌ Failed to build Docker image."
    exit 1
fi 