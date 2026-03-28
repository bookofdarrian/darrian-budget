"""
utils/voice_input.py
Universal voice-to-text component for all Streamlit pages.
Uses st.audio_input() (Streamlit 1.27+) + local OpenAI Whisper via subprocess.

DESIGN: The microphone button is a large, deliberate, unmissable CTA button.
It requires a conscious "Activate Recording" click before the audio widget appears,
preventing accidental presses. The active state is clearly styled in red.

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

# ── CSS injected once per session ──────────────────────────────────────────────
_VOICE_CSS = """
<style>
/* ── Voice Input Button ────────────────────────────────────────────────────── */
.voice-btn-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 16px 0;
}
.voice-activate-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background: linear-gradient(135deg, #1e1e3f 0%, #2d1b69 100%);
    border: 2px solid rgba(167,139,250,0.4);
    border-radius: 100px;
    padding: 14px 32px;
    font-size: 1rem;
    font-weight: 700;
    color: #a78bfa;
    cursor: pointer;
    min-width: 200px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    box-shadow: 0 4px 20px rgba(124,58,237,0.25);
    transition: all 0.2s;
}
.voice-activate-btn:hover {
    border-color: rgba(167,139,250,0.8);
    box-shadow: 0 6px 28px rgba(124,58,237,0.45);
    transform: translateY(-1px);
}
.voice-active-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(239,68,68,0.12);
    border: 2px solid rgba(239,68,68,0.5);
    border-radius: 100px;
    padding: 8px 20px;
    font-size: 0.82rem;
    font-weight: 700;
    color: #ef4444;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    animation: pulse-border 1.5s infinite;
}
.voice-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #ef4444;
    animation: pulse-dot 1.5s infinite;
    flex-shrink: 0;
}
@keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.7); }
}
@keyframes pulse-border {
    0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.3); }
    50% { box-shadow: 0 0 0 6px rgba(239,68,68,0.0); }
}
.voice-instructions {
    font-size: 0.78rem;
    color: rgba(255,255,255,0.35);
    text-align: center;
    line-height: 1.5;
}
.voice-cancel-hint {
    font-size: 0.72rem;
    color: rgba(239,68,68,0.5);
    text-align: center;
    margin-top: -4px;
}
</style>
"""


def _inject_voice_css():
    """Inject voice input CSS once per session."""
    if not st.session_state.get("_voice_css_injected"):
        st.markdown(_VOICE_CSS, unsafe_allow_html=True)
        st.session_state["_voice_css_injected"] = True


def _read_audio_bytes(audio_bytes) -> bytes:
    """
    Safely extract raw bytes from whatever st.audio_input() returns.
    Handles:
      - bytes / bytearray         (newer Streamlit returns raw bytes)
      - UploadedFile / BytesIO    (older Streamlit returns file-like)
    """
    if isinstance(audio_bytes, (bytes, bytearray)):
        return bytes(audio_bytes)
    if hasattr(audio_bytes, "seek"):
        audio_bytes.seek(0)
    if hasattr(audio_bytes, "getvalue"):
        return audio_bytes.getvalue()
    if hasattr(audio_bytes, "read"):
        return audio_bytes.read()
    return bytes(audio_bytes)


def _detect_audio_extension(raw: bytes) -> str:
    """
    Detect the real audio container format from magic bytes.
    Browser MediaRecorder typically outputs WebM (Chrome) or OGG (Firefox).
    """
    if len(raw) < 4:
        return "webm"
    if raw[:4] == b"RIFF":
        return "wav"
    if raw[:4] == b"OggS":
        return "ogg"
    if raw[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    if raw[:3] == b"ID3" or (len(raw) >= 2 and raw[0] == 0xFF and raw[1] & 0xE0 == 0xE0):
        return "mp3"
    if raw[:4] == b"fLaC":
        return "flac"
    if len(raw) >= 8 and raw[4:8] in (b"ftyp", b"moov", b"mdat"):
        return "mp4"
    return "webm"


def render_voice_input(
    label: str = "Voice Input",
    key: str = "voice_input",
    button_label: str = "🎤  Hold to Record",
    help_text: str = "Click to activate, then record, then click stop.",
) -> str:
    """
    Renders a large, deliberate microphone activation button.

    Flow:
      1. User sees a prominent "🎤 Activate Microphone" button (hard to miss, hard to accidentally press)
      2. Clicking it reveals the actual audio_input recorder in ACTIVE / RED state
      3. User records, stops, waits for transcription
      4. Result is returned and the recorder resets

    Returns the transcribed string, or "" if nothing recorded.
    """
    _inject_voice_css()

    activate_key = f"_voice_active_{key}"
    result_key   = f"_voice_result_{key}"

    # If we have a pending result from a previous transcription, clear & return it
    if result_key in st.session_state:
        result = st.session_state.pop(result_key)
        return result

    is_active = st.session_state.get(activate_key, False)

    if not is_active:
        # ── BIG UNMISSABLE ACTIVATION BUTTON ──────────────────────────────────
        st.markdown(f"""
        <div class="voice-btn-wrapper">
            <div class="voice-instructions">
                🎤 Voice input available — click the button below to start
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_l, col_btn, col_r = st.columns([1, 2, 1])
        with col_btn:
            if st.button(
                button_label,
                key=f"_voice_activate_btn_{key}",
                use_container_width=True,
                help="Click to activate the microphone recorder. You'll then be able to record and stop.",
            ):
                st.session_state[activate_key] = True
                st.rerun()
        return ""

    else:
        # ── ACTIVE RECORDING STATE — clearly styled ───────────────────────────
        st.markdown("""
        <div class="voice-btn-wrapper">
            <div class="voice-active-indicator">
                <span class="voice-dot"></span>
                MICROPHONE ACTIVE — Record below, then click Stop
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Cancel button — top right so it's accessible but not where you'd accidentally hit it
        cancel_col, _, _ = st.columns([1, 2, 1])
        with cancel_col:
            if st.button("✕ Cancel Recording", key=f"_voice_cancel_{key}"):
                st.session_state[activate_key] = False
                st.rerun()

        st.markdown("""
        <div class="voice-cancel-hint">
            👆 Click "Cancel Recording" above to dismiss the mic without recording
        </div>
        """, unsafe_allow_html=True)

        # The actual audio input — only shown when deliberately activated
        audio_bytes = st.audio_input(
            f"🔴 {label} — Click to record, click again to stop",
            key=f"_voice_recorder_{key}",
        )

        if audio_bytes is not None:
            raw = _read_audio_bytes(audio_bytes)
            if not raw:
                st.warning("⚠️ No audio data received — please try recording again.")
                return ""

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
                        st.success(f"🎙️ Transcribed: *{text}*")
                        # Reset the active state
                        st.session_state[activate_key] = False
                        # Store result to return on next render
                        st.session_state[result_key] = text
                        st.rerun()
                    else:
                        st.warning("⚠️ No speech detected — try speaking louder or closer to the mic.")
                except Exception as e:
                    st.error(f"Transcription error: {e}")
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass

        return ""


def _transcribe_via_subprocess(audio_path: str) -> str:
    """
    Transcribe audio using the venv's whisper CLI via subprocess.
    Falls back to direct Python import if the CLI isn't found.
    """
    out_dir = "/tmp"
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    txt_file = os.path.join(out_dir, base_name + ".txt")

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
            return ""
        except subprocess.TimeoutExpired:
            raise Exception("Transcription timed out — audio may be too long (max ~2 min)")
        except FileNotFoundError:
            pass

    try:
        import whisper  # noqa: F401
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
