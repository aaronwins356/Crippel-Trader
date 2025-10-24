#!/usr/bin/env python3
"""
🐊 Croc-Bot Auto-Push Script
Automatically commits and pushes all changes to GitHub
"""

import subprocess
import time
import os
from datetime import datetime
import sys

def run_command(command, cwd=None):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd,
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout.strip(), True
    except subprocess.CalledProcessError as e:
        return e.stderr.strip(), False

def check_git_status():
    """Check if there are any changes to commit"""
    output, success = run_command("git status --porcelain")
    return len(output.strip()) > 0 if success else False

def auto_commit_and_push():
    """Automatically commit and push changes"""
    print("🔍 Checking for changes...")
    
    if not check_git_status():
        print("✅ No changes to commit")
        return True
    
    print("📝 Changes detected! Committing...")
    
    # Add all changes
    output, success = run_command("git add .")
    if not success:
        print(f"❌ Failed to add changes: {output}")
        return False
    
    # Create commit message with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"🤖 Auto-commit: Updates at {timestamp}"
    
    # Commit changes
    output, success = run_command(f'git commit -m "{commit_message}"')
    if not success:
        print(f"❌ Failed to commit: {output}")
        return False
    
    print(f"✅ Committed: {commit_message}")
    
    # Push to GitHub
    print("🚀 Pushing to GitHub...")
    output, success = run_command("git push")
    if not success:
        print(f"❌ Failed to push: {output}")
        return False
    
    print("✅ Successfully pushed to GitHub!")
    return True

def continuous_auto_push(interval_minutes=5):
    """Continuously monitor and auto-push changes"""
    print("🐊 Croc-Bot Auto-Push Started")
    print("=" * 50)
    print(f"📊 Monitoring for changes every {interval_minutes} minutes")
    print("🔄 Will automatically commit and push any changes")
    print("⚠️  Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        while True:
            try:
                auto_commit_and_push()
                print(f"⏰ Next check in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
            except Exception as e:
                print(f"❌ Error during auto-push: {e}")
                time.sleep(30)  # Wait 30 seconds before retrying
                
    except KeyboardInterrupt:
        print("\n🛑 Auto-push stopped by user")

def immediate_push():
    """Immediately push any current changes"""
    print("🐊 Croc-Bot Immediate Push")
    print("=" * 30)
    return auto_commit_and_push()

if __name__ == "__main__":
    # Change to the Croc-Bot directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        # Immediate push mode
        success = immediate_push()
        sys.exit(0 if success else 1)
    elif len(sys.argv) > 1 and sys.argv[1].startswith("--interval="):
        # Custom interval mode
        try:
            interval = int(sys.argv[1].split("=")[1])
            continuous_auto_push(interval)
        except ValueError:
            print("❌ Invalid interval. Use --interval=5 for 5 minutes")
            sys.exit(1)
    else:
        # Default continuous mode (5 minutes)
        continuous_auto_push()