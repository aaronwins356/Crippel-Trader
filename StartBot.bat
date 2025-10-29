@echo off
setlocal EnableDelayedExpansion

REM ==================================================================
REM  Croc-Bot Unified Launcher
REM  This script boots the complete Croc-Bot stack: backend services
REM  and the HTML control dashboard. Execute from the repository root.
REM ==================================================================

REM Ensure we are running from the directory that contains this script.
pushd "%~dp0" >nul 2>&1

cls
title 🐊 Croc-Bot Trading System Launcher

echo.
echo  ██████╗██████╗  ██████╗  ██████╗      ██████╗  ██████╗ ████████╗
echo ██╔════╝██╔══██╗██╔═══██╗██╔════╝      ██╔══██╗██╔═══██╗╚══██╔══╝
echo ██║     ██████╔╝██║   ██║██║     █████╗██████╔╝██║   ██║   ██║
echo ██║     ██╔══██╗██║   ██║██║     ╚════╝██╔══██╗██║   ██║   ██║
echo ╚██████╗██║  ██║╚██████╔╝╚██████╗      ██████╔╝╚██████╔╝   ██║
echo  ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝      ╚═════╝  ╚═════╝    ╚═╝
echo.
echo 🚀 Initialising Croc-Bot environment...
echo ===============================================
echo.

REM Validate key project assets before continuing.
if not exist "start_croc_bot.py" (
    echo ❌ Error: start_croc_bot.py missing. Please verify repository contents.
    goto :abort
)
if not exist "start_real_trading.py" (
    echo ❌ Error: start_real_trading.py missing. Please verify repository contents.
    goto :abort
)
if not exist "trading_dashboard.html" (
    echo ❌ Error: trading_dashboard.html missing. Please verify repository contents.
    goto :abort
)

echo 🔍 Checking Python installation...
for /f "tokens=2 delims= " %%I in ('python -V 2^>^&1') do set PY_VERSION=%%I
if not defined PY_VERSION (
    echo ❌ Python was not detected on PATH. Install Python 3.8 or newer and retry.
    goto :abort
)

for /f "tokens=1,2 delims=." %%A in ("!PY_VERSION!") do (
    set PY_MAJOR=%%A
    set PY_MINOR=%%B
)
if "!PY_MAJOR!"=="" goto :badpython
if !PY_MAJOR! LSS 3 goto :badpython
if !PY_MAJOR!==3 if !PY_MINOR! LSS 8 goto :badpython

echo ✅ Python !PY_VERSION! detected.
echo.

echo 📦 Ensuring required Python packages are installed...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip is unavailable. Ensure Python is installed with pip support.
    goto :abort
)

python -m pip install --upgrade pip >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Warning: pip upgrade failed. Continuing with current version.
)

if exist "crippel-trader\requirements.txt" (
    python -m pip install -r "crippel-trader\requirements.txt"
    if errorlevel 1 (
        echo ❌ Dependency installation failed. Review the error output above.
        goto :abort
    )
) else (
    echo ⚠️  Warning: Dependency file crippel-trader\requirements.txt not found.
)

echo ✅ Dependencies verified.
echo.

echo 🌐 Launching Croc-Bot backend services...
start "🐊 Croc-Bot Backend" cmd /k "cd /d %~dp0 && echo 🔧 Backend starting... && python start_croc_bot.py"
if errorlevel 1 (
    echo ❌ Failed to start backend service window.
    goto :abort
)

REM Provide the backend some time to establish external connections.
timeout /t 5 /nobreak >nul

echo 💹 Launching real trading engine window...
start "🐊 Real Trading Engine" cmd /k "cd /d %~dp0 && echo 💰 Real trading engine starting... && python start_real_trading.py"
if errorlevel 1 (
    echo ❌ Failed to start real trading engine window.
    goto :abort
)

REM Additional delay so the backend processes can warm up.
timeout /t 3 /nobreak >nul

echo 🖥️ Opening Croc-Bot dashboard in your default browser...
start "🐊 Croc-Bot Dashboard" "trading_dashboard.html"
if errorlevel 1 (
    echo ❌ Failed to open trading_dashboard.html
    goto :abort
)

echo.
echo 🎉 Croc-Bot Trading System is now running!
echo =============================================
echo 📊 Dashboard: trading_dashboard.html
echo 🔧 Backend:  python start_croc_bot.py (separate window)
echo 💰 Real Engine: python start_real_trading.py (separate window)
echo.
echo ℹ️  Close all spawned windows to fully shut down the bot.
echo.

:finish
pause
popd >nul 2>&1
endlocal
exit /b 0

:badpython
echo ❌ Python 3.8 or newer is required. Detected version: !PY_VERSION!
goto :abort

:abort
pause
popd >nul 2>&1
endlocal
exit /b 1
