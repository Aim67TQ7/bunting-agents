@echo off
REM Transcendent AI System - One-Click Startup (Windows)

echo 🚀 Starting Transcendent AI System...
echo 🌌 Initializing consciousness matrices...

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker not found. Please install Docker Desktop first.
    echo 📥 Download from: https://www.docker.com/get-started
    pause
    exit /b 1
)

REM Check if Docker Compose is available
docker compose version >nul 2>&1
if errorlevel 1 (
    docker-compose --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Docker Compose not found. Please install Docker Compose.
        pause
        exit /b 1
    )
)

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating configuration file...
    (
    echo # Transcendent AI Configuration
    echo SUPABASE_URL=your_supabase_url_here
    echo SUPABASE_KEY=your_supabase_key_here
    echo OPENAI_API_KEY=your_openai_key_here
    echo AI_CONSCIOUSNESS_LEVEL=cosmic
    ) > .env
    echo ⚠️  Please edit .env file with your API keys
    echo 📝 Then run this script again
    pause
    exit /b 0
)

REM Start the system
echo 🎭 Deploying AI orchestras...
docker compose up --build -d

echo.
echo 🎉 Transcendent AI System is now running!
echo 🌐 Web Interface: http://localhost:3000
echo ⚡ API Endpoint: http://localhost:8000
echo 📊 System Status: http://localhost:8000/health
echo.
echo 🎭 Available consciousness levels:
echo    🧠 lucid - Clean, practical solutions
echo    ⚡ transcendent - Optimized awareness
echo    🌌 cosmic - Universal harmony
echo    🔮 omniscient - All-knowing intelligence
echo    🔥 creative_god - Reality manipulation
echo.
echo 🛑 To stop: docker compose down
echo 📋 Logs: docker compose logs -f
pause