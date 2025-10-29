# Windows setup script for Croc-Bot Trading System
# Run this script with: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Croc-Bot Trading System - Windows Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.10 or higher." -ForegroundColor Red
    exit 1
}
Write-Host "Found: $pythonVersion" -ForegroundColor Green
Write-Host ""

# Navigate to backend directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path (Split-Path -Parent $scriptPath) "backend"
Set-Location $backendPath

Write-Host "Upgrading pip, wheel, and setuptools..." -ForegroundColor Yellow
python -m pip install --upgrade pip wheel setuptools
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to upgrade pip/wheel/setuptools" -ForegroundColor Red
    exit 1
}
Write-Host "Upgrade complete!" -ForegroundColor Green
Write-Host ""

Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Yellow
Write-Host "Note: Some dependencies (ta-lib) may require Visual C++ build tools." -ForegroundColor Yellow
Write-Host "If installation fails, you can skip ta-lib - it's optional." -ForegroundColor Yellow
Write-Host ""

pip install -r ../requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Some dependencies failed to install." -ForegroundColor Yellow
    Write-Host "This is often due to ta-lib requiring native compilation." -ForegroundColor Yellow
    Write-Host "The system will work without it." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Attempting to install optional dependencies..." -ForegroundColor Yellow
# Try to install uvloop (will fail on Windows, that's OK)
pip install uvloop 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "uvloop installed (Linux/Mac optimization)" -ForegroundColor Green
} else {
    Write-Host "uvloop skipped (Windows - not required)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Copy .env.example to .env and configure your settings" -ForegroundColor White
Write-Host "2. Set CRIPPEL_KRAKEN_API_KEY and CRIPPEL_KRAKEN_API_SECRET for live trading" -ForegroundColor White
Write-Host "3. Run the backend: uvicorn crippel.app:app --reload" -ForegroundColor White
Write-Host ""
Write-Host "For paper trading (default), no API keys are required." -ForegroundColor Yellow
Write-Host ""
