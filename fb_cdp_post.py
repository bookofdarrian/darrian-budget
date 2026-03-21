#!/usr/bin/env python3
"""
Post to Facebook by connecting to Chrome via CDP (remote debugging).
Chrome must be launched with --remote-debugging-port=9222 using your real profile.
"""
import asyncio
import subprocess
import time
import os

POST = open("FB_POST.txt").read()

# Kill current Chrome and relaunch with remote debugging + real profile
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
USER_DATA = os.path.expanduser("~/Library/Application Support/Google/Chrome")

print("Relaunching Chrome with remote debugging...")
# Gracefully quit Chrome first
subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to quit'], capture_output=True)
time.sleep(2)

# Launch Chrome with remote debugging (uses real profile = real cookies = logged into FB)
subprocess.Popen([
    CHROME_PATH,
    "--remote-debugging-port=9222",
    f"--user-data-dir={USER_DATA}",
    "--no-first-run",
    "--no-default-browser-check",
    "https://www.facebook.com",
])
print("Chrome launching... waiting 8 seconds for it to load...")
time.sleep(8)

async def post():
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    async with async_playwright() as p:
        # Connect to existing Chrome via CDP
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        print(f"✅ Connected to Chrome — {len(browser.contexts)} contexts")

        # Get the Facebook page
        page = None
        for ctx in browser.contexts:
            for pg in ctx.pages:
                if "facebook.com" in pg.url:
                    page = pg
                    break
        
        if not page:
            # Use first available page and navigate
            ctx = browser.contexts[0]
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await page.goto("https://www.facebook.com", wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)

        print(f"  Page: {page.url}")
        await page.bring_to_front()
        await page.wait_for_timeout(2000)

        # Click compose box
        selectors = [
            'div[aria-label*="mind"]',
            'div[aria-label*="Mind"]',
            'div:has-text("What\'s on your mind")',
        ]
        clicked = False
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    await el.click(timeout=5000)
                    clicked = True
                    print(f"  ✅ Compose clicked: {sel}")
                    break
            except Exception:
                continue

        if not clicked:
            # Try JS click
            await page.evaluate("""
                var el = document.querySelector('[aria-label*="mind"]');
                if (!el) {
                    var spans = Array.from(document.querySelectorAll('span'));
                    el = spans.find(s => s.innerText && s.innerText.includes('mind'));
                }
                if (el) el.click();
            """)
            print("  Tried JS click")

        await page.wait_for_timeout(3000)

        # Wait for contenteditable
        try:
            await page.wait_for_selector('div[contenteditable="true"]', timeout=15000)
            boxes = page.locator('div[contenteditable="true"]')
            count = await boxes.count()
            box = boxes.nth(count - 1)
            await box.click()
            await page.wait_for_timeout(500)

            # Type the post
            print("  Typing post...")
            await box.fill(POST)
            await page.wait_for_timeout(2000)

            # Click Post button
            for btn_sel in ['div[aria-label="Post"]', 'div[role="button"]:has-text("Post")']:
                try:
                    btn = page.locator(btn_sel).last
                    if await btn.count() > 0:
                        await btn.click()
                        print("  ✅ POSTED TO FACEBOOK!")
                        await page.wait_for_timeout(5000)
                        return
                except Exception:
                    continue
            print("  ⚠️  Post button not found — post is typed, click Post manually")
            await page.wait_for_timeout(15000)

        except Exception as e:
            print(f"  ❌ {e}")

asyncio.run(post())
print("✅ Done!")
