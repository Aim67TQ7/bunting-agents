#!/bin/bash

echo "Starting Contract Analysis Tool (Electron Desktop App)"
echo "====================================================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed or not in PATH"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check if npm modules are installed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        exit 1
    fi
fi

# Check for OpenAI API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Warning: OPENAI_API_KEY environment variable is not set"
    echo "The application may not work properly without an API key"
    echo
    read -p "Enter your OpenAI API key (or press Enter to continue): " API_KEY
    if [ ! -z "$API_KEY" ]; then
        export OPENAI_API_KEY="$API_KEY"
    fi
fi

echo
echo "Starting Electron application..."
npx electron .

if [ $? -ne 0 ]; then
    echo
    echo "Error: Failed to start Electron application"
    echo "Please check the error messages above"
fi