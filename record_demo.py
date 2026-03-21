#!/usr/bin/env python3
"""
record_demo.py — Auto-records a cinematic tour of the app.

Playwright records the video automatically (no QuickTime needed).
Output: videos/demo_tour.webm  (convert to mp4 with ffmpeg)

Usage:
  python3 record_demo.py          — full 90s tour (YouTube/long)
  python3 record_demo.py --short  — 60s tour (TikTok/Reels/Shorts)

You record the voiceover separately (Voice Memos, then sync in CapCut).
Voiceover script is printed to terminal as it runs.
"""
import asyncio
import sys
import os
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

SHORT = "--short" in sys.argv
DURATION = 60 if SHORT else 90

# Always use prod URL
APP_URL = "https://peachstatesavings.com"
PROD_URL = "https://peachstatesavings.com"

VIDEO_DIR = Path("videos")
VIDEO_DIR.mkdir(exist_ok=True)

VOICEOVER = """
╔══════════════════════════════════════════════════════════╗
║  🎙️  VOICEOVER SCRIPT — read this while recording       ║
║  Record in Voice Memos app, then sync in CapCut          ║
╚══════════════════════════════════════════════════════════╝

[0:00 — HOOK — Dashboard Overview]
"My computer built me a new app feature while I was sleeping.
 This is everything I've built."

[0:08 — Expenses & Income pages]
"Peach State Savings — a personal finance operating system.
 140 pages. Budget tracker, income manager, RSU calendar,
 investments, cash flow — all in one place. Free."

[0:20 — SoleOps — Inventory + ARB Scanner]
"SoleOps — my sneaker resale business suite.
 AI listing generator, inventory manager, and an ARB scanner
 that texts me when a pair drops below my buy price.
 It made me $200 before breakfast."

[0:35 — College Confused]
"College Confused — free AI college prep for first-gen students.
 FAFSA walkthrough, essay assistant, AI mock interviews.
 I was first-gen. This is the platform I wish I'd had.
 Always free. Always will be."

[0:48 — Social Media Manager + AI Budget Chat]
"And all of this runs on a server in my house,
 managed by an overnight AI system that builds features
 while I sleep."

[0:56 — End card]
"peachstatesavings.com — free.
 getsoleops.com — April launch.
 collegeconfused.org — always free.
 Follow the build: @bookofdarrian"
"""


async def scroll_page(page, px: int = 600, pause: float = 0.8):
    await page.evaluate(f"window.scrollBy({{top: {px}, behavior: 'smooth'}})")
    await page.wait_for_timeout(int(pause * 1000))


async def nav(page, path: str, wait: int = 4000, scroll: bool = True):
    await page.goto(f"{APP_URL}{path}", wait_until="domcontentloaded", timeout=20000)
    await page.wait_for_timeout(2500)
    if scroll:
        await scroll_page(page, 300)
    await page.wait_for_timeout(wait)


async def handle_login(page):
    """Always wait for login — 90 second window."""
    await page.wait_for_timeout(2000)
    content = await page.content()
    if "Login" in content or "login" in page.url or "Sign in" in content:
        print("\n⏳ LOG IN NOW — you have 90 seconds in the browser window...")
        print("   Enter your username + password, then press Enter/Sign In")
        try:
            # Wait until the page title changes away from Login
            await page.wait_for_function(
                "() => !document.body.innerText.includes('Password') && document.body.innerText.length > 500",
                timeout=90000,
            )
            print("  ✓ Logged in! Starting tour in 3 seconds...")
        except PWTimeout:
            print("  ⚠️  Login timed out — check browser")
        await page.wait_for_timeout(3000)
    else:
        print("  ✓ Already logged in — starting tour...")
        await page.wait_for_timeout(1000)


