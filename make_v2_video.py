#!/usr/bin/env python3
"""
make_v2_video.py — v2 redesign
MUCH cleaner. Bigger text. More whitespace. Social-first 9:16 design.
Inspired by top-performing TikTok/IG text slides.
"""
from PIL import Image, ImageDraw, ImageFont
import subprocess
from pathlib import Path

FFMPEG = "/usr/local/bin/ffmpeg"
W, H   = 1080, 1920
OUT    = Path("/tmp/v2slides")
OUT.mkdir(exist_ok=True)

# Palette
BG    = (8,  10, 18)
CARD  = (16, 20, 38)
PEACH = (255, 135, 55)
LITE  = (255, 175, 100)
WHITE = (252, 252, 255)
GREY  = (135, 145, 170)
GREEN = (65, 210, 130)
CYAN  = (65, 185, 230)

def bold(sz):
    for f in ["/System/Library/Fonts/Helvetica.ttc",
              "/System/Library/Fonts/SFNSDisplay.ttf"]:
        try:
            ft = ImageFont.truetype(f, sz, index=2)  # bold index
            return ft
        except Exception:
            pass
    for f in ["/System/Library/Fonts/Helvetica.ttc",
              "/System/Library/Fonts/SFNSDisplay.ttf"]:
        try: return ImageFont.truetype(f, sz)
        except: pass
    return ImageFont.load_default()

def reg(sz):
    for f in ["/System/Library/Fonts/Helvetica.ttc",
              "/System/Library/Fonts/SFNSDisplay.ttf"]:
        try:
            ft = ImageFont.truetype(f, sz, index=1)
            return ft
        except Exception:
            pass
    return bold(sz)

def cx(d, text, y, font, color, shadow=True):
    """Centered text with optional shadow."""
    bb = d.textbbox((0,0), text, font=font)
    tw = bb[2] - bb[0]
    x  = (W - tw) // 2
    if shadow:
        d.text((x+4, y+4), text, fill=(0,0,0), font=font)
    d.text((x, y), text, fill=color, font=font)
    return bb[3] - bb[1]

def hbar(d, y, color=PEACH, thick=6, margin=90):
    """Horizontal accent bar."""
    d.rectangle([margin, y, W-margin, y+thick], fill=color)

def bg(color=BG):
    img = Image.new("RGB", (W, H), color)
    d   = ImageDraw.Draw(img)
    # Subtle corner glow
    for i in range(80, 0, -10):
        a = int(12 * i/80)
        d.ellipse([-i*3+200, -i*3+400, i*3+200, i*3+400], fill=tuple(min(255,c+a) for c in PEACH))
    # Top + bottom bars
    for yi in range(16):
        t = yi / 16
        r = int(PEACH[0]*(1-t) + BG[0]*t)
        g = int(PEACH[1]*(1-t) + BG[1]*t)
        b = int(PEACH[2]*(1-t) + BG[2]*t)
        d.line([(0, yi), (W, yi)], fill=(r,g,b))
        d.line([(0, H-1-yi), (W, H-1-yi)], fill=(r,g,b))
    return img, d

