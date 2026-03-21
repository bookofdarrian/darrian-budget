#!/usr/bin/env python3
"""
make_vertical_video.py
Creates a production-ready 9:16 (1080x1920) vertical social video.
Design: dark background, peach gradient accents, bold white typography.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import subprocess, math
from pathlib import Path

FFMPEG = "/usr/local/bin/ffmpeg"
W, H   = 1080, 1920          # 9:16 portrait — TikTok / IG Reels / YT Shorts
OUT    = Path("/tmp/vslides")
OUT.mkdir(exist_ok=True)

# ── Color palette ─────────────────────────────────────────────────────────────
BG      = (10, 12, 20)
DARK    = (18, 22, 36)
PEACH   = (255, 138, 61)
PEACH2  = (255, 100, 30)
WHITE   = (255, 255, 255)
OFF_W   = (220, 225, 240)
MUTED   = (130, 140, 165)
GREEN   = (72, 219, 145)

# ── Font loader ───────────────────────────────────────────────────────────────
def F(size, bold=False):
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for p in candidates:
        try: return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default()

# ── Drawing helpers ───────────────────────────────────────────────────────────
def draw_gradient_rect(d, x0, y0, x1, y1, c1, c2, vertical=True):
    steps = (y1 - y0) if vertical else (x1 - x0)
    for i in range(steps):
        t = i / max(steps, 1)
        r = int(c1[0] + (c2[0]-c1[0])*t)
        g = int(c1[1] + (c2[1]-c1[1])*t)
        b = int(c1[2] + (c2[2]-c1[2])*t)
        if vertical:
            d.line([(x0, y0+i), (x1, y0+i)], fill=(r,g,b))
        else:
            d.line([(x0+i, y0), (x0+i, y1)], fill=(r,g,b))

def centered_text(d, text, y, font, color, width=W):
    bbox = d.textbbox((0,0), text, font=font)
    tw   = bbox[2] - bbox[0]
    x    = (width - tw) // 2
    # Drop shadow
    d.text((x+3, y+3), text, fill=(0,0,0,120), font=font)
    d.text((x, y), text, fill=color, font=font)
    return bbox[3] - bbox[1]  # return height

def make_base():
    img = Image.new("RGB", (W, H), BG)
    d   = ImageDraw.Draw(img)
    # Subtle gradient background
    draw_gradient_rect(d, 0, 0, W, H//2, (10,12,20), (20,24,42))
    draw_gradient_rect(d, 0, H//2, W, H, (20,24,42), (10,12,20))
    # Peach glow top-left
    for r in range(200, 0, -20):
        alpha = int(25 * (1 - r/200))
        d.ellipse([-r+160, -r+300, r+160, r+300], fill=(*PEACH2, alpha))
    # Bottom peach bar
    draw_gradient_rect(d, 0, H-12, W, H, PEACH2, PEACH, vertical=False)
    draw_gradient_rect(d, 0, 0, W, 12, PEACH2, PEACH, vertical=False)
    return img, d

def save(img, name):
    path = OUT / name
    img.save(str(path), quality=95)
    return path

# ── SLIDE 1: Hook ─────────────────────────────────────────────────────────────
def slide_01():
    img, d = make_base()
    f_big  = F(88, bold=True)
    f_med  = F(52)
    f_sm   = F(36)
    # Peach accent line
    draw_gradient_rect(d, 80, 680, W-80, 686, PEACH2, PEACH, vertical=False)
    centered_text(d, "my computer built me", 580, f_big, WHITE)
    centered_text(d, "a feature", 700, F(120, bold=True), PEACH)
    centered_text(d, "while I was sleeping.", 840, f_big, WHITE)
    centered_text(d, "here's everything I've built 👇", 1020, f_med, MUTED)
    # Bottom brand
    centered_text(d, "@bookofkaur", H-140, f_sm, MUTED)
    return save(img, "01.png")

# ── SLIDE 2: PSS ──────────────────────────────────────────────────────────────
def slide_02():
    img, d = make_base()
    f_em   = F(72, bold=True)
    f_big  = F(80, bold=True)
    f_med  = F(44)
    f_sm   = F(32)
    f_tag  = F(26)
    # Card background
    d.rounded_rectangle([60, 420, W-60, 1100], radius=30, fill=(22,28,50))
    draw_gradient_rect(d, 60, 420, W-60, 428, PEACH2, PEACH, vertical=False)
    centered_text(d, "🍑", 460, F(100), WHITE)
    centered_text(d, "Peach State Savings", 590, f_em, PEACH)
    centered_text(d, "Personal finance OS", 690, f_med, WHITE)
    # Feature pills
    features = ["Budget & Income", "RSU Calendar", "140+ Pages", "AI Assistant", "Portfolio Tracker"]
    pill_y = 780
    for feat in features:
        bf  = F(28)
        bbox = d.textbbox((0,0), feat, font=bf)
        pw  = bbox[2] - bbox[0] + 40
        px  = (W - pw) // 2
        d.rounded_rectangle([px, pill_y, px+pw, pill_y+44], radius=22, fill=(40,50,80))
        d.text((px+20, pill_y+8), feat, fill=OFF_W, font=bf)
        pill_y += 58
    # FREE badge
    d.rounded_rectangle([W//2-80, 1040, W//2+80, 1100], radius=30, fill=GREEN)
    centered_text(d, "FREE", 1050, F(38, bold=True), (10,12,20))
    centered_text(d, "peachstatesavings.com", H-140, f_tag, PEACH)
    return save(img, "02.png")

# ── SLIDE 3: SoleOps ─────────────────────────────────────────────────────────
def slide_03():
    img, d = make_base()
    f_em   = F(72, bold=True)
    f_med  = F(44)
    f_sm   = F(32)
    f_tag  = F(26)
    d.rounded_rectangle([60, 420, W-60, 1100], radius=30, fill=(22,28,50))
    draw_gradient_rect(d, 60, 420, W-60, 428, PEACH2, PEACH, vertical=False)
    centered_text(d, "👟", 460, F(100), WHITE)
    centered_text(d, "SoleOps", 590, f_em, PEACH)
    centered_text(d, "Sneaker resale suite", 690, f_med, WHITE)
    features = ["AI Listing Generator", "ARB Scanner", "Inventory Manager", "Price Predictor", "Profit Optimizer"]
    pill_y = 780
    for feat in features:
        bf   = F(28)
        bbox = d.textbbox((0,0), feat, font=bf)
        pw   = bbox[2] - bbox[0] + 40
        px   = (W - pw) // 2
        d.rounded_rectangle([px, pill_y, px+pw, pill_y+44], radius=22, fill=(40,50,80))
        d.text((px+20, pill_y+8), feat, fill=OFF_W, font=bf)
        pill_y += 58
    centered_text(d, "$200 before breakfast 💸", 1040, F(36, bold=True), PEACH)
    centered_text(d, "getsoleops.com", H-140, f_tag, PEACH)
    return save(img, "03.png")

# ── SLIDE 4: College Confused ─────────────────────────────────────────────────
def slide_04():
    img, d = make_base()
    f_em   = F(68, bold=True)
    f_med  = F(44)
    f_tag  = F(26)
    d.rounded_rectangle([60, 420, W-60, 1100], radius=30, fill=(22,28,50))
    draw_gradient_rect(d, 60, 420, W-60, 428, PEACH2, PEACH, vertical=False)
    centered_text(d, "🎓", 460, F(100), WHITE)
    centered_text(d, "College Confused", 590, f_em, PEACH)
    centered_text(d, "Free AI college prep", 690, f_med, WHITE)
    features = ["FAFSA Guidance", "Essay Writing", "Mock Interviews", "Scholarship Finder", "Application Tracker"]
    pill_y = 780
    for feat in features:
        bf   = F(28)
        bbox = d.textbbox((0,0), feat, font=bf)
        pw   = bbox[2] - bbox[0] + 40
        px   = (W - pw) // 2
        d.rounded_rectangle([px, pill_y, px+pw, pill_y+44], radius=22, fill=(40,50,80))
        d.text((px+20, pill_y+8), feat, fill=OFF_W, font=bf)
        pill_y += 58
    d.rounded_rectangle([W//2-120, 1040, W//2+120, 1100], radius=30, fill=GREEN)
    centered_text(d, "ALWAYS FREE", 1050, F(34, bold=True), (10,12,20))
    centered_text(d, "collegeconfused.org", H-140, f_tag, PEACH)
    return save(img, "04.png")

# ── SLIDE 5: The setup ───────────────────────────────────────────────────────
def slide_05():
    img, d = make_base()
    f_big  = F(84, bold=True)
    f_med  = F(48)
    f_sm   = F(34)
    draw_gradient_rect(d, 80, 680, W-80, 686, PEACH2, PEACH, vertical=False)
    centered_text(d, "all of this runs", 520, f_big, WHITE)
    centered_text(d, "on a server", 630, f_big, WHITE)
    centered_text(d, "in my house.", 740, f_big, PEACH)
    centered_text(d, "AI builds features while I sleep.", 880, f_med, OFF_W)
    centered_text(d, "I just wake up and use them.", 960, f_med, MUTED)
    centered_text(d, "@bookofkaur", H-140, f_sm, PEACH)
    return save(img, "05.png")

# ── SLIDE 6: URLs ────────────────────────────────────────────────────────────
def slide_06():
    img, d = make_base()
    f_big  = F(52, bold=True)
    f_med  = F(38)
    f_sm   = F(30)
    centered_text(d, "check it out 👇", 560, F(64, bold=True), WHITE)
    for i, (label, url, color) in enumerate([
        ("💰 Personal Finance", "peachstatesavings.com", PEACH),
        ("👟 Sneaker Resale", "getsoleops.com", PEACH),
        ("🎓 College Prep", "collegeconfused.org", GREEN),
    ]):
        y_base = 720 + i * 170
        d.rounded_rectangle([80, y_base, W-80, y_base+140], radius=20, fill=(22,28,50))
        centered_text(d, label, y_base+18, F(36), OFF_W)
        centered_text(d, url, y_base+72, F(38, bold=True), color)
    centered_text(d, "all free. always.", 1330, F(44, bold=True), PEACH)
    centered_text(d, "@bookofkaur", H-140, f_sm, MUTED)
    return save(img, "06.png")

# ── SLIDE 7: CTA ─────────────────────────────────────────────────────────────
def slide_07():
    img, d = make_base()
    f_big  = F(90, bold=True)
    f_med  = F(52)
    f_sm   = F(36)
    draw_gradient_rect(d, 80, 920, W-80, 926, PEACH2, PEACH, vertical=False)
    centered_text(d, "follow", 680, f_big, WHITE)
    centered_text(d, "the build.", 790, f_big, WHITE)
    centered_text(d, "@bookofkaur", 930, F(72, bold=True), PEACH)
    centered_text(d, "new feature every week.", 1050, f_sm, MUTED)
    return save(img, "07.png")

print("Building slides...")
slides_data = [
    (slide_01, 8),
    (slide_02, 14),
    (slide_03, 15),
    (slide_04, 14),
    (slide_05, 11),
    (slide_06, 10),
    (slide_07, 11),
]
paths = []
for fn, dur in slides_data:
    p = fn()
    paths.append((p, dur))
    print(f"  ✅ {p.name}")

# Build concat file
concat = OUT / "concat.txt"
entries = []
for p, dur in paths:
    entries.append(f"file '{p}'\nduration {dur}")
entries.append(f"file '{paths[-1][0]}'")
concat.write_text("\n".join(entries))

BASE = Path("/Users/darrianbelcher/Downloads/darrian-budget/videos/v_base.mp4")
print("\nRendering base video (1080x1920)...")
r = subprocess.run([
    FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
    "-vf", "fps=25,scale=1080:1920",
    "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p",
    str(BASE)
], capture_output=True, text=True)

if not BASE.exists() or BASE.stat().st_size < 50000:
    print(f"❌ Base render failed: {r.stderr[-200:]}")
    exit(1)
print(f"  ✅ {BASE.name} — {BASE.stat().st_size//1024}KB")

VOICE = "/Users/darrianbelcher/Downloads/The Vivian 4.m4a"
BEAT  = "/Users/darrianbelcher/Downloads/darrian-budget/videos/beat_cole_03.mp3"
FINAL = Path("/Users/darrianbelcher/Downloads/darrian-budget/videos/final_vertical.mp4")

# Get voice duration
r2 = subprocess.run([FFMPEG, "-i", VOICE], capture_output=True, text=True)
vox_dur = 83.0
for line in r2.stderr.split("\n"):
    if "Duration" in line:
        t = line.split("Duration:")[1].split(",")[0].strip()
        h,m,s = t.split(":"); vox_dur = float(h)*3600+float(m)*60+float(s)
print(f"  Voice duration: {vox_dur:.1f}s")

print("Mixing audio + rendering final...")
result = subprocess.run([
    FFMPEG, "-y",
    "-stream_loop", "-1", "-i", str(BASE),
    "-i", VOICE,
    "-stream_loop", "-1", "-i", BEAT,
    "-filter_complex",
    f"[1:a]volume=1.0[v];[2:a]volume=0.08[b];[v][b]amix=inputs=2:duration=first[out]",
    "-map", "0:v",
    "-map", "[out]",
    "-vf", f"fade=t=in:st=0:d=0.8,fade=t=out:st={vox_dur-1.5:.1f}:d=1.5",
    "-c:v", "libx264", "-crf", "18", "-preset", "fast",
    "-c:a", "aac", "-b:a", "192k",
    "-t", str(vox_dur),
    "-movflags", "+faststart",
    str(FINAL)
], capture_output=True, text=True)

if FINAL.exists() and FINAL.stat().st_size > 500000:
    sz = FINAL.stat().st_size / 1024 / 1024
    print(f"\n✅ final_vertical.mp4 — {sz:.1f}MB — 1080x1920 — ready for TikTok/IG Reels/YT Shorts")
    subprocess.run(["open", str(FINAL)])
    # Also show in Finder
    subprocess.run(["open", "-R", str(FINAL)])
else:
    print(f"❌ Final render error: {result.stderr[-400:]}")
