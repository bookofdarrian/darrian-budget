#!/usr/bin/env python3
"""
autopost_social.py
Uses your existing Chrome login sessions to auto-post to Twitter/X and Facebook.
Runs a visible browser so you can watch + intervene if needed.
"""

import asyncio
import time
from playwright.async_api import async_playwright

CHROME_USER_DATA = "/Users/darrianbelcher/Library/Application Support/Google/Chrome"

# ── Content ───────────────────────────────────────────────────────────────────

TWITTER_TWEETS = [
    "🧵 THREAD: I built 140 AI-powered apps while working at Visa, going to Georgia Tech, and running a sneaker business.\n\nHere's everything, and everyone who made it possible. 🍑 (1/12)",
    "2/ Three platforms. One home server. Zero outside funding.\n→ Peach State Savings (peachstatesavings.com) — personal finance OS\n→ SoleOps (getsoleops.com) — sneaker resale suite\n→ College Confused (collegeconfused.org) — first-gen college prep\nAll live. All real. All built by me + AI.",
    "3/ Peach State Savings is a 140+ page financial operating system.\n\nBudget tracker, income manager, RSU vest calendar, portfolio monitor, cash flow forecast, debt payoff planner, investment rebalancer, AI budget chat, crypto tracker, sneaker resale P&L, tax projection...\n\nFree at peachstatesavings.com",
    "4/ SoleOps is the sneaker reseller's operating system.\n\nThe feature I'm most proud of: an ARB scanner that monitors Mercari 24/7 and sends a Telegram alert when a pair on my watchlist drops below my max buy price.\n\nIt texted me a $200 opportunity before breakfast last month.",
    "5/ College Confused is personal.\n\nI was a first-gen college student. No one in my family knew what FAFSA was. I got into 25 schools.\n\nCC is the free AI platform I wish I'd had. FAFSA walkthrough, essay assistant, scholarship tracker, AI mock interviews.\n\nAlways free. collegeconfused.org",
    "6/ The tech: Python + Streamlit. SQLite/PostgreSQL. Anthropic Claude API.\nHome server running Proxmox. Tailscale VPN. Nginx. Docker. Grafana + Prometheus.\n\nAnd the wildest part — an overnight AI dev system that builds features WHILE I SLEEP. Tested. Committed. Deployed.",
    "7/ Now the most important part.\n\nSHOUTOUTS.\n\nNothing I've built happened alone. Let me be explicit about that.",
    "8/ @AnthropicAI + Claude — my co-creator.\n\nClaude isn't just a tool in my apps. It reviews my code, writes features, debugs errors, and talks to my users about their money.\n\nThey built something that genuinely changed what one person can build.",
    "9/ The Streamlit team — you lowered the barrier.\n\nI'm a TPM, not a frontend engineer. Streamlit let me build 140 production-quality app pages in Python, no React required.\n\nIf you want to build something real and know Python — streamlit.io. No more excuses.",
    "10/ My Visa + Georgia Tech communities.\n\nWorking as a TPM at Visa taught me how to ship real programs. Georgia Tech taught me to think in data and systems.\n\nBoth show up in every product decision I make.",
    "11/ My people. This is for y'all.\n\nMy family — every sacrifice, every belief, everything.\nDr. Bedir — for promoting the growth of beautiful minds.\nJosh, Keona, Nylah, Omar, Noah, Liddon, Nauri, Metri, Joa, Juan + the whole Menace2 GC.\nVine — you were there from the start.\n252 // 525 — you already know.\nRIP Danny 🕊️ — gone too soon. Building for you.",
    "12/ If you made it here:\n✅ peachstatesavings.com — free personal finance OS\n👟 getsoleops.com — sneaker resale suite (April launch)\n🎓 collegeconfused.org — free first-gen college prep\n📱 @bookofdarrian — follow the build\n\nOne year ago: a spreadsheet.\nToday: three live products.\nTomorrow: $1K MRR.\n\nThe build continues. 🍑",
]

FB_PERSONAL = """I've been building in silence for a while. Today I'm sharing everything.

Over the past year — while working full-time as a Technical Program Manager at Visa and finishing my Georgia Tech data analytics degree — I've been building three AI-powered platforms from a home server in my house.

📊 Peach State Savings (peachstatesavings.com)
A 140+ page personal finance operating system. Budget tracking, investment monitoring, RSU calendar, cash flow forecasting, AI budget chat, and a full sneaker resale business suite called SoleOps. Free for everyone.

👟 SoleOps (getsoleops.com — launching April 2026)
A full operating system for sneaker resellers. AI listing generator, inventory manager, P&L dashboard, live price monitor, and an arbitrage scanner that texts you on Telegram when a pair you're watching drops below your buy price. First 25 signups get 30 free Pro days.

🎓 College Confused (collegeconfused.org)
Free AI-powered college prep for first-gen students. FAFSA walkthrough, essay assistant, scholarship tracker, AI mock interview prep. I was a first-gen student — this is the platform I wish I'd had. Always free.

I could not have done any of this without:

❤️ Anthropic / Claude AI — genuine co-creator on every feature
❤️ The Streamlit framework team
❤️ Georgia Tech for teaching me to build in systems
❤️ My colleagues at Visa for the program discipline I apply to every build
❤️ My family — every sacrifice, every "go do what you gotta do" — this is for you
❤️ Dr. Bedir — for promoting the growth of beautiful minds. Thank you for seeing us.
❤️ Josh, Keona, Nylah, Omar, Noah, Liddon, Nauri, Metri, Joa, Juan + the whole Menace2 GC — y'all kept me going
❤️ Vine — you were there from the start. Still building for you.
❤️ 252 // 525 — you already know. Always.
❤️ RIP Danny 🕊️ — gone too soon. This one's for you too.
❤️ Everyone who's ever used these tools and left feedback

To the Atlanta community — you've been with me since the beginning and it shows.

If you know someone who'd benefit from any of these tools, please share.
If you want to follow the build journey, subscribe to my YouTube: @bookofdarrian

One year ago I had a spreadsheet. Today I have three live products and a server that builds features while I sleep.

This is just the beginning. 🍑"""


