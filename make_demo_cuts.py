#!/usr/bin/env python3
"""
make_demo_cuts.py — Multi-platform demo video renderer + caption sidecar files
Produces clean crops for each platform + per-segment SRT files.

Native captions (upload .srt to TikTok/YouTube/IG/LinkedIn) are MORE accessible
than burned-in — they can be translated, adjusted, and indexed by search engines.

Platforms:
  TikTok / IG Reels / YT Shorts  → 1080x1920 (9:16)
  YouTube / LinkedIn              → 1920x1080 (16:9)
  Instagram Feed Square           → 1080x1080 (1:1)
  Instagram Feed Portrait 4:5     → 1080x1350

Segments:
  full    → 0-44s (full demo)
  hook    → 0-8s  (opening hook)
  pss     → 8-21s (Peach State Savings)
  soleops → 21-31s (SoleOps)
  cc      → 31-44s (College Confused + CTA)
"""

import subprocess, os, sys, re

FFMPEG  = "/opt/anaconda3/bin/ffmpeg"
SRC     = "/Users/darrianbelcher/Downloads/IMG_3480.MOV"
SRT     = "/Users/darrianbelcher/Downloads/darrian-budget/videos/IMG_3480.srt"
OUT     = "/Users/darrianbelcher/Downloads/darrian-budget/videos/cuts"
os.makedirs(OUT, exist_ok=True)

# ── Platform crop/scale filters ───────────────────────────────────────────────
# After transpose=1: stored 3840x2160 → display 2160w x 3840h (portrait)
# Center crops:
#   9:16  → 1080x1920 → x=(2160-1080)/2=540,  y=(3840-1920)/2=960
#   16:9  → 2160x1215 → x=0,                  y=(3840-1215)/2=1312
#   1:1   → 2160x2160 → x=0,                  y=(3840-2160)/2=840
#   4:5   → 2160x2700 → x=0,                  y=(3840-2700)/2=570
PLATFORMS = [
    ("tiktok_reels_shorts",  1080, 1920,
     "transpose=1,crop=1080:1920:540:960"),
    ("youtube_linkedin",     1920, 1080,
     "transpose=1,crop=2160:1215:0:1312,scale=1920:1080"),
    ("instagram_square",     1080, 1080,
     "transpose=1,crop=2160:2160:0:840,scale=1080:1080"),
    ("instagram_4x5",        1080, 1350,
     "transpose=1,crop=2160:2700:0:570,scale=1080:1350"),
]

# ── Segments (name, start_sec, end_sec) ───────────────────────────────────────
SEGMENTS = [
    ("full",    None,  None),
    ("hook",    "0",   "8"),
    ("pss",     "8",   "21"),
    ("soleops", "21",  "31"),
    ("cc",      "31",  None),
]

# ── SRT parser / writer ───────────────────────────────────────────────────────
def ts_to_sec(ts):
    h, m, rest = ts.strip().split(":")
    s, ms = rest.replace(",", ".").split(".")
    return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000

def sec_to_ts(sec):
    h  = int(sec // 3600)
    m  = int((sec % 3600) // 60)
    s  = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def parse_srt(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        raw = f.read().strip()
    subs = []
    for block in re.split(r'\n\n+', raw):
        lines = block.strip().splitlines()
        for i, line in enumerate(lines):
            if '-->' in line:
                parts = line.split('-->')
                t_in  = ts_to_sec(parts[0])
                t_out = ts_to_sec(parts[1])
                text  = '\n'.join(lines[i+1:]).strip()
                subs.append((t_in, t_out, text))
                break
    return subs

def write_srt(subs, seg_start, seg_end, out_path):
    """Write a trimmed SRT adjusted to segment-relative timestamps."""
    seg_start = seg_start or 0.0
    seg_end   = seg_end   or 1e9
    out = []
    idx = 1
    for (t_in, t_out, text) in subs:
        # Only include captions within this segment
        if t_out <= seg_start or t_in >= seg_end:
            continue
        adj_in  = max(0.0, t_in  - seg_start)
        adj_out = max(0.0, min(t_out, seg_end) - seg_start)
        out.append(f"{idx}\n{sec_to_ts(adj_in)} --> {sec_to_ts(adj_out)}\n{text}\n")
        idx += 1
    if out:
        with open(out_path, 'w') as f:
            f.write('\n'.join(out))
        return True
    return False


def run(cmd, label):
    print(f"\n▶  {label}")
    result = subprocess.run(cmd, shell=True, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout or ""
    lines  = [l for l in output.splitlines() if l.strip()][-3:]
    for l in lines:
        print(f"   {l}")
    ok = result.returncode == 0
    print(f"   {'✓ DONE' if ok else '✗ FAILED (see above)'}")
    return ok


def build_video(platform_name, w, h, crop_filter, seg_name, t_start, t_end):
    fname    = f"{platform_name}__{seg_name}.mp4"
    out_path = os.path.join(OUT, fname)

    trim_in  = f"-ss {t_start}" if t_start else ""
    trim_out = f"-to {t_end}"   if t_end   else ""

    cmd = (
        f'{FFMPEG} -y {trim_in} -i "{SRC}" {trim_out} '
        f'-vf "{crop_filter}" '
        f'-c:v libx264 -crf 23 -preset fast '
        f'-c:a aac -b:a 128k '
        f'-movflags +faststart '
        f'"{out_path}"'
    )
    return run(cmd, f"{platform_name} / {seg_name}  [{w}x{h}]")


# ── Main ─────────────────────────────────────────────────────────────────────
if not os.path.exists(SRC):
    print(f"ERROR: Source not found: {SRC}"); sys.exit(1)

subs = parse_srt(SRT)
print(f"Loaded {len(subs)} subtitle entries")
print(f"Rendering {len(PLATFORMS)} platforms × {len(SEGMENTS)} segments = {len(PLATFORMS)*len(SEGMENTS)} videos\n")

# First, write per-segment SRT files (shared across platforms)
srt_dir = os.path.join(OUT, "captions")
os.makedirs(srt_dir, exist_ok=True)
for seg_name, t_start, t_end in SEGMENTS:
    srt_out = os.path.join(srt_dir, f"{seg_name}.srt")
    s = float(t_start) if t_start else 0.0
    e = float(t_end)   if t_end   else 1e9
    written = write_srt(subs, s, e, srt_out)
    if written:
        print(f"  ✓ captions/{seg_name}.srt")

print()

# Render all platform/segment combos
success = 0
total   = 0
for plat_name, w, h, crop in PLATFORMS:
    for seg_name, t_start, t_end in SEGMENTS:
        total += 1
        ok = build_video(plat_name, w, h, crop, seg_name, t_start, t_end)
        if ok:
            success += 1

print(f"\n{'='*60}")
print(f"COMPLETE: {success}/{total} video renders succeeded")
print(f"Captions: {srt_dir}/")
print(f"Videos:   {OUT}/")
print(f"{'='*60}")
subprocess.run(f'ls -lh "{OUT}"/*.mp4 2>/dev/null', shell=True)
print("\nCABTION FILES:")
subprocess.run(f'ls -lh "{srt_dir}"/*.srt 2>/dev/null', shell=True)
print("\n📋 UPLOAD GUIDE:")
print("  TikTok   → Creator Tools → Captions → Upload .srt")
print("  YouTube  → Details → Subtitles → Upload file")
print("  IG Reels → Add Captions (auto) or manual")
print("  LinkedIn → Manage → Closed Captions → Upload .srt")
