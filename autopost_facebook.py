#!/usr/bin/env python3
"""Facebook-only post — runs after Twitter thread is already live."""
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

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


async def main():
    print("=" * 60)
    print("🍑  Facebook Post — Playwright (visible window)")
    print("=" * 60)
    print("Browser opening → log into Facebook → script posts automatically\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        await page.goto("https://www.facebook.com", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Wait for login
        if "login" in page.url:
            print("⏳ Log into Facebook in the browser window (90 seconds)...")
            try:
                await page.wait_for_function(
                    "() => !window.location.href.includes('login')", timeout=90000
                )
            except PWTimeout:
                pass
            await page.wait_for_timeout(3000)

        print(f"  URL: {page.url}")
        print("  Looking for compose box...")

        # Try clicking compose
        compose_selectors = [
            '[aria-label*="mind"]',
            '[aria-label*="Mind"]',
            'div[role="button"]:has-text("What")',
            'span:has-text("What\'s on your mind")',
            'div[data-pagelet="FeedComposer"] div[role="button"]',
        ]
        clicked = False
        for sel in compose_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    await el.wait_for(state="visible", timeout=5000)
                    await el.evaluate("el => el.click()")
                    clicked = True
                    print(f"  ✓ Compose opened: {sel}")
                    break
            except Exception:
                continue

        if not clicked:
            print("  ⚠️  Can't find compose box automatically.")
            print("  → Please CLICK the 'What\\'s on your mind' box in the browser")
            print("     You have 60 seconds. Script watches for the dialog to open...")

        # Wait for the compose dialog to appear (contenteditable) — up to 60s
        await page.wait_for_timeout(1000)

        # Type the post
        try:
            await page.wait_for_selector('div[contenteditable="true"]', timeout=60000)
            boxes = page.locator('div[contenteditable="true"]')
            count = await boxes.count()
            box = boxes.nth(count - 1)
            await box.evaluate("el => el.focus()")
            await page.wait_for_timeout(300)
            print("  Typing post...")
            await page.keyboard.type(FB_POST, delay=5)
            await page.wait_for_timeout(2000)
            print("  ✓ Post typed. Looking for Post button...")

            # Click post button
            for btn_sel in [
                'div[aria-label="Post"]',
                'div[aria-label="Share"]',
                'button[type="submit"]',
                'div[role="button"]:has-text("Post")',
            ]:
                try:
                    btn = page.locator(btn_sel).last
                    if await btn.count() > 0:
                        await btn.evaluate("el => el.click()")
                        await page.wait_for_timeout(3000)
                        print(f"  ✅ FACEBOOK POST SUBMITTED! (via {btn_sel})")
                        await page.wait_for_timeout(10000)
                        await browser.close()
                        return
                except Exception:
                    continue

            print("  ⚠️  Post typed — click 'Post' manually in the window")
            await page.wait_for_timeout(30000)

        except Exception as e:
            print(f"  ❌ Error: {e}")
            print("  Keeping browser open 30s so you can post manually")
            await page.wait_for_timeout(30000)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
