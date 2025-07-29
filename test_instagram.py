#!/usr/bin/env python3
"""
Instagram Access Test - Verify we can read recent posts
"""

import json
import logging
import time
from datetime import datetime

# Import our event alert system
try:
    from event_alert import EventAlert
    import instaloader
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the ticketnotifier virtual environment:")
    print("./ticketnotifier/bin/python test_instagram.py")
    exit(1)

def test_instagram_access():
    """Test Instagram access and show recent post content."""
    print("🔍 Testing Instagram POST CONTENT Access for Making Time Monitor")
    print("=" * 65)
    
    # Load the Making Time session config
    try:
        with open("sessions/making_time.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ Session config not found: sessions/making_time.json")
        return False
    
    # Get Instagram users from config
    instagram_users = config.get('instagram_users', [])
    if not instagram_users:
        print("❌ No Instagram users configured")
        return False
    
    print(f"📱 Testing POST CONTENT access to: {', '.join(instagram_users)}")
    print("💡 We need to verify we can read post captions, not just profile info")
    print()
    
    success_count = 0
    total_posts_read = 0
    
    # Test Instagram access
    try:
        L = instaloader.Instaloader(
            download_pictures=False,
            download_comments=False,
            download_videos=False,
            save_metadata=False,
            quiet=True,
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            request_timeout=30,  # Longer timeout
            max_connection_attempts=1  # Don't retry immediately on failure
        )
        
        for user in instagram_users:
            print(f"🔍 Checking POST CONTENT from @{user}...")
            
            try:
                profile = instaloader.Profile.from_username(L.context, user)
                print(f"✅ Profile access successful for @{user}")
                print(f"   📊 {profile.followers:,} followers, {profile.mediacount:,} posts")
                
                # Small delay after getting profile info (human-like)
                time.sleep(2)
                
                # The critical test: Can we read POST CAPTIONS?
                print(f"   🔍 Attempting to read recent POST CAPTIONS...")
                
                posts_read = 0
                captions_found = 0
                
                for post in profile.get_posts():
                    if posts_read >= 3:  # Test only 3 recent posts to avoid rate limiting
                        break
                    
                    posts_read += 1
                    
                    # Add delay between posts (human-like browsing)
                    if posts_read > 1:
                        print(f"   ⏳ Waiting 2 seconds before next post (human-like browsing)...")
                        time.sleep(2)
                    
                    caption = post.caption or ""
                    
                    if caption:
                        captions_found += 1
                        total_posts_read += 1
                        
                        print(f"   📰 Post {posts_read} ({post.date_utc.strftime('%Y-%m-%d')}):")
                        print(f"       📍 URL: https://instagram.com/p/{post.shortcode}")
                        print(f"       👍 {post.likes:,} likes")
                        
                        # Show first 150 characters of caption
                        caption_preview = caption[:150].replace('\n', ' ')
                        if len(caption) > 150:
                            caption_preview += "..."
                        print(f"       💬 Caption: \"{caption_preview}\"")
                        
                        # Test trigger detection
                        alert = EventAlert({'triggers': config['triggers']})
                        match = alert.text_matches(caption)
                        if match:
                            print(f"       🎯 *** TRIGGER DETECTED: '{match}' ***")
                        else:
                            print(f"       ✅ No triggers (normal for non-ticket posts)")
                        print()
                    else:
                        print(f"   📷 Post {posts_read}: No caption (image/video only)")
                
                if captions_found > 0:
                    print(f"   ✅ SUCCESS: Read {captions_found} post captions from @{user}")
                    success_count += 1
                else:
                    print(f"   ⚠️  WARNING: Could not read any post captions from @{user}")
                    print(f"   💡 This could mean rate limiting or the posts have no captions")
                
                print()
                
            except Exception as e:
                print(f"❌ Failed to access POST CONTENT from @{user}: {e}")
                if "401" in str(e) or "403" in str(e):
                    print("   💡 Rate limiting detected - Instagram is blocking automated access")
                    print("   💡 This is temporary and the monitor will retry later")
                elif "Query" in str(e):
                    print("   💡 Instagram GraphQL query blocked - this is rate limiting")
                    print("   💡 The monitor handles this gracefully with retries")
                print()
        
        print("🎯 Instagram POST CONTENT Test Results:")
        print("=" * 45)
        print(f"✅ Accounts with successful post reading: {success_count}/{len(instagram_users)}")
        print(f"📰 Total post captions read: {total_posts_read}")
        
        if total_posts_read > 0:
            print("\n🎉 EXCELLENT! We can read Instagram post content!")
            print("   ✅ Ticket announcements in posts will be detected")
            print("   ✅ The monitor will catch Making Time single-day ticket posts")
        elif success_count > 0:
            print("\n⚠️  PARTIAL SUCCESS: Some posts readable, but rate limited")
            print("   🔄 The monitor will retry and work around rate limits")
            print("   ⏰ Instagram access varies throughout the day")
        else:
            print("\n⚠️  NO POST CONTENT ACCESS: Instagram is blocking us")
            print("   💡 This is likely temporary rate limiting")
            print("   🔄 The monitor will keep retrying (Instagram blocks are usually temporary)")
            print("   📧 You'll get health alerts if this persists for 3+ days")
        
        print(f"\n🔬 TECHNICAL VERIFICATION:")
        print(f"   📱 Profile access: {'✅ Working' if success_count > 0 else '❌ Blocked'}")
        print(f"   📰 Post content access: {'✅ Working' if total_posts_read > 0 else '❌ Blocked (likely temporary)'}")
        print(f"   🎯 Trigger detection: {'✅ Ready' if total_posts_read > 0 else '⏳ Will work when posts accessible'}")
        
        return total_posts_read > 0
        
    except Exception as e:
        print(f"❌ Instagram test completely failed: {e}")
        return False

if __name__ == "__main__":
    test_instagram_access()
