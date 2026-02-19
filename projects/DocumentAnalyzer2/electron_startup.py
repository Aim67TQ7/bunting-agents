#!/usr/bin/env python3
"""
Startup script for the Contract Analysis Tool Electron app.
This ensures all dependencies are available and the Flask server starts properly.
"""

import os
import sys
import subprocess
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_python_dependencies():
    """Check if all required Python packages are installed"""
    required_packages = [
        'flask', 'openai', 'pdfplumber', 'pypdf', 'python-docx', 
        'pillow', 'pytesseract', 'tiktoken', 'pydantic', 'gunicorn'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Missing Python packages: {', '.join(missing_packages)}")
        return False
    
    logger.info("All Python dependencies are available")
    return True

def check_system_dependencies():
    """Check if system dependencies like Tesseract are available"""
    try:
        subprocess.run(['tesseract', '--version'], 
                      capture_output=True, check=True)
        logger.info("Tesseract OCR is available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("Tesseract OCR not found - OCR functionality may be limited")
        return False

def check_api_keys():
    """Check if required API keys are configured"""
    openai_key = os.environ.get('OPENAI_API_KEY')
    if not openai_key:
        logger.warning("OPENAI_API_KEY not found - AI analysis will not work")
        return False
    
    logger.info("OpenAI API key is configured")
    return True

def create_directories():
    """Ensure required directories exist"""
    directories = ['uploads', 'reports']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Directory '{directory}' is ready")

def start_flask_server():
    """Start the Flask server using gunicorn"""
    logger.info("Starting Flask server...")
    
    # Set environment variables for Flask
    os.environ.setdefault('SESSION_SECRET', 'electron-app-secret-key')
    
    # Start gunicorn server
    cmd = [
        'gunicorn',
        '--bind', '127.0.0.1:5000',
        '--workers', '1',
        '--timeout', '300',
        '--access-logfile', '-',
        '--error-logfile', '-',
        'main:app'
    ]
    
    return subprocess.Popen(cmd, 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.STDOUT,
                           universal_newlines=True)

def main():
    """Main startup function"""
    logger.info("Starting Contract Analysis Tool...")
    
    # Check dependencies
    deps_ok = check_python_dependencies()
    sys_ok = check_system_dependencies()
    api_ok = check_api_keys()
    
    if not deps_ok:
        logger.error("Cannot start - missing Python dependencies")
        return False
    
    if not api_ok:
        logger.error("Cannot start - missing OpenAI API key")
        return False
    
    # Create required directories
    create_directories()
    
    # Start Flask server
    flask_process = start_flask_server()
    
    # Wait a moment for server to start
    time.sleep(2)
    
    # Check if server started successfully
    try:
        import urllib.request
        urllib.request.urlopen('http://127.0.0.1:5000', timeout=5)
        logger.info("Flask server started successfully")
        return True
    except Exception as e:
        logger.error(f"Flask server failed to start: {e}")
        flask_process.terminate()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)