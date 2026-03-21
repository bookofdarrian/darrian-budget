#!/usr/bin/env python3
"""
make_video.py — Combine screen recording + voice + background beat.

Usage:
  python3 make_video.py [voice_file] [beat_file]

  voice_file: path to your recorded voice (mp3/m4a/aiff/wav)
              Default: looks for videos/my_voice.* or uses AI fallback
  beat_file:  path to background music (any mp3)
              Drop ANY mp3 as videos/beat.mp3 and it will be mixed in at low volume

Examples:
  python3 make_video.py                                # auto-detect
  python3 make_video.py videos/my_voice.m4a            # your recorded voice
  python3 make_video.py videos/my_voice.m4a videos/beat.mp3  # voice + beat
"""
import subprocess, sys, glob
from pathlib import Path

VIDEOS = Path("videos")
VIDEO_IN = VIDEOS / "tour_v2.mp4"
if not VIDEO_IN.exists():
    VIDEO_IN = VIDEOS / "short_tour.mp4"   # fallback
FINAL = VIDEOS / "final_v3.mp4"
FFMPEG = "/usr/local/bin/ffmpeg"

# --- Find voice file ---
voice = None
if len(sys.argv) > 1:
    voice = Path(sys.argv[1])
else:
    # Auto-detect: look for user's recorded voice first
    for pattern in ["videos/my_voice.*", "videos/voice_record.*", "videos/recording.*"]:
        found = glob.glob(pattern)
        if found:
            voice = Path(found[0])
            print(f"  Auto-detected voice: {voice}")
            break
    if not voice:
        # Fall back to aria
        voice = VIDEOS / "voice_aria_woman.mp3"
        print(f"  Using AI voice: {voice}")

# --- Find beat file ---
beat = None
if len(sys.argv) > 2:
    beat = Path(sys.argv[2])
elif (VIDEOS / "beat.mp3").exists():
    beat = VIDEOS / "beat.mp3"
    print(f"  Found beat: {beat}")

if not voice or not voice.exists():
    print(f"❌ Voice file not found: {voice}")
    print("  AirDrop your Voice Memos recording to your Mac,")
    print("  then move it to: videos/my_voice.m4a")
    print("  Then re-run: python3 make_video.py videos/my_voice.m4a")
    sys.exit(1)

print(f"\n📹 Video:  {VIDEO_IN}")
print(f"🎤 Voice:  {voice}")
print(f"🎵 Beat:   {beat or 'none'}")
print(f"📤 Output: {FINAL}\n")

# --- Get duration helper ---
def duration(p):
    r = subprocess.run([FFMPEG, "-i", str(p)], capture_output=True, text=True)
    for line in r.stderr.split("\n"):
        if "Duration" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return float(h)*3600 + float(m)*60 + float(s)
    return 0

vid_dur = duration(VIDEO_IN)
vox_dur = duration(voice)
print(f"  Video: {vid_dur:.1f}s  |  Voice: {vox_dur:.1f}s")

# --- Build ffmpeg command ---
target = max(vid_dur, vox_dur)

# Convert voice to temp wav (normalize any format)
tmp_voice = VIDEOS / "_voice_norm.wav"
subprocess.run([FFMPEG, "-y", "-i", str(voice),
                "-ar", "44100", "-ac", "1", str(tmp_voice)],
               capture_output=True)

if beat and beat.exists():
    # Mix voice (loud) + beat (quiet, 20% volume)
    tmp_mix = VIDEOS / "_audio_mix.wav"
    beat_dur = duration(beat)
    subprocess.run([
        FFMPEG, "-y",
        "-stream_loop", "-1", "-i", str(tmp_voice),
        "-stream_loop", "-1", "-i", str(beat),
        "-filter_complex",
        f"[0:a]volume=1.0[vox];[1:a]volume=0.15[bg];[vox][bg]amix=inputs=2:duration=first[out]",
        "-map", "[out]",
        "-t", str(vox_dur),
        str(tmp_mix)
    ], capture_output=True)
    audio_src = tmp_mix
else:
    audio_src = tmp_voice

# Combine: loop video if voice is longer
if vox_dur > vid_dur * 1.5:
    video_filter = "-stream_loop -1"
    cmd = [FFMPEG, "-y",
           "-stream_loop", "-1", "-i", str(VIDEO_IN),
           "-i", str(audio_src),
           "-c:v", "libx264", "-crf", "22", "-preset", "fast",
           "-c:a", "aac", "-b:a", "192k",
           "-shortest", "-movflags", "+faststart",
           str(FINAL)]
else:
    cmd = [FFMPEG, "-y",
           "-i", str(VIDEO_IN),
           "-i", str(audio_src),
           "-c:v", "libx264", "-crf", "22", "-preset", "fast",
           "-c:a", "aac", "-b:a", "192k",
           "-shortest", "-movflags", "+faststart",
           str(FINAL)]

result = subprocess.run(cmd, capture_output=True, text=True)

# Cleanup temp files
for f in [tmp_voice, VIDEOS / "_audio_mix.wav"]:
    if f.exists():
        f.unlink()

if FINAL.exists() and FINAL.stat().st_size > 10000:
    print(f"\n✅ FINAL VIDEO: {FINAL} ({FINAL.stat().st_size // 1024}KB)")
    subprocess.run(["open", str(FINAL)])
    print("▶️  Opening in QuickTime...")
    print()
    print("══════════════════════════════════════════")
    print("  Drag to CapCut → add text overlays")
    print("  Export 9:16 for TikTok/IG/YouTube Shorts")
    print("══════════════════════════════════════════")
else:
    print(f"❌ ffmpeg error:\n{result.stderr[-1000:]}")