async def record_tour():
    print("=" * 60)
    print(f"🎬  Recording {'60s' if SHORT else '90s'} App Tour")
    print("=" * 60)
    print(VOICEOVER)
    print("Starting browser... log in if prompted.\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--window-size=1280,800",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(VIDEO_DIR),
            record_video_size={"width": 1280, "height": 720},
        )
        page = await context.new_page()

        # ── Opening: Dashboard ─────────────────────────────────
        print("🎬 [0:00] Opening dashboard...")
        await page.goto(APP_URL, wait_until="domcontentloaded", timeout=20000)
        await handle_login(page)

        await page.wait_for_timeout(3000)
        await scroll_page(page, 400, 1.5)
        await scroll_page(page, 400, 1.5)

        # ── Expenses ───────────────────────────────────────────
        print("🎬 [0:08] Expenses page...")
        await nav(page, "/1_expenses", wait=4000)

        # ── Income ─────────────────────────────────────────────
        print("🎬 [0:14] Income page...")
        await nav(page, "/2_income", wait=3000)

        # ── Trends ─────────────────────────────────────────────
        print("🎬 [0:18] Trends...")
        await nav(page, "/4_trends", wait=3000)

        # ── SoleOps: Inventory ─────────────────────────────────
        print("🎬 [0:22] SoleOps inventory...")
        await nav(page, "/118_soleops_inventory_manager", wait=4000, scroll=True)

        # ── SoleOps: ARB Scanner ───────────────────────────────
        print("🎬 [0:28] ARB Scanner / watchlist...")
        await nav(page, "/137_soleops_arb_scanner_watchlist_ui", wait=4000, scroll=True)

        # ── SoleOps: Drop Calendar ─────────────────────────────
        print("🎬 [0:34] Drop Calendar...")
        await nav(page, "/135_soleops_drop_calendar", wait=3000, scroll=True)

        if not SHORT:
            # ── College Confused ───────────────────────────────
            print("🎬 [0:38] College Confused...")
            try:
                await page.goto("https://collegeconfused.org", wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(4000)
                await scroll_page(page, 500, 2.0)
            except Exception:
                print("  ⚠️  collegeconfused.org not reachable — skipping")

        # ── Social Media Manager ───────────────────────────────
        print(f"🎬 [{'0:44' if SHORT else '0:48'}] Social Media Manager...")
        await nav(page, "/57_social_media_manager", wait=4000, scroll=True)

        # ── AI Budget Chat ─────────────────────────────────────
        print(f"🎬 [{'0:50' if SHORT else '0:56'}] AI Budget Chat...")
        await nav(page, "/55_ai_budget_chat", wait=3000, scroll=False)

        # ── Dashboard for end card ─────────────────────────────
        print("🎬 Final shot: back to dashboard...")
        await page.goto(APP_URL, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(4000)

        print("\n✅ Tour complete! Saving video...")
        await context.close()
        await browser.close()

    # Find the recorded file
    videos = list(VIDEO_DIR.glob("*.webm"))
    if videos:
        latest = max(videos, key=lambda v: v.stat().st_mtime)
        final_name = VIDEO_DIR / f"{'short' if SHORT else 'full'}_tour.webm"
        latest.rename(final_name)
        print(f"\n✅ VIDEO SAVED: {final_name}")
        print(f"   Size: {final_name.stat().st_size / 1024 / 1024:.1f} MB")
        print(f"\n📱 Convert to mp4 for CapCut/TikTok upload:")
        print(f"   ffmpeg -i {final_name} -c:v libx264 -crf 23 videos/tour.mp4")
        print(f"\n   OR: Open {final_name} in VLC → File → Convert")
    else:
        print("⚠️  No video found — check the videos/ folder")

    print("\n" + "=" * 60)
    print("📝  NEXT STEPS:")
    print("=" * 60)
    print("""
1. Convert to mp4:
   ffmpeg -i videos/short_tour.webm videos/tour.mp4
   (or just drag .webm into CapCut — it accepts both)

2. Open CapCut → New Project → import tour.mp4

3. Record voiceover in Voice Memos (read the script above)
   → Save as audio file → import into CapCut

4. Sync voiceover to video in CapCut

5. Add text overlays (product names, URLs, #hashtags)

6. Export 9:16 for TikTok/Reels, 16:9 for YouTube

7. Upload! Captions are in VIDEO_CONTENT_PACKAGE.md
""")


if __name__ == "__main__":
    asyncio.run(record_tour())
