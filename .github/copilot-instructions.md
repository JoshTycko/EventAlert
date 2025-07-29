# Copilot Instructions

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

This is a Python project for monitoring Making Time Philadelphia festival single-day ticket announcements. The system:

- Monitors multiple web sources (official website, Resident Advisor)
- Tracks Instagram accounts for announcements
- Sends email notifications when trigger phrases are detected
- Maintains state between runs to avoid duplicate notifications

Key components:
- Web scraping with requests and BeautifulSoup
- Instagram monitoring with instaloader
- Email notifications via SMTP
- Scheduled execution with the schedule library
- JSON state persistence

Focus on robust error handling, rate limiting, and reliable notification delivery.
