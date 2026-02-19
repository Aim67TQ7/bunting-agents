@echo off
echo Starting Contract Analysis Tool (Electron Desktop App)
echo =====================================================

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Check if npm modules are installed
if not exist "node_modules" (
    echo Installing dependencies...
    npm install
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Check for OpenAI API key
if "%OPENAI_API_KEY%"=="" (
    echo Warning: OPENAI_API_KEY environment variable is not set
    echo The application may not work properly without an API key
    echo.
    set /p API_KEY="Enter your OpenAI API key (or press Enter to continue): "
    if not "%API_KEY%"=="" (
        set OPENAI_API_KEY=%API_KEY%
    )
)

echo.
echo Starting Electron application...
npx electron .

if errorlevel 1 (
    echo.
    echo Error: Failed to start Electron application
    echo Please check the error messages above
    pause
)