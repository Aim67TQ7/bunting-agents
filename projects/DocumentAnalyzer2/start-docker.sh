#!/bin/bash

echo "Starting Contract Analysis Tool (Docker)"
echo "========================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    echo "Please install Docker from https://docker.com/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed or not in PATH"
    echo "Please install Docker Compose"
    exit 1
fi

# Check for .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        echo "Creating .env file from template..."
        cp .env.template .env
        echo "Please edit .env file and add your OpenAI API key, then run this script again"
        exit 1
    else
        echo "Warning: No .env file found"
        echo "Creating minimal .env file..."
        echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
        echo "SESSION_SECRET=docker-session-secret-$(date +%s)" >> .env
        echo "Please edit .env file and add your OpenAI API key, then run this script again"
        exit 1
    fi
fi

# Check if OpenAI API key is set
if grep -q "your_openai_api_key_here" .env; then
    echo "Error: Please set your OpenAI API key in the .env file"
    echo "Edit .env and replace 'your_openai_api_key_here' with your actual API key"
    exit 1
fi

echo "Building and starting Docker containers..."
docker-compose up --build -d

if [ $? -eq 0 ]; then
    echo
    echo "✅ Docker containers started successfully!"
    echo "🌐 Application is available at: http://localhost:5000"
    echo
    echo "To view logs: docker-compose logs -f"
    echo "To stop: docker-compose down"
else
    echo
    echo "❌ Failed to start Docker containers"
    echo "Check the error messages above"
fi