@echo off
TITLE Crypto Dashboard - Production Build
SETLOCAL

echo ========================================
echo Building Crypto Dashboard for Production
echo ========================================

:: Check if running from the correct directory
if not exist "backend" (
    echo Error: Please run this script from the project root directory
    pause
    exit /b 1
)

:: Build Frontend
echo.
echo Building Frontend...
echo ------------------
cd frontend

:: Install dependencies if needed
if not exist "node_modules" (
    echo Installing frontend dependencies...
    npm install
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to install frontend dependencies
        cd ..
        pause
        exit /b 1
    )
)

:: Create production build
echo Creating production build...
npm run build
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to build frontend
    cd ..
    pause
    exit /b 1
)

cd ..

:: Build Backend
echo.
echo Building Backend...
echo ------------------
cd backend

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to create Python virtual environment
        cd ..
        pause
        exit /b 1
    )
)

:: Install dependencies
echo Installing backend dependencies...
venv\Scripts\pip install -r requirements.txt >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to install backend dependencies
    cd ..
    pause
    exit /b 1
)

cd ..

echo.
echo ========================================
echo Production build completed successfully!
echo ========================================
echo To run in production:
echo 1. Start backend: cd backend ^&^& venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
echo 2. Serve frontend: Use a web server to serve the frontend/.next directory
echo ========================================
pause