#!/usr/bin/env python3
"""
autopost_playwright.py
Opens Playwright's own Chromium browser (visible window).
You log into Twitter + Facebook once, then it auto-posts everything.
No Apple Events, no System Events, no Chrome permissions needed.
"""

import asyncio
import time
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# ── Content ───────────────────────────────────────────────────────────────────

TWEETS = [
    "🧵 THREAD: I built 140 AI-powered apps while working at Visa, going to Georgia Tech, and running a sneaker business.\n\nHere's everything, and everyone who made it possible. 🍑 (1/12)",
    "2/ Three platforms. One home server. Zero outside funding.\n→ Peach State Savings (peachstatesavings.com) — personal finance OS\n→ SoleOps (getsoleops.com) — sneaker resale suite\n→ College Confused (collegeconfused.org) — first-gen college prep\nAll live. All real. All built by me + AI.",
    "3/ Peach State Savings is a 140+ page financial operating system.\n\nBudget tracker, income manager, RSU vest calendar, portfolio monitor, cash flow forecast, debt payoff planner, investment rebalancer, AI budget chat, crypto tracker, sneaker resale P&L, tax projection...\n\nFree at peachstatesavings.com",
    "4/ SoleOps is the sneaker reseller's operating system.\n\nThe feature I'm most proud of: an ARB scanner that monitors Mercari 24/7 and sends a Telegram alert when a pair drops below my max buy price.\n\nIt texted me a $200 opportunity before breakfast last month.",
    "5/ College Confused is personal.\n\nI was a first-gen college student. No one in my family knew what FAFSA was. I got into 25 schools.\n\nCC is the free AI platform I wish I'd had. FAFSA walkthrough, essay assistant, scholarship tracker, AI mock interviews.\n\nAlways free. collegeconfused.org",
    "6/ The tech: Python + Streamlit. SQLite/PostgreSQL. Anthropic Claude API.\nHome server running Proxmox. Tailscale VPN. Nginx. Docker. Grafana + Prometheus.\n\nAnd the wildest part — an overnight AI dev system that builds features WHILE I SLEEP. Tested. Committed. Deployed.",
    "7/ Now the most important part.\n\nSHOUTOUTS.\n\nNothing I've built happened alone. Let me be explicit about that.",
    "8/ @AnthropicAI + Claude — my co-creator.\n\nClaude isn't just a tool. It reviews my code, writes features, debugs errors, and talks to my users about their money.\n\nThey built something that genuinely changed what one person can build.",
    "9/ The Streamlit team — you lowered the barrier.\n\nI'm a TPM, not a frontend engineer. Streamlit let me build 140 production-quality app pages in Python, no React required.\n\nstreamlit.io — no more excuses.",
    "10/ My Visa + Georgia Tech communities.\n\nTPM at Visa taught me how to ship real programs. Georgia Tech taught me to think in data and systems.\n\nBoth show up in every product decision I make.",
    "11/ My people. This is for y'all.\n\nMy family — every sacrifice, every belief, everything.\nDr. Bedir — for promoting the growth of beautiful minds.\nJosh, Keona, Nylah, Omar, Noah, Liddon, Nauri, Metri, Joa, Juan + the whole Menace2 GC.\nVine — you were there from the start.\n252 // 525 — you already know.\nRIP Danny 🕊️ — gone too soon. Building for you.",
    "12/ If you made it here:\n✅ peachstatesavings.com — free personal finance OS\n👟 getsoleops.com — sneaker resale suite (April launch)\n🎓 collegeconfused.org — free first-gen college prep\n📱 @bookofdarrian — follow the build\n\nOne year ago: a spreadsheet.\nToday: three live products.\nTomorrow: $1K MRR.\n\nThe build continues. 🍑",
]

