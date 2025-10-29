#!/usr/bin/env python3
"""Startup script for Croc-Bot Trading System."""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the Croc-Bot trading system."""
    print("🐊 Starting Croc-Bot Trading System")
    print("=" * 50)
    
    # Get the project root directory
    project_root = Path(__file__).parent
    backend_dir = project_root
    
    # Check if backend directory exists
    # Ensure backend directory exists
    if not backend_dir.exists():
        print("❌ Project directory not found!")
        print(f"Expected: {backend_dir}")
        return 1

    os.chdir(backend_dir)
    print(f"📁 Working directory: {backend_dir}")

    # Check if virtual environment should be created
    venv_dir = backend_dir / ".venv"
    if not venv_dir.exists():
        print("🔧 Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        print("✅ Virtual environment created")
    
    # Determine the correct Python executable
    if os.name == 'nt':  # Windows
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:  # Unix/Linux/macOS
        python_exe = venv_dir / "bin" / "python"
    
    # Install dependencies if needed
    requirements_file = project_root / "requirements.txt"
    if requirements_file.exists():
        print("📦 Installing dependencies...")
        try:
            subprocess.run([
                str(python_exe), "-m", "pip", "install", "-r", str(requirements_file)
            ], check=True, capture_output=True, text=True)
            print("✅ Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Some dependencies may have failed to install: {e}")
            print("Continuing anyway...")
    
    # Set environment variables
    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_dir)
    
    print("\n🚀 Starting Croc-Bot Trading System...")
    print("📊 Dashboard will be available at:")
    print("   - UI: http://localhost:8000")
    print("   - Config: http://localhost:8000/config")
    print("   - WebSocket: ws://localhost:8000/ws/state")
    print("\n" + "=" * 50)
    
    try:
        # Start the FastAPI server
        subprocess.run([
            str(python_exe), "-m", "uvicorn", 
            "bot.server:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ], env=env, check=True)
    except KeyboardInterrupt:
        print("\n\n🛑 Croc-Bot Trading System stopped by user")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to start server: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())