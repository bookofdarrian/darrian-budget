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

    with st.spinner("🎙️ Transcribing your audio..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir="/tmp") as f:
            f.write(audio_bytes.read())
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
                    "--model", "base",
                    "--language", "en",
                    "--output_format", "txt",
                    "--output_dir", out_dir,
                ],
                capture_output=True,
                timeout=120,
            )
            if os.path.exists(txt_file):
                text = open(txt_file).read().strip()
                os.remove(txt_file)
                return text
        except subprocess.TimeoutExpired:
            raise Exception("Transcription timed out — audio may be too long")
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
        st.session_state["whisper_model"] = whisper.load_model("base")

    model = st.session_state["whisper_model"]
    result = model.transcribe(audio_path, language="en", fp16=False)
    return result["text"].strip()
