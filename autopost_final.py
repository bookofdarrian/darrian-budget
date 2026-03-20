#!/usr/bin/env python3
"""
autopost_final.py — Posts Chuck Norris tribute, J Cole tweet, and Facebook post.

Uses exact same approach as the working 12-tweet thread (autopost_playwright.py):
  - Standard Playwright Chromium (not channel="chrome") 
  - keyboard.type() with delay=8
  - div[data-testid^="tweetTextarea"] with .nth(count-1)

SAFETY GUARDS added for Facebook:
  - REQUIRES role="dialog" to be open before typing anything
  - All typing and submit scoped to inside the dialog only
  - Never types into feed comment boxes

Run modes:
  python3 autopost_final.py           — post everything
  python3 autopost_final.py --dry-run — verify selectors, type NOTHING
"""
import asyncio
import sys
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

DRY_RUN = "--dry-run" in sys.argv

FB_POST = open("FB_POST.txt").read().strip()
CHUCK_TWEET = "RIP Chuck Norris 🕊️ — 86 years of being the most legendary dude on the planet. One of a kind. Rest easy, legend."
JCOLE_TWEET = "building to '03 adolescence by j. cole on repeat. the vibe just hits different when you're turning nothing into something. 🍑"


# ─────────────────────────────────────────────────────────────
# TWITTER — exact same logic that posted the 12-tweet thread
# ─────────────────────────────────────────────────────────────
async def post_tweet(page, text: str, label: str):
    print(f"\n  🐦 Tweet: {label}")

    await page.goto("https://x.com/compose/post", wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    # Guard: make sure we're not on the login page
    if "login" in page.url or "i/flow" in page.url:
        print("  ❌ Twitter: not logged in — skipping")
        return False

    # Dismiss overlays (same as working script)
    for mask_sel in ['[data-testid="twc-cc-mask"]']:
        try:
            m = page.locator(mask_sel).first
            if await m.count() > 0:
                await m.click(force=True)
                await page.wait_for_timeout(300)
        except Exception:
            pass

    # Find textarea using exact same working approach: count all, use last
    boxes = page.locator('div[data-testid^="tweetTextarea"]')
    count = await boxes.count()
    if count == 0:
        print("  ❌ Compose textarea not found (not logged in?)")
        return False

    box = boxes.nth(count - 1)

    if DRY_RUN:
        print(f"  🧪 DRY RUN — found {count} tweetTextarea(s) ✓  would type: {text[:60]}...")
        return True

    # JS click then paste via clipboard (most reliable for React — avoids delay issues)
    await box.evaluate("el => el.click()")
    await page.wait_for_timeout(500)
    # Inject text directly into React's internal fiber state, then fire input event
    await page.evaluate(f"""
        const el = document.querySelector('div[data-testid^="tweetTextarea"]');
        if (el) {{
            el.focus();
            document.execCommand('insertText', false, {repr(text)});
        }}
    """)
    await page.wait_for_timeout(2000)

    # Post button — wait up to 20 seconds
    try:
        post_btn = page.locator('[data-testid="tweetButton"]').last
        await post_btn.wait_for(state="visible", timeout=20000)
        await post_btn.evaluate("el => el.click()")
        await page.wait_for_timeout(4000)
        print(f"  ✅ POSTED: {label}")
        return True
    except PWTimeout:
        print(f"  ⚠️  Post button not found — click Post manually (15s window)")
        await page.wait_for_timeout(15000)
        return False


# ─────────────────────────────────────────────────────────────
# FACEBOOK — with strict dialog safety guard
# ─────────────────────────────────────────────────────────────
async def post_facebook(page, text: str, label: str = "Facebook post"):
    print(f"\n  📘 {label}")

    # Longer timeout for Facebook navigation
    await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(4000)

    if "login" in page.url:
        print("  ❌ Facebook: not logged in — skipping")
        return False

    print(f"  ✓ Facebook loaded: {page.url}")

    # Try to open the compose dialog — only click inside FeedComposer
    compose_selectors = [
        'div[role="button"]:has-text("What")',
        '[data-pagelet="FeedComposer"] [role="button"]',
        '[aria-label="Create a post"]',
        '[aria-label*="mind"]',
    ]
    compose_opened = False
    for sel in compose_selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                await el.wait_for(state="visible", timeout=4000)
                await el.evaluate("el => el.click()")
                print(f"  ✓ Clicked compose: {sel}")
                compose_opened = True
                break
        except Exception:
            continue

    if not compose_opened:
        print("  ⚠️  Auto-click failed — click 'What's on your mind' manually (2 min window)")

    # ── SAFETY GATE: Wait for DIALOG ─────────────────────────
    print("  ⏳ Waiting for compose dialog...")
    try:
        await page.wait_for_selector('div[role="dialog"]', timeout=120000)
        print("  ✓ Compose dialog OPEN")
    except PWTimeout:
        print("  ❌ Dialog never opened — aborting. Nothing was typed.")
        return False

    # Only interact inside the dialog
    dialog = page.locator('div[role="dialog"]')
    try:
        compose_box = dialog.locator('div[contenteditable="true"]').last
        await compose_box.wait_for(state="visible", timeout=10000)
    except PWTimeout:
        print("  ❌ No contenteditable inside dialog — aborting")
        return False

    if DRY_RUN:
        print(f"  🧪 DRY RUN — dialog ✓  contenteditable inside dialog ✓")
        print(f"  🧪 Would type: {text[:80]}...")
        return True

    await compose_box.evaluate("el => el.focus()")
    await page.wait_for_timeout(300)
    print("  Typing post...")
    await page.keyboard.type(text, delay=4)
    await page.wait_for_timeout(2000)

    # Post button — only inside dialog
    for btn_sel in [
        'div[role="dialog"] div[aria-label="Post"]',
        'div[role="dialog"] div[aria-label="Share"]',
        'div[role="dialog"] div[role="button"]:has-text("Post")',
    ]:
        try:
            btn = page.locator(btn_sel).last
            if await btn.count() > 0:
                await btn.wait_for(state="visible", timeout=5000)
                await btn.evaluate("el => el.click()")
                await page.wait_for_timeout(5000)
                print(f"  ✅ FACEBOOK POSTED!")
                return True
        except Exception:
            continue

    print("  ⚠️  Post button not found — click 'Post' in the dialog manually")
    await page.wait_for_timeout(30000)
    return False


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
async def main():
    mode = "🧪 DRY RUN" if DRY_RUN else "🔴 LIVE"
    print("=" * 60)
    print(f"🍑  Autopost Final   [{mode}]")
    print("=" * 60)
    print("""
Browser opening — log into Twitter when it loads.
  90 seconds to log in. Posts fire automatically after.
  Facebook: click 'What's on your mind' when it opens.
""")

    async with async_playwright() as p:
        # Standard Playwright Chromium — exactly what worked for the 12-tweet thread
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = await context.new_page()

        # Navigate to Twitter — wait for login
        await page.goto("https://x.com", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        if "login" in page.url or not await page.locator('a[href="/home"]').count():
            print("⏳ Log into Twitter (90 seconds)...")
            try:
                await page.wait_for_url("**/home", timeout=90000)
                print("  ✓ Logged in!")
            except PWTimeout:
                print("  ⚠️  Login timed out — trying anyway")
            await page.wait_for_timeout(2000)

        results = {}

        try:
            results["chuck_tweet"] = await post_tweet(page, CHUCK_TWEET, "RIP Chuck Norris 🕊️")
        except Exception as e:
            print(f"  ❌ {e}")
            results["chuck_tweet"] = False

        try:
            results["jcole_tweet"] = await post_tweet(page, JCOLE_TWEET, "J. Cole '03 Adolescence 🍑")
        except Exception as e:
            print(f"  ❌ {e}")
            results["jcole_tweet"] = False

        try:
            results["facebook"] = await post_facebook(
                page, FB_POST, "Launch story + Chuck Norris tribute"
            )
        except Exception as e:
            print(f"  ❌ Facebook: {e}")
            results["facebook"] = False

        print("\n" + "=" * 60)
        print("📊  RESULTS")
        print("=" * 60)
        for key, ok in results.items():
            print(f"  {'✅' if ok else '❌'} {key}")

        await page.wait_for_timeout(10000)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
