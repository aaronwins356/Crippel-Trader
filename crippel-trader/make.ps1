# Windows Makefile equivalent - PowerShell script
# Run commands with: powershell .\make.ps1 <command>

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "Croc-Bot Trading System - Available Commands" -ForegroundColor Cyan
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  setup       - Install dependencies (runs scripts\setup.ps1)" -ForegroundColor White
    Write-Host "  lint        - Run ruff linter on backend" -ForegroundColor White
    Write-Host "  format      - Format code with ruff" -ForegroundColor White
    Write-Host "  typecheck   - Run mypy type checker" -ForegroundColor White
    Write-Host "  test        - Run pytest tests" -ForegroundColor White
    Write-Host "  run         - Run backend in production mode" -ForegroundColor White
    Write-Host "  run-dev     - Run backend in development mode (with reload)" -ForegroundColor White
    Write-Host "  backend     - Alias for run-dev" -ForegroundColor White
    Write-Host "  frontend    - Run frontend development server" -ForegroundColor White
    Write-Host "  clean       - Remove temporary files and caches" -ForegroundColor White
    Write-Host ""
}

function Invoke-Setup {
    Write-Host "Running setup script..." -ForegroundColor Yellow
    & powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
}

function Invoke-Lint {
    Write-Host "Running ruff linter..." -ForegroundColor Yellow
    ruff check backend\crippel --fix
}

function Invoke-Format {
    Write-Host "Formatting code with ruff..." -ForegroundColor Yellow
    ruff format backend\crippel
}

function Invoke-Typecheck {
    Write-Host "Running mypy type checker..." -ForegroundColor Yellow
    Set-Location backend
    mypy crippel --strict
    Set-Location ..
}

function Invoke-Test {
    Write-Host "Running pytest..." -ForegroundColor Yellow
    Set-Location backend
    pytest -v --cov=crippel --cov-report=term-missing
    Set-Location ..
}

function Invoke-Run {
    Write-Host "Starting backend (production mode)..." -ForegroundColor Yellow
    Set-Location backend
    uvicorn crippel.app:app --host 0.0.0.0 --port 8000
}

function Invoke-RunDev {
    Write-Host "Starting backend (development mode with reload)..." -ForegroundColor Yellow
    Set-Location backend
    uvicorn crippel.app:app --reload --host 0.0.0.0 --port 8000
}

function Invoke-Frontend {
    Write-Host "Starting frontend development server..." -ForegroundColor Yellow
    Set-Location frontend
    npm run dev
}

function Invoke-Clean {
    Write-Host "Cleaning temporary files..." -ForegroundColor Yellow
    
    # Remove Python cache directories
    Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Directory -Filter ".pytest_cache" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Directory -Filter ".mypy_cache" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Directory -Filter ".ruff_cache" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    
    # Remove .pyc files
    Get-ChildItem -Path . -Recurse -File -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force
    
    Write-Host "Clean complete!" -ForegroundColor Green
}

# Main command dispatcher
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "setup" { Invoke-Setup }
    "lint" { Invoke-Lint }
    "format" { Invoke-Format }
    "typecheck" { Invoke-Typecheck }
    "test" { Invoke-Test }
    "run" { Invoke-Run }
    "run-dev" { Invoke-RunDev }
    "backend" { Invoke-RunDev }
    "frontend" { Invoke-Frontend }
    "clean" { Invoke-Clean }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
    }
}
