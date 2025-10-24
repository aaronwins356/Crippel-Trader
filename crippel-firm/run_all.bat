@echo off
setlocal enabledelayedexpansion

REM Navigate to the directory of this script
pushd %~dp0

set PROJECT_ROOT=%cd%
set FRONTEND_DIR=%PROJECT_ROOT%\frontend

REM Detect a Python interpreter
set PYTHON_CMD=
for %%I in (py python) do (
    if not defined PYTHON_CMD (
        where %%I >nul 2>nul && set PYTHON_CMD=%%I
    )
)

if not defined PYTHON_CMD (
    echo [ERROR] Python 3.10+ is required but was not found on PATH.
    echo Install Python from https://www.python.org/downloads/ and try again.
    exit /b 1
)

REM Create the virtual environment if needed
if not exist .venv\Scripts\python.exe (
    echo [INFO] Creating virtual environment with %PYTHON_CMD%.
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create the virtual environment.
        exit /b 1
    )
)

REM Activate the environment and install backend dependencies
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate the virtual environment.
    exit /b 1
)

echo [INFO] Upgrading pip and installing backend requirements...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies.
    exit /b 1
)

REM Install frontend dependencies
if not exist "%FRONTEND_DIR%" (
    echo [ERROR] Frontend directory not found: %FRONTEND_DIR%
    exit /b 1
)

pushd "%FRONTEND_DIR%"
where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm was not found on PATH. Install Node.js 18+ from https://nodejs.org/.
    exit /b 1
)

echo [INFO] Installing frontend dependencies...
call npm install
if errorlevel 1 (
    echo [ERROR] npm install failed.
    exit /b 1
)
popd

REM Launch backend and frontend in separate windows
start "Crippel-Firm Backend" cmd /k "cd /d %PROJECT_ROOT% && call .venv\Scripts\activate.bat && uvicorn backend.app:app --host 0.0.0.0 --port 8000"
start "Crippel-Firm Frontend" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"

echo.
echo [SUCCESS] Crippel-Firm backend and frontend are starting in separate windows.
echo [INFO] Backend: http://localhost:8000
echo [INFO] Frontend: http://localhost:3000

echo [INFO] Press any key to close this setup window (services keep running in their own windows)...
pause >nul

popd
endlocal
