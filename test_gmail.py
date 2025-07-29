#!/usr/bin/env python3
"""
Quick Gmail Test - Test your App Password
"""

import smtplib
import getpass
from email.message import EmailMessage

def test_gmail():
    email = "your-email@gmail.com"
    
    print("🔐 Testing Gmail App Password...")
    print("Make sure you're using a Gmail App Password (not your regular password)")
    print("Generate one at: https://myaccount.google.com/apppasswords")
    
    app_password = getpass.getpass("\nEnter Gmail App Password: ")
    
    try:
        msg = EmailMessage()
        msg["Subject"] = "🎵 Making Time Monitor - Quick Test"
        msg["From"] = email
        msg["To"] = email
        msg.set_content("✅ Your Gmail App Password is working! You can now start the Making Time monitor.")
        
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email, app_password)
            server.send_message(msg)
        
        print("✅ SUCCESS! Test email sent.")
        print("🚀 Your Gmail is configured correctly.")
        print("\n📋 Next steps:")
        print("   ./start_robust_monitor.sh")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        if "Username and Password not accepted" in str(e):
            print("\n💡 This usually means:")
            print("   1. You're using your regular Gmail password (not App Password)")
            print("   2. 2-Factor Authentication isn't enabled")
            print("   3. The App Password was typed incorrectly")

if __name__ == "__main__":
    test_gmail()
