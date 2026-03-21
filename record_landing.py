#!/usr/bin/env python3
"""
record_landing.py — Record the PUBLIC landing page (no login needed) in portrait/9:16
then extract good frames from short_tour.mp4 for inner app pages,
compile into a final video with original voice + Cole beat.
"""
import subprocess, asyncio, time
from pathlib import Path
from playwright.async_api import async_playwright

FFMPEG = "/usr/local/bin/ffmpeg"
VIDEOS = Path("videos")
VOICE  = "/Users/darrianbelcher/Downloads/The Vivian 4.m4a"
BEAT   = str(VIDEOS / "beat_cole_03.mp3")

# ─── STEP 1: Record landing page (scrolling tour, no login) ───────────────────
async def record_landing():
    print("📹 Recording landing page (public, no login)...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            "--no-sandbox",
            "--disable-gpu",
        ])
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(VIDEOS),
            record_video_size={"width": 1280, "height": 720},
        )
        page = await ctx.new_page()

        # Load the public landing page
        print("  Loading https://peachstatesavings.com/00_landing ...")
        try:
            await page.goto("http://100.95.125.112:8501/00_landing",
                            wait_until="networkidle", timeout=30000)
        except Exception:
            await page.goto("http://100.95.125.112:8501/",
                            wait_until="networkidle", timeout=30000)

        await asyncio.sleep(3)  # Let Streamlit render

        # Slow scroll down through the whole landing page
        print("  Scrolling through landing page...")
        for scroll_y in range(0, 8000, 80):
            await page.evaluate(f"window.scrollTo(0, {scroll_y})")
            await asyncio.sleep(0.05)

        await asyncio.sleep(2)
        # Scroll back up
        for scroll_y in range(8000, 0, -120):
            await page.evaluate(f"window.scrollTo(0, {scroll_y})")
            await asyncio.sleep(0.04)

        await asyncio.sleep(2)

        video_path = await page.video.path()
        await ctx.close()
        await browser.close()

    # Convert webm → mp4
    landing_mp4 = VIDEOS / "landing_tour.mp4"
    subprocess.run([
        FFMPEG, "-y", "-i", str(video_path),
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        str(landing_mp4)
    ], capture_output=True)
    if video_path.exists():
        video_path.unlink()
    print(f"  ✅ Landing tour: {landing_mp4} ({landing_mp4.stat().st_size//1024}KB)")
    return landing_mp4

# ─── STEP 2: Extract ONLY good (non-white) frames from short_tour.mp4 ─────────
def extract_good_segments():
    """
    Use ffmpeg to extract frames, check file sizes, identify good time ranges,
    then cut those segments from short_tour.mp4.
    """
    print("\n🔍 Finding good frames in short_tour.mp4...")
    src = VIDEOS / "short_tour.mp4"

    # Extract one frame per second to /tmp/frames/
    frames_dir = Path("/tmp/smm_frames")
    frames_dir.mkdir(exist_ok=True)

    subprocess.run([
        FFMPEG, "-y", "-i", str(src),
        "-vf", "fps=1",
        str(frames_dir / "f%04d.jpg")
    ], capture_output=True)

    # Find frames with actual content (>15KB = not white screen)
    frames = sorted(frames_dir.glob("f*.jpg"))
    good_seconds = []
    for frame in frames:
        sec = int(frame.stem[1:]) - 1  # 0-indexed
        if frame.stat().st_size > 15000:  # 15KB threshold
            good_seconds.append(sec)

    print(f"  Good seconds: {good_seconds}")

    if not good_seconds:
        return None

    # Build consecutive ranges
    ranges = []
    start = good_seconds[0]
    prev  = good_seconds[0]
    for s in good_seconds[1:]:
        if s - prev > 3:  # gap > 3s → new range
            ranges.append((start, prev + 1))
            start = s
        prev = s
    ranges.append((start, prev + 1))
    print(f"  Good ranges: {ranges}")

    # Cut each range and concat
    clips = []
    for i, (ts, te) in enumerate(ranges):
        clip = VIDEOS / f"_clip_{i}.mp4"
        subprocess.run([
            FFMPEG, "-y",
            "-ss", str(max(0, ts - 0.5)),
            "-i", str(src),
            "-t", str(te - ts + 1),
            "-c:v", "libx264", "-crf", "20", "-preset", "fast",
            "-an",
            str(clip)
        ], capture_output=True)
        if clip.exists() and clip.stat().st_size > 10000:
            clips.append(clip)

    if not clips:
        return None

    # Concatenate clips
    concat_file = Path("/tmp/concat_list.txt")
    concat_file.write_text("\n".join([f"file '{c}'" for c in clips]))
    inner_mp4 = VIDEOS / "inner_tour.mp4"
    subprocess.run([
        FFMPEG, "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy", str(inner_mp4)
    ], capture_output=True)

    # Cleanup
    for c in clips:
        c.unlink(missing_ok=True)
    for f in frames_dir.glob("*.jpg"):
        f.unlink()

    dur = 0
    r = subprocess.run([FFMPEG, "-i", str(inner_mp4)], capture_output=True, text=True)
    for line in r.stderr.split("\n"):
        if "Duration" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            dur = float(h)*3600 + float(m)*60 + float(s)
    print(f"  ✅ Inner tour: {inner_mp4} ({dur:.1f}s)")
    return inner_mp4

