#!/usr/bin/env python3
"""
Making Time Monitor - Setup Script
Sets up virtual environment and dependencies for ticket monitoring.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta

def run_command(cmd, description):
    """Run a command and show progress."""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def create_session_config():
    """Create the Making Time session configuration."""
    # Calculate end date (7 weeks from now)
    end_date = datetime.now() + timedelta(weeks=7)
    
    config = {
        "name": "Making Time Philadelphia",
        "event_name": "Making Time Philadelphia", 
        "description": "Monitor for Making Time Philadelphia single-day ticket announcements",
        "urls": [
            "https://makingtimeisrad.com"
        ],
        "instagram_users": [
            "makingtimeisrad"
        ],
        "triggers": [
            "single day tickets",
            "day passes",
            "individual day",
            "one day tickets",
            "daily passes",
            "single-day passes",
            "day tickets available",
            "day-by-day tickets"
        ],
        "end_date": end_date.isoformat(),
        "check_interval_minutes": 15
    }
    
    os.makedirs("sessions", exist_ok=True)
    
    with open("sessions/making_time.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"📝 Created Making Time session config")
    print(f"   🎯 Monitoring until: {end_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"   ⏱️  Check interval: {config['check_interval_minutes']} minutes")

def main():
    print("🎵 Making Time Monitor - Setup")
    print("=" * 35)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Create virtual environment
    venv_path = Path("ticketnotifier")
    if not venv_path.exists():
        if not run_command("python3 -m venv ticketnotifier", "Creating virtual environment"):
            sys.exit(1)
    else:
        print("📦 Virtual environment already exists")
    
    # Install dependencies
    pip_cmd = "./ticketnotifier/bin/pip install --upgrade pip"
    if not run_command(pip_cmd, "Upgrading pip"):
        sys.exit(1)
    
    deps_cmd = "./ticketnotifier/bin/pip install -r requirements.txt"
    if not run_command(deps_cmd, "Installing dependencies"):
        sys.exit(1)
    
    # Create directories
    os.makedirs("logs", exist_ok=True)
    
    # Create session configuration
    create_session_config()
    
    # Create .env file if it doesn't exist
    env_file = Path(".env")
    if not env_file.exists():
        with open(".env", "w") as f:
            f.write("GMAIL_USER=joshtycko@gmail.com\n")
            f.write("# Gmail App Password will be prompted securely\n")
        print("📝 Created .env configuration file")
    
    print("\n✅ Setup complete!")
    print("\n📋 Next steps:")
    print("   1. Test Gmail: ./ticketnotifier/bin/python test_gmail.py")
    print("   2. Test Instagram: ./ticketnotifier/bin/python test_instagram.py") 
    print("   3. Start monitoring: ./start_robust_monitor.sh")
    print("\n🛡️ The monitor will run persistently (survives laptop sleep/wake)")
    print("📧 You'll get weekly status emails and immediate ticket alerts")

if __name__ == "__main__":
    main()
