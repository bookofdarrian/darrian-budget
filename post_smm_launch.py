#!/usr/bin/env python3
"""
post_smm_launch.py
Posts the Social Media Manager launch video + caption to Twitter/X and TikTok.
Browser opens — log in when prompted, script handles the rest.
"""
import asyncio, subprocess
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

VIDEO  = str(Path(__file__).parent / "videos/final_slides.mp4")

TWEET = """just built the ultimate social media manager 📱

compose once → post to TikTok, IG Reels, YouTube Shorts, Facebook & Twitter/X — all from one page

running on a home server while i'm at work 😭 AI keeps adding features

built with python + streamlit + claude
peachstatesavings.com

#buildinpublic #blacktech #solofounder #ai #sideproject"""

TIKTOK_CAPTION = """built my own social media manager so I can post everywhere at once 😭

one page → TikTok, IG Reels, YouTube Shorts, Facebook, Twitter all at the same time
AI writes the captions, builds 30-day calendars, adapts for each platform

running this from a server in my house while working fulltime at Visa & finishing Georgia Tech

peachstatesavings.com — free
follow the build 👉 @bookofdarrian

#buildinpublic #techlife #softwareengineer #sideproject #ai #blacktech #solofounder #socialmedia"""

async def post_tweet(page, text, video_path):
    print("\n  🐦 Posting to Twitter/X...")
    await page.goto("https://x.com/home", wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    if "login" in page.url or "/i/flow" in page.url:
        print("  ⏳ Please log into Twitter/X (90 seconds)...")
        try:
            await page.wait_for_url("**/home", timeout=90000)
        except PWTimeout:
            print("  ⚠️ Login timeout — skipping Twitter")
            return

    # Click compose
    try:
        await page.goto("https://x.com/compose/post", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
    except Exception:
        pass

    # Type tweet
    try:
        box = page.locator('div[data-testid^="tweetTextarea"]').last
        await box.click()
        await page.wait_for_timeout(500)
        await page.keyboard.type(text[:280], delay=10)
        await page.wait_for_timeout(800)

        # Attach video via file chooser
        async with page.expect_file_chooser(timeout=5000) as fc_info:
            await page.locator('[data-testid="fileInput"]').click()
        fc = await fc_info.value
        await fc.set_files(video_path)
        await page.wait_for_timeout(4000)
        print("  📎 Video attached")
    except Exception as e:
        print(f"  ⚠️ Attach failed ({e}) — posting text only")
        box = page.locator('div[data-testid^="tweetTextarea"]').last
        await box.click()
        await page.keyboard.type(text[:280], delay=10)

    # Post
    try:
        post_btn = page.locator('[data-testid="tweetButton"]').last
        await post_btn.wait_for(state="visible", timeout=8000)
        await post_btn.click()
        await page.wait_for_timeout(3000)
        print("  ✅ Twitter/X posted!")
    except Exception as e:
        print(f"  ⚠️ Post click failed: {e}")

async def post_tiktok(page, caption, video_path):
    print("\n  🎵 Posting to TikTok...")
    await page.goto("https://www.tiktok.com/upload", wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)

    if "login" in page.url:
        print("  ⏳ Please log into TikTok (120 seconds)...")
        try:
            await page.wait_for_function(
                "() => window.location.href.includes('upload')", timeout=120000
            )
        except PWTimeout:
            print("  ⚠️ TikTok login timeout")
            return

    # Upload video
    try:
        async with page.expect_file_chooser(timeout=8000) as fc_info:
            await page.locator('input[type="file"]').click()
        fc = await fc_info.value
        await fc.set_files(video_path)
        await page.wait_for_timeout(8000)
        print("  📎 Video uploading...")

        # Add caption
        cap_el = page.locator('[data-text="true"]').first
        await cap_el.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.type(caption, delay=5)
        await page.wait_for_timeout(1000)

        # Post
        post_btn = page.locator('button:has-text("Post")').last
        await post_btn.wait_for(state="visible", timeout=10000)
        await post_btn.click()
        await page.wait_for_timeout(3000)
        print("  ✅ TikTok posted!")
    except Exception as e:
        print(f"  ⚠️ TikTok error: {e} — upload manually at tiktok.com/upload")

async def main():
    print(f"🎬 Video: {VIDEO}")
    if not Path(VIDEO).exists():
        print("❌ Video not found!"); return

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized"]
        )
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36"
        )
        page = await ctx.new_page()

        await post_tweet(page, TWEET, VIDEO)
        await asyncio.sleep(2)
        await post_tiktok(page, TIKTOK_CAPTION, VIDEO)

        print("\n✅ All done! Check Twitter/X and TikTok.")
        print("📋 For Instagram Reels + YouTube Shorts — upload manually from:")
        print(f"   {VIDEO}")
        await asyncio.sleep(5)
        await browser.close()

asyncio.run(main())
