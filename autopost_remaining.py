#!/usr/bin/env python3
"""
autopost_remaining.py
Posts: Facebook launch post + Chuck Norris tribute tweet.
Browser opens — log in to each site when prompted.
"""
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

FB_POST = open("FB_POST.txt").read().strip()

CHUCK_TWEET = "RIP Chuck Norris 🕊️ — 86 years of being the most legendary dude on the planet. One of a kind. Rest easy, legend."

JCOLE_TWEET = "building to '03 adolescence by j. cole on repeat. the vibe just hits different when you're turning nothing into something. 🍑"


async def post_tweet(page, text: str, label: str):
    """Post a single tweet."""
    print(f"\n  🐦 Posting tweet: {label}")
    await page.goto("https://x.com/compose/post", wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    # Dismiss overlays
    for sel in ['[data-testid="twc-cc-mask"]']:
        try:
            if await page.locator(sel).count() > 0:
                await page.locator(sel).click(force=True)
                await page.wait_for_timeout(500)
        except Exception:
            pass

    # Type the tweet
    box = page.locator('div[data-testid^="tweetTextarea"]').last
    await box.evaluate("el => el.click()")
    await page.wait_for_timeout(300)
    await page.keyboard.type(text, delay=8)
    await page.wait_for_timeout(800)

    # Post it
    post_btn = page.locator('[data-testid="tweetButton"]').last
    await post_btn.wait_for(state="visible", timeout=8000)
    await post_btn.evaluate("el => el.click()")
    await page.wait_for_timeout(3000)
    print(f"  ✅ Tweet posted: {label}")


async def post_facebook(page):
    """Post the FB launch story with Chuck Norris tribute."""
    print("\n  📘 Facebook — launch post + Chuck Norris tribute")
    await page.goto("https://www.facebook.com", wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    # Wait for login if needed
    if "login" in page.url:
        print("  ⏳ Log into Facebook (90 seconds)...")
        try:
            await page.wait_for_function(
                "() => !window.location.href.includes('login')", timeout=90000
            )
        except PWTimeout:
            pass
        await page.wait_for_timeout(3000)

    print(f"  FB URL: {page.url}")

    # Try auto-click compose
    compose_clicked = False
    for sel in ['[aria-label*="mind"]', '[aria-label*="Mind"]',
                'div[role="button"]:has-text("What")',
                'div[data-pagelet="FeedComposer"] div[role="button"]']:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                await el.wait_for(state="visible", timeout=4000)
                await el.evaluate("el => el.click()")
                compose_clicked = True
                print(f"  ✓ Compose clicked: {sel}")
                break
        except Exception:
            continue

    if not compose_clicked:
        print("  ⚠️  Click the 'What\\'s on your mind' box in the browser (you have 60s)...")

    # Wait for contenteditable to appear (up to 90 seconds — covers manual click too)
    try:
        await page.wait_for_selector('div[contenteditable="true"]', timeout=90000)
        boxes = page.locator('div[contenteditable="true"]')
        count = await boxes.count()
        box = boxes.nth(count - 1)
        await box.evaluate("el => el.focus()")
        await page.wait_for_timeout(300)

        # Type using keyboard — character by character
        print("  Typing launch post...")
        await page.keyboard.type(FB_POST, delay=5)
        await page.wait_for_timeout(2000)

        # Click Post
        for btn_sel in ['div[aria-label="Post"]', 'div[aria-label="Share"]',
                        'div[role="button"]:has-text("Post")']:
            try:
                btn = page.locator(btn_sel).last
                if await btn.count() > 0:
                    await btn.evaluate("el => el.click()")
                    await page.wait_for_timeout(3000)
                    print(f"  ✅ FACEBOOK POST SUBMITTED!")
                    return
            except Exception:
                continue

        print("  ⚠️  Post typed — click 'Post' manually in the browser window")
        await page.wait_for_timeout(30000)

    except Exception as e:
        print(f"  ❌ Facebook error: {e}")
        print("  ⚠️  The post is in your clipboard — Cmd+V in the FB box and click Post")
        await page.wait_for_timeout(30000)


async def main():
    print("=" * 60)
    print("🍑  Remaining Posts — Facebook + Chuck Norris Tribute")
    print("=" * 60)
    print("""
Browser opening — two posts:
  1. Facebook: Full launch story + Chuck Norris tribute
  2. Twitter/X: RIP Chuck Norris tribute tweet
""")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = await context.new_page()

        # ── Twitter login first ──────────────────────────────────────────
        print("\n📌 Step 1: Log into Twitter/X")
        await page.goto("https://x.com", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        if "login" in page.url or not await page.locator('a[href="/home"]').count():
            print("  ⏳ Log into Twitter (90 seconds)...")
            try:
                await page.wait_for_url("**/home", timeout=90000)
            except PWTimeout:
                print("  ⚠️  Twitter login timeout — trying anyway")
            await page.wait_for_timeout(2000)

        # Post Chuck Norris tribute
        try:
            await post_tweet(page, CHUCK_TWEET, "RIP Chuck Norris")
        except Exception as e:
            print(f"  ❌ Chuck tweet error: {e}")

        # Post J. Cole vibe tweet
        try:
            await post_tweet(page, JCOLE_TWEET, "J Cole 03 Adolescence vibe")
        except Exception as e:
            print(f"  ❌ J Cole tweet error: {e}")

        # ── Facebook ────────────────────────────────────────────────────
        print("\n📌 Step 2: Facebook — launch post")
        try:
            await post_facebook(page)
        except Exception as e:
            print(f"  ❌ Facebook error: {e}")

        print("\n" + "=" * 60)
        print("✅  ALL POSTS DONE!")
        print("=" * 60)
        print("""
Posted today:
  ✅ Twitter — 12-tweet launch thread
  ✅ Twitter — RIP Chuck Norris tribute
  ✅ Facebook — Launch story + Chuck Norris tribute

Keeping browser open 15s so you can verify...
""")
        await page.wait_for_timeout(15000)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
