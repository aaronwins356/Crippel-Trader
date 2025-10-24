@echo off
title 🐊 Croc-Bot: Update Local Folder
cls
echo.
echo 🐊 Croc-Bot: Update Local Folder from GitHub
echo =============================================
echo.
echo 📥 This will download the latest changes from GitHub
echo    and update your local Croc-Bot folder
echo.

REM Check if we're in a git repository
if not exist ".git" (
    echo ❌ Error: Not in a Git repository!
    echo    Make sure you're running this from the Croc-Bot folder
    echo    If this is a fresh download, run: git init
    pause
    exit /b 1
)

echo 🔍 Checking current status...
for /f "tokens=*" %%i in ('git branch --show-current 2^>nul') do set current_branch=%%i
if "%current_branch%"=="" set current_branch=main
echo 📍 Current branch: %current_branch%
echo.

echo 🌐 Connecting to GitHub repository...
git remote -v | findstr "github.com/aaronwins356/Croc-Bot" >nul
if errorlevel 1 (
    echo 🔧 Setting up GitHub remote...
    git remote add origin https://github.com/aaronwins356/Croc-Bot.git
    if errorlevel 1 (
        echo ⚠️  Remote may already exist, continuing...
    )
)

echo 📡 Fetching latest changes from GitHub...
git fetch origin
if errorlevel 1 (
    echo ❌ Failed to fetch from GitHub
    echo    Check your internet connection
    pause
    exit /b 1
)

echo ✅ Successfully connected to GitHub
echo.

echo 🔍 Checking for updates...
git status -uno > temp_status.txt 2>nul
findstr /C:"Your branch is behind" temp_status.txt >nul
if errorlevel 1 (
    findstr /C:"Your branch is up to date" temp_status.txt >nul
    if not errorlevel 1 (
        echo ✅ Already up-to-date!
        echo    Your local folder matches GitHub exactly
        del temp_status.txt 2>nul
        echo.
        echo 🎉 No updates needed - you have the latest version!
        pause
        exit /b 0
    )
)

del temp_status.txt 2>nul

echo 📥 New updates available on GitHub!
echo.

REM Check for local uncommitted changes
git status --porcelain > temp_changes.txt 2>nul
set /p local_changes=<temp_changes.txt 2>nul
del temp_changes.txt 2>nul

if not "%local_changes%"=="" (
    echo ⚠️  WARNING: You have local changes that haven't been saved!
    echo.
    echo 📝 Your local changes:
    git status --short
    echo.
    echo 🤔 What would you like to do?
    echo    1. Save local changes and update (recommended)
    echo    2. Discard local changes and update
    echo    3. Cancel update
    echo.
    set /p choice="Enter your choice (1, 2, or 3): "
    
    if "%choice%"=="1" (
        echo 📦 Saving your local changes...
        git stash push -m "Auto-save before update at %date% %time%"
        if errorlevel 1 (
            echo ❌ Failed to save changes
            pause
            exit /b 1
        )
        echo ✅ Local changes saved safely
        echo.
    ) else if "%choice%"=="2" (
        echo ⚠️  Discarding local changes...
        git reset --hard HEAD
        git clean -fd
        echo ✅ Local changes discarded
        echo.
    ) else (
        echo 🛑 Update cancelled
        echo    Your local changes are preserved
        pause
        exit /b 0
    )
)

echo 📥 Downloading latest updates from GitHub...
git pull origin %current_branch%
if errorlevel 1 (
    echo ❌ Failed to update from GitHub
    echo    There might be conflicts that need manual resolution
    echo.
    echo 🔧 To resolve conflicts manually:
    echo    1. Check 'git status' to see conflicted files
    echo    2. Edit the files to resolve conflicts
    echo    3. Run 'git add .' to stage resolved files
    echo    4. Run 'git commit' to complete the update
    pause
    exit /b 1
)

echo ✅ Update completed successfully!
echo.

REM If we saved changes, offer to restore them
git stash list 2>nul | findstr "Auto-save before update" >nul
if not errorlevel 1 (
    echo 📦 You have saved changes from before the update
    echo.
    set /p restore="Would you like to restore your saved changes? (y/n): "
    if /i "%restore%"=="y" (
        echo 📤 Restoring your saved changes...
        git stash pop
        if errorlevel 1 (
            echo ⚠️  There were conflicts restoring your saved changes
            echo    Your changes are still saved. Use 'git stash pop' manually when ready
        ) else (
            echo ✅ Saved changes restored successfully
        )
        echo.
    ) else (
        echo 📦 Your changes remain saved
        echo    Use 'git stash pop' to restore them later
        echo.
    )
)

echo 🎉 SUCCESS! Your local folder is now updated!
echo ============================================
echo.
echo 📊 What's new in this update:
git log --oneline -5 --color=never
echo.
echo ✅ Your Croc-Bot is now running the latest version from GitHub
echo 🚀 You can now run StartBot.bat to launch the updated system
echo.
pause