@echo off
setlocal

rem Crippel-Trader launcher for the GitHub repo at https://github.com/CrippelHQ/Crippel-Trader
rem Determines the repository root (directory containing this script)
set "REPO_DIR=%~dp0"
cd /d "%REPO_DIR%"

echo [INFO] Launching Crippel-Trader from %REPO_DIR%

rem Ensure Node dependencies are installed
if not exist "%REPO_DIR%node_modules" (
    echo [INFO] Installing Node.js dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed. Aborting startup.
        exit /b 1
    )
)

rem Locate Python interpreter, preferring a local virtual environment
set "PYTHON_CMD="
if exist "%REPO_DIR%venv\Scripts\python.exe" (
    set "PYTHON_CMD=%REPO_DIR%venv\Scripts\python.exe"
)

if not defined PYTHON_CMD (
    for %%P in (python python3 py) do (
        where %%P >nul 2>&1 && (
            set "PYTHON_CMD=%%P"
            goto :FOUND_PYTHON
        )
    )
)

:FOUND_PYTHON
if not defined PYTHON_CMD (
    echo [ERROR] No Python interpreter found. Install Python 3.11+ and try again.
    exit /b 1
)

rem Ensure Python dependencies are installed
if exist "%REPO_DIR%requirements.txt" (
    echo [INFO] Ensuring Python dependencies are installed...
    "%PYTHON_CMD%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [WARN] Python dependency installation encountered issues. Review the messages above.
    )
)

rem Launch backend server
start "Crippel-Trader Backend" cmd /k "cd /d \"%REPO_DIR%\" ^&^& \"%PYTHON_CMD%\" -m uvicorn pybackend.server:app --reload --host 0.0.0.0 --port 4000"

rem Launch frontend development server
start "Crippel-Trader Frontend" cmd /k "cd /d \"%REPO_DIR%\" ^&^& npm run dev:frontend"

echo [INFO] Backend and frontend launch commands issued.
endlocal