def pill(d, text, cx_pos, y, font, bg_color, text_color=WHITE):
    bb  = d.textbbox((0,0), text, font=font)
    pw  = bb[2] - bb[0] + 48
    ph  = bb[3] - bb[1] + 24
    x0  = cx_pos - pw//2
    d.rounded_rectangle([x0, y, x0+pw, y+ph], radius=ph//2, fill=bg_color)
    d.text((x0+24, y+12), text, fill=text_color, font=font)
    return ph

def save(img, name):
    path = OUT / name
    img.save(str(path), quality=95)
    return path

# ══════════════════════════════════════════════════════
# SLIDE 1 — Hook (8s)
# ══════════════════════════════════════════════════════
def s01():
    img, d = bg()
    # Top label
    cx(d, "BUILD IN PUBLIC", 160, reg(32), PEACH, shadow=False)
    hbar(d, 210, PEACH, 2, 200)

    # Big hook
    cx(d, "my AI built me", 640, bold(96), WHITE)
    cx(d, "a new feature", 770, bold(96), WHITE)
    cx(d, "while I was sleeping", 900, bold(96), PEACH)

    hbar(d, 1080, GREY, 2, 200)
    cx(d, "here's what I've built 👇", 1120, reg(48), GREY, shadow=False)

    # Bottom handle
    cx(d, "@bookofkaur", H-160, reg(40), GREY, shadow=False)
    return save(img, "01.png")

# ══════════════════════════════════════════════════════
# SLIDE 2 — PSS (14s)
# ══════════════════════════════════════════════════════
def s02():
    img, d = bg()
    cx(d, "🍑", 280, bold(120), WHITE, shadow=False)
    cx(d, "Peach State Savings", 440, bold(72), PEACH)
    cx(d, "Personal Finance OS", 540, reg(48), WHITE)
    hbar(d, 630, PEACH, 3, 120)

    # 3 key points
    points = [
        ("📊", "Budget, Income & Expenses"),
        ("📈", "RSU, Stocks & Portfolio"),
        ("🤖", "AI Assistant — 140+ Pages"),
    ]
    y = 680
    for icon, txt in points:
        d.rounded_rectangle([90, y, W-90, y+80], radius=16, fill=CARD)
        d.text((130, y+18), icon, fill=WHITE, font=bold(40))
        d.text((220, y+22), txt, fill=WHITE, font=reg(36))
        y += 100

    d.rounded_rectangle([W//2-110, 1040, W//2+110, 1116], radius=34, fill=GREEN)
    cx(d, "FREE FOREVER", 1052, bold(38), (8,10,18), shadow=False)

    hbar(d, 1160, GREY, 1, 200)
    cx(d, "peachstatesavings.com", 1200, reg(40), PEACH, shadow=False)
    cx(d, "@bookofkaur", H-150, reg(34), GREY, shadow=False)
    return save(img, "02.png")

# ══════════════════════════════════════════════════════
# SLIDE 3 — SoleOps (15s)
# ══════════════════════════════════════════════════════
def s03():
    img, d = bg()
    cx(d, "👟", 280, bold(120), WHITE, shadow=False)
    cx(d, "SoleOps", 440, bold(88), PEACH)
    cx(d, "Sneaker Resale Suite", 550, reg(48), WHITE)
    hbar(d, 640, PEACH, 3, 120)

    points = [
        ("✨", "AI Listing Generator"),
        ("🔍", "Arbitrage Scanner"),
        ("📦", "Inventory Manager"),
    ]
    y = 700
    for icon, txt in points:
        d.rounded_rectangle([90, y, W-90, y+80], radius=16, fill=CARD)
        d.text((130, y+18), icon, fill=WHITE, font=bold(40))
        d.text((220, y+22), txt, fill=WHITE, font=reg(36))
        y += 100

    cx(d, "$200 before breakfast 💸", 1070, bold(46), PEACH)
    hbar(d, 1150, GREY, 1, 200)
    cx(d, "getsoleops.com", 1190, reg(40), PEACH, shadow=False)
    cx(d, "@bookofkaur", H-150, reg(34), GREY, shadow=False)
    return save(img, "03.png")

# ══════════════════════════════════════════════════════
# SLIDE 4 — College Confused (14s)
# ══════════════════════════════════════════════════════
def s04():
    img, d = bg()
    cx(d, "🎓", 280, bold(120), WHITE, shadow=False)
    cx(d, "College Confused", 440, bold(72), PEACH)
    cx(d, "Free AI College Prep", 550, reg(48), WHITE)
    hbar(d, 640, PEACH, 3, 120)

    points = [
        ("📝", "Essay Writing Assistant"),
        ("💰", "FAFSA & Aid Guidance"),
        ("🎤", "Mock Interviews"),
    ]
    y = 700
    for icon, txt in points:
        d.rounded_rectangle([90, y, W-90, y+80], radius=16, fill=CARD)
        d.text((130, y+18), icon, fill=WHITE, font=bold(40))
        d.text((220, y+22), txt, fill=WHITE, font=reg(36))
        y += 100

    d.rounded_rectangle([W//2-140, 1040, W//2+140, 1116], radius=34, fill=GREEN)
    cx(d, "ALWAYS FREE", 1052, bold(42), (8,10,18), shadow=False)

    hbar(d, 1160, GREY, 1, 200)
    cx(d, "collegeconfused.org", 1200, reg(40), PEACH, shadow=False)
    cx(d, "@bookofkaur", H-150, reg(34), GREY, shadow=False)
    return save(img, "04.png")

# ══════════════════════════════════════════════════════
# SLIDE 5 — The Setup (11s)
# ══════════════════════════════════════════════════════
def s05():
    img, d = bg()
    cx(d, "🏠", 300, bold(120), WHITE, shadow=False)
    cx(d, "BUILT IN PUBLIC", 460, reg(34), PEACH, shadow=False)
    hbar(d, 520, PEACH, 3, 120)

    cx(d, "all of this runs", 600, bold(88), WHITE)
    cx(d, "on a server", 720, bold(88), WHITE)
    cx(d, "in my house.", 840, bold(88), PEACH)

    hbar(d, 1000, GREY, 2, 200)
    cx(d, "AI builds while I sleep.", 1060, reg(48), GREY)
    cx(d, "I wake up and use it.", 1140, reg(48), GREY)
    cx(d, "@bookofkaur", H-150, reg(34), GREY, shadow=False)
    return save(img, "05.png")

# ══════════════════════════════════════════════════════
# SLIDE 6 — Links (10s)
# ══════════════════════════════════════════════════════
def s06():
    img, d = bg()
    cx(d, "check it out 👇", 240, bold(72), WHITE)
    hbar(d, 350, PEACH, 4, 90)

    cards = [
        ("💰", "Peach State Savings", "peachstatesavings.com", PEACH),
        ("👟", "SoleOps",             "getsoleops.com",        CYAN),
        ("🎓", "College Confused",    "collegeconfused.org",   GREEN),
    ]
    y = 420
    for icon, name, url, color in cards:
        d.rounded_rectangle([70, y, W-70, y+170], radius=22, fill=CARD)
        d.rectangle([70, y, 76, y+170], fill=color)  # left color stripe
        d.text((110, y+28), icon, fill=WHITE, font=bold(60))
        d.text((200, y+32), name, fill=WHITE, font=bold(44))
        d.text((200, y+98), url,  fill=color,  font=reg(36))
        y += 190

    cx(d, "all free. always.", 1310, bold(52), PEACH)
    cx(d, "@bookofkaur", H-150, reg(34), GREY, shadow=False)
    return save(img, "06.png")

# ══════════════════════════════════════════════════════
# SLIDE 7 — CTA (11s)
# ══════════════════════════════════════════════════════
def s07():
    img, d = bg()
    hbar(d, 640, PEACH, 6, 90)
    cx(d, "follow", 700, bold(120), WHITE)
    cx(d, "the build.", 850, bold(120), WHITE)
    hbar(d, 1010, PEACH, 6, 90)
    cx(d, "@bookofkaur", 1080, bold(80), PEACH)
    cx(d, "new feature. every week.", 1210, reg(44), GREY, shadow=False)
    return save(img, "07.png")


# ── BUILD ──────────────────────────────────────────────
print("Building v2 slides...")
SLIDES = [
    (s01, 8), (s02, 14), (s03, 15),
    (s04, 14), (s05, 11), (s06, 10), (s07, 11),
]
paths = []
for fn, dur in SLIDES:
    p = fn()
    paths.append((p, dur))
    print(f"  ✅ {p.name}")

concat = OUT / "c.txt"
entries = [f"file '{p}'\nduration {d}" for p, d in paths]
entries.append(f"file '{paths[-1][0]}'")
concat.write_text("\n".join(entries))

BASE  = Path("/Users/darrianbelcher/Downloads/darrian-budget/videos/v2_base.mp4")
VOICE = "/Users/darrianbelcher/Downloads/The Vivian 4.m4a"
BEAT  = "/Users/darrianbelcher/Downloads/darrian-budget/videos/beat_cole_03.mp3"
FINAL = Path("/Users/darrianbelcher/Downloads/darrian-budget/videos/final_v2.mp4")

print("\nRendering 1080x1920 base...")
subprocess.run([
    FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
    "-vf", "fps=25,scale=1080:1920", "-c:v", "libx264",
    "-crf", "17", "-preset", "fast", "-pix_fmt", "yuv420p", str(BASE)
], capture_output=True)
print(f"  ✅ {BASE.stat().st_size//1024}KB")

# Voice duration
r = subprocess.run([FFMPEG, "-i", VOICE], capture_output=True, text=True)
vd = 83.1
for l in r.stderr.split("\n"):
    if "Duration" in l:
        t = l.split("Duration:")[1].split(",")[0].strip()
        h,m,s = t.split(":"); vd = float(h)*3600+float(m)*60+float(s)

print(f"  Voice: {vd:.1f}s — mixing...")
result = subprocess.run([
    FFMPEG, "-y",
    "-stream_loop", "-1", "-i", str(BASE),
    "-i", VOICE,
    "-stream_loop", "-1", "-i", BEAT,
    "-filter_complex",
    "[1:a]volume=1.0[v];[2:a]volume=0.08[b];[v][b]amix=inputs=2:duration=first[out]",
    "-map", "0:v", "-map", "[out]",
    "-vf", f"fade=t=in:st=0:d=0.6,fade=t=out:st={vd-1.2:.1f}:d=1.2",
    "-c:v", "libx264", "-crf", "17", "-preset", "fast",
    "-c:a", "aac", "-b:a", "192k",
    "-t", str(vd), "-movflags", "+faststart", str(FINAL)
], capture_output=True, text=True)

if FINAL.exists() and FINAL.stat().st_size > 500000:
    mb = FINAL.stat().st_size / 1024 / 1024
    print(f"\n✅ final_v2.mp4 — {mb:.1f}MB — 1080x1920 — @bookofkaur")
    subprocess.Popen(["open", str(FINAL)])
    subprocess.Popen(["open", str(OUT / "01.png")])
else:
    print(f"❌ {result.stderr[-300:]}")