async def post_twitter_thread(page):
    print("\n📌 Step 1: Posting Twitter/X thread (12 tweets)...")
    await page.goto("https://x.com/compose/tweet", wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    # Check if we need to log in
    if "login" in page.url or "i/flow" in page.url:
        print("  ⚠️  Twitter not logged in — waiting up to 60s for you to log in...")
        await page.wait_for_url("**/home**", timeout=60000)
        await page.goto("https://x.com/compose/tweet", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

    for i, tweet_text in enumerate(TWITTER_TWEETS):
        print(f"  → Typing tweet {i+1}/12...")

        # Find the active compose box
        compose_box = page.locator('div[data-testid="tweetTextarea_0"]').last
        try:
            await compose_box.wait_for(timeout=5000)
        except Exception:
            # Try alternative selector
            compose_box = page.locator('div[contenteditable="true"]').last

        await compose_box.click()
        await page.wait_for_timeout(500)
        await compose_box.fill("")
        await page.keyboard.type(tweet_text, delay=10)
        await page.wait_for_timeout(800)

        if i < len(TWITTER_TWEETS) - 1:
            # Click "Add another tweet" button
            add_btn = page.locator('div[data-testid="addButton"]')
            try:
                await add_btn.wait_for(timeout=5000)
                await add_btn.click()
                await page.wait_for_timeout(1000)
            except Exception:
                print(f"    ⚠️  Could not find Add button after tweet {i+1} — trying keyboard shortcut")
                # Try Cmd+Enter as shortcut
                pass

    print("  → Clicking Post All...")
    post_btn = page.locator('div[data-testid="tweetButton"]')
    try:
        await post_btn.wait_for(timeout=5000)
        await post_btn.click()
        await page.wait_for_timeout(3000)
        print("  ✅ Twitter thread posted!")
    except Exception:
        print("  ⚠️  Could not click Post — the thread is ready. Please click 'Post' manually in the browser.")
        await page.wait_for_timeout(15000)


async def post_facebook_personal(page):
    print("\n📌 Step 2: Posting to Facebook (personal)...")
    await page.goto("https://www.facebook.com", wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    if "login" in page.url:
        print("  ⚠️  Facebook not logged in — waiting up to 60s for you to log in...")
        await page.wait_for_url("**/", timeout=60000)
        await page.wait_for_timeout(2000)

    # Click the status/post box
    try:
        post_box = page.locator('div[aria-label*="mind"]').first
        await post_box.wait_for(timeout=8000)
        await post_box.click()
        await page.wait_for_timeout(2000)
    except Exception:
        try:
            post_box = page.locator('div[role="button"]').filter(has_text="What's on your mind").first
            await post_box.click()
            await page.wait_for_timeout(2000)
        except Exception:
            print("  ⚠️  Could not find Facebook post box — navigating to post page...")
            await page.goto("https://www.facebook.com/?sk=nf", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

    # Type in the textarea that appears
    try:
        text_area = page.locator('div[aria-label*="mind"]').last
        await text_area.wait_for(timeout=5000)
        await text_area.click()
        await page.wait_for_timeout(500)
        await page.keyboard.type(FB_PERSONAL, delay=5)
        await page.wait_for_timeout(1500)

        # Click Post button
        post_btn = page.locator('div[aria-label="Post"]').last
        await post_btn.wait_for(timeout=5000)
        await post_btn.click()
        await page.wait_for_timeout(3000)
        print("  ✅ Facebook personal post submitted!")
    except Exception as e:
        print(f"  ⚠️  Facebook auto-post hit a snag ({e}). The page is open — please paste and post manually.")
        # Copy to clipboard as fallback
        import subprocess
        subprocess.run(['pbcopy'], input=FB_PERSONAL.encode('utf-8'))
        print("  📋 Caption copied to clipboard — just Cmd+V to paste")
        await page.wait_for_timeout(20000)


async def main():
    print("=" * 55)
    print("🍑  Peach State Savings — Auto-Post Script")
    print("=" * 55)
    print("Opening your Chrome profile (you'll stay logged in)...")
    print("A browser window will appear — watch it go!\n")

    async with async_playwright() as p:
        # Use existing Chrome profile so you're already logged in
        context = await p.chromium.launch_persistent_context(
            user_data_dir=CHROME_USER_DATA,
            channel="chrome",
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=["--no-first-run", "--no-default-browser-check"],
        )

        page = await context.new_page()

        try:
            await post_twitter_thread(page)
        except Exception as e:
            print(f"  ❌ Twitter error: {e}")

        try:
            await post_facebook_personal(page)
        except Exception as e:
            print(f"  ❌ Facebook error: {e}")

        print("\n" + "=" * 55)
        print("✅  Auto-post complete!")
        print("=" * 55)
        print("\nFor Instagram, TikTok, and YouTube:")
        print("  → Those need your screen recording first (no video file yet)")
        print("  → All captions are saved in your SMM Queue tab at:")
        print("     http://100.95.125.112:8501/social_media_manager")
        print("\nBrowser staying open for 30 seconds so you can check...")
        await page.wait_for_timeout(30000)
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
