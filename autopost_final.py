#!/usr/bin/env python3
"""
autopost_final.py — SAFE autoposting with strict dialog guards.

SAFETY RULES (enforced in code, not just comments):
  Twitter  — only types inside x.com/compose/post modal (data-testid=tweetTextarea_0)
  Facebook — ONLY types inside a role="dialog" AFTER the compose modal opens.
             NEVER types into any contenteditable that is not inside a dialog.

Run modes:
  python3 autopost_final.py           — post everything
  python3 autopost_final.py --dry-run — shows selectors found, types NOTHING
"""
import asyncio
import sys
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

DRY_RUN = "--dry-run" in sys.argv

FB_POST = open("FB_POST.txt").read().strip()
CHUCK_TWEET = "RIP Chuck Norris 🕊️ — 86 years of being the most legendary dude on the planet. One of a kind. Rest easy, legend."
JCOLE_TWEET = "building to '03 adolescence by j. cole on repeat. the vibe just hits different when you're turning nothing into something. 🍑"

# ─────────────────────────────────────────────────────────────
# TWITTER — safe post
# ─────────────────────────────────────────────────────────────
async def post_tweet(page, text: str, label: str):
    """
    Posts a tweet via x.com/compose/post ONLY.
    Only types inside data-testid='tweetTextarea_0' (the compose modal textarea).
    Never touches any other contenteditable on the page.
    """
    print(f"\n  🐦 Tweet: {label}")

    # Navigate to the dedicated compose URL — this opens a modal overlay
    await page.goto("https://x.com/compose/post", wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)

    # Verify we're on x.com (not redirected to login page)
    if "login" in page.url or "i/flow" in page.url:
        print("  ❌ Not logged into Twitter — skipping")
        return False

    # Wait for the SPECIFIC compose textarea (index 0, not .last)
    try:
        textarea = page.locator('[data-testid="tweetTextarea_0"]')
        await textarea.wait_for(state="visible", timeout=12000)
    except PWTimeout:
        print("  ❌ Compose textarea not found — not logged in or page changed")
        return False

    if DRY_RUN:
        print(f"  🧪 DRY RUN — found tweetTextarea_0 ✓  would type: {text[:60]}...")
        return True

    # Click, paste via clipboard (most reliable with React)
    await textarea.evaluate("el => el.click()")
    await page.wait_for_timeout(400)
    await page.evaluate(f"navigator.clipboard.writeText({repr(text)})")
    await page.keyboard.press("Meta+v")
    await page.wait_for_timeout(1500)

    # Submit — only via the tweetButton inside the compose overlay
    try:
        post_btn = page.locator('[data-testid="tweetButton"]').last
        await post_btn.wait_for(state="visible", timeout=15000)
        await post_btn.evaluate("el => el.click()")
        await page.wait_for_timeout(4000)
        print(f"  ✅ POSTED: {label}")
        return True
    except PWTimeout:
        print(f"  ⚠️  Post button not found — click Post manually")
        await page.wait_for_timeout(10000)
        return False


