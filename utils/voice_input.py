"""
utils/voice_input.py
Universal voice-to-text component for all Streamlit pages.
Uses st.audio_input() (Streamlit 1.27+) + local OpenAI Whisper.

Usage (any page):
    from utils.voice_input import render_voice_input
    text = render_voice_input(label="🎤 Speak a note", key="notes_voice")
    if text:
        st.session_state.note_content = text
"""

import os
import tempfile
import streamlit as st


def render_voice_input(
    label: str = "🎤 Speak",
    key: str = "voice_input",
) -> str:
    """
    Renders a microphone widget. When the user records audio, it transcribes
    via local Whisper and returns the transcribed string.
    Returns empty string if no audio or transcription fails.
    """
    audio_bytes = st.audio_input(label, key=key)

    if audio_bytes is None:
        return ""

    with st.spinner("Transcribing..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_bytes.read())
            tmp_path = f.name
        try:
            text = _transcribe_whisper(tmp_path)
            if text:
                st.success(f"🎙️ *{text}*")
            return text
        except ImportError:
            st.warning(
                "⚠️ Whisper not installed. Run: `pip install openai-whisper` in your venv."
            )
            return ""
        except Exception as e:
            st.error(f"Transcription error: {e}")
            return ""
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _transcribe_whisper(audio_path: str) -> str:
    """
    Transcribe audio using the local Whisper model.
    Caches the model in st.session_state so it only loads once per session.
    Uses 'base' model — fast, ~150MB, good accuracy for English.
    Upgrade to 'small' or 'medium' for better accuracy at higher cost.
    """
    import whisper  # pip install openai-whisper

    if "whisper_model" not in st.session_state:
        st.session_state["whisper_model"] = whisper.load_model("base")

    model = st.session_state["whisper_model"]
    result = model.transcribe(audio_path, language="en", fp16=False)
    return result["text"].strip()