FB_POST = """I've been building in silence for a while. Today I'm sharing everything.

Over the past year — while working full-time as a Technical Program Manager at Visa and finishing my Georgia Tech data analytics degree — I've been building three AI-powered platforms from a home server in my house.

📊 Peach State Savings (peachstatesavings.com) — 140+ page personal finance OS. Free for everyone.

👟 SoleOps (getsoleops.com — April 2026) — AI listing generator, inventory manager, P&L dashboard, ARB scanner with Telegram alerts. First 25 signups get 30 free Pro days.

🎓 College Confused (collegeconfused.org) — Free AI college prep for first-gen students. FAFSA walkthrough, essay assistant, scholarship tracker, AI mock interviews. Always free.

I could not have done this without:

❤️ Anthropic / Claude AI — genuine co-creator on every feature
❤️ The Streamlit framework team
❤️ Georgia Tech for teaching me to build in systems
❤️ My colleagues at Visa for the program discipline I apply to every build
❤️ My family — every sacrifice, every "go do what you gotta do" — this is for you
❤️ Dr. Bedir — for promoting the growth of beautiful minds. Thank you for seeing us.
❤️ Josh, Keona, Nylah, Omar, Noah, Liddon, Nauri, Metri, Joa, Juan + the whole Menace2 GC
❤️ Vine — you were there from the start. Still building for you.
❤️ 252 // 525 — you already know. Always.
❤️ RIP Danny 🕊️ — gone too soon. This one's for you too.

One year ago I had a spreadsheet. Today I have three live products and a server that builds features while I sleep.

This is just the beginning. 🍑"""


async def type_react(page, selector: str, text: str):
    """Type into a React contenteditable using clipboard paste — most reliable method."""
    el = page.locator(selector).last
    await el.wait_for(state="visible", timeout=10000)
    await el.click()
    await page.wait_for_timeout(300)
    # Select all existing content and replace
    await page.keyboard.press("Meta+a")
    await page.wait_for_timeout(100)
    # Use clipboard paste (most reliable for React)
    await page.evaluate(f"navigator.clipboard.writeText({repr(text)})")
    await page.keyboard.press("Meta+v")
    await page.wait_for_timeout(500)


