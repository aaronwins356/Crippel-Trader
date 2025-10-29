#!/bin/bash
# Linux/macOS setup script for Croc-Bot Trading System
# Run this script with: bash scripts/setup.sh

set -e  # Exit on error

echo "========================================"
echo "Croc-Bot Trading System - POSIX Setup"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "Found: $PYTHON_VERSION"
echo ""

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "Upgrading pip, wheel, and setuptools..."
python3 -m pip install --upgrade pip wheel setuptools
echo "Upgrade complete!"
echo ""

echo "Installing dependencies from requirements.txt..."
pip3 install -r requirements.txt

echo ""
echo "Installing optional dependencies..."
# Install uvloop for Linux/macOS performance
echo "Installing uvloop (Unix optimization)..."
pip3 install 'uvloop>=0.19' || echo "Warning: uvloop installation failed, continuing..."

# Try to install ta-lib if available
echo "Attempting to install ta-lib (optional)..."
pip3 install 'TA-Lib>=0.4.28' 2>/dev/null || {
    echo "Warning: ta-lib installation failed."
    echo "To install ta-lib:"
    echo "  Ubuntu/Debian: sudo apt-get install ta-lib"
    echo "  macOS: brew install ta-lib"
    echo "  Then: pip3 install TA-Lib"
    echo "The system will work without it."
}

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and configure your settings"
echo "2. Set CRIPPEL_KRAKEN_API_KEY and CRIPPEL_KRAKEN_API_SECRET for live trading"
echo "3. Run the backend: cd backend && uvicorn crippel.app:app --reload"
echo ""
echo "For paper trading (default), no API keys are required."
echo ""
