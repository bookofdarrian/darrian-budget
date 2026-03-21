#!/usr/bin/env python3
"""Create professional text-slide video with Pillow + ffmpeg"""
from PIL import Image, ImageDraw, ImageFont
import subprocess, os
from pathlib import Path

FFMPEG = "/usr/local/bin/ffmpeg"
W, H = 1280, 720
OUT_DIR = Path("/tmp/pss_slides")
OUT_DIR.mkdir(exist_ok=True)
BG, PEACH, WHITE, MUTED = (8,11,18), (255,140,66), (245,247,255), (100,112,135)

def font(size):
    for path in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Arial.ttf",
    ]:
        try: return ImageFont.truetype(path, size)
        except: pass
    return ImageFont.load_default()

def slide(name, blocks, accent_text=""):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H-5, W, H], fill=PEACH)
    d.rectangle([0, 0, W, 5], fill=PEACH)
    total_h = sum(b[2] for b in blocks) + (len(blocks)-1)*16
    y = (H - total_h) // 2
    for text, color, line_h in blocks:
        sz = 80 if line_h > 80 else (56 if line_h > 56 else (36 if line_h > 36 else 26))
        f = font(sz)
        bbox = d.textbbox((0,0), text, font=f)
        x = (W - (bbox[2]-bbox[0])) // 2
        d.text((x, y), text, fill=color, font=f)
        y += line_h + 16
    path = OUT_DIR / name
    img.save(str(path))
    return path

P, W2, M = PEACH, WHITE, MUTED

slides = [
    ("01.png", [
        ("My computer built me", W2, 88),
        ("a feature while I was sleeping.", W2, 88),
    ], 7),
    ("02.png", [
        ("Here's everything I've built.", W2, 88),
    ], 5),
    ("03.png", [
        ("🍑  Peach State Savings", P, 88),
        ("Personal finance operating system", W2, 60),
        ("140 pages  •  Budget  •  RSU  •  Investments", M, 38),
        ("FREE.", P, 60),
    ], 14),
    ("04.png", [
        ("👟  SoleOps", P, 88),
        ("Sneaker resale suite.", W2, 60),
        ("AI listings  •  ARB scanner  •  Inventory", M, 38),
        ("$200 before breakfast.", P, 60),
    ], 15),
    ("05.png", [
        ("🎓  College Confused", P, 88),
        ("Free AI college prep.", W2, 60),
        ("FAFSA  •  Essays  •  Mock interviews", M, 38),
        ("Always free.", P, 60),
    ], 14),
    ("06.png", [
        ("All of this runs", W2, 88),
        ("on a server in my house.", W2, 88),
        ("AI builds features while I sleep.", P, 56),
    ], 11),
    ("07.png", [
        ("peachstatesavings.com", W2, 56),
        ("getsoleops.com   •   collegeconfused.org", W2, 46),
    ], 7),
    ("08.png", [
        ("Follow the build.", W2, 88),
        ("@bookofdarrian", P, 88),
    ], 10),
]

print("Creating slides...")
entries = []
for name, blocks, dur in slides:
    p = slide(name, blocks)
    entries.append(f"file '{p}'\nduration {dur}")
    print(f"  ✅ {name} ({dur}s)")
entries.append(f"file '{OUT_DIR}/{slides[-1][0]}'")  # ffmpeg needs last frame twice

concat = OUT_DIR / "concat.txt"
concat.write_text("\n".join(entries))

base = Path("/Users/darrianbelcher/Downloads/darrian-budget/videos/slides_base.mp4")
r = subprocess.run([
    FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
    "-vf", "fps=25,scale=1280:720",
    "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p",
    str(base)
], capture_output=True, text=True)

if base.exists() and base.stat().st_size > 50000:
    print(f"\n✅ slides_base.mp4 — {base.stat().st_size//1024}KB")
    # Now combine with voice + Cole
    VOICE = "/Users/darrianbelcher/Downloads/The Vivian 4.m4a"
    BEAT  = "/Users/darrianbelcher/Downloads/darrian-budget/videos/beat_cole_03.mp3"
    FINAL = "/Users/darrianbelcher/Downloads/darrian-budget/videos/final_slides.mp4"
    
    r2 = subprocess.run([
        FFMPEG, "-y",
        "-stream_loop", "-1", "-i", str(base),
        "-i", VOICE,
        "-stream_loop", "-1", "-i", BEAT,
        "-filter_complex",
        "[1:a]volume=1.0[v];[2:a]volume=0.10[b];[v][b]amix=inputs=2:duration=first[out]",
        "-map", "0:v", "-map", "[out]",
        "-vf", "fade=t=in:st=0:d=1,fade=t=out:st=81:d=2",
        "-c:v", "libx264", "-crf", "19", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-t", "83.1", "-movflags", "+faststart",
        FINAL
    ], capture_output=True, text=True)
    
    fp = Path(FINAL)
    if fp.exists() and fp.stat().st_size > 500000:
        print(f"✅ FINAL: final_slides.mp4 — {fp.stat().st_size/1024/1024:.1f}MB")
        print("Opening...")
        subprocess.run(["open", FINAL])
    else:
        print(f"Combine error: {r2.stderr[-200:]}")
else:
    print(f"❌ Slides error: {r.stderr[-300:]}")