# ─── STEP 3: Combine landing + inner + voice + beat ───────────────────────────
def combine(landing_mp4, inner_mp4):
    print("\n🎬 Combining all segments...")
    FINAL = VIDEOS / "final_real.mp4"

    # Mix audio: ORIGINAL voice (no EQ) + Cole at 10%
    mix = VIDEOS / "_final_mix.wav"
    subprocess.run([
        FFMPEG, "-y",
        "-i", VOICE,
        "-stream_loop", "-1", "-i", BEAT,
        "-filter_complex",
        "[0:a]volume=1.0[v];[1:a]volume=0.10[b];[v][b]amix=inputs=2:duration=first[out]",
        "-map", "[out]", "-ar", "44100", str(mix)
    ], capture_output=True)

    def dur(p):
        r = subprocess.run([FFMPEG, "-i", str(p)], capture_output=True, text=True)
        for line in r.stderr.split("\n"):
            if "Duration" in line:
                t = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = t.split(":")
                return float(h)*3600 + float(m)*60 + float(s)
        return 0

    vox_dur = dur(VOICE)

    # Build video source list — use both landing and inner, loop to fill voice length
    sources = []
    if landing_mp4 and landing_mp4.exists() and landing_mp4.stat().st_size > 50000:
        sources.append(str(landing_mp4))
    if inner_mp4 and inner_mp4.exists() and inner_mp4.stat().st_size > 50000:
        sources.append(str(inner_mp4))

    if not sources:
        # Fallback: just loop short_tour
        sources = [str(VIDEOS / "short_tour.mp4")]

    # Create concat list, loop to fill vox_dur
    current_dur = sum([dur(p) for p in sources])
    concat_entries = sources[:]
    while current_dur < vox_dur + 5:
        concat_entries.extend(sources)
        current_dur += sum([dur(p) for p in sources])

    concat_file = Path("/tmp/final_concat.txt")
    concat_file.write_text("\n".join([f"file '{p}'" for p in concat_entries]))

    # Render
    result = subprocess.run([
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", str(mix),
        "-vf", "fade=t=in:st=0:d=1,fade=t=out:st={:.1f}:d=1.5".format(max(1, vox_dur-2)),
        "-c:v", "libx264", "-crf", "19", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(vox_dur),
        "-movflags", "+faststart",
        str(FINAL)
    ], capture_output=True, text=True)

    mix.unlink(missing_ok=True)

    if FINAL.exists() and FINAL.stat().st_size > 200000:
        print(f"\n✅ FINAL: {FINAL} — {FINAL.stat().st_size/1024/1024:.1f} MB")
        print(f"   Voice: original (no EQ) | Beat: J. Cole 03 Adolescence @ 10%")
        return True
    else:
        print(f"❌ Combine failed:\n{result.stderr[-400:]}")
        return False

async def main():
    landing = await record_landing()
    inner   = extract_good_segments()
    ok = combine(landing, inner)
    if ok:
        print("\n📹 DO NOT OPEN until you review — check file size is > 2MB")
        print(f"   videos/final_real.mp4")
    else:
        print("❌ Failed. Check errors above.")

asyncio.run(main())
