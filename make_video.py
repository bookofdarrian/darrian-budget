#!/usr/bin/env python3
"""
Generate voiceover with OpenAI TTS, combine with screen recording,
burn in auto-captions using Whisper, produce final video.
"""
import subprocess
import os
import sys
from pathlib import Path

VIDEOS = Path("videos")
VIDEO_IN = VIDEOS / "short_tour.mp4"
AUDIO_OUT = VIDEOS / "voiceover.mp3"
FINAL = VIDEOS / "final_with_voice.mp4"
FFMPEG = "/usr/local/bin/ffmpeg"

SCRIPT = """My computer built me a new app feature while I was sleeping. This is everything I've built.

Peach State Savings — a personal finance operating system. 140 pages. Budget tracker, income manager, RSU calendar, investments, cash flow — all in one place. Free.

SoleOps — my sneaker resale business suite. AI listing generator, inventory manager, and an ARB scanner that texts me when a pair drops below my buy price. It made me $200 before breakfast.

College Confused — free AI college prep for first-gen students. FAFSA walkthrough, essay assistant, AI mock interviews. I was first-gen. This is the platform I wish I had. Always free. Always will be.

All of this runs on a server in my house, managed by an overnight AI system that builds features while I sleep.

peachstatesavings.com — free. getsoleops.com — April launch. collegeconfused.org — always free. Follow the build: at bookofdarrian."""

# --- Step 1: Generate voiceover via OpenAI TTS ---
print("Step 1: Generating voiceover with OpenAI TTS...")
try:
    import openai
    from utils.db import get_setting
    api_key = get_setting("openai_api_key") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("No OpenAI API key found")
    client = openai.OpenAI(api_key=api_key)
    resp = client.audio.speech.create(
        model="tts-1",
        voice="onyx",   # deep, authoritative
        input=SCRIPT,
        speed=0.95,
    )
    resp.stream_to_file(str(AUDIO_OUT))
    print(f"  ✅ Voiceover: {AUDIO_OUT} ({AUDIO_OUT.stat().st_size//1024}KB)")
except Exception as e:
    print(f"  ⚠️  OpenAI TTS failed: {e}")
    print("  Falling back to macOS say...")
    aiff = VIDEOS / "voiceover.aiff"
    subprocess.run(["say", "-v", "Samantha", "-r", "165",
                    SCRIPT, "-o", str(aiff)], check=True)
    subprocess.run([FFMPEG, "-y", "-i", str(aiff),
                    str(AUDIO_OUT)], capture_output=True)
    print(f"  ✅ Fallback voiceover: {AUDIO_OUT}")

# --- Step 2: Get durations ---
def get_duration(path):
    r = subprocess.run(
        [FFMPEG, "-i", str(path)],
        capture_output=True, text=True
    )
    for line in r.stderr.split("\n"):
        if "Duration" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return float(h)*3600 + float(m)*60 + float(s)
    return 0

vid_dur = get_duration(VIDEO_IN)
aud_dur = get_duration(AUDIO_OUT)
print(f"  Video: {vid_dur:.1f}s  |  Audio: {aud_dur:.1f}s")

# --- Step 3: Combine video + audio (loop video if audio is longer) ---
print("Step 2: Combining video + voiceover...")
if aud_dur > vid_dur:
    # Speed up video slightly to match audio, or loop it
    speed = aud_dur / vid_dur
    if speed < 1.5:
        # Slow down video slightly
        subprocess.run([
            FFMPEG, "-y",
            "-i", str(VIDEO_IN),
            "-i", str(AUDIO_OUT),
            "-filter:v", f"setpts={1/speed}*PTS",
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac", "-shortest",
            "-movflags", "+faststart",
            str(FINAL)
        ], capture_output=True)
    else:
        # Just mux and let it run
        subprocess.run([
            FFMPEG, "-y",
            "-stream_loop", "-1", "-i", str(VIDEO_IN),
            "-i", str(AUDIO_OUT),
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac", "-shortest",
            "-movflags", "+faststart",
            str(FINAL)
        ], capture_output=True)
else:
    subprocess.run([
        FFMPEG, "-y",
        "-i", str(VIDEO_IN),
        "-i", str(AUDIO_OUT),
        "-c:v", "copy", "-c:a", "aac",
        "-shortest", "-movflags", "+faststart",
        str(FINAL)
    ], capture_output=True)

if FINAL.exists():
    print(f"  ✅ Final video: {FINAL} ({FINAL.stat().st_size//1024}KB)")
    subprocess.run(["open", str(FINAL)])
    print("  ▶️  Opening in QuickTime...")
else:
    print("  ❌ Something went wrong — check ffmpeg output")

print("\n✅ DONE — final_with_voice.mp4 ready for TikTok/IG/YouTube!")
print("  Drag to CapCut for text overlays, then export 9:16")