# ─────────────────────────────────────────────────────────────
# FACEBOOK — safe post
# Critical safety rule: ONLY type inside role="dialog"
# ─────────────────────────────────────────────────────────────
async def post_facebook(page, text: str, label: str = "Facebook post"):
    """
    Posts to Facebook feed.

    SAFETY GUARD: We REQUIRE a role='dialog' to be open before typing ANYTHING.
    This ensures we never accidentally type into a comment box on someone's post.
    If the dialog is not open, we wait up to 2 minutes for the user to click
    'What's on your mind' manually.
    """
    print(f"\n  📘 {label}")
    await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)

    # Verify we're logged in
    if "login" in page.url:
        print("  ❌ Not logged into Facebook — skipping")
        return False

    print(f"  ✓ Facebook loaded: {page.url}")

    # Try to auto-click the compose button ONLY inside FeedComposer
    compose_opened = False
    compose_selectors = [
        '[data-pagelet="FeedComposer"] [role="button"]:has-text("What")',
        '[data-pagelet="FeedComposer"] [role="button"]',
        '[aria-label="Create a post"]',
    ]
    for sel in compose_selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                await el.wait_for(state="visible", timeout=4000)
                await el.click()
                print(f"  ✓ Clicked compose: {sel}")
                compose_opened = True
                break
        except Exception:
            continue

    if not compose_opened:
        print("  ⚠️  Auto-click failed — click 'What's on your mind' in the browser (2 min)")

    # ── SAFETY GATE: Wait for a DIALOG to open ──────────────────────────
    # We NEVER type into anything that is not inside role="dialog"
    print("  ⏳ Waiting for compose DIALOG to open...")
    try:
        await page.wait_for_selector('div[role="dialog"]', timeout=120000)
        print("  ✓ Compose dialog is OPEN")
    except PWTimeout:
        print("  ❌ Compose dialog never opened — aborting (no typing, nothing posted)")
        return False

    # Find contenteditable INSIDE the dialog ONLY
    dialog = page.locator('div[role="dialog"]')
    compose_box_sel = 'div[contenteditable="true"]'

    try:
        compose_box = dialog.locator(compose_box_sel).last
        await compose_box.wait_for(state="visible", timeout=10000)
    except PWTimeout:
        print("  ❌ No contenteditable found inside dialog — aborting")
        return False

    if DRY_RUN:
        print(f"  🧪 DRY RUN — found dialog ✓  contenteditable inside dialog ✓")
        print(f"  🧪 Would type: {text[:80]}...")
        return True

    # Type inside the dialog compose box
    await compose_box.evaluate("el => el.focus()")
    await page.wait_for_timeout(300)
    print("  Typing post...")
    await page.keyboard.type(text, delay=4)
    await page.wait_for_timeout(2000)

    # Click Post INSIDE the dialog only
    post_btn = None
    for btn_sel in [
        'div[role="dialog"] div[aria-label="Post"]',
        'div[role="dialog"] div[aria-label="Share"]',
        'div[role="dialog"] div[role="button"]:has-text("Post")',
    ]:
        try:
            btn = page.locator(btn_sel).last
            if await btn.count() > 0:
                await btn.wait_for(state="visible", timeout=5000)
                post_btn = btn
                break
        except Exception:
            continue

    if post_btn:
        await post_btn.evaluate("el => el.click()")
        await page.wait_for_timeout(5000)
        print(f"  ✅ FACEBOOK POSTED: {label}")
        return True
    else:
        print("  ⚠️  Post button not found inside dialog — click 'Post' manually")
        await page.wait_for_timeout(30000)
        return False


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
async def main():
    mode = "🧪 DRY RUN — nothing will be posted" if DRY_RUN else "🔴 LIVE — posting for real"
    print("=" * 60)
    print(f"🍑  Autopost Final   [{mode}]")
    print("=" * 60)
    print("""
Browser opening — log into Twitter when it opens.
  You have 90 seconds. Posts fire automatically after login.
  Facebook will wait for you to click 'What's on your mind'.
""")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = await context.new_page()

        # Navigate to Twitter — wait for login
        await page.goto("https://x.com/home", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        if "login" in page.url or "i/flow" in page.url:
            print("⏳ Log into Twitter now (90 seconds)...")
            try:
                await page.wait_for_url("**/home", timeout=90000)
                print("  ✓ Logged in!")
            except PWTimeout:
                print("  ⚠️  Login timed out — trying anyway")
            await page.wait_for_timeout(2000)

        results = {}

        # ── Twitter posts ───────────────────────────────────────
        try:
            results["chuck"] = await post_tweet(page, CHUCK_TWEET, "RIP Chuck Norris 🕊️")
        except Exception as e:
            print(f"  ❌ Chuck tweet error: {e}")
            results["chuck"] = False

        try:
            results["jcole"] = await post_tweet(page, JCOLE_TWEET, "J. Cole '03 Adolescence 🍑")
        except Exception as e:
            print(f"  ❌ J Cole tweet error: {e}")
            results["jcole"] = False

        # ── Facebook ────────────────────────────────────────────
        try:
            results["facebook"] = await post_facebook(
                page, FB_POST, "Launch story + Chuck Norris tribute"
            )
        except Exception as e:
            print(f"  ❌ Facebook error: {e}")
            results["facebook"] = False

        # ── Summary ─────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("📊  RESULTS")
        print("=" * 60)
        for key, ok in results.items():
            status = "✅" if ok else "❌"
            print(f"  {status} {key}")

        await page.wait_for_timeout(10000)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
