@echo off
echo 🐊 Croc-Bot: Push Local Changes to GitHub
echo ==========================================
echo.
echo 📤 This will push all your local changes to GitHub
echo.

REM Check if we're in a git repository
if not exist ".git" (
    echo ❌ Error: Not in a Git repository!
    echo    Make sure you're running this from the Croc-Bot folder
    pause
    exit /b 1
)

echo 🔍 Checking for local changes...
git status --porcelain > temp_status.txt
set /p changes=<temp_status.txt
del temp_status.txt

if "%changes%"=="" (
    echo ✅ No local changes to push
    echo    Your local files are already synced with GitHub
    pause
    exit /b 0
)

echo 📝 Local changes detected:
git status --short
echo.

echo 📦 Adding all changes...
git add .
if errorlevel 1 (
    echo ❌ Failed to add changes
    pause
    exit /b 1
)

echo ✅ Changes added successfully
echo.

REM Create commit message with timestamp
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%-%MM%-%DD% %HH%:%Min%:%Sec%"

echo 💾 Committing changes...
git commit -m "🚀 Local Update: %timestamp%"
if errorlevel 1 (
    echo ❌ Failed to commit changes
    pause
    exit /b 1
)

echo ✅ Changes committed successfully
echo.

echo 🚀 Pushing to GitHub...
git push
if errorlevel 1 (
    echo ❌ Failed to push to GitHub
    echo    Check your internet connection and GitHub credentials
    pause
    exit /b 1
)

echo.
echo ✅ SUCCESS! Your local changes have been pushed to GitHub
echo 🎉 Your GitHub repository is now up-to-date
echo.
pause