#!/Users/darrianbelcher/Downloads/darrian-budget/venv/bin/python3
"""
Whisper Dictate Daemon — Option+M smart hotkey listener
- TAP  ⌥M (< 0.5 sec): records for 8 seconds then transcribes
- HOLD ⌥M (> 0.5 sec): records the entire time you hold, stops on release

Model: whisper medium (best accuracy for normal speech + accents)
Auto-pastes transcription into whatever app is active.
Run at login via LaunchAgent. Requires Accessibility permission.

Hotkey: ⌥ + M  (Option+M)
NOTE: ⌘M is reserved by macOS to minimize windows — using ⌥M instead.
"""

import subprocess
import threading
import time
import os
import tempfile
import sys
from pynput import keyboard

FFMPEG   = "/opt/anaconda3/bin/ffmpeg"
WHISPER  = "/Users/darrianbelcher/Downloads/darrian-budget/venv/bin/whisper"
MODEL    = "medium"
TAP_THRESHOLD = 0.5   # seconds — below = tap, above = hold
TAP_DURATION  = 8     # seconds to record on a single tap

_press_time  = None
_ffmpeg_proc = None
_recording   = False
_lock        = threading.Lock()
_alt_held    = False    # track whether Option (Alt) is currently down


# ────────────────────────────────────────────────────────────
# Notifications
# ────────────────────────────────────────────────────────────

def notify(msg: str, title: str = "🎙️ Whisper Dictate"):
    subprocess.Popen(["osascript", "-e",
        f'display notification "{msg}" with title "{title}"'])


# ────────────────────────────────────────────────────────────
# Recording
# ────────────────────────────────────────────────────────────

def start_recording(tmpfile: str):
    global _ffmpeg_proc, _recording
    with _lock:
        if _recording:
            return
        _recording = True
    _ffmpeg_proc = subprocess.Popen([
        FFMPEG, "-f", "avfoundation", "-i", ":0",
        "-ar", "16000", "-ac", "1", tmpfile,
        "-y", "-loglevel", "quiet",
    ])
    notify("🎙️ Recording… speak now")


def stop_recording():
    global _ffmpeg_proc, _recording
    with _lock:
        if not _recording:
            return
        _recording = False
    if _ffmpeg_proc and _ffmpeg_proc.poll() is None:
        _ffmpeg_proc.terminate()
        _ffmpeg_proc.wait()
    _ffmpeg_proc = None


# ────────────────────────────────────────────────────────────
# Transcription + paste
# ────────────────────────────────────────────────────────────

def transcribe_and_paste(tmpfile: str):
    notify("⏳ Transcribing…")
    try:
        txt_file = tmpfile.replace(".wav", ".txt")
        subprocess.run([
            WHISPER, tmpfile,
            "--model", MODEL,
            "--language", "en",
            "--output_format", "txt",
            "--output_dir", os.path.dirname(tmpfile),
        ], capture_output=True, timeout=120)

        if os.path.exists(txt_file):
            text = open(txt_file).read().strip()
            os.remove(txt_file)
            if text:
                subprocess.run(["pbcopy"], input=text.encode())
                subprocess.run(["osascript", "-e",
                    'tell application "System Events" to keystroke "v" using command down'])
                display = f"✅ {text[:60]}…" if len(text) > 60 else f"✅ {text}"
                notify(display)
            else:
                notify("❌ No speech detected")
        else:
            notify("❌ Transcription failed")
    except Exception as e:
        notify(f"❌ Error: {str(e)[:60]}")
    finally:
        try:
            os.remove(tmpfile)
        except OSError:
            pass


# ────────────────────────────────────────────────────────────
# Key listener — Option (⌥) + M
# macOS: Option+M produces µ (micro sign) as key.char
# We detect EITHER µ directly OR alt-held + m for robustness.
# ────────────────────────────────────────────────────────────

def _is_option_m(key) -> bool:
    """Return True if this key event is Option+M (⌥M)."""
    try:
        ch = key.char
        # macOS sends µ when Option+M is pressed
        if ch == "µ":
            return True
        # Fallback: alt held + plain m
        if ch and ch.lower() == "m" and _alt_held:
            return True
    except AttributeError:
        pass
    return False


def on_press(key):
    global _press_time, _alt_held

    # Track Option/Alt key state
    if key in (keyboard.Key.alt, keyboard.Key.alt_r, keyboard.Key.alt_l):
        _alt_held = True
        return

    # Trigger on ⌥M
    if _is_option_m(key):
        if _press_time is not None:
            return  # already in a recording session
        _press_time = time.time()
        tmpfile = tempfile.mktemp(suffix=".wav", dir="/tmp")
        on_press._tmpfile = tmpfile
        start_recording(tmpfile)


def on_release(key):
    global _press_time, _alt_held

    # Track Option/Alt key state
    if key in (keyboard.Key.alt, keyboard.Key.alt_r, keyboard.Key.alt_l):
        _alt_held = False
        return

    # Release ⌥M → decide tap vs hold
    if _is_option_m(key) and _press_time is not None:
        held    = time.time() - _press_time
        tmpfile = getattr(on_press, "_tmpfile", None)
        _press_time = None

        if held >= TAP_THRESHOLD:
            # HOLD mode: stop immediately on release
            stop_recording()
            if tmpfile:
                threading.Thread(
                    target=transcribe_and_paste, args=(tmpfile,), daemon=True
                ).start()
        else:
            # TAP mode: keep recording for TAP_DURATION more seconds
            def timed_record():
                time.sleep(TAP_DURATION)
                stop_recording()
                if tmpfile:
                    transcribe_and_paste(tmpfile)
            threading.Thread(target=timed_record, daemon=True).start()


# ────────────────────────────────────────────────────────────
# Entry
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    notify("✅ Whisper Daemon started — ⌥M to dictate", "Whisper Dictate")
    print(f"Whisper Daemon running — ⌥M (Option+M) to dictate  (model={MODEL}, tap={TAP_DURATION}s, hold=release to stop)")
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
