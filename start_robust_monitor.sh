#!/bin/bash

# Making Time Monitor - Robust Laptop-Safe Launcher
# Uses launchd for persistence across sleep/wake cycles

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_FILE="$HOME/Library/LaunchAgents/com.user.making-time-monitor.plist"

echo "🎵 Making Time Monitor - Robust Launcher"
echo "========================================"

# Stop any existing service
if launchctl list | grep -q "com.user.making-time-monitor"; then
    echo "🛑 Stopping existing monitor service..."
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    launchctl remove com.user.making-time-monitor 2>/dev/null || true
fi

# Create the launchd plist file
echo "📝 Creating launchd service configuration..."
cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.making-time-monitor</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$SCRIPT_DIR/ticketnotifier/bin/python</string>
        <string>$SCRIPT_DIR/event_alert.py</string>
        <string>--session</string>
        <string>making_time</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <true/>
    </dict>
    
    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/logs/launchd_stdout.log</string>
    
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/logs/launchd_stderr.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    
    <key>ProcessType</key>
    <string>Background</string>
    
    <key>LimitLoadToSessionType</key>
    <string>Aqua</string>
</dict>
</plist>
EOF

# Make sure logs directory exists
mkdir -p "$SCRIPT_DIR/logs"

# Load and start the service
echo "🚀 Starting persistent monitor service..."
launchctl load "$PLIST_FILE"

# Wait a moment and check if it started
sleep 3

if launchctl list | grep -q "com.user.making-time-monitor"; then
    echo "✅ SUCCESS! Monitor is now running persistently."
    echo ""
    echo "🛡️ ROBUSTNESS FEATURES:"
    echo "   • Survives laptop sleep/wake cycles"
    echo "   • Automatically restarts if crashed"
    echo "   • Runs in background (no screen session needed)"
    echo "   • Weekly status emails to confirm it's alive"
    echo "   • Auto-shutdown after 7 weeks or repeated failures"
    echo ""
    echo "📊 TO CHECK STATUS:"
    echo "   launchctl list | grep making-time"
    echo ""
    echo "🛑 TO STOP MONITOR:"
    echo "   launchctl unload \"$PLIST_FILE\""
    echo ""
    echo "📧 You'll get weekly 'I'm alive' emails every Tuesday."
    echo "📧 You'll get immediate alerts if tickets are found."
    echo "📧 You'll get health warnings if problems persist."
else
    echo "❌ Failed to start monitor service."
    echo "Check logs at: $SCRIPT_DIR/logs/launchd_stderr.log"
fi
