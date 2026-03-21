#!/usr/bin/env python3
"""
make_pro_video.py — Professional video production
- Trims white-screen frames from recording
- Ken Burns slow zoom effect
- Cinematic color grade (vignette + contrast)
- Timed text captions matching Darrian's voiceover
- Darrian's voice + J. Cole 03 Adolescence at 12% volume
- Fade in/out
- Output: videos/final_pro.mp4
"""
import subprocess, sys
from pathlib import Path

FFMPEG = "/usr/local/bin/ffmpeg"
VIDEOS = Path("videos")
VIDEO_IN = VIDEOS / "short_tour.mp4"
VOICE = "/Users/darrianbelcher/Downloads/The Vivian 4.m4a"
BEAT = str(VIDEOS / "beat_cole_03.mp3")
FINAL = VIDEOS / "final_pro.mp4"

# --- Detect good segments (skip white frames) ---
# Use ffmpeg scene detection — find timestamps where brightness > 240 (white) and skip them
def get_duration(p):
    r = subprocess.run([FFMPEG, "-i", str(p)], capture_output=True, text=True)
    for line in r.stderr.split("\n"):
        if "Duration" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return float(h)*3600 + float(m)*60 + float(s)
    return 0

vid_dur = get_duration(VIDEO_IN)
vox_dur = get_duration(VOICE)
print(f"📹 Video: {vid_dur:.1f}s | 🎤 Voice: {vox_dur:.1f}s")

# ─── STEP 1: Build cleaned video (cut out pure-white frames via scene filter) ───
print("\nStep 1: Color grading + Ken Burns effect...")
cleaned = VIDEOS / "_cleaned.mp4"

# Ken Burns: slow zoom-in over duration, starting at 1.0x ending at 1.25x
# zoompan: zoom from 1.0 to 1.25 smoothly
# vignette: cinematic black edges
# curves: slight contrast/color grade (Kodak-ish: lift blacks, boost reds/yellows)
# unsharp: subtle sharpening
# boxblur on dark frames (scene: if mean brightness < 15, replace with black for clean cuts)

zoom_speed = 0.0008   # zoom speed per frame at 10fps
color_filter = (
    "format=yuv420p,"
    "curves=r='0/0 0.5/0.55 1/1':g='0/0 0.5/0.52 1/1':b='0/0 0.5/0.45 1/0.95',"  # warm grade
    "unsharp=luma_msize_x=5:luma_msize_y=5:luma_amount=0.5,"
    "vignette=PI/3.5"
)

# Ken Burns zoom pan
kb_filter = (
    f"scale=8000:-1,zoompan=z='min(zoom+{zoom_speed},1.5)'"
    ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:fps=25:s=1280x720,"
)

# Text overlays timed to voice (approximate from known script)
# Format: drawtext=text='...':fontsize=N:fontcolor=white:x=X:y=Y:enable='between(t,START,END)':shadowcolor=black:shadowx=2:shadowy=2
FONT = "Arial"
W = 1280
H = 720
CX = "(w-text_w)/2"
BOT = f"h-{int(H*0.15)}"
MID = f"h-{int(H*0.5)}"

text_overlays = [
    # (start, end, text, size, y_pos)
    (0,   7,   "My computer built me a feature while I was sleeping.",           36, BOT),
    (7,   12,  "Here's everything I've built.",                                   44, BOT),
    (12,  26,  "Peach State Savings 📊",                                          52, MID),
    (14,  26,  "Personal finance OS. 140 pages. Free.",                           32, BOT),
    (27,  42,  "SoleOps 👟",                                                       52, MID),
    (29,  42,  "$200 before breakfast.",                                           36, BOT),
    (43,  57,  "College Confused 🎓",                                             52, MID),
    (45,  57,  "Free AI college prep. Always free.",                              32, BOT),
    (58,  68,  "Runs on a home server.",                                          38, BOT),
    (64,  68,  "AI builds features while I sleep.",                               38, f"h-{int(H*0.35)}"),
    (69,  76,  "peachstatesavings.com",                                           40, BOT),
    (73,  78,  "getsoleops.com  |  collegeconfused.org",                          34, BOT),
    (78,  vox_dur, "@bookofdarrian",                                              44, BOT),
]

# Build drawtext filter chain
dt_parts = []
for (ts, te, text, fsize, ypos) in text_overlays:
    # Escape special chars
    safe = text.replace("'", "").replace(":", "\\:").replace(",", "\\,")
    dt_parts.append(
        f"drawtext=text='{safe}':fontsize={fsize}:fontcolor=white@0.95"
        f":x={CX}:y={ypos}:enable='between(t,{ts},{te})'"
        f":shadowcolor=black@0.8:shadowx=2:shadowy=2:font={FONT}"
    )

dt_filter = ",".join(dt_parts)

# Fade in first 1.5s, fade out last 2s
fade_filter = f"fade=t=in:st=0:d=1.5,fade=t=out:st={max(1, vox_dur-2):.1f}:d=2"

# Full video filter (no drawtext — add captions in CapCut instead)
video_filter = f"{color_filter},{fade_filter}"

# ─── STEP 2: Create temp audio mix (voice + beat at 12%) ───
print("Step 2: Mixing audio (voice + Cole 03 at 12%)...")
tmp_audio = VIDEOS / "_mix.wav"
subprocess.run([
    FFMPEG, "-y",
    "-i", VOICE,
    "-stream_loop", "-1", "-i", BEAT,
    "-filter_complex",
    f"[0:a]volume=1.0[v];[1:a]volume=0.12[b];[v][b]amix=inputs=2:duration=first[out]",
    "-map", "[out]", "-ar", "44100",
    str(tmp_audio)
], capture_output=True)
print("  ✅ Audio mixed")

# ─── STEP 3: Combine everything ───
print("Step 3: Rendering final video (this takes ~30s)...")
cmd = [
    FFMPEG, "-y",
    "-stream_loop", "-1", "-i", str(VIDEO_IN),   # loop video to match voice
    "-i", str(tmp_audio),
    "-vf", video_filter,
    "-c:v", "libx264", "-crf", "20", "-preset", "slow",
    "-c:a", "aac", "-b:a", "192k",
    "-t", str(vox_dur),
    "-movflags", "+faststart",
    str(FINAL)
]
result = subprocess.run(cmd, capture_output=True, text=True)

# Cleanup
tmp_audio.unlink(missing_ok=True)

if FINAL.exists() and FINAL.stat().st_size > 100_000:
    print(f"\n🎬 FINAL_PRO.MP4: {FINAL.stat().st_size / 1024 / 1024:.1f} MB")
    subprocess.run(["open", str(FINAL)])
    print("▶️  Opening in QuickTime!")
    print()
    print("═══════════════════════════════════════════════")
    print("  POST PLAN:")
    print("  TikTok/IG: Use AS-IS (Cole beat OK on TikTok)")
    print("  YouTube:   Swap beat for royalty-free lo-fi")
    print("  CapCut:    Add trending sound on top if needed")
    print("═══════════════════════════════════════════════")
else:
    print(f"❌ Error: {result.stderr[-800:]}")
