#!/usr/bin/env python3
"""
autopost_setup_session.py  — Run ONCE to save your logins.
Opens a browser, you log into Twitter + Facebook,
then close the browser. Sessions are saved to .playwright_profile/
and all future autopost runs will use them automatically.
"""
import asyncio
from playwright.async_api import async_playwright

PROFILE_DIR = ".playwright_profile"

async def main():
    print("=" * 60)
    print("🔑  ONE-TIME SESSION SETUP")
    print("=" * 60)
    print("""
This opens a browser and saves your logins permanently.
You'll never have to log in again after this.

Steps:
  1. Browser opens to x.com — log in to @bookofdarrian
  2. After you're logged in, navigate to facebook.com and log in
  3. Once both tabs are showing your feeds, close the browser window
  4. Script will say "✅ Sessions saved!"

Ready? The browser is opening now...
""")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await context.new_page()
        await page.goto("https://x.com", wait_until="domcontentloaded")

        print("🌐 Browser open. Log into Twitter, then Facebook.")
        print("   Close the browser window when both are logged in.")
        print("   (Waiting up to 5 minutes...)\n")

        # Wait until browser is closed
        try:
            await page.wait_for_event("close", timeout=300000)
        except Exception:
            pass

        await context.close()

    print("\n✅ Sessions saved to .playwright_profile/")
    print("   Run: python3 autopost_final.py   to post everything!")

if __name__ == "__main__":
    asyncio.run(main())
