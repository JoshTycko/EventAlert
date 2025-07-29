#!/usr/bin/env python3
"""
EventAlert - Generic Event Ticket Notifier
==========================================

A configurable system for monitoring various sources (websites, social media)
for event ticket announcements and sending notifications when triggers are detected.

Usage:
    python event_alert.py --session <session_name>
    python event_alert.py --session making_time
    python event_alert.py --list-sessions
"""

import os
import re
import time
import smtplib
import json
import schedule
import logging
import argparse
import getpass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from email.message import EmailMessage

import requests
from bs4 import BeautifulSoup
import instaloader
from dotenv import load_dotenv

# Optional SMS support
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

# Load environment variables from .env file
load_dotenv()

class EventAlert:
    """Generic event ticket notification system."""
    
    def __init__(self, session_config: Dict[str, Any], smtp_password: Optional[str] = None, end_date: Optional[datetime] = None):
        self.config = session_config
        self.session_name = session_config.get('name', 'default')
        self.smtp_password = smtp_password
        self.end_date = end_date
        
        # File paths
        self.state_file = f"state_{self.session_name}.json"
        self.log_file = f"logs/{self.session_name}.log"
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Validate configuration
        self._validate_config()
        
        if self.end_date:
            self.logger.info(f"EventAlert initialized for session: {self.session_name} (will stop on {self.end_date.strftime('%Y-%m-%d %H:%M')})")
        else:
            self.logger.info(f"EventAlert initialized for session: {self.session_name}")
    
    def _setup_logging(self):
        """Setup logging configuration."""
        self.logger = logging.getLogger(f"EventAlert.{self.session_name}")
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _validate_config(self):
        """Validate session configuration."""
        required_fields = ['name', 'description', 'triggers']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required field in session config: {field}")
        
        # Validate email config (password will be prompted if not provided)
        email_fields = ['EMAIL_FROM', 'EMAIL_TO', 'SMTP_USER']
        missing_fields = [field for field in email_fields if not os.getenv(field)]
        if missing_fields:
            raise ValueError(f"Missing email configuration: {missing_fields}")
    
    def send_test_email(self) -> bool:
        """Send a test email to confirm setup and explain what will be monitored."""
        event_name = self.config.get('event_name', self.session_name)
        
        subject = f"🎵 {event_name} Monitor - Setup Complete!"
        
        body = f"""Your {event_name} ticket monitor is now active and working!

📊 MONITORING DETAILS:
─────────────────────

🔍 What we're watching:
{self._format_monitoring_sources()}

⚡ Trigger phrases we'll detect:
{self._format_triggers()}

⏰ Check frequency: Every {self.config.get('check_interval_minutes', 30)} minutes

📧 You'll receive an email like this one whenever we detect any of the trigger phrases on the monitored sources.

🛡️  Your password was entered securely and is not stored anywhere.

🔄 Monitor started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This is a one-time setup confirmation. Future emails will only be sent when tickets are detected!

Happy ticket hunting! 🎫
"""
        
        return self.send_email(subject, body)
    
    def _format_monitoring_sources(self) -> str:
        """Format the monitoring sources for display."""
        sources = []
        
        # Add URLs
        urls = self.config.get('urls', [])
        if isinstance(urls, dict):
            # Handle dict format: {"name": "url"}
            for name, url in urls.items():
                sources.append(f"  🌐 {name}: {url}")
        else:
            # Handle list format: ["url1", "url2"]
            for url in urls:
                sources.append(f"  🌐 {url}")
        
        # Add Instagram accounts
        instagram_users = self.config.get('instagram_users', [])
        for user in instagram_users:
            sources.append(f"  📱 Instagram @{user}")
        
        return "\n".join(sources) if sources else "  No sources configured"
    
    def is_monitoring_expired(self) -> bool:
        """Check if the monitoring period has ended."""
        if not self.end_date:
            return False
        
        now = datetime.now()
        if now >= self.end_date:
            self.logger.info(f"Monitoring period ended at {self.end_date.strftime('%Y-%m-%d %H:%M')}")
            return True
        
        return False
    
    def check_system_health(self, state: Dict) -> bool:
        """Check if the monitoring system is healthy and send alerts if not."""
        health = state.get("health_status", {})
        now = datetime.now()
        
        # Initialize weekly status tracking
        if "last_weekly_status" not in health:
            health["last_weekly_status"] = now.isoformat()
        
        # Check if it's time for weekly status email
        last_weekly = health.get("last_weekly_status")
        if last_weekly:
            last_weekly_time = datetime.fromisoformat(last_weekly)
            days_since_weekly = (now - last_weekly_time).total_seconds() / (24 * 3600)
            if days_since_weekly >= 7:  # Send weekly status
                self.send_weekly_status(state)
                health["last_weekly_status"] = now.isoformat()
        
        # Check for prolonged failures (3+ days) - but only after we've been running for a while
        max_failure_hours = 72  # 3 days
        
        # Check URL health
        url_failures = health.get("consecutive_url_failures", 0)
        last_url_success = health.get("last_successful_url_check")
        
        # Check Instagram health  
        instagram_failures = health.get("consecutive_instagram_failures", 0)
        last_instagram_success = health.get("last_successful_instagram_check")
        
        # Don't trigger health alerts in the first hour of operation
        first_run_grace_period = 86400  # 24 hours in seconds (very generous for testing)
        health_start_time = health.get("health_monitoring_started")
        if not health_start_time:
            health["health_monitoring_started"] = now.isoformat()
            health_start_time = now.isoformat()
        
        time_since_health_start = (now - datetime.fromisoformat(health_start_time)).total_seconds()
        if time_since_health_start < first_run_grace_period:
            self.logger.info(f"Health monitoring in grace period ({time_since_health_start:.0f}s < {first_run_grace_period}s) - skipping failure checks")
            return True  # Don't fail during initial grace period
        
        # Determine if we should send a health warning
        should_alert = False
        alert_reasons = []
        
        if last_url_success:
            hours_since_url_success = (now - datetime.fromisoformat(last_url_success)).total_seconds() / 3600
            if hours_since_url_success > max_failure_hours:
                should_alert = True
                alert_reasons.append(f"Website checking failed for {hours_since_url_success:.1f} hours")
        elif time_since_health_start > max_failure_hours * 3600:  # Only alert if we've been running for 3+ days
            should_alert = True
            alert_reasons.append(f"Website checking has never succeeded in {time_since_health_start/3600:.1f} hours")
        
        if last_instagram_success:
            hours_since_instagram_success = (now - datetime.fromisoformat(last_instagram_success)).total_seconds() / 3600
            if hours_since_instagram_success > max_failure_hours:
                should_alert = True
                alert_reasons.append(f"Instagram checking failed for {hours_since_instagram_success:.1f} hours")
        elif time_since_health_start > max_failure_hours * 3600:  # Only alert if we've been running for 3+ days
            should_alert = True
            alert_reasons.append(f"Instagram checking has never succeeded in {time_since_health_start/3600:.1f} hours")
        
        # Send alert if needed
        if should_alert and health.get("health_warnings_sent", 0) < 3:  # Max 3 warnings
            self.send_health_alert(alert_reasons, state)
            health["health_warnings_sent"] = health.get("health_warnings_sent", 0) + 1
            
            # If this is the 3rd warning, initiate shutdown
            if health["health_warnings_sent"] >= 3:
                self.logger.error("Maximum health warnings reached. Initiating shutdown.")
                self.send_shutdown_email("Too many consecutive failures")
                return False  # Signal to stop monitoring
        
        return True
    
    def send_health_alert(self, reasons: List[str], state: Dict):
        """Send health alert email."""
        event_name = self.config.get('event_name', self.session_name)
        warning_num = state.get("health_status", {}).get("health_warnings_sent", 0) + 1
        
        subject = f"⚠️ {event_name} Monitor - Health Warning #{warning_num}"
        
        body = f"""Your {event_name} monitor is experiencing issues:

🚨 HEALTH PROBLEMS DETECTED:
──────────────────────────

{chr(10).join(f"• {reason}" for reason in reasons)}

📊 TROUBLESHOOTING:
──────────────────
• The monitor is still running and will keep trying
• Some sources may be temporarily blocking automated access
• This is warning #{warning_num} of 3 maximum warnings

🛑 AUTOMATIC SHUTDOWN:
─────────────────────
If problems persist for too long, the monitor will automatically shut down and send you a final notification.

⚙️ CURRENT STATUS:
─────────────────
• Session: {self.session_name}
• Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Total checks: {state.get("health_status", {}).get("total_checks", 0)}

The monitor will continue trying to access the sources.
"""
        
        self.send_email(subject, body)
    
    def send_weekly_status(self, state: Dict):
        """Send weekly 'I'm alive' status email."""
        event_name = self.config.get('event_name', self.session_name)
        health = state.get("health_status", {})
        
        # Calculate runtime
        if self.end_date:
            start_date = self.end_date - timedelta(weeks=7)
            days_running = (datetime.now() - start_date).days
            days_remaining = (self.end_date - datetime.now()).days
        else:
            days_running = "Unknown"
            days_remaining = "No end date set"
        
        # Get recent activity stats
        total_checks = health.get("total_checks", 0)
        last_url_success = health.get("last_successful_url_check", "Never")
        last_instagram_success = health.get("last_successful_instagram_check", "Never")
        
        if last_url_success != "Never":
            try:
                last_url_time = datetime.fromisoformat(last_url_success)
                url_status = f"✅ Last successful: {last_url_time.strftime('%Y-%m-%d %H:%M')}"
            except:
                url_status = "✅ Recently successful"
        else:
            url_status = "⚠️ No successful checks yet"
            
        if last_instagram_success != "Never":
            try:
                last_instagram_time = datetime.fromisoformat(last_instagram_success)
                instagram_status = f"✅ Last successful: {last_instagram_time.strftime('%Y-%m-%d %H:%M')}"
            except:
                instagram_status = "✅ Recently successful"
        else:
            instagram_status = "⚠️ No successful checks yet"
        
        subject = f"📊 {event_name} Monitor - Weekly Status Report"
        
        body = f"""Your {event_name} monitor is alive and running!

🟢 SYSTEM STATUS: RUNNING
──────────────────────────

📅 RUNTIME STATISTICS:
• Days running: {days_running}
• Days remaining: {days_remaining}
• Total system checks: {total_checks:,}
• Session: {self.session_name}

🌐 WEB MONITORING:
{url_status}

📱 INSTAGRAM MONITORING:
{instagram_status}

🔍 WHAT I'M WATCHING FOR:
──────────────────────────
• "single day tickets"
• "day passes" 
• "individual day"
• "one day tickets"
• And other ticket-related phrases

💻 TECHNICAL STATUS:
───────────────────
• Screen session: Should be running
• Last report: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Health warnings: {health.get('health_warnings_sent', 0)}/3

🛡️ ROBUSTNESS FEATURES:
──────────────────────
• Auto-retry on failures
• Health monitoring active
• Progressive warning system
• Auto-shutdown after repeated failures

✅ Everything looks good! I'll email you immediately if tickets are announced.

Next weekly report: {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}
"""
        
        self.send_email(subject, body)
    
    def send_shutdown_email(self, reason: str):
        """Send email notification that monitoring is shutting down due to failures."""
        event_name = self.config.get('event_name', self.session_name)
        
        subject = f"🛑 {event_name} Monitor - Automatic Shutdown"
        
        body = f"""Your {event_name} monitor has automatically shut down.

🛑 SHUTDOWN REASON:
─────────────────
{reason}

📊 FINAL STATUS:
──────────────
• Session: {self.session_name}
• Shutdown time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Reason: System health check failed repeatedly

🔄 TO RESTART:
─────────────
If you want to restart monitoring, run:
    ./ticketnotifier/bin/python event_alert.py --session making_time --test-email

The monitor has disconnected from all services.
"""
        
        self.send_email(subject, body)
        """Send email notification that monitoring has completed."""
        if not self.end_date:
            return False
            
        event_name = self.config.get('event_name', self.session_name)
        
        subject = f"🎵 {event_name} Monitor - 7-Week Period Complete"
        
        start_date = self.end_date - timedelta(weeks=7)
        
        body = f"""Your {event_name} monitoring period has completed!

📊 MONITORING SUMMARY:
─────────────────────

⏰ Started: {start_date.strftime('%Y-%m-%d %H:%M')}
🏁 Ended: {self.end_date.strftime('%Y-%m-%d %H:%M')}
📧 Monitoring session: {self.session_name}

The monitor has automatically stopped and disconnected from your email.

🎫 If tickets haven't been announced yet and you want to continue monitoring, 
you can restart the monitor with:

    ./ticketnotifier/bin/python event_alert.py --session making_time --test-email

Thank you for using EventAlert! 🎵
"""
        
        return self.send_email(subject, body)
    
    def _format_triggers(self) -> str:
        """Format trigger phrases for display."""
        triggers = self.config.get('triggers', [])
        formatted = []
        for trigger in triggers:
            # Convert regex to more readable format
            readable = trigger.replace('\\s*', ' ').replace('\\s', ' ').replace('(', '').replace(')', '').replace('|', ' or ')
            formatted.append(f"  • \"{readable}\"")
        
        return "\n".join(formatted) if formatted else "  No triggers configured"
    
    def load_state(self) -> Dict:
        """Load the persistent state from JSON file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                self.logger.warning(f"Could not load state file: {e}")
        
        return {
            "last_instagram_ids": {},
            "last_check": None,
            "notifications_sent": [],
            "session_name": self.session_name,
            "health_status": {
                "last_successful_url_check": None,
                "last_successful_instagram_check": None,
                "consecutive_url_failures": 0,
                "consecutive_instagram_failures": 0,
                "total_checks": 0,
                "health_warnings_sent": 0
            }
        }
    
    def save_state(self, state: Dict) -> None:
        """Save the current state to JSON file."""
        try:
            state["session_name"] = self.session_name
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save state: {e}")
    
    def send_sms(self, message: str) -> bool:
        """Send SMS notification via Twilio."""
        if not TWILIO_AVAILABLE:
            self.logger.warning("Twilio not available for SMS notifications")
            return False
        
        try:
            twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
            twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
            twilio_from = os.getenv("TWILIO_PHONE_FROM")
            twilio_to = os.getenv("TWILIO_PHONE_TO")
            
            if not all([twilio_sid, twilio_token, twilio_from, twilio_to]):
                self.logger.warning("Twilio credentials not configured")
                return False
            
            client = TwilioClient(twilio_sid, twilio_token)
            
            message = client.messages.create(
                body=message,
                from_=twilio_from,
                to=twilio_to
            )
            
            self.logger.info(f"SMS sent successfully to {twilio_to}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send SMS: {e}")
            return False
    
    def send_email(self, subject: str, body: str) -> bool:
        """Send email notification."""
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = os.getenv("EMAIL_FROM")
            msg["To"] = os.getenv("EMAIL_TO")
            msg.set_content(body)
            
            smtp_user = os.getenv("SMTP_USER")
            
            # Use provided password or get from environment or prompt for it
            if self.smtp_password:
                smtp_pass = self.smtp_password
            else:
                smtp_pass = os.getenv("GMAIL_APP_PASSWORD") or os.getenv("SMTP_PASS")
                if not smtp_pass:
                    print(f"\n🔐 Please enter email password for {smtp_user}:")
                    smtp_pass = getpass.getpass("Password: ")
            
            if not smtp_user or not smtp_pass:
                raise ValueError("SMTP credentials not configured")
            
            with smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), 
                            int(os.getenv("SMTP_PORT", "587"))) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            
            self.logger.info(f"Email sent successfully to {os.getenv('EMAIL_TO')}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False
    
    def text_matches(self, text: str) -> Optional[str]:
        """Check if text contains any trigger phrases. Returns the matched pattern."""
        triggers = self.config.get('triggers', [])
        for pattern in triggers:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
    
    def check_urls(self, state: Dict) -> List[str]:
        """Check all monitored URLs for trigger phrases."""
        hits = []
        urls = self.config.get('urls', [])
        health = state.setdefault("health_status", {})
        
        any_url_success = False
        
        if isinstance(urls, dict):
            # Handle dict format: {"name": "url"}
            url_items = urls.items()
        else:
            # Handle list format: ["url1", "url2"] - create name from URL
            url_items = [(url.split('/')[-1] or url, url) for url in urls]
        
        for name, url in url_items:
            try:
                self.logger.debug(f"Checking {name}: {url}")
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                
                response = requests.get(url, timeout=15, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                text = soup.get_text(" ", strip=True)
                
                # Mark as successful
                any_url_success = True
                health["consecutive_url_failures"] = 0
                
                matched_phrase = self.text_matches(text)
                if matched_phrase:
                    hit_msg = f"{name}: {url} (found: '{matched_phrase}')"
                    hits.append(hit_msg)
                    self.logger.info(f"TRIGGER DETECTED on {name}: {matched_phrase}")
                    
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Network error checking {url}: {e}")
                health["consecutive_url_failures"] = health.get("consecutive_url_failures", 0) + 1
            except Exception as e:
                self.logger.warning(f"Error checking {url}: {e}")
                health["consecutive_url_failures"] = health.get("consecutive_url_failures", 0) + 1
        
        # Update health status
        if any_url_success:
            health["last_successful_url_check"] = datetime.now().isoformat()
        
        return hits
    
    def check_instagram(self, state: Dict) -> List[str]:
        """Check Instagram accounts for trigger phrases in recent posts."""
        hits = []
        instagram_users = self.config.get('instagram_users', [])
        health = state.setdefault("health_status", {})
        
        if not instagram_users:
            return hits
        
        any_instagram_success = False
        
        try:
            # Configure instaloader to be less aggressive and more human-like
            L = instaloader.Instaloader(
                download_pictures=False,
                download_comments=False,
                download_videos=False,
                save_metadata=False,
                quiet=True,
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                request_timeout=30,  # Longer timeout
                max_connection_attempts=1  # Don't retry immediately
            )
            
            for user_idx, user in enumerate(instagram_users):
                try:
                    self.logger.debug(f"Checking Instagram @{user}")
                    
                    # Add delay between users to avoid rate limiting
                    if user_idx > 0:
                        self.logger.debug("Waiting 5 seconds between Instagram accounts...")
                        time.sleep(5)
                    
                    # Check if we've been rate limited recently and should wait longer
                    instagram_backoff = health.get("instagram_backoff_until")
                    if instagram_backoff:
                        backoff_time = datetime.fromisoformat(instagram_backoff)
                        if datetime.now() < backoff_time:
                            minutes_to_wait = (backoff_time - datetime.now()).total_seconds() / 60
                            self.logger.debug(f"Instagram backoff active, waiting {minutes_to_wait:.1f} more minutes")
                            continue  # Skip this user for now
                    
                    profile = instaloader.Profile.from_username(L.context, user)
                    
                    # Longer delay after getting profile (reduce API pressure)
                    time.sleep(3)
                    
                    last_seen_id = state["last_instagram_ids"].get(user)
                    
                    new_posts = []
                    posts_checked = 0
                    recent_captions = []  # For health monitoring
                    
                    for post in profile.get_posts():
                        posts_checked += 1
                        
                        # Stop if we've reached the last seen post
                        if post.shortcode == last_seen_id:
                            break
                        
                        # Check only recent posts (last 3 instead of 5 to reduce requests)
                        if posts_checked > 3:
                            break
                        
                        # Add delay between post requests (human-like browsing)
                        if posts_checked > 1:
                            self.logger.debug(f"Waiting 2 seconds before next post...")
                            time.sleep(2)
                        
                        new_posts.append(post)
                        
                        # Check caption for trigger phrases
                        caption = post.caption or ""
                        recent_captions.append(caption[:100])  # Store snippet for health check
                        
                        matched_phrase = self.text_matches(caption)
                        
                        if matched_phrase:
                            hit_msg = f"Instagram @{user}: https://instagram.com/p/{post.shortcode} (found: '{matched_phrase}')"
                            hits.append(hit_msg)
                            self.logger.info(f"TRIGGER DETECTED on Instagram @{user}: {matched_phrase}")
                    
                    # Update last seen post if we found any new posts
                    if new_posts:
                        state["last_instagram_ids"][user] = new_posts[0].shortcode
                        self.logger.debug(f"Updated last seen post for @{user}")
                    
                    # Mark as successful if we got captions
                    if recent_captions:
                        any_instagram_success = True
                        health["consecutive_instagram_failures"] = 0
                        # Log recent captions for verification
                        self.logger.debug(f"✅ Successfully read {len(recent_captions)} recent posts from @{user}")
                        for i, caption in enumerate(recent_captions):
                            self.logger.debug(f"  Post {i+1}: {caption}")
                    
                except Exception as e:
                    error_msg = str(e)
                    self.logger.warning(f"Error checking Instagram @{user}: {error_msg}")
                    health["consecutive_instagram_failures"] = health.get("consecutive_instagram_failures", 0) + 1
                    
                    # Check if this is a rate limiting error
                    if "403" in error_msg or "401" in error_msg or "rate" in error_msg.lower():
                        # Set backoff period - start with 30 minutes, increase on repeated failures
                        failures = health.get("consecutive_instagram_failures", 0)
                        backoff_minutes = min(30 * (2 ** min(failures-1, 3)), 240)  # Max 4 hours
                        backoff_until = datetime.now() + timedelta(minutes=backoff_minutes)
                        health["instagram_backoff_until"] = backoff_until.isoformat()
                        self.logger.info(f"Instagram rate limited, backing off for {backoff_minutes} minutes")
                    
        except Exception as e:
            self.logger.error(f"Instagram check failed: {e}")
            health["consecutive_instagram_failures"] = health.get("consecutive_instagram_failures", 0) + 1
        
        # Update health status
        if any_instagram_success:
            health["last_successful_instagram_check"] = datetime.now().isoformat()
        
        return hits
    
    def run_check(self):
        """Run a complete check of all monitored sources."""
        self.logger.info("Starting ticket availability check...")
        
        state = self.load_state()
        state["last_check"] = datetime.now().isoformat()
        
        # Increment total checks for health monitoring
        health = state.setdefault("health_status", {})
        health["total_checks"] = health.get("total_checks", 0) + 1
        
        # Check system health first
        if not self.check_system_health(state):
            self.logger.error("System health check failed. Shutting down.")
            return None  # Signal health failure (different from no tickets found)
        
        # Check all sources
        url_hits = self.check_urls(state)
        instagram_hits = self.check_instagram(state)
        
        all_hits = url_hits + instagram_hits
        
        if all_hits:
            # Send notification
            event_name = self.config.get('event_name', self.session_name)
            subject = f"🎯 {event_name} - Tickets Detected!"
            body = (
                f"One or more sources mentioned tickets for {event_name}:\n\n" +
                "\n".join(f"• {hit}" for hit in all_hits) +
                f"\n\nCheck performed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            if self.send_email(subject, body):
                # Also send SMS if configured
                sms_message = f"{event_name} tickets detected! Check your email for details."
                self.send_sms(sms_message)
                
                # Record successful notification
                notification_record = {
                    "timestamp": datetime.now().isoformat(),
                    "hits": all_hits
                }
                state["notifications_sent"].append(notification_record)
                self.logger.info("Notification sent successfully!")
            else:
                self.logger.error("Failed to send notification")
        else:
            self.logger.info("No triggers detected - continuing to monitor")
        
        # Save updated state
        self.save_state(state)
        
        return len(all_hits) > 0
    
    def send_completion_email(self) -> bool:
        """Send email notification that monitoring has completed."""
        if not self.end_date:
            return False
            
        event_name = self.config.get('event_name', self.session_name)
        
        subject = f"🎵 {event_name} Monitor - 7-Week Period Complete"
        
        start_date = self.end_date - timedelta(weeks=7)
        
        body = f"""Your {event_name} monitoring period has completed!

