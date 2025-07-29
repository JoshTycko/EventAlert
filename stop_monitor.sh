#!/bin/bash

# Stop Making Time Monitor

PLIST_FILE="$HOME/Library/LaunchAgents/com.user.making-time-monitor.plist"

echo "🛑 Stopping Making Time Monitor..."

# Stop launchd service if running
if launchctl list | grep -q "com.user.making-time-monitor"; then
    launchctl unload "$PLIST_FILE" 2>/dev/null
    echo "✅ Stopped launchd service."
fi

# Stop simple background process if running
MONITOR_PIDS=$(pgrep -f "event_alert.py.*making_time")
if [ -n "$MONITOR_PIDS" ]; then
    echo "   Stopping background processes: $MONITOR_PIDS"
    kill $MONITOR_PIDS
    echo "✅ Stopped background monitor processes."
    echo "📧 You will NOT receive any more notifications."
else
    echo "ℹ️  No background monitor processes found."
fi

echo ""
echo "🚀 TO RESTART: ./start_simple_monitor.sh"
