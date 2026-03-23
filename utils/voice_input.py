"""
utils/voice_input.py
Universal voice-to-text component for all Streamlit pages.
Uses st.audio_input() (Streamlit 1.27+) + local OpenAI Whisper via subprocess.

How it works in the UI:
  - Click 🎤 once to START recording (red dot appears)
  - Click 🔴 again to STOP recording
  - Auto-transcribes and returns text

Usage (any page):
    from utils.voice_input import render_voice_input
    text = render_voice_input(label="🎤 Speak a note", key="notes_voice")
    if text:
        st.session_state.note_content = text

FIX (2026-03-23): st.audio_input() returns WebM/OGG bytes from the browser,
NOT WAV. Saving as .wav caused Whisper to misdetect the format and return
empty/garbage. Now we detect the real format from magic bytes and save with
the correct extension before passing to Whisper.
"""

import os
import subprocess
import tempfile
import streamlit as st

# Path to the venv whisper CLI — works even when app runs under Anaconda's Python
VENV_WHISPER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "venv", "bin", "whisper"
)
VENV_PYTHON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "venv", "bin", "python3"
)


def _read_audio_bytes(audio_bytes) -> bytes:
    """
    Safely extract raw bytes from whatever st.audio_input() returns.
    Handles:
      - bytes / bytearray         (newer Streamlit returns raw bytes)
      - UploadedFile / BytesIO    (older Streamlit returns file-like)
    """
    if isinstance(audio_bytes, (bytes, bytearray)):
        return bytes(audio_bytes)
    # file-like object — seek to start just in case the pointer moved
    if hasattr(audio_bytes, "seek"):
        audio_bytes.seek(0)
    if hasattr(audio_bytes, "getvalue"):
        return audio_bytes.getvalue()
    if hasattr(audio_bytes, "read"):
        return audio_bytes.read()
    # last resort
    return bytes(audio_bytes)


def _detect_audio_extension(raw: bytes) -> str:
    """
    Detect the real audio container format from magic bytes.
    Browser MediaRecorder typically outputs WebM (Chrome) or OGG (Firefox).
    Saving with the wrong extension causes Whisper to mis-detect the format.

    Returns the correct file extension (without dot) to use when writing the
    temp file so that Whisper's ffmpeg backend handles it correctly.
    """
    if len(raw) < 4:
        return "webm"

    # RIFF WAV
    if raw[:4] == b"RIFF":
        return "wav"
    # OGG / OGG+Opus  (Firefox MediaRecorder default)
    if raw[:4] == b"OggS":
        return "ogg"
    # WebM / Matroska  (Chrome/Edge MediaRecorder default — EBML magic)
    if raw[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    # MP3 — ID3 tag or sync word
    if raw[:3] == b"ID3" or (len(raw) >= 2 and raw[0] == 0xFF and raw[1] & 0xE0 == 0xE0):
        return "mp3"
    # FLAC
    if raw[:4] == b"fLaC":
        return "flac"
    # MP4 / M4A  (some mobile browsers)
    if len(raw) >= 8 and raw[4:8] in (b"ftyp", b"moov", b"mdat"):
        return "mp4"

    # Default: WebM (most common from Chrome-based browsers)
    return "webm"


def render_voice_input(
    label: str = "🎤 Click to record, click again to stop",
    key: str = "voice_input",
) -> str:
    """
    Renders a microphone widget. When the user records audio, it transcribes
    and returns the transcribed string.

    HOW TO USE:
      1. Click the microphone button to START recording
      2. Speak clearly
      3. Click the button again to STOP recording
      4. Wait ~5 seconds for transcription

    Returns empty string if no audio or transcription fails.
    """
    audio_bytes = st.audio_input(label, key=key)

    if audio_bytes is None:
        return ""

    raw = _read_audio_bytes(audio_bytes)
    if not raw:
        st.warning("⚠️ No audio data received — please try recording again.")
        return ""

    # Detect the real audio format so Whisper's ffmpeg backend handles it correctly
    ext = _detect_audio_extension(raw)

    with st.spinner("🎙️ Transcribing your audio..."):
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{ext}", dir="/tmp"
        ) as f:
            f.write(raw)
            tmp_path = f.name
        try:
            text = _transcribe_via_subprocess(tmp_path)
            if text:
                st.success(f"🎙️ *{text}*")
            else:
                st.warning("⚠️ No speech detected — try speaking louder or closer to the mic.")
            return text or ""
        except Exception as e:
            st.error(f"Transcription error: {e}")
            return ""
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _transcribe_via_subprocess(audio_path: str) -> str:
    """
    Transcribe audio using the venv's whisper CLI via subprocess.
    This works even when the Streamlit app runs under Anaconda's Python,
    which doesn't have whisper installed.

    Falls back to direct Python import if the CLI isn't found.
    """
    out_dir = "/tmp"
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    txt_file = os.path.join(out_dir, base_name + ".txt")

    # Try venv whisper CLI first (most reliable cross-env approach)
    if os.path.exists(VENV_WHISPER):
        try:
            result = subprocess.run(
                [
                    VENV_WHISPER, audio_path,
                    "--model", "medium",
                    "--language", "en",
                    "--output_format", "txt",
                    "--output_dir", out_dir,
                ],
                capture_output=True,
                timeout=120,
            )
            # Check for subprocess errors and surface them
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace").strip()
                stdout = result.stdout.decode("utf-8", errors="replace").strip()
                raise Exception(
                    f"Whisper exited with code {result.returncode}. "
                    f"stderr: {stderr[:400] or '(none)'} | stdout: {stdout[:200] or '(none)'}"
                )
            if os.path.exists(txt_file):
                text = open(txt_file).read().strip()
                try:
                    os.remove(txt_file)
                except OSError:
                    pass
                return text
            # whisper ran OK but no txt file — empty audio
            return ""
        except subprocess.TimeoutExpired:
            raise Exception("Transcription timed out — audio may be too long (max ~2 min)")
        except FileNotFoundError:
            pass  # fall through to Python import

    # Fallback: try direct Python import (works if whisper is in current env)
    try:
        import whisper  # noqa: F401 — only used as fallback
        return _transcribe_whisper_direct(audio_path)
    except ImportError:
        raise Exception(
            "Whisper not found. Run: pip install openai-whisper  "
            "(or ensure venv/bin/whisper exists)"
        )


def _transcribe_whisper_direct(audio_path: str) -> str:
    """
    Transcribe audio using the local Whisper model (direct Python import).
    Caches the model in st.session_state so it only loads once per session.
    """
    import whisper

    if "whisper_model" not in st.session_state:
        st.session_state["whisper_model"] = whisper.load_model("medium")

    model = st.session_state["whisper_model"]
    result = model.transcribe(audio_path, language="en", fp16=False)
    return result["text"].strip()
