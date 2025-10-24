@echo off
:menu
cls
echo 🐊 Croc-Bot GitHub Sync Menu
echo =============================
echo.
echo 📊 Choose your sync option:
echo.
echo 1. 📤 Push local changes TO GitHub
echo    (Upload your local files to GitHub)
echo.
echo 2. 📥 Pull changes FROM GitHub to local
echo    (Download latest files from GitHub)
echo.
echo 3. 🔄 Check sync status
echo    (See if local and GitHub are in sync)
echo.
echo 4. 🚪 Exit
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" (
    echo.
    echo 🚀 Starting push to GitHub...
    call push_to_github.bat
    echo.
    echo Press any key to return to menu...
    pause >nul
    goto menu
)

if "%choice%"=="2" (
    echo.
    echo 📥 Starting pull from GitHub...
    call pull_from_github.bat
    echo.
    echo Press any key to return to menu...
    pause >nul
    goto menu
)

if "%choice%"=="3" (
    echo.
    echo 🔍 Checking sync status...
    echo.
    
    REM Check if we're in a git repository
    if not exist ".git" (
        echo ❌ Error: Not in a Git repository!
        echo    Make sure you're running this from the Croc-Bot folder
        pause
        goto menu
    )
    
    echo 📍 Current branch:
    git branch --show-current
    echo.
    
    echo 🌐 Fetching latest info from GitHub...
    git fetch origin
    echo.
    
    echo 📊 Local vs GitHub status:
    git status -uno
    echo.
    
    echo 📝 Local changes (if any):
    git status --short
    echo.
    
    echo 📈 Recent commits:
    git log --oneline -5
    echo.
    
    echo Press any key to return to menu...
    pause >nul
    goto menu
)

if "%choice%"=="4" (
    echo.
    echo 👋 Goodbye!
    exit /b 0
)

echo.
echo ❌ Invalid choice. Please enter 1, 2, 3, or 4.
echo.
pause
goto menu