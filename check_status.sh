#!/bin/bash

# Check Making Time Monitor Status

echo "📊 Making Time Monitor Status"
echo "============================="

# Check for launchd service
if launchctl list | grep -q "com.user.making-time-monitor"; then
    echo "🟢 LAUNCHD SERVICE: RUNNING"
    SERVICE_INFO=$(launchctl list com.user.making-time-monitor 2>/dev/null)
    if echo "$SERVICE_INFO" | grep -q '"PID"'; then
        PID=$(echo "$SERVICE_INFO" | grep '"PID"' | sed 's/.*"PID" = \([0-9]*\).*/\1/')
        echo "   🔍 Process ID: $PID"
        if ps -p "$PID" -o etime= > /dev/null 2>&1; then
            RUNTIME=$(ps -p "$PID" -o etime= | tr -d ' ')
            echo "   ⏱️  Runtime: $RUNTIME"
        fi
    fi
else
    echo "🔴 LAUNCHD SERVICE: NOT RUNNING"
fi

# Check for simple background process
MONITOR_PIDS=$(pgrep -f "event_alert.py.*making_time")
if [ -n "$MONITOR_PIDS" ]; then
    echo "🟢 BACKGROUND PROCESS: RUNNING"
    for PID in $MONITOR_PIDS; do
        echo "   🔍 Process ID: $PID"
        if ps -p "$PID" -o etime= > /dev/null 2>&1; then
            RUNTIME=$(ps -p "$PID" -o etime= | tr -d ' ')
            echo "   ⏱️  Runtime: $RUNTIME"
        fi
    done
else
    echo "🔴 BACKGROUND PROCESS: NOT RUNNING"
fi

echo ""
echo "📁 LOG FILES:"
echo "   monitor:  logs/monitor.log"
echo "   launchd:  logs/launchd_stderr.log"
echo "   app:      logs/making_time.log"

echo ""
echo "🎯 RECENT ACTIVITY:"
if [ -f "logs/monitor.log" ]; then
    echo "   Last 3 log entries from monitor.log:"
    tail -n 3 logs/monitor.log | sed 's/^/   /'
elif [ -f "logs/making_time.log" ]; then
    echo "   Last 3 log entries from making_time.log:"
    tail -n 3 logs/making_time.log | sed 's/^/   /'
else
    echo "   No activity logs found"
fi

echo ""
echo "💻 COMMANDS:"
echo "   🚀 Start:  ./start_simple_monitor.sh"
echo "   🛑 Stop:   ./stop_monitor.sh"
echo "   📊 Status: ./check_status.sh"
echo "   📁 Logs:   tail -f logs/monitor.log"
