#!/usr/bin/env python3
"""
make_linkedin_video.py
======================
LinkedIn Media Production Pipeline — Darrian Belcher / Peach State Savings

Workflow:
  1. Downloads royalty-free NCS background music via yt-dlp
  2. Loops music to match voice video duration
  3. Mixes voice (100%) + music (15%) with professional ducking
  4. Outputs 3 LinkedIn-optimized formats:
       - Vertical  9:16  (1080x1920) — LinkedIn mobile feed (primary)
       - Landscape 16:9  (1280x720)  — LinkedIn desktop / newsletter
       - Square    1:1   (1080x1080) — LinkedIn feed / carousel
  5. Adds subtle watermark/branding overlay
  6. Prints copy-paste SEO post ready to use

Usage:
  python3 make_linkedin_video.py
  python3 make_linkedin_video.py --no-music       (voice only)
  python3 make_linkedin_video.py --format vertical (single format)
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
VIDEOS_DIR   = BASE_DIR / "videos"
OUTPUT_DIR   = VIDEOS_DIR / "linkedin"
MUSIC_RAW    = VIDEOS_DIR / "music_bed_raw.mp3"
MUSIC_LOOPED = VIDEOS_DIR / "music_bed_looped.mp3"

# ─── Source video (voice already recorded — 1080x1920, 2:49) ─────────────────
SOURCE_VIDEO = VIDEOS_DIR / "final_real_voice.mp4"

# ─── Output targets ───────────────────────────────────────────────────────────
OUTPUT_VERTICAL  = OUTPUT_DIR / "linkedin_vertical_9x16.mp4"    # Primary
OUTPUT_LANDSCAPE = OUTPUT_DIR / "linkedin_landscape_16x9.mp4"   # Desktop
OUTPUT_SQUARE    = OUTPUT_DIR / "linkedin_square_1x1.mp4"       # Universal

# ─── Audio mix levels ────────────────────────────────────────────────────────
VOICE_VOLUME = "1.0"   # Keep recorded voice at 100%
MUSIC_VOLUME = "0.14"  # Background music at 14% — heard but not distracting

# ─── Royalty-free music (NoCopyrightSounds — free to use commercially) ───────
# Primary: Jim Yosef - Firefly [NCS Release] — ambient/motivational
MUSIC_URLS = [
    "https://www.youtube.com/watch?v=x_OwcYTNbHs",  # Jim Yosef - Firefly
    "https://www.youtube.com/watch?v=FNAGEqBVhHk",  # Lost Sky - Vision [NCS]
    "https://www.youtube.com/watch?v=eO36Z08nTe0",  # Tobu & Itro - Sunburst
]

# ─── Watermark text ──────────────────────────────────────────────────────────
WATERMARK = "peachstatesavings.com"
AUTHOR    = "Darrian Belcher"


# ──────────────────────────────────────────────────────────────────────────────
def run_cmd(cmd: str, label: str = "", capture: bool = True) -> tuple[bool, str]:
    """Run a shell command, return (success, output)."""
    if label:
        print(f"\n  ⚙️  {label}")
    result = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        print(f"     ❌  Error: {output[:300]}")
        return False, output
    return True, output


def get_duration(filepath: Path) -> float:
    """Get video/audio duration in seconds via ffprobe."""
    _, out = run_cmd(
        f'ffprobe -v quiet -show_entries format=duration '
        f'-of default=noprint_wrappers=1:nokey=1 "{filepath}"'
    )
    try:
        return float(out.strip())
    except ValueError:
        return 170.0  # fallback to ~2:50


# ──────────────────────────────────────────────────────────────────────────────
# STEP 1 — MUSIC
# ──────────────────────────────────────────────────────────────────────────────
def download_music() -> bool:
    """Download royalty-free NCS background music via yt-dlp."""
    if MUSIC_RAW.exists():
        print("  ✅ Music already cached — skipping download")
        return True

    for i, url in enumerate(MUSIC_URLS, 1):
        print(f"  🎵 Downloading music [{i}/{len(MUSIC_URLS)}]: {url}")
        ok, _ = run_cmd(
            f'yt-dlp -x --audio-format mp3 --audio-quality 0 '
            f'--no-playlist -o "{MUSIC_RAW}" "{url}" 2>&1',
            capture=False
        )
        if ok and MUSIC_RAW.exists():
            print("  ✅ Music downloaded (NCS — royalty-free, no attribution required)")
            return True

    print("  ⚠️  All downloads failed → generating synthesized ambient music...")
    return generate_ambient_music()


def generate_ambient_music() -> bool:
    """Fallback: generate a professional ambient music bed using ffmpeg filters."""
    duration = get_duration(SOURCE_VIDEO) + 15
    # Multi-frequency ambient pad: bass (55Hz) + harmonics + soft filtered noise
    cmd = (
        f'ffmpeg -y -f lavfi '
        f'-i "aevalsrc='
        f'0.35*sin(2*PI*55*t)+'
        f'0.25*sin(2*PI*110*t)+'
        f'0.20*sin(2*PI*165*t)+'
        f'0.12*sin(2*PI*220*t)+'
        f'0.08*sin(2*PI*330*t)+'
        f'0.05*sin(2*PI*440*t):'
        f's=44100:d={duration:.0f}" '
        f'-af "'
        f'aecho=0.7:0.7:50:0.35,'
        f'aecho=0.5:0.5:120:0.25,'
        f'lowpass=f=700,'
        f'equalizer=f=100:t=o:w=50:g=4,'
        f'volume=0.45,'
        f'afade=t=in:ss=0:d=4,'
        f'afade=t=out:st={duration - 4:.0f}:d=4" '
        f'"{MUSIC_RAW}" 2>&1'
    )
    ok, _ = run_cmd(cmd, "Synthesizing ambient music bed")
    return ok and MUSIC_RAW.exists()


def loop_music(target_duration: float) -> bool:
    """Loop the music track to cover the full video duration + buffer."""
    if MUSIC_LOOPED.exists():
        print("  ✅ Looped music already exists — skipping")
        return True

    music_dur = get_duration(MUSIC_RAW)
    if music_dur <= 0:
        return False

    loops = int(target_duration / music_dur) + 3
    concat_file = VIDEOS_DIR / "_music_concat.txt"

    with open(concat_file, "w") as f:
        for _ in range(loops):
            f.write(f"file '{MUSIC_RAW.absolute()}'\n")

    ok, _ = run_cmd(
        f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
        f'-t {target_duration + 8:.0f} -ar 44100 -ac 2 '
        f'"{MUSIC_LOOPED}" 2>&1',
        "Looping music to match video length"
    )
    if concat_file.exists():
        concat_file.unlink()

    if ok:
        print(f"  ✅ Music looped to {target_duration + 8:.0f}s")
    return ok


# ──────────────────────────────────────────────────────────────────────────────
# STEP 2 — VIDEO PRODUCTION
# ──────────────────────────────────────────────────────────────────────────────
def _base_filter(width: int, height: int) -> str:
    """Return the ffmpeg filtergraph for voice+music mix and video scaling."""
    return (
        f"[0:a]volume={VOICE_VOLUME}[voice];"
        f"[1:a]volume={MUSIC_VOLUME},apad=pad_dur=2[music];"
        f"[voice][music]amix=inputs=2:duration=first:dropout_transition=2[audio_out];"
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black[video_out]"
    )


# ─── Font path detection ──────────────────────────────────────────────────────
def _find_font() -> str:
    """Find a system font that ffmpeg drawtext can use on macOS/Linux."""
    candidates = [
        # macOS
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Helvetica.dfont",
        "/System/Library/Fonts/SFNSDisplay.otf",
        "/Library/Fonts/Georgia.ttf",
        # Linux / CT100 prod server
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


def _watermark_filter(width: int, height: int, text: str, size: int) -> str:
    """Return filtergraph with watermark drawtext if a font is available,
    otherwise fall back to clean scale+pad (no text overlay)."""
    font = _find_font()
    base = _base_filter(width, height)
    if not font:
        # No usable font found — skip watermark, still delivers clean video
        return base

    # Watermark: bottom-centre, semi-transparent white, small
    watermark = (
        f"[video_out]drawtext="
        f"fontfile='{font}':"
        f"text='{text}':"
        f"fontcolor=white@0.55:"
        f"fontsize={size}:"
        f"x=(w-text_w)/2:"
        f"y=h-th-24:"
        f"box=1:boxcolor=black@0.30:boxborderw=6"
        f"[video_out]"
    )
    return base + ";" + watermark


def encode_video(
    output: Path, width: int, height: int, label: str,
    no_music: bool = False
) -> bool:
    """Encode a single LinkedIn video format.
    Uses atomic write: renders to .tmp file first, then renames on success.
    This prevents a half-written file from being mistaken for a valid output.
    """
    music_input = "" if no_music else f'-i "{MUSIC_LOOPED}"'
    filter_text  = _watermark_filter(width, height, WATERMARK, 26)
    tmp_output   = output.with_suffix(".tmp.mp4")

    if no_music:
        # Voice-only path: scale + pad, no music mixing
        filter_text = (
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black[video_out]"
        )
        map_audio = "-map 0:a"
    else:
        map_audio = '-map "[audio_out]"'

    # Clean up any previous failed temp file
    if tmp_output.exists():
        tmp_output.unlink()

    cmd = (
        f'ffmpeg -y '
        f'-i "{SOURCE_VIDEO}" {music_input} '
        f'-filter_complex "{filter_text}" '
        f'-map "[video_out]" {map_audio} '
        f'-c:v libx264 -preset medium -crf 28 -profile:v high -level 4.0 '
        f'-c:a aac -b:a 192k -ar 44100 '
        f'-movflags +faststart '
        f'-metadata title="Darrian Belcher — Autonomous AI SDLC Pipeline" '
        f'-metadata artist="{AUTHOR}" '
        f'-metadata comment="peachstatesavings.com | AI automation | SDLC | Python" '
        f'"{tmp_output}" 2>&1'
    )
    ok, _ = run_cmd(cmd, f"{label} → {output.name}")
    if ok and tmp_output.exists():
        # Atomic promotion: rename temp → final
        tmp_output.rename(output)
        size_mb = output.stat().st_size / (1024 * 1024)
        print(f"     📦 File size: {size_mb:.1f} MB")
        return True
    # Cleanup failed temp
    if tmp_output.exists():
        tmp_output.unlink()
    return False


# ──────────────────────────────────────────────────────────────────────────────
# STEP 3 — SUMMARY & SEO COPY
# ──────────────────────────────────────────────────────────────────────────────
SEO_POST_SHORT = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LINKEDIN VIDEO CAPTION — SHORT (Hook + CTA)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I built a system that ships production code while I sleep.

6 AI agents. 1 home lab. $0/month infra.
73+ pages shipped. ~$1/night in Claude API costs.

Full autonomous SDLC: feature → dev → qa → staging → prod.

The pipeline is the product. 🔥

Drop a 🔁 to see the full architecture.
peachstatesavings.com

#AI #MachineLearning #SoftwareEngineering #BuildInPublic #Python
"""

