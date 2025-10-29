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

echo 📊 Starting Real Trading Dashboard...
echo    - Live portfolio monitoring with REAL money
echo    - Real-time market data (bid/ask/spreads)
echo    - Professional risk management
echo    - Manual trading interface
echo.

REM Start the dashboard in a new window
start "🐊 Real Trading Dashboard" cmd /k "echo 📊 Real Trading Dashboard Starting... && streamlit run real_trading_dashboard.py --server.port 12000 --server.address 0.0.0.0 --server.allowRunOnSave true"

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
echo    ✅ Paper trading engine ($1000 starting capital)
echo    ✅ Real-time market data streaming
echo    ✅ 10 advanced trading strategies
echo    ✅ Risk management system
echo    ✅ Discord notifications
echo    ✅ Real trading dashboard with live money
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