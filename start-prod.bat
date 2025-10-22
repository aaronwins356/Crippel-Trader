@echo off
TITLE Crypto Dashboard - Production Environment
SETLOCAL

echo ========================================
echo Starting Crypto Dashboard Production Environment
echo ========================================

:: Check if running from the correct directory
if not exist "backend" (
    echo Error: Please run this script from the project root directory
    pause
    exit /b 1
)

:: Check if production build exists
if not exist "frontend\.next" (
    echo Error: Production build not found. Please run build-prod.bat first.
    pause
    exit /b 1
)

:: Start Backend Server
echo.
echo Starting Backend Server...
echo --------------------------
cd backend

:: Check if virtual environment exists
if not exist "venv" (
    echo Error: Virtual environment not found. Please run build-prod.bat first.
    cd ..
    pause
    exit /b 1
)

:: Start backend server in a new window
start "Backend Server - Crypto Dashboard (Production)" /D "%CD%" cmd /k "venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000"
cd ..

:: Wait a moment for backend to start
timeout /t 3 /nobreak >nul

:: Start Frontend Server (serving static files)
echo.
echo Starting Frontend Server...
echo --------------------------
cd frontend

:: Start a simple HTTP server to serve the static files
start "Frontend Server - Crypto Dashboard (Production)" cmd /k "npx serve .next\standalone"
cd ..

echo.
echo ========================================
echo Production servers started successfully!
echo ========================================
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000
echo ========================================
echo Close this window or press Ctrl+C to exit
echo ========================================
echo.

:: Keep the main window open
pause