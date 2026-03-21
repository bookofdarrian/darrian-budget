#!/usr/bin/env python3
"""Take screenshots of all 3 live sites for phone mockup video."""
import asyncio, subprocess
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path("/tmp/site_shots")
OUT.mkdir(exist_ok=True)

SITES = [
    ("pss",  "http://100.95.125.112:8501/",          "mobile"),   # PSS login/landing
    ("pss2", "http://100.95.125.112:8501/00_landing", "mobile"),   # PSS actual landing
    ("sole", "https://getsoleops.com",                "mobile"),   # SoleOps
    ("cc",   "https://collegeconfused.org",           "mobile"),   # College Confused
]

async def shoot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for name, url, mode in SITES:
            print(f"  📸 {name}: {url}")
            # Mobile viewport (iPhone 14 Pro)
            ctx = await browser.new_context(
                viewport={"width": 390, "height": 844},
                device_scale_factor=3,
                is_mobile=True,
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
            )
            page = await ctx.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(4)  # Wait for Streamlit/JS to render
                path = str(OUT / f"{name}.png")
                await page.screenshot(path=path, full_page=False)
                size = Path(path).stat().st_size // 1024
                print(f"     ✅ {name}.png — {size}KB")
            except Exception as e:
                print(f"     ⚠️ {name} failed: {e}")
            await ctx.close()

        await browser.close()

asyncio.run(shoot())
print("\nShots saved to /tmp/site_shots/")
for f in sorted(OUT.glob("*.png")):
    print(f"  {f.name}: {f.stat().st_size//1024}KB")