SEO_POST_LONG = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LINKEDIN VIDEO CAPTION — LONG FORM (Algorithm-optimized)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I built a system that ships production code while I sleep. 🤖

I'm a Product Manager at Visa by day.
At night I run 3 products:
→ Peach State Savings (personal finance app)
→ SoleOps (sneaker resale platform)
→ College Confused (college prep tool)

More ideas than hours. The bottleneck was always: shipping.

So I took the gated SDLC I learned at Visa — and gave it to AI agents.

Here's the architecture in 30 seconds:

⏰ 11PM cron kicks off on my home lab (Proxmox CT100 + Tailscale)

🧠 Planner Agent reads BACKLOG.md → writes spec
⚙️  Backend Agent generates DB tables + logic (follows my patterns)
🎨 UI Agent scaffolds Streamlit pages (my sidebar standard)
🧪 Test Agent writes + runs pytest
✅ QA Agent checks: no hardcoded keys, all tests pass, patterns correct
🚀 Git Agent commits on a feature branch, opens a GitHub PR

I wake up. Review the PR. Merge. Done.

What makes it different from vibe coding:
→ Guardrails are in the SYSTEM, not repeated every session
→ It knows my codebase, my patterns, my DB helpers
→ If tests fail → nothing commits
→ Human judgment is always the final gate

