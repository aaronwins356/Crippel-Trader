@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Resolve the root directory of this script to support double-click execution
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "BACKEND_DIR=%SCRIPT_DIR%\croc-bot\backend"
set "FRONTEND_DIR=%SCRIPT_DIR%\croc-bot\frontend"

if not exist "%BACKEND_DIR%" (
    echo [Error] Backend directory not found at "%BACKEND_DIR%".
    echo Please verify the Croc-Bot repository structure.
    goto :EOF
)

if not exist "%FRONTEND_DIR%" (
    echo [Error] Frontend directory not found at "%FRONTEND_DIR%".
    echo Please verify the Croc-Bot repository structure.
    goto :EOF
)

echo Launching Croc-Bot Backend...
start "Croc-Bot Backend" cmd /k "cd /d \"%BACKEND_DIR%\" ^&^& echo Starting Croc-Bot backend in %%CD%%... ^&^& python -m croc.app"

REM Wait a few seconds to avoid port collisions during startup
timeout /t 5 /nobreak >nul

echo Launching Croc-Bot Frontend...
start "Croc-Bot Frontend" cmd /k "cd /d \"%FRONTEND_DIR%\" ^&^& echo Starting Croc-Bot frontend in %%CD%%... ^&^& npm run dev"

echo Both Croc-Bot servers have been launched. Backend and frontend windows remain open for monitoring.

goto :EOF