📊 MONITORING SUMMARY:
─────────────────────

⏰ Started: {start_date.strftime('%Y-%m-%d %H:%M')}
🏁 Ended: {self.end_date.strftime('%Y-%m-%d %H:%M')}
📧 Monitoring session: {self.session_name}

The monitor has automatically stopped and disconnected from your email.

🎫 If tickets haven't been announced yet and you want to continue monitoring, 
you can restart the monitor with:

    ./ticketnotifier/bin/python event_alert.py --session making_time --test-email

Thank you for using EventAlert! 🎵
"""
        
        return self.send_email(subject, body)
    
    def start_monitoring(self, send_test: bool = False):
        """Start the monitoring loop."""
        check_interval = self.config.get('check_interval_minutes', 30)
        
        # Check if monitoring period has already expired
        if self.is_monitoring_expired():
            self.logger.info("Monitoring period has already expired. Sending completion notice and exiting.")
            self.send_completion_email()
            return
        
        self.logger.info(f"Starting monitoring for {self.config['event_name']}")
        self.logger.info(f"Check interval: {check_interval} minutes")
        
        if self.end_date:
            days_remaining = (self.end_date - datetime.now()).days
            self.logger.info(f"Monitoring will end in {days_remaining} days on {self.end_date.strftime('%Y-%m-%d')}")
        
        self.logger.info(f"Monitoring URLs: {self.config.get('urls', [])}")
        self.logger.info(f"Monitoring Instagram: {self.config.get('instagram_users', [])}")
        
        # Send test email if requested
        if send_test:
            self.logger.info("Sending test email...")
            if self.send_test_email():
                self.logger.info("✅ Test email sent successfully!")
                print("✅ Test email sent! Check your inbox to confirm setup.")
            else:
                self.logger.error("❌ Failed to send test email")
                print("❌ Failed to send test email. Please check your configuration.")
                return
        
        # Add monitoring control flag
        self.monitoring_active = True
        
        def scheduled_check():
            """Wrapper for run_check that handles health failures."""
            if not self.monitoring_active:
                return
            
            check_result = self.run_check()
            if check_result is None:  # Health check failed
                self.logger.error("🛑 Health check failed. Stopping monitoring.")
                self.monitoring_active = False
        
        # Schedule regular checks
        schedule.every(check_interval).minutes.do(scheduled_check)
        
        # Run initial check
        self.logger.info("Running initial check...")
        initial_result = self.run_check()
        if initial_result is None:
            self.logger.error("🛑 Initial health check failed. Aborting startup.")
            return
        
        # Main monitoring loop
        self.logger.info("Starting monitoring loop...")
        try:
            while self.monitoring_active:
                # Check if monitoring period has ended
                if self.is_monitoring_expired():
                    self.logger.info("🏁 Monitoring period completed! Sending final notification...")
                    self.send_completion_email()
                    self.logger.info("✅ Monitoring ended gracefully. Goodbye!")
                    break
                
                # Run scheduled jobs (this will run scheduled_check when it's time)
                schedule.run_pending()
                time.sleep(30)  # Check for scheduled jobs every 30 seconds
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Monitoring loop error: {e}")
            # Send error notification
            self.send_shutdown_email(f"Unexpected error: {str(e)}")
            raise


def load_session_config(session_name: str) -> Dict[str, Any]:
    """Load session configuration from file."""
    config_file = f"sessions/{session_name}.json"
    
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Session config not found: {config_file}")
    
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in session config: {e}")


def list_sessions():
    """List all available session configurations."""
    sessions_dir = Path("sessions")
    if not sessions_dir.exists():
        print("No sessions directory found. Run setup.py first.")
        return
    
    config_files = list(sessions_dir.glob("*.json"))
    
    if not config_files:
        print("No session configurations found in sessions/ directory.")
        return
    
    print("Available sessions:")
    for config_file in config_files:
        session_name = config_file.stem
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            event_name = config.get('event_name', session_name)
            description = config.get('description', 'No description')
            print(f"  • {session_name}: {event_name} - {description}")
        except Exception as e:
            print(f"  • {session_name}: Error loading config - {e}")


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="EventAlert - Generic Event Ticket Notifier"
    )
    parser.add_argument(
        "--session", "-s",
        help="Session name to run (e.g., making_time)"
    )
    parser.add_argument(
        "--list-sessions", "-l",
        action="store_true",
        help="List all available sessions"
    )
    parser.add_argument(
        "--test-email", "-t",
        action="store_true",
        help="Send a test email and start monitoring"
    )
    parser.add_argument(
        "--password", "-p",
        help="SMTP password (will be prompted securely if not provided)"
    )
    parser.add_argument(
        "--weeks", "-w",
        type=int,
        default=7,
        help="Number of weeks to monitor (default: 7)"
    )
    
    args = parser.parse_args()
    
    if args.list_sessions:
        list_sessions()
        return
    
    if not args.session:
        print("Error: Must specify --session or --list-sessions")
        print("Use --help for usage information")
        return
    
    try:
        # Load session configuration
        config = load_session_config(args.session)
        
        # Calculate end date (7 weeks from now by default)
        end_date = datetime.now() + timedelta(weeks=args.weeks)
        
        # Get password securely if not provided
        smtp_password = args.password
        if not smtp_password and not os.getenv("GMAIL_APP_PASSWORD") and not os.getenv("SMTP_PASS"):
            print(f"\n🔐 Enter email password for {os.getenv('SMTP_USER')}:")
            smtp_password = getpass.getpass("Password (hidden): ")
        
        print(f"\n🎯 Starting {args.weeks}-week monitoring for {config['event_name']}")
        print(f"📅 Will automatically stop on: {end_date.strftime('%Y-%m-%d at %H:%M')}")
        print(f"🔄 Press Ctrl+C to stop early\n")
        
        # Create and start event alert
        alert = EventAlert(config, smtp_password, end_date)
        alert.start_monitoring(send_test=args.test_email)
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Use --list-sessions to see available sessions")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
