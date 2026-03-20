#!/usr/bin/env python3
"""
post_now.py — SIMPLEST POSSIBLE APPROACH.

Uses Twitter's built-in intent URL — pre-fills your tweet in REAL Chrome.
No Playwright. No login. Just click Tweet.

Run: python3 post_now.py
"""
import subprocess
import time
import urllib.parse

CHUCK_TWEET = "RIP Chuck Norris 🕊️ — 86 years of being the most legendary dude on the planet. One of a kind. Rest easy, legend."
JCOLE_TWEET = "building to '03 adolescence by j. cole on repeat. the vibe just hits different when you're turning nothing into something. 🍑"
FB_POST = open("FB_POST.txt").read().strip()


def open_url(url):
    subprocess.run(["open", "-a", "Google Chrome", url])


def copy(text):
    subprocess.run(["pbcopy"], input=text.encode())


print("=" * 60)
print("🍑  Post Now — Real Chrome, No Automation")
print("=" * 60)

# ── TWEET 1: Chuck Norris ─────────────────────────────────────
chuck_url = "https://twitter.com/intent/tweet?text=" + urllib.parse.quote(CHUCK_TWEET)
print("\n📋 TWEET 1: RIP Chuck Norris 🕊️")
print(f"   {CHUCK_TWEET}")
open_url(chuck_url)
print("\n   ✅ Chrome opened — text is pre-filled. Just click 'Post'!")
print("   Press ENTER when you've clicked Post...")

# ── TWEET 2: J Cole ───────────────────────────────────────────
print("\n📋 TWEET 2: J. Cole '03 Adolescence 🍑")
print(f"   {JCOLE_TWEET}")
jcole_url = "https://twitter.com/intent/tweet?text=" + urllib.parse.quote(JCOLE_TWEET)
open_url(jcole_url)
print("\n   ✅ Chrome opened — text is pre-filled. Just click 'Post'!")
print("   Press ENTER when you've clicked Post...")

# ── FACEBOOK ─────────────────────────────────────────────────
print("\n📋 FACEBOOK: Launch story + Chuck Norris tribute")
copy(FB_POST)
open_url("https://www.facebook.com/")
print("\n   ✅ FB post COPIED to clipboard!")
print("   → Click 'What\\'s on your mind' → Cmd+V → click Post")
print("\nDone! All posts handled. 🍑")
