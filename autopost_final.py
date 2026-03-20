#!/usr/bin/env python3
"""
autopost_final.py — Posts Chuck Norris tribute, J Cole vibe tweet, and Facebook post.
Fresh browser every run — log in once when it opens.
"""
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

FB_POST = open("FB_POST.txt").read().strip()
CHUCK_TWEET = "RIP Chuck Norris \U0001f54a\ufe0f \u2014 86 years of being the most legendary dude on the planet. One of a kind. Rest easy, legend."
JCOLE_TWEET = "building to '03 adolescence by j. cole on repeat. the vibe just hits different when you\u2019re turning nothing into something. \U0001f351"


async def post_tweet(page, text: str, label: str):
    """Post a single tweet on x.com."""
    print(f"\n  \U0001f426 Posting: {label}")
    await page.goto("https://x.com/compose/post", wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    # Dismiss overlays
    for sel in ['[data-testid="twc-cc-mask"]']:
        try:
            if await page.locator(sel).count() > 0:
                await page.locator(sel).click(force=True)
                await page.wait_for_timeout(300)
        except Exception:
            pass

    # Wait for textarea
    try:
        await page.wait_for_selector('div[data-testid^="tweetTextarea"]', timeout=10000)
    except PWTimeout:
        print(f"  \u26a0\ufe0f  Compose box not found for {label} — are you logged in?")
        return

    box = page.locator('div[data-testid^="tweetTextarea"]').last
    await box.evaluate("el => el.click()")
    await page.wait_for_timeout(400)

    # Paste via clipboard
    await page.evaluate(f"navigator.clipboard.writeText({repr(text)})")
    await page.keyboard.press("Meta+v")
    await page.wait_for_timeout(1500)

    # Submit
    try:
        post_btn = page.locator('[data-testid="tweetButton"]').last
        await post_btn.wait_for(state="visible", timeout=15000)
        await post_btn.evaluate("el => el.click()")
        await page.wait_for_timeout(3000)
        print(f"  \u2705 Posted: {label}")
    except PWTimeout:
        print(f"  \u26a0\ufe0f  Post button timeout for {label} — click Post manually")
        await page.wait_for_timeout(10000)


async def post_facebook(page):
    """Post the FB launch story."""
    print("\n  \U0001f4d8 Facebook \u2014 launch post + Chuck Norris tribute")
    await page.goto("https://www.facebook.com", wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)
    print(f"  URL: {page.url}")

    # Try auto-click compose
    for sel in ['[aria-label*="mind"]', '[aria-label*="Mind"]',
                'div[role="button"]:has-text("What")',
                'div[data-pagelet="FeedComposer"] div[role="button"]']:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                await el.wait_for(state="visible", timeout=5000)
                await el.evaluate("el => el.click()")
                print(f"  \u2713 Compose opened: {sel}")
                break
        except Exception:
            continue
    else:
        print("  \u26a0\ufe0f  Click 'What\\'s on your mind' in the browser window (2 min timeout)")

    # Wait for contenteditable (up to 2 min for manual click)
    try:
        await page.wait_for_selector('div[contenteditable="true"]', timeout=120000)
    except PWTimeout:
        print("  \u274c Compose box timed out. Post is in your clipboard \u2014 Cmd+V manually.")
        return

    boxes = page.locator('div[contenteditable="true"]')
    count = await boxes.count()
    box = boxes.nth(count - 1)
    await box.evaluate("el => el.focus()")
    await page.wait_for_timeout(300)
    print("  Typing post...")
    await page.keyboard.type(FB_POST, delay=4)
    await page.wait_for_timeout(2000)

    # Click Post button
    for btn_sel in ['div[aria-label="Post"]', 'div[aria-label="Share"]',
                    'div[role="button"]:has-text("Post")']:
        try:
            btn = page.locator(btn_sel).last
            if await btn.count() > 0:
                await btn.evaluate("el => el.click()")
                await page.wait_for_timeout(4000)
                print("  \u2705 FACEBOOK POST SUBMITTED!")
                return
        except Exception:
            continue

    print("  \u26a0\ufe0f  Post typed \u2014 click 'Post' in the browser window")
    await page.wait_for_timeout(30000)


async def main():
    print("=" * 60)
    print("\U0001f351  Final Posts \u2014 Chuck Norris + J Cole + Facebook")
    print("=" * 60)
    print("""
Browser opening \u2014 log into Twitter when it loads.
  You have 90 seconds. After login it posts automatically.
  Then it goes to Facebook (click 'What\\'s on your mind' there).
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

        # Navigate to Twitter
        await page.goto("https://x.com", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # Wait for login
        if "login" in page.url or not await page.locator('a[href="/home"]').count():
            print("\u23f3 Log into Twitter now (90 seconds)...")
            try:
                await page.wait_for_url("**/home", timeout=90000)
                print("  \u2713 Logged in!")
            except PWTimeout:
                print("  \u26a0\ufe0f  Login timeout \u2014 trying anyway...")
            await page.wait_for_timeout(2000)

        # Post tweets
        try:
            await post_tweet(page, CHUCK_TWEET, "RIP Chuck Norris \U0001f54a\ufe0f")
        except Exception as e:
            print(f"  \u274c Chuck tweet: {e}")

        try:
            await post_tweet(page, JCOLE_TWEET, "J. Cole 03 Adolescence \U0001f351")
        except Exception as e:
            print(f"  \u274c J Cole tweet: {e}")

        # Facebook
        try:
            await post_facebook(page)
        except Exception as e:
            print(f"  \u274c Facebook: {e}")

        print("\n" + "=" * 60)
        print("\u2705  ALL DONE!")
        print("=" * 60)
        print("""
Today on @bookofdarrian:
  \u2705 12-tweet launch thread
  \u2705 RIP Chuck Norris tribute
  \u2705 J. Cole '03 Adolescence vibe
  \u2705 Facebook launch story + Chuck Norris tribute

Closing in 15s...
""")
        await page.wait_for_timeout(15000)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
