#!/bin/bash

# Making Time Monitor - Simple Persistent Launcher
# This approach avoids launchd permission issues

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/logs/monitor.log"

echo "🎵 Making Time Monitor - Simple Persistent Launcher" | tee -a "$LOG_FILE"
echo "====================================================" | tee -a "$LOG_FILE"

# Check if already running
if pgrep -f "event_alert.py.*making_time" > /dev/null; then
    echo "⚠️  Monitor is already running!" | tee -a "$LOG_FILE"
    echo "   Process ID: $(pgrep -f 'event_alert.py.*making_time')"
    echo "   To stop: ./stop_monitor.sh"
    exit 1
fi

# Prompt for Gmail password and test it
echo "🔐 Gmail App Password Setup"
echo "Generate one at: https://myaccount.google.com/apppasswords"
echo ""
read -s -p "Enter your Gmail App Password: " GMAIL_PASSWORD
echo ""

if [ -z "$GMAIL_PASSWORD" ]; then
    echo "❌ No password entered. Exiting."
    exit 1
fi

# Test the Gmail credentials first
echo "🧪 Testing Gmail credentials..."
export GMAIL_APP_PASSWORD="$GMAIL_PASSWORD"
if ! "$SCRIPT_DIR/ticketnotifier/bin/python" -c "
import smtplib
import os
from email.message import EmailMessage

try:
    msg = EmailMessage()
    msg['Subject'] = '🎵 Making Time Monitor - Starting Up'
    msg['From'] = 'your-email@gmail.com'
    msg['To'] = 'your-email@gmail.com'
    msg.set_content('✅ Making Time monitor is starting up successfully!')
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('your-email@gmail.com', os.getenv('GMAIL_APP_PASSWORD'))
        server.send_message(msg)
    print('✅ Gmail test successful!')
except Exception as e:
    print(f'❌ Gmail test failed: {e}')
    exit(1)
"; then
    echo "❌ Gmail credentials test failed. Please check your App Password."
    exit 1
fi

echo "✅ Gmail credentials verified!"

# Start monitoring in background with nohup (survives terminal closure)
echo "🚀 Starting persistent monitor..." | tee -a "$LOG_FILE"
echo "   This will run even when you close your laptop" | tee -a "$LOG_FILE"

nohup "$SCRIPT_DIR/ticketnotifier/bin/python" "$SCRIPT_DIR/event_alert.py" --session making_time >> "$LOG_FILE" 2>&1 &

MONITOR_PID=$!
echo "✅ Monitor started successfully!" | tee -a "$LOG_FILE"
echo "   Process ID: $MONITOR_PID" | tee -a "$LOG_FILE"
echo "   Log file: $LOG_FILE"

# Wait a moment to check if it started properly
sleep 3

if kill -0 "$MONITOR_PID" 2>/dev/null; then
    echo ""
    echo "🎯 MONITORING ACTIVE:"
    echo "   • Checking every 60 minutes for ticket announcements"
    echo "   • Weekly status emails to confirm it's alive"
    echo "   • Automatic shutdown after 7 weeks (Sept 16, 2025)"
    echo "   • Health warnings if Instagram/web access fails for 3+ days"
    echo ""
    echo "📊 TO CHECK STATUS: ./check_status.sh"
    echo "🛑 TO STOP: ./stop_monitor.sh"
    echo "📁 LOGS: tail -f logs/monitor.log"
    echo ""
    echo "📧 You should get a weekly status email to confirm it's working!"
else
    echo "❌ Monitor failed to start. Check logs/monitor.log for details."
    exit 1
fi
