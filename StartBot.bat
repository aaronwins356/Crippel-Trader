@echo off
title 🐊 Croc-Bot Trading System
cls
echo.
echo  ██████╗██████╗  ██████╗  ██████╗      ██████╗  ██████╗ ████████╗
echo ██╔════╝██╔══██╗██╔═══██╗██╔════╝      ██╔══██╗██╔═══██╗╚══██╔══╝
echo ██║     ██████╔╝██║   ██║██║     █████╗██████╔╝██║   ██║   ██║   
echo ██║     ██╔══██╗██║   ██║██║     ╚════╝██╔══██╗██║   ██║   ██║   
echo ╚██████╗██║  ██║╚██████╔╝╚██████╗      ██████╔╝╚██████╔╝   ██║   
echo  ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝      ╚═════╝  ╚═════╝    ╚═╝   
echo.
echo 🚀 Starting Complete Croc-Bot Trading System...
echo ================================================
echo.

REM Check if we're in the right directory
if not exist "simple_dashboard.py" (
    echo ❌ Error: simple_dashboard.py not found!
    echo    Make sure you're running this from the Croc-Bot folder
    pause
    exit /b 1
)

echo 🔍 Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo    Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo ✅ Python found
echo.

echo 📦 Installing/updating required packages...
pip install fastapi uvicorn websockets requests python-multipart jinja2 >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Some packages may have failed to install, but continuing...
)

echo ✅ Dependencies ready
echo.

echo 🌐 Starting Backend API Server...
echo    - Kraken WebSocket connection
echo    - Paper trading engine
echo    - Risk management system
echo    - Discord notifications
echo    - 10 trading strategies
echo.

REM Start the backend in a new window
start "🐊 Croc-Bot Backend" cmd /k "echo 🔧 Backend Server Starting... && python start_croc_bot.py"

echo ⏳ Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

echo 📊 Starting Trading Dashboard...
echo    - Real-time portfolio tracking
echo    - Strategy performance monitoring
echo    - Risk management controls
echo    - Live market data
echo.

REM Start the dashboard in a new window
start "🐊 Croc-Bot Dashboard" cmd /k "echo 📊 Dashboard Starting... && python simple_dashboard.py"

echo ⏳ Waiting for dashboard to load...
timeout /t 3 /nobreak >nul

echo.
echo 🎉 Croc-Bot Trading System is now RUNNING!
echo ==========================================
echo.
echo 📊 Dashboard: http://localhost:12000
echo 🔧 API Backend: http://localhost:8000
echo.
echo 💡 What's Running:
echo    ✅ Backend API with Kraken integration
echo    ✅ Paper trading engine ($200 starting capital)
echo    ✅ Real-time market data streaming
echo    ✅ 10 advanced trading strategies
echo    ✅ Risk management system
echo    ✅ Discord notifications
echo    ✅ Professional trading dashboard
echo.
echo 🌐 Open your browser to: http://localhost:12000
echo.
echo ⚠️  To stop the system:
echo    - Close this window
echo    - Close the Backend window
echo    - Close the Dashboard window
echo.
echo 🐊 Happy Trading! Your autonomous trading bot is live!
echo.
pause