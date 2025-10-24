@echo off
echo 🐊 Croc-Bot: Pull Changes from GitHub to Local
echo ===============================================
echo.
echo 📥 This will download the latest changes from GitHub
echo.

REM Check if we're in a git repository
if not exist ".git" (
    echo ❌ Error: Not in a Git repository!
    echo    Make sure you're running this from the Croc-Bot folder
    pause
    exit /b 1
)

echo 🔍 Checking current branch...
for /f "tokens=*" %%i in ('git branch --show-current') do set current_branch=%%i
echo 📍 Current branch: %current_branch%
echo.

echo 🌐 Fetching latest changes from GitHub...
git fetch origin
if errorlevel 1 (
    echo ❌ Failed to fetch from GitHub
    echo    Check your internet connection
    pause
    exit /b 1
)

echo ✅ Fetched successfully
echo.

echo 🔍 Checking for updates...
git status -uno > temp_status.txt
findstr /C:"Your branch is behind" temp_status.txt >nul
if errorlevel 1 (
    findstr /C:"Your branch is ahead" temp_status.txt >nul
    if not errorlevel 1 (
        echo ⚠️  WARNING: You have local changes that aren't on GitHub
        echo    Your local files are ahead of GitHub
        echo    Consider running push_to_github.bat first
        del temp_status.txt
        pause
        exit /b 0
    )
    
    findstr /C:"Your branch is up to date" temp_status.txt >nul
    if not errorlevel 1 (
        echo ✅ Already up-to-date!
        echo    Your local files match GitHub exactly
        del temp_status.txt
        pause
        exit /b 0
    )
)

del temp_status.txt

echo 📥 New changes available on GitHub!
echo.

REM Check for local uncommitted changes
git status --porcelain > temp_changes.txt
set /p local_changes=<temp_changes.txt
del temp_changes.txt

if not "%local_changes%"=="" (
    echo ⚠️  WARNING: You have uncommitted local changes!
    echo.
    echo 📝 Your local changes:
    git status --short
    echo.
    echo 🤔 What would you like to do?
    echo    1. Stash local changes and pull (recommended)
    echo    2. Commit local changes first, then pull
    echo    3. Cancel and handle manually
    echo.
    set /p choice="Enter your choice (1, 2, or 3): "
    
    if "%choice%"=="1" (
        echo 📦 Stashing your local changes...
        git stash push -m "Auto-stash before pull at %date% %time%"
        if errorlevel 1 (
            echo ❌ Failed to stash changes
            pause
            exit /b 1
        )
        echo ✅ Local changes stashed
        echo.
    ) else if "%choice%"=="2" (
        echo 💾 Committing your local changes first...
        git add .
        for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
        set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
        set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
        set "timestamp=%YYYY%-%MM%-%DD% %HH%:%Min%:%Sec%"
        git commit -m "💾 Auto-commit before pull: %timestamp%"
        if errorlevel 1 (
            echo ❌ Failed to commit changes
            pause
            exit /b 1
        )
        echo ✅ Local changes committed
        echo.
    ) else (
        echo 🛑 Operation cancelled
        echo    Handle your local changes manually, then run this script again
        pause
        exit /b 0
    )
)

echo 📥 Pulling latest changes from GitHub...
git pull origin %current_branch%
if errorlevel 1 (
    echo ❌ Failed to pull from GitHub
    echo    There might be merge conflicts that need manual resolution
    echo.
    echo 🔧 To resolve conflicts:
    echo    1. Check 'git status' to see conflicted files
    echo    2. Edit the files to resolve conflicts
    echo    3. Run 'git add .' to stage resolved files
    echo    4. Run 'git commit' to complete the merge
    pause
    exit /b 1
)

echo ✅ Pull completed successfully!
echo.

REM If we stashed changes, offer to restore them
git stash list | findstr "Auto-stash before pull" >nul
if not errorlevel 1 (
    echo 📦 You have stashed changes from earlier
    echo.
    set /p restore="Would you like to restore your stashed changes? (y/n): "
    if /i "%restore%"=="y" (
        echo 📤 Restoring your stashed changes...
        git stash pop
        if errorlevel 1 (
            echo ⚠️  There were conflicts restoring your stashed changes
            echo    Your stash is still saved. Use 'git stash pop' manually when ready
        ) else (
            echo ✅ Stashed changes restored successfully
        )
        echo.
    ) else (
        echo 📦 Your changes remain stashed
        echo    Use 'git stash pop' to restore them later
        echo.
    )
)

echo 🎉 SUCCESS! Your local folder is now updated with the latest GitHub changes
echo 📊 Summary:
git log --oneline -5
echo.
pause