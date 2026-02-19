#!/usr/bin/env python3
"""
Deployment script for Contract Analysis Tool
Creates deployment packages for both Docker and Electron distributions
"""

import os
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path
import json

def run_command(cmd, description="", check=True):
    """Run a shell command with error handling"""
    print(f"🔄 {description}")
    print(f"   Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    
    try:
        result = subprocess.run(cmd, shell=isinstance(cmd, str), check=check, 
                              capture_output=True, text=True)
        if result.stdout:
            print(f"   ✅ {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Command failed: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def check_dependencies():
    """Check if required tools are installed"""
    print("🔍 Checking dependencies...")
    
    deps = {
        'docker': 'Docker',
        'docker-compose': 'Docker Compose', 
        'node': 'Node.js',
        'npm': 'npm',
        'python3': 'Python 3'
    }
    
    missing = []
    for cmd, name in deps.items():
        try:
            subprocess.run([cmd, '--version'], capture_output=True, check=True)
            print(f"   ✅ {name} is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"   ❌ {name} is missing")
            missing.append(name)
    
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("Please install the missing dependencies and try again.")
        return False
    
    print("✅ All dependencies are available")
    return True

def build_docker_image():
    """Build Docker image"""
    print("\n🐳 Building Docker image...")
    
    # Build the image
    run_command(['docker', 'build', '-t', 'contract-analysis-tool', '.'], 
                "Building Docker image")
    
    # Save image to tar file
    print("📦 Saving Docker image to file...")
    run_command(['docker', 'save', '-o', 'dist/contract-analysis-docker.tar', 
                'contract-analysis-tool'],
                "Saving Docker image")
    
    # Compress the tar file
    print("🗜️ Compressing Docker image...")
    run_command(['gzip', 'dist/contract-analysis-docker.tar'],
                "Compressing Docker image")
    
    print("✅ Docker image built and saved")

def build_electron_app():
    """Build Electron application"""
    print("\n⚡ Building Electron application...")
    
    # Install Node dependencies if needed
    if not os.path.exists('node_modules'):
        run_command(['npm', 'install'], "Installing Node.js dependencies")
    
    # Run Electron build
    run_command(['node', 'build-electron.js'], "Building Electron executable")
    
    print("✅ Electron application built")

def create_deployment_package():
    """Create complete deployment package"""
    print("\n📦 Creating deployment package...")
    
    # Ensure dist directory exists
    os.makedirs('dist', exist_ok=True)
    
    # Create deployment structure
    deploy_dir = 'dist/contract-analysis-deployment'
    if os.path.exists(deploy_dir):
        shutil.rmtree(deploy_dir)
    os.makedirs(deploy_dir)
    
    # Copy Docker files
    docker_files = ['Dockerfile', 'docker-compose.yml', '.env.template']
    docker_dir = f'{deploy_dir}/docker'
    os.makedirs(docker_dir)
    
    for file in docker_files:
        if os.path.exists(file):
            shutil.copy(file, docker_dir)
    
    # Copy application files needed for Docker
    app_files = [
        'app.py', 'main.py', 'agent1_parser.py', 'agent2_risk.py', 'agent3_report.py',
        'seller.md', 'seller_baseline_terms.md', 'pyproject.toml', 'uv.lock'
    ]
    
    for file in app_files:
        if os.path.exists(file):
            shutil.copy(file, docker_dir)
    
    # Copy directories
    for dir_name in ['static', 'templates']:
        if os.path.exists(dir_name):
            shutil.copytree(dir_name, f'{docker_dir}/{dir_name}')
    
    # Create empty directories
    os.makedirs(f'{docker_dir}/uploads', exist_ok=True)
    os.makedirs(f'{docker_dir}/reports', exist_ok=True)
    
    # Copy Electron builds if they exist
    electron_dist = 'dist'
    electron_files = []
    
    if os.path.exists(electron_dist):
        for item in os.listdir(electron_dist):
            if item.endswith(('.exe', '.dmg', '.AppImage', '.deb')):
                electron_files.append(item)
                shutil.copy(f'{electron_dist}/{item}', deploy_dir)
    
    # Create deployment instructions
    create_deployment_instructions(deploy_dir, electron_files)
    
    # Create deployment zip
    zip_path = 'dist/contract-analysis-tool-deployment.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(deploy_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, deploy_dir)
                zipf.write(file_path, arc_path)
    
    print(f"✅ Deployment package created: {zip_path}")
    return zip_path

def create_deployment_instructions(deploy_dir, electron_files):
    """Create deployment instructions"""
    instructions = f"""# Contract Analysis Tool - Deployment Instructions

## Quick Start

### Option 1: Docker Deployment (Recommended for Servers)

1. Navigate to the `docker/` directory
2. Copy `.env.template` to `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
3. Run with Docker Compose:
   ```bash
   docker-compose up -d
   ```
4. Access the application at http://localhost:5000

### Option 2: Desktop Application

Desktop executables are included in this package:
{chr(10).join(f"- {file}" for file in electron_files) if electron_files else "- No desktop executables found in this package"}

To run the desktop application:
1. Install the appropriate executable for your platform
2. Set the OPENAI_API_KEY environment variable
3. Launch the application

## Environment Variables

Required:
- `OPENAI_API_KEY`: Your OpenAI API key for contract analysis

Optional:
- `SESSION_SECRET`: Secret key for session management (auto-generated if not set)

## System Requirements

### Docker Deployment
- Docker and Docker Compose
- 2GB RAM minimum
- OpenAI API key

### Desktop Application  
- Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- 4GB RAM recommended
- OpenAI API key
- Internet connection for AI analysis

## Support

For issues or questions, please check the application logs:
- Docker: `docker-compose logs`
- Desktop: Check the application's log directory

## Features

- Multi-format document processing (PDF, DOCX, images)
- AI-powered contract analysis using OpenAI
- Risk assessment and compliance scoring
- Report generation in multiple formats (JSON, Markdown, XML)
- Secure file handling and processing

Generated: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}
"""
    
    with open(f'{deploy_dir}/README.md', 'w') as f:
        f.write(instructions)

def main():
    """Main deployment function"""
    print("🚀 Contract Analysis Tool - Deployment Builder")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Create dist directory
    os.makedirs('dist', exist_ok=True)
    
    # Build Docker image
    try:
        build_docker_image()
    except Exception as e:
        print(f"⚠️  Docker build failed: {e}")
        print("Continuing with Electron build...")
    
    # Build Electron app
    try:
        build_electron_app() 
    except Exception as e:
        print(f"⚠️  Electron build failed: {e}")
        print("Continuing with deployment package...")
    
    # Create deployment package
    package_path = create_deployment_package()
    
    print("\n🎉 Deployment completed successfully!")
    print(f"📦 Package location: {package_path}")
    print("\nNext steps:")
    print("1. Extract the deployment package")
    print("2. Follow the README.md instructions")
    print("3. Set your OpenAI API key")
    print("4. Deploy using Docker or install the desktop app")

if __name__ == '__main__':
    main()