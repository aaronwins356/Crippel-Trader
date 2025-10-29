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
if not exist "trading_dashboard.html" (
    echo ❌ Error: trading_dashboard.html not found!
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
python -m pip install --upgrade pip >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Failed to upgrade pip. Continuing with existing version...
)
python -m pip install -r crippel-trader\requirements.txt >nul 2>&1
if errorlevel 1 (
    echo ❌ Failed to install Croc-Bot dependencies.
    echo    Run "python -m pip install -r crippel-trader\requirements.txt" manually for details.
    pause
    exit /b 1
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
timeout /t 3 /nobreak >nul

echo 🤖 Starting Real Trading Engine...
echo    - Live market data from Kraken
echo    - Real capital management
echo    - Professional risk controls
echo    - Bid/ask spread handling
echo.

REM Start the real trading system in a new window
start "🐊 Real Trading Engine" cmd /k "echo 💰 Real Trading Engine Starting... && python start_real_trading.py"

echo ⏳ Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

echo 🖥️ Opening HTML Control Center...
echo    - Unified monitoring across paper and real trading
echo    - Live metrics and manual order ticket
echo    - Works in any modern browser
echo.

REM Launch the HTML dashboard in default browser
start "🐊 Croc-Bot Dashboard" "trading_dashboard.html"

echo ⏳ Waiting for dashboard to open...
timeout /t 2 /nobreak >nul

echo.
echo 🎉 Croc-Bot Trading System is now RUNNING!
echo ==========================================
echo.
echo 📊 Dashboard: trading_dashboard.html
echo 🔧 API Backend: http://localhost:8000
echo.
echo 💡 What's Running:
echo    ✅ Backend API with Kraken integration
echo    ✅ Paper trading engine ($1000 starting capital)
echo    ✅ Real-time market data streaming
echo    ✅ 10 advanced trading strategies
echo    ✅ Risk management system
echo    ✅ Discord notifications
echo    ✅ HTML command center for monitoring and manual control
echo.
echo 🌐 If the dashboard did not open automatically, double-click trading_dashboard.html
echo.
echo ⚠️  To stop the system:
echo    - Close this window
echo    - Close the Backend window
echo    - Close the Dashboard window
echo.
echo 🐊 Happy Trading! Your autonomous trading bot is live!
echo.
pause