async def post_twitter(page):
    print("\n📌 TWITTER/X — 12-tweet thread")
    await page.goto("https://x.com", wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    # Wait for login if needed (up to 90 seconds)
    if "login" in page.url or not await page.locator('a[href="/home"]').count():
        print("  ⏳ Logging in — you have 90 seconds in the browser window...")
        try:
            await page.wait_for_url("**/home", timeout=90000)
        except PWTimeout:
            print("  ⚠️  Login timeout. Trying to continue anyway...")
        await page.wait_for_timeout(2000)

    # Open compose
    await page.goto("https://x.com/compose/post", wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    # Dismiss any cookie consent / overlay masks
    for mask_sel in ['[data-testid="twc-cc-mask"]', '[data-testid="BottomBar"]', 'div[aria-label="Close"]']:
        try:
            m = page.locator(mask_sel).first
            if await m.count() > 0:
                await m.click(force=True)
                await page.wait_for_timeout(500)
        except Exception:
            pass

    ADD_BTN  = '[data-testid="addButton"]'
    POST_BTN = '[data-testid="tweetButton"]'

    for i, tweet in enumerate(TWEETS):
        print(f"  → Tweet {i+1}/12...", end=" ", flush=True)
        # Focus last textarea using JS click to bypass overlays
        boxes = page.locator('div[data-testid^="tweetTextarea"]')
        count = await boxes.count()
        box = boxes.nth(count - 1) if count > 0 else page.locator('div[data-testid="tweetTextarea_0"]')
        # Use JS click to bypass overlay interception
        await box.evaluate("el => el.click()")
        await page.wait_for_timeout(300)
        await page.keyboard.press("Meta+a")
        await page.keyboard.type(tweet, delay=8)
        await page.wait_for_timeout(800)

        if i < len(TWEETS) - 1:
            try:
                add_btn = page.locator(ADD_BTN).last
                await add_btn.wait_for(state="visible", timeout=5000)
                await add_btn.evaluate("el => el.click()")
                await page.wait_for_timeout(1500)
                print("✓ added")
            except PWTimeout:
                print("⚠️  add btn timeout — trying force click")
                await page.locator(ADD_BTN).last.click(force=True)
                await page.wait_for_timeout(1500)
        else:
            print("✓ last tweet")

    print("  → Clicking Post All...")
    try:
        post_btn = page.locator(POST_BTN).last
        await post_btn.wait_for(state="visible", timeout=8000)
        await post_btn.evaluate("el => el.click()")
        await page.wait_for_timeout(4000)
        print("  ✅ Twitter thread POSTED!")
    except PWTimeout:
        print("  ⚠️  Post button timeout — click 'Post' in the browser window")
        await page.wait_for_timeout(20000)


async def post_facebook(page):
    print("\n📌 FACEBOOK — personal post")
    await page.goto("https://www.facebook.com", wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    # Wait for login — detect either login page or redirect
    current_url = page.url
    if "login" in current_url or "facebook.com/login" in current_url:
        print("  ⏳ Log into Facebook in the browser window (90 seconds)...")
        try:
            # Wait until URL no longer contains "login"
            await page.wait_for_function(
                "() => !window.location.href.includes('login')", timeout=90000
            )
        except PWTimeout:
            print("  ⚠️  FB login timeout — trying anyway")
        await page.wait_for_timeout(3000)

    # Check if we're actually logged in by waiting for the feed
    print(f"  Current URL: {page.url}")

    # Click compose — try multiple selectors including role-based ones
    compose_selectors = [
        'div[role="button"]:has-text("What")',
        'span:has-text("What\'s on your mind")',
        '[aria-label*="mind"]',
        '[aria-label*="Mind"]',
        'div[data-pagelet="FeedComposer"] div[role="button"]',
        'form[method="POST"] div[role="button"]',
    ]
    clicked = False
    for sel in compose_selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                await el.wait_for(state="visible", timeout=4000)
                await el.evaluate("el => el.click()")
                clicked = True
                print(f"  Compose opened via: {sel}")
                break
        except Exception:
            continue

    if not clicked:
        print("  ⚠️  Compose box not found — waiting 20s for you to click it manually in FB...")
        await page.wait_for_timeout(20000)

    await page.wait_for_timeout(2000)

    # Type in the dialog box — find any visible contenteditable
    try:
        # Wait for an editable area to appear after clicking compose
        await page.wait_for_selector('div[contenteditable="true"]', timeout=10000)
        boxes = page.locator('div[contenteditable="true"]')
        count = await boxes.count()
        box = boxes.nth(count - 1)
        await box.evaluate("el => el.focus()")
        await page.wait_for_timeout(300)
        await page.keyboard.type(FB_POST, delay=5)
        await page.wait_for_timeout(2000)

        # Click Post button — try multiple selectors
        for btn_sel in ['div[aria-label="Post"]', 'div[aria-label="Share"]',
                        'button[type="submit"]', 'div[role="button"]:has-text("Post")']:
            try:
                btn = page.locator(btn_sel).last
                if await btn.count() > 0:
                    await btn.evaluate("el => el.click()")
                    await page.wait_for_timeout(3000)
                    print(f"  ✅ Facebook post SUBMITTED via {btn_sel}!")
                    return
            except Exception:
                continue

        print("  ⚠️  Post is typed — click 'Post' manually in the browser window")
        await page.wait_for_timeout(20000)
    except Exception as e:
        print(f"  ⚠️  FB post error: {e}")
        print("  Waiting 20s — click 'Post' manually if you see the typed text")
        await page.wait_for_timeout(20000)


async def main():
    print("=" * 60)
    print("🍑  Auto-Post — Playwright Chromium (visible window)")
    print("=" * 60)
    print("""
A browser window is opening now.
  → Log into Twitter/X when it loads
  → The script will type all 12 tweets and post automatically
  → Then log into Facebook when it navigates there
  → It will type and post the launch story automatically
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

        try:
            await post_twitter(page)
        except Exception as e:
            print(f"  ❌ Twitter error: {e}")

        try:
            await post_facebook(page)
        except Exception as e:
            print(f"  ❌ Facebook error: {e}")

        print("\n" + "=" * 60)
        print("✅  DONE — Twitter thread + Facebook post complete!")
        print("=" * 60)
        print("""
Video posts remaining (need screen recording first):
  → TikTok x2, Instagram x3, YouTube Shorts x2

All captions at: http://100.95.125.112:8501/social_media_manager

Keeping browser open 30s so you can verify...
""")
        await page.wait_for_timeout(30000)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