Cost: ~$1/night (Claude Opus 4)
Infrastructure: $0/month (self-hosted homelab)
Pages shipped: 73+
Time saved: 3–4 hours per feature

This isn't replacing my engineering judgment.
It's amplifying it.

A human still drives. The AI handles the road.

Comment "PIPELINE" and I'll share the orchestrator code. 👇

#AI #SDLC #ProductManagement #Python #Streamlit
#BuildInPublic #IndieHacker #MachineLearning #Automation
#SoftwareEngineering #CareerGrowth #TechInnovation
"""


def print_summary(no_music: bool, fmt: str | None):
    """Print full production summary with SEO copy."""
    print("\n" + "═" * 65)
    print("🚀  LINKEDIN MEDIA PACKAGE COMPLETE")
    print("═" * 65)

    outputs = [OUTPUT_VERTICAL, OUTPUT_LANDSCAPE, OUTPUT_SQUARE]
    labels  = ["9:16 Vertical (Mobile — PRIMARY)", "16:9 Landscape (Desktop)", "1:1 Square (Universal Feed)"]

    for out, lbl in zip(outputs, labels):
        if out.exists():
            size = out.stat().st_size / (1024 * 1024)
            print(f"  ✅  {lbl:<40} {out.name} ({size:.1f}MB)")
        else:
            print(f"  ⏭️  {lbl:<40} SKIPPED")

    print("\n" + "─" * 65)
    print("📋  POSTING ORDER (Strategic Distribution)")
    print("─" * 65)
    print("  1. LinkedIn (VERTICAL)   → Upload video + long caption + hashtags")
    print("  2. Instagram Reels       → Same vertical video, shorter caption")
    print("  3. TikTok                → Vertical, trending sounds optional")
    print("  4. YouTube Shorts        → Vertical, add chapters if > 60s")
    print("  5. Facebook              → Landscape version, tag Peach State Savings")
    print("  6. Twitter/X             → Landscape, thread format")
    print("  7. LinkedIn Newsletter   → Landscape, embed in article")
    print()
    print(SEO_POST_SHORT)
    print(SEO_POST_LONG)
    print("═" * 65)
    print("🎯  Optimal LinkedIn Posting Times (EST):")
    print("     Tuesday–Thursday  →  7:30–9:00 AM  |  12:00–1:00 PM  |  5:30–6:30 PM")
    print("     Monday            →  8:00–10:00 AM (high intent)")
    print("     AVOID             →  Weekends, Fri after 3PM")
    print("═" * 65)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="LinkedIn Media Production Pipeline")
    parser.add_argument("--no-music", action="store_true", help="Skip music, voice only")
    parser.add_argument("--format", choices=["vertical", "landscape", "square"],
                        help="Produce only one format")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║   🎬  LinkedIn Media Production — Darrian Belcher           ║")
    print("║   🎵  Voice + Music → Multi-Format LinkedIn Videos          ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # Validate source
    if not SOURCE_VIDEO.exists():
        print(f"❌  Source video not found: {SOURCE_VIDEO}")
        sys.exit(1)

    duration = get_duration(SOURCE_VIDEO)
    print(f"\n  📹  Source : {SOURCE_VIDEO.name}")
    print(f"  ⏱️  Duration: {duration:.0f}s ({duration/60:.1f} min)")
    print(f"  📐  Format  : 1080x1920 (9:16 portrait)")
    print(f"  🔊  Audio   : AAC voice recording — ready for music mix")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Music
    if not args.no_music:
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("STEP 1 — MUSIC (Royalty-Free NCS)")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        if not download_music():
            print("❌  Music setup failed. Use --no-music flag.")
            sys.exit(1)

        print()
        if not loop_music(duration):
            print("❌  Music looping failed.")
            sys.exit(1)
    else:
        print("\n  ℹ️  --no-music flag set — producing voice-only video")

    # Step 2: Encode video formats
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("STEP 2 — VIDEO PRODUCTION")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    fmt = args.format
    no_music = args.no_music

    if not fmt or fmt == "vertical":
        encode_video(OUTPUT_VERTICAL,  1080, 1920, "LinkedIn Vertical  9:16  (Mobile PRIMARY)", no_music)
    if not fmt or fmt == "landscape":
        encode_video(OUTPUT_LANDSCAPE, 1280,  720, "LinkedIn Landscape 16:9  (Desktop/Newsletter)", no_music)
    if not fmt or fmt == "square":
        encode_video(OUTPUT_SQUARE,    1080, 1080, "LinkedIn Square    1:1   (Universal Feed)", no_music)

    # Step 3: Summary + SEO copy
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("STEP 3 — SUMMARY & SEO COPY")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print_summary(no_music, fmt)


if __name__ == "__main__":
    main()
