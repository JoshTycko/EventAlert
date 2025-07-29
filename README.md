# EventAlert - Generic Event Ticket Notifier

A configurable Python system that monitors multiple sources for event ticket announcements and sends email notifications when they become available. Easily customizable for any event through session-based configurations.

## Features

- **Multi-Source Monitoring**: Websites, Instagram accounts, and more
- **Session-Based Configuration**: Easy setup for different events
- **Smart Detection**: Configurable trigger phrases with regex support
- **Email Notifications**: Immediate alerts when tickets are detected
- **State Persistence**: Avoids duplicate notifications
- **Robust Logging**: Comprehensive logging per session
- **Virtual Environment**: Isolated Python environment

## Quick Start

1. **Run the setup script**:
   ```bash
   python3 setup.py
   ```
   This will:
   - Create a virtual environment
   - Install all dependencies
   - Create configuration templates

2. **Configure email settings**:
   ```bash
   # Edit the .env file with your email configuration
   nano .env
   ```

3. **Choose or create a session**:
   ```bash
   # List available sessions
   ./ticketnotifier/bin/python event_alert.py --list-sessions
   
   # Run Making Time monitoring
   ./ticketnotifier/bin/python event_alert.py --session making_time
   ```

## Session Configuration

Sessions are JSON files in the `sessions/` directory that define what to monitor for each event.

### Example: Making Time Philadelphia
```json
{
  "name": "making_time",
  "event_name": "Making Time Philadelphia",
  "description": "Making Time Philadelphia festival single-day ticket monitoring",
  "check_interval_minutes": 30,
  "urls": {
    "makingtime_site": "https://makingtimeisrad.com",
    "makingtime_tickets": "https://makingtimeisrad.com/tickets",
    "resident_advisor": "https://ra.co/events/2159561"
  },
  "instagram_users": [
    "makingtimeisrad",
    "davep_makingtime"
  ],
  "triggers": [
    "single\\s*day\\s*(tickets|passes)",
    "day\\s*pass\\s*(on\\s*sale|available)",
    "saturday\\s*(only|pass|ticket)"
  ]
}
```

### Creating New Sessions

1. Copy an existing session file in `sessions/`
2. Modify the configuration for your event
3. Run with: `./ticketnotifier/bin/python event_alert.py --session your_session_name`

## Running Commands

All commands should use the virtual environment:

```bash
# List available sessions
./ticketnotifier/bin/python event_alert.py --list-sessions

# Run a specific session
./ticketnotifier/bin/python event_alert.py --session making_time

# Run in background (macOS/Linux)
nohup ./ticketnotifier/bin/python event_alert.py --session making_time > logs/making_time_output.log 2>&1 &

# Check if running
ps aux | grep event_alert

# Stop background process
pkill -f "event_alert.py --session making_time"
```

## Configuration

### Email Setup (Required)

The script uses SMTP to send email notifications. For Gmail:

1. **Enable 2-Factor Authentication** on your Google account
2. **Generate an App Password**:
   - Go to [Google Account Settings](https://myaccount.google.com/apppasswords)
   - Generate an app password for "Mail"
3. **Update `.env` file**:
   ```
   EMAIL_FROM=your-email@gmail.com
   EMAIL_TO=your-email@gmail.com
   SMTP_USER=your-email@gmail.com
   SMTP_PASS=your-16-character-app-password
   ```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHECK_INTERVAL_MIN` | 30 | Minutes between checks |
| `EMAIL_FROM` | - | Sender email address |
| `EMAIL_TO` | - | Recipient email address |
| `SMTP_HOST` | smtp.gmail.com | SMTP server |
| `SMTP_PORT` | 587 | SMTP port |
| `SMTP_USER` | - | SMTP username |
| `SMTP_PASS` | - | SMTP password/app password |

## Supported Sources

EventAlert can monitor:

### Websites
- Official event websites
- Ticketing platforms
- Music news sites (Resident Advisor, etc.)
- Any webpage with detectable content changes

### Social Media
- Instagram accounts (with rate limiting)
- Any platform that provides RSS/API access

### Detection Methods
- Text pattern matching with regex support
- Content change detection
- Configurable trigger phrases per session

## Running in Background

### macOS/Linux
```bash
# Run in background
nohup ./ticketnotifier/bin/python event_alert.py --session your_session > logs/your_session_output.log 2>&1 &

# Check if running
ps aux | grep event_alert

# Stop
pkill -f "event_alert.py --session your_session"
```

### Using Screen
```bash
# Start a screen session
screen -S ticket-monitor

# Run the script
./ticketnotifier/bin/python event_alert.py --session your_session

# Detach: Ctrl+A, then D
# Reattach: screen -r ticket-monitor
```

## Files Created

- `state_[session_name].json`: Persistent state (last checked posts, etc.)
- `logs/[session_name].log`: Application logs per session
- `logs/[session_name]_output.log`: Output when running in background

## Troubleshooting

### Common Issues

1. **Email not sending**:
   - Check your app password (not regular password for Gmail)
   - Verify 2FA is enabled on Google account
   - Check firewall/network settings

2. **Instagram errors**:
   - Instagram may temporarily block requests
   - The script includes rate limiting and error handling
   - Check logs for specific error messages

3. **Website access issues**:
   - Sites may block automated requests
   - Script includes proper User-Agent headers
   - Consider adjusting check frequency if needed

### Viewing Logs
```bash
# Follow live logs for a specific session
tail -f logs/your_session.log

# View recent activity
tail -50 logs/your_session.log

# View all session logs
ls logs/
```

## Updating Sessions

1. **Edit session configuration**:
   ```bash
   nano sessions/your_session.json
   ```

2. **Update URLs for future years**:
   - Edit the session JSON file
   - Update event-specific URLs and IDs
   - Modify social media accounts as needed

3. **Test configuration**:
   ```bash
   ./ticketnotifier/bin/python event_alert.py --session your_session
   ```

## Development

### Testing Email
```bash
./ticketnotifier/bin/python -c "
import os
from dotenv import load_dotenv
load_dotenv()
from event_alert import EventAlert
config = {'name': 'test', 'event_name': 'Test Event', 'triggers': []}
alert = EventAlert(config)
alert.send_email('Test Subject', 'Test message from EventAlert')
"
```

### Testing Triggers
```bash
./ticketnotifier/bin/python -c "
from event_alert import EventAlert
config = {'name': 'test', 'triggers': ['single.*day.*(tickets|passes)']}
alert = EventAlert(config)
print(alert.text_matches('Single day passes now available!'))
"
```

## Contributing

Feel free to improve the script:
- Add more monitoring sources
- Improve trigger phrase detection
- Add notification methods (SMS, Discord, etc.)
- Enhance error handling

## License

Free to use and modify. No warranty provided.

---

**Note**: This script is for personal use. Be respectful of websites' terms of service and don't abuse rate limits.
