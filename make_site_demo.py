#!/usr/bin/env python3
"""
make_site_demo.py — Real site screenshots + your voice, no background music
Output: videos/final_site_demo.mp4

Password: gullah  (APP_PASSWORD mode — just enter gullah in the box)
"""
import subprocess, time, sys, os
from pathlib import Path

FFMPEG  = "/usr/local/bin/ffmpeg"
VOICE   = "/tmp/voice_narration.mp3"   # already copied here (colon-free path)
OUT_DIR = Path("/tmp/site_shots2")
VID_DIR = Path("videos")
OUT_DIR.mkdir(exist_ok=True)
VID_DIR.mkdir(exist_ok=True)
BASE_URL = "https://peachstatesavings.com"

# (path, hold_sec)  — no scroll needed (Chrome JS from Apple Events is off)
PAGES = [
    ("/",                                     6),
    ("/1_expenses",                           5),
    ("/2_income",                             4),
    ("/4_trends",                             5),
    ("/10_rsu_espp",                          5),
    ("/11_portfolio",                         4),
    ("/118_soleops_inventory_manager",        5),
    ("/137_soleops_arb_scanner_watchlist_ui", 4),
    ("/135_soleops_drop_calendar",            4),
    ("/15_bills",                             4),
    ("/17_personal_assistant",                4),
    ("/",                                     5),
]

def chrome(url):
    subprocess.run(["open", "-a", "Google Chrome", url])
    time.sleep(4)

def activate_chrome():
    subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'])
    time.sleep(0.8)

def shot(idx):
    p = str(OUT_DIR / f"s{idx:03d}.png")
    # -w : capture front window only (not full screen)
    subprocess.run(["screencapture", "-x", "-o", "-l",
                    str(int(subprocess.check_output(
                        ["osascript", "-e",
                         "tell application \"Google Chrome\" to id of window 1"]
                    ).decode().strip())),
                    "-t", "png", p])
    return p

# ── Open site + wait for login ────────────────────────────────────────────
print("🌐 Opening peachstatesavings.com...")
chrome(BASE_URL)
activate_chrome()
time.sleep(2)

print("⏳ 60 seconds to log in with password: gullah")
print("   (Just type gullah in the password box and press Enter)")
for i in range(60, 0, -1):
    sys.stdout.write(f"\r   {i:2d}s  LOG IN NOW — password: gullah   ")
    sys.stdout.flush()
    time.sleep(1)
print("\r✅ Starting capture now!                                ")

# ── Capture pages ─────────────────────────────────────────────────────────
shots = []
idx = 0
activate_chrome()
time.sleep(1)

for page_path, hold in PAGES:
    url = BASE_URL + page_path
    print(f"📸 {url}")
    chrome(url)
    activate_chrome()
    time.sleep(3)
    try:
        p = shot(idx)
        shots.append(p)
        idx += 1
        print(f"   ✓ {p}")
    except Exception as e:
        print(f"   ⚠ screenshot failed: {e}")
    time.sleep(hold)

if not shots:
    print("❌ No screenshots captured — exiting")
    sys.exit(1)

print(f"\n✅ {len(shots)} screenshots")

# ── Voice duration ────────────────────────────────────────────────────────
r = subprocess.run(
    ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
     "-of", "csv=p=0", VOICE],
    capture_output=True, text=True
)
voice_dur = float(r.stdout.strip()) if r.stdout.strip() else 90.0
per_shot  = voice_dur / len(shots)
print(f"🎙  Voice: {voice_dur:.1f}s → {per_shot:.2f}s per shot")

# ── Build concat list ─────────────────────────────────────────────────────
concat = OUT_DIR / "concat.txt"
with open(concat, "w") as f:
    for s in shots:
        f.write(f"file '{s}'\nduration {per_shot:.3f}\n")
    f.write(f"file '{shots[-1]}'\n")

# ── Silent video ──────────────────────────────────────────────────────────
silent = str(OUT_DIR / "silent.mp4")
print("🎬 Building video from screenshots...")
result = subprocess.run([
    FFMPEG, "-y",
    "-f", "concat", "-safe", "0", "-i", str(concat),
    "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
           "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
    "-r", "30", "-c:v", "libx264", "-preset", "fast",
    "-crf", "20", "-pix_fmt", "yuv420p",
    silent
], capture_output=True, text=True)
if result.returncode != 0:
    print("ffmpeg stderr:", result.stderr[-500:])
    sys.exit(1)
print("✅ Silent video done")

# ── Add voice only ────────────────────────────────────────────────────────
final = str(VID_DIR / "final_site_demo.mp4")
result2 = subprocess.run([
    FFMPEG, "-y",
    "-i", silent,
    "-i", VOICE,
    "-c:v", "copy",
    "-c:a", "aac", "-b:a", "192k",
    "-shortest",
    "-map", "0:v:0", "-map", "1:a:0",
    final
], capture_output=True, text=True)
if result2.returncode != 0:
    print("ffmpeg stderr:", result2.stderr[-500:])
    sys.exit(1)

mb = os.path.getsize(final) / 1024 / 1024
print(f"\n🎉 DONE! → {final} ({mb:.1f} MB)")
print("   ✓ Real site footage  ✓ Your voice only  ✓ No background music")
subprocess.run(["open", final])
