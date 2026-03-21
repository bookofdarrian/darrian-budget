#!/usr/bin/env python3
"""
record_v2.py — Fixed recording that shows actual site (waits for real content).
Uses peachstatesavings.com with proper load detection.
"""
import asyncio, sys, subprocess
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

VIDEO_DIR = Path("videos")
VIDEO_DIR.mkdir(exist_ok=True)

APP = "https://peachstatesavings.com"


async def wait_for_streamlit(page, timeout=20000):
    """Wait for Streamlit to finish loading (no spinner visible)."""
    try:
        # Wait for the main content to load
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass
    await page.wait_for_timeout(2000)


async def nav(page, path, wait=5000):
    """Navigate to a page and wait for Streamlit to load."""
    await page.goto(f"{APP}{path}", wait_until="networkidle", timeout=25000)
    await page.wait_for_timeout(3000)
    # Scroll to show content
    await page.evaluate("window.scrollTo(0, 200)")
    await page.wait_for_timeout(500)
    await page.wait_for_timeout(wait)


async def record():
    print("=" * 60)
    print("🎬  Recording App Tour v2 (proper load detection)")
    print("=" * 60)
    print("\n⚠️  You'll need to log in when the browser opens.")
    print("   You have 90 seconds. Script will wait.\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--window-size=1280,720", "--disable-blink-features=AutomationControlled"]
        )
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(VIDEO_DIR),
            record_video_size={"width": 1280, "height": 720},
        )
        page = await ctx.new_page()

        # Go to the app
        print("Opening peachstatesavings.com...")
        await page.goto(APP, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Check for login
        body = await page.inner_text("body")
        if "Password" in body or "Login" in body or "Sign in" in body:
            print("\n⏳ LOG IN NOW — 90 seconds...\n")
            try:
                await page.wait_for_function(
                    """() => {
                        const t = document.body.innerText;
                        return !t.includes('Password') && t.length > 800;
                    }""",
                    timeout=90000
                )
                print("  ✅ Logged in!")
            except PWTimeout:
                print("  ⚠️  Login timeout — continuing")
            await page.wait_for_timeout(4000)
        else:
            print("  ✅ Already logged in")
            await page.wait_for_timeout(2000)

        # Wait for dashboard to fully render
        await wait_for_streamlit(page)

        # ── Dashboard ──────────────────────────────────────────
        print("🎬 Dashboard...")
        await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await page.wait_for_timeout(5000)
        await page.evaluate("window.scrollTo({top: 400, behavior: 'smooth'})")
        await page.wait_for_timeout(3000)

        # ── Expenses ───────────────────────────────────────────
        print("🎬 Expenses...")
        await nav(page, "/1_expenses", wait=5000)

        # ── Income ─────────────────────────────────────────────
        print("🎬 Income...")
        await nav(page, "/2_income", wait=4000)

        # ── Trends ─────────────────────────────────────────────
        print("🎬 Trends...")
        await nav(page, "/4_trends", wait=4000)

        # ── SoleOps Inventory ──────────────────────────────────
        print("🎬 SoleOps Inventory...")
        await nav(page, "/118_soleops_inventory_manager", wait=5000)

        # ── ARB Scanner ────────────────────────────────────────
        print("🎬 ARB Scanner...")
        await nav(page, "/137_soleops_arb_scanner_watchlist_ui", wait=5000)

        # ── Drop Calendar ──────────────────────────────────────
        print("🎬 Drop Calendar...")
        await nav(page, "/135_soleops_drop_calendar", wait=4000)

        # ── Social Media Manager ───────────────────────────────
        print("🎬 Social Media Manager...")
        await nav(page, "/57_social_media_manager", wait=5000)

        # ── AI Budget Chat ─────────────────────────────────────
        print("🎬 AI Budget Chat...")
        await nav(page, "/55_ai_budget_chat", wait=4000)

        # ── Back to dashboard ──────────────────────────────────
        print("🎬 Final: Dashboard...")
        await page.goto(APP, wait_until="networkidle", timeout=25000)
        await page.wait_for_timeout(5000)

        print("\n✅ Done recording! Saving...")
        await ctx.close()
        await browser.close()

    # Rename
    vids = sorted(VIDEO_DIR.glob("*.webm"), key=lambda v: v.stat().st_mtime)
    if vids:
        latest = vids[-1]
        out = VIDEO_DIR / "tour_v2.webm"
        latest.rename(out)
        print(f"\n✅ SAVED: {out} ({out.stat().st_size / 1024 / 1024:.1f} MB)")

        # Convert to mp4
        ffmpeg = "/usr/local/bin/ffmpeg"
        mp4 = VIDEO_DIR / "tour_v2.mp4"
        subprocess.run([ffmpeg, "-y", "-i", str(out), "-c:v", "libx264", "-crf", "23",
                        "-preset", "fast", "-movflags", "+faststart", str(mp4)],
                       capture_output=True)
        if mp4.exists():
            print(f"✅ MP4: {mp4} ({mp4.stat().st_size // 1024}KB)")
    else:
        print("⚠️  No webm found")


asyncio.run(record())
