#!/usr/bin/env python3
"""
open_all_posts.py
Opens Twitter x2 + Facebook in Chrome (already logged in).
Copies each post to clipboard in sequence with pauses.
User just Cmd+V and clicks Post each time.
"""
import subprocess
import time

CHUCK_TWEET = "RIP Chuck Norris 🕊️ — 86 years of being the most legendary dude on the planet. One of a kind. Rest easy, legend."
JCOLE_TWEET = "building to '03 adolescence by j. cole on repeat. the vibe just hits different when you're turning nothing into something. 🍑"
FB_POST = open("FB_POST.txt").read().strip()

def copy(text):
    subprocess.run(["pbcopy"], input=text.encode())

def open_url(url):
    subprocess.run(["open", "-a", "Google Chrome", url])
    time.sleep(1)

print("=" * 60)
print("🍑  COPY & POST — All 3 remaining posts")
print("=" * 60)

# ── POST 1: Chuck Norris Tweet ─────────────────────────────────
print("\n📋 POST 1: RIP Chuck Norris tweet")
print(f"   \"{CHUCK_TWEET}\"")
copy(CHUCK_TWEET)
open_url("https://x.com/compose/post")
print("\n   ✅ Chuck Norris tweet COPIED to clipboard!")
print("   → Chrome just opened x.com/compose/post")
print("   → Click the text box, Cmd+V, then click POST")
print("   → Press ENTER here when done posting...")
input()

# ── POST 2: J Cole Tweet ───────────────────────────────────────
print("\n📋 POST 2: J. Cole '03 Adolescence vibe tweet")
print(f"   \"{JCOLE_TWEET}\"")
copy(JCOLE_TWEET)
open_url("https://x.com/compose/post")
print("\n   ✅ J. Cole tweet COPIED to clipboard!")
print("   → Chrome opened another compose window")
print("   → Click the text box, Cmd+V, then click POST")
print("   → Press ENTER here when done posting...")
input()

# ── POST 3: Facebook ───────────────────────────────────────────
print("\n📋 POST 3: Facebook — Full launch story + Chuck Norris tribute")
print("   (Long post — see FB_POST.txt for full text)")
copy(FB_POST)
open_url("https://www.facebook.com")
print("\n   ✅ Facebook post COPIED to clipboard!")
print("   → Chrome opened Facebook")
print("   → Click 'What\\'s on your mind', Cmd+V, then click POST")
print("   → Press ENTER here when done posting...")
input()

print("\n" + "=" * 60)
print("🎉  ALL DONE! Today's posts on @bookofdarrian:")
print("=" * 60)
print("""
  ✅ Twitter — 12-tweet launch thread (posted earlier)
  ✅ Twitter — RIP Chuck Norris tribute
  ✅ Twitter — J. Cole '03 Adolescence vibe
  ✅ Facebook — Full launch story + Chuck Norris tribute

🔥 You're live everywhere. Go check the notifications!
""")
