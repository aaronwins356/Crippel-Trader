@echo off
TITLE Crypto Dashboard - Development Environment
SETLOCAL

echo ========================================
echo Starting Crypto Dashboard Development Environment
echo ========================================

:: Check if running from the correct directory
if not exist "backend" (
    echo Error: Please run this script from the project root directory
    echo The backend folder was not found.
    pause
    exit /b 1
)

:: Start Backend Server
echo.
echo Starting Backend Server...
echo --------------------------
cd backend

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to create Python virtual environment
        echo Please ensure Python is installed and accessible from the command line
        cd ..
        pause
        exit /b 1
    )
)

:: Install Python dependencies
echo Installing/Updating Python dependencies...
venv\Scripts\pip install -r requirements.txt >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to install Python dependencies
    cd ..
    pause
    exit /b 1
)

:: Start backend server in a new window
start "Backend Server - Crypto Dashboard" /D "%CD%" cmd /k "venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"
cd ..

:: Wait a moment for backend to start
timeout /t 3 /nobreak >nul

:: Start Frontend Server
echo.
echo Starting Frontend Server...
echo --------------------------
:: Install Node.js dependencies if needed
if not exist "node_modules" (
    echo Installing Node.js dependencies...
    npm install
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to install Node.js dependencies
        echo Please ensure Node.js is installed and accessible from the command line
        pause
        exit /b 1
    )
)

:: Start frontend server in a new window
start "Frontend Server - Crypto Dashboard" cmd /k "npm run dev"

:: Final message
echo.
echo ========================================
echo Development servers started successfully!
echo ========================================
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000
echo ========================================
echo Close this window or press Ctrl+C to exit
echo ========================================
echo.

:: Keep the main window open
pause