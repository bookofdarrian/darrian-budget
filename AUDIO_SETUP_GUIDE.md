# Ultimate Audio Setup — Darrian Belcher / Peach State Savings
**Owner: Darrian Belcher | Created: 2026-02-28**

> You have two powerful but underused smart speakers — an **Apple HomePod Mini**
> (hackathon win) and an **Amazon Echo Dot** (gift from mom) — plus a JBL Xtreme 3,
> a Bluedee desktop speaker, a Samsung Smart TV, and your phone.
>
> This guide turns that collection into a **multi-room, AI-powered audio system**
> with your own custom Jarvis voice, voice-to-text in all your homelab apps,
> automated playlists, and cat dinner sounds. Built in phases so you can
> start today with what you have.

---

## 🎯 What You're Building (End State)

```
YOUR AUDIO ECOSYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HomePod Mini          → Bedroom / Apple Music hub + Siri Shortcuts
  Echo Dot              → Kitchen / Living Room + Alexa Routines
  JBL Xtreme 3          → Portable + outdoor / Bluetooth from phone
  Bluedee Desktop       → Desk setup / wired/BT to Mac
  Samsung Smart TV      → Main audio anchor for movies/TV
  iPhone                → Mobile remote control for everything
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Home Assistant (CT100) orchestrates ALL automations:
    → Morning playlist triggers at wake time
    → Evening playlist at sunset
    → Cat dinner chime at feeding times
    → Voice commands via Echo Dot → Home Assistant
    → Custom Jarvis TTS responses from your homelab

  Streamlit Apps (peachstatesavings.com):
    → Whisper voice-to-text button on every page
    → Speak notes, expenses, todos hands-free
    → AI responses read aloud via TTS
```

---

## 🗂️ Your Current Hardware Inventory

| Device | Type | Status | Best Use |
|--------|------|--------|----------|
| **Apple HomePod Mini** | Smart Speaker | Underused — activate it! | Bedroom music + Apple ecosystem |
| **Amazon Echo Dot** | Smart Speaker | Underused — activate it! | Voice control hub + Alexa routines |
| **JBL Xtreme 3** | Portable BT Speaker | In use | Portable / outdoor / party mode |
| **Bluedee Desktop Speaker** | Desktop BT/Wired | In use | Work desk audio |
| **Samsung Smart TV** | Smart TV | In use | Main room audio anchor |
| **iPhone** | Mobile | In use | Remote control for everything |

**Bottom line:** You already have a multi-room audio setup. You just haven't
connected it yet. The HomePod Mini and Echo Dot are the two missing pieces
that unlock the whole ecosystem.

---

## 📋 PHASE 1 — Activate What You Have (This Week, $0)

### Step 1: Set Up the HomePod Mini Properly

The HomePod Mini has been sitting unused. Wake it up tonight:

```
iPhone → Home app → Add Accessory → Scan HomePod Mini bottom
→ Assign to a room (Bedroom recommended)
→ Sign in with your Apple ID
→ Enable: Personal Requests (so Siri can access your calendar, reminders, etc.)
→ Enable: Recognize My Voice
```

**What the HomePod Mini unlocks for you:**
- Plays Apple Music playlists on schedule via Shortcuts automations
- Acts as a Thread/Matter smart home hub (future-proofs all smart home gear)
- Intercom to your phone ("Hey Siri, announce dinner's ready")
- Plays custom sounds and chimes via Shortcuts (cat dinner!)
- AirPlay target for your Mac, iPhone, or TV audio

**HomePod Mini — Morning Playlist Shortcut:**
```
Shortcuts app → Automation → New Automation → Time of Day → 7:00 AM
Action: "Play playlist" → select your morning playlist
Device: HomePod Mini (Kitchen)
Run: Automatically (no confirmation needed)
```

**HomePod Mini — Cat Dinner Chime:**
```
Shortcuts app → Automation → New Automation → Time of Day → 6:00 PM
Action 1: "Play sound" → pick a fun chime or a custom .m4a file
Action 2: "Speak" → "Dinner time for the cats!"
Device: HomePod Mini (Kitchen)
```

---

### Step 2: Set Up the Echo Dot Properly

```
Alexa app → Devices → Add Device → Amazon Echo → Echo Dot
→ Connect to your WiFi
→ Place in the living room / couch area (your main hangout zone)
→ Wake word options: "Alexa", "Computer", or "Echo"
```

**Echo Dot becomes your voice control hub for the whole apartment.**

**Alexa Routines to create right now (Alexa app → More → Routines):**

```
Routine: "Good Morning"
  Trigger: Say "Alexa, good morning"
  Actions:
    1. Flash Briefing (weather + news)
    2. Smart Home: Turn on morning lights
    3. Media: Play morning playlist on Echo Dot
    4. HA Webhook: Fire morning automation (when HA is set up)

Routine: "Cat Dinner" (TIME-BASED)
  Trigger: 6:00 PM every day
  Actions:
    1. Announcement: "Dinner time! Your cats are hungry."
    2. Play sound: Pick from Alexa soundboard (animal sounds)
    3. (Later) HA Webhook: Trigger Petlibro feeder dispense

Routine: "Goodnight"
  Trigger: Say "Alexa, goodnight"
  Actions:
    1. Smart Home: Turn off all lights
    2. Media: Play evening/sleep playlist at 20% volume
    3. Announcement: "Goodnight Darrian. Sleep well."
```

---

### Step 3: Connect Both Speakers to Home Assistant

Home Assistant is the brain that ties HomePod + Echo Dot + lights + feeder together.

**Install these HA integrations (Settings → Integrations → Add Integration):**

```
1. "Apple TV / HomePod" → makes HomePod Mini a media_player entity
2. "Alexa Media Player" (via HACS) → full control of Echo Dot from HA
3. "Music Assistant" (via HACS) → unified music playback to any speaker
```

**Music Assistant** is the key — it lets Home Assistant send music to ANY
speaker (HomePod, Echo Dot, Chromecast, TV) from one interface with one command.

```yaml
# After Music Assistant is installed — unified morning playlist:
automation:
  - alias: "Morning Playlist — All Speakers"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      service: music_assistant.play_media
      data:
        entity_id:
          - media_player.homepod_mini_bedroom
          - media_player.echo_dot_kitchen
        media_id: "playlist:Morning Vibes"
        media_type: playlist

  - alias: "Evening Wind-Down Playlist"
    trigger:
      platform: sun
      event: sunset
    action:
      service: music_assistant.play_media
      data:
        entity_id: media_player.echo_dot_living_room
        media_id: "playlist:Evening Wind Down"
        media_type: playlist
        volume: 30

  - alias: "Cat Dinner Sound + Feeder"
    trigger:
      platform: time
      at: "18:00:00"
    action:
      - service: tts.speak
        data:
          entity_id: media_player.echo_dot_kitchen
          message: "Dinner time! Time to feed the cats."
      - service: button.press
        target:
          entity_id: button.cat_feeder_dispense
```

---

## 📋 PHASE 2 — Your Custom Jarvis Voice ($0–$5/mo, 1-2 Weekends)

This is where it gets fun. You're building a custom AI voice assistant
that lives on YOUR homelab — not Amazon's or Apple's cloud.

### The Architecture

```
You speak → Whisper (STT) → Claude API → Custom TTS Voice → Speaker
                ↓                               ↑
            Your homelab                ElevenLabs or Piper TTS
               (CT100)                  (custom "Jarvis" voice)
```

---

### Option A: Piper TTS via Home Assistant (FREE, Easiest, Start Here)

Piper is the official HA local TTS engine. Runs 100% on your homelab, zero cost.

```
Home Assistant → Settings → Add-ons → Add-on Store → Search "Piper"
→ Install → Start → Configuration:
  voice: en_US-ryan-high   # Deep male American voice — sounds great
```

Use in automations:
```yaml
action:
  service: tts.speak
  data:
    entity_id: media_player.echo_dot_kitchen
    message: "Good morning Darrian. You have 3 meetings today."
    options:
      voice: en_US-ryan-high
```

**Best Piper voices for the "Jarvis" effect:**
- `en_US-ryan-high` — American, authoritative, clear
- `en_GB-alan-medium` — British accent (classic movie Jarvis)
- `en_GB-cori-high` — British, very crisp and precise

---

### Option B: ElevenLabs Custom Voice (~$5/mo, Best Quality)

ElevenLabs lets you choose from premium AI voices or clone your own voice
from a 3-5 minute recording. The clone option is wild — your homelab
responds in YOUR voice.

```python
# utils/tts_client.py — add to your homelab utils

import requests
from utils.db import get_setting

def speak_as_jarvis(text: str, output_path: str = "/tmp/jarvis_response.mp3"):
    api_key = get_setting("elevenlabs_api_key")
    voice_id = get_setting("elevenlabs_voice_id")  # set in app_settings DB

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    body = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.75,
            "similarity_boost": 0.85
        }
    }
    response = requests.post(url, json=body, headers=headers)
    with open(output_path, "wb") as f:
        f.write(response.content)
    return output_path
```

**ElevenLabs Pricing:**
- Free: 10,000 chars/month — enough for testing and light use
- Starter ($5/mo): 30,000 chars/month
- Creator ($22/mo): 100,000 chars/month + instant voice cloning

**Voice cloning setup:** Record yourself narrating for 3-5 minutes
(read an article, describe your day) → upload to ElevenLabs → done.
Your homelab now speaks in your voice. Very Iron Man.

---

### Option C: Coqui TTS (Free, Fully Local, No API)

100% free, runs entirely on CT100, no internet needed for TTS.

```bash
# Install on CT100:
pip install TTS

# Test it:
tts --text "Good morning Darrian. Your portfolio is up 2.3 percent today." \
    --model_name "tts_models/en/vctk/vits" \
    --speaker_idx "p273" \
    --out_path /tmp/jarvis.wav

# Good speaker IDs for deep/authoritative voices: p260, p273, p302
```

---

### Jarvis Personality Layer (Claude API)

Wire Claude into the voice pipeline so responses feel like a real assistant:

```python
# aura/jarvis.py — runs as a service on CT100

from anthropic import Anthropic
from utils.db import get_setting

client = Anthropic(api_key=get_setting("anthropic_api_key"))

JARVIS_SYSTEM_PROMPT = """You are JARVIS, the personal AI assistant for Darrian Belcher.
You are helpful, precise, and occasionally witty — like Tony Stark's AI.
You know about Darrian's finances, home lab, content creation, and cats.
Keep all responses under 2 sentences for voice output. Be direct. No fluff.
Always address him as "Darrian" or occasionally "sir" for fun."""

def ask_jarvis(user_query: str, context: str = "") -> str:
    messages = []
    if context:
        messages.append({"role": "user", "content": f"Context: {context}"})
        messages.append({"role": "assistant", "content": "Understood."})
    messages.append({"role": "user", "content": user_query})

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=150,
        system=JARVIS_SYSTEM_PROMPT,
        messages=messages
    )
    return response.content[0].text
```

---

## 📋 PHASE 3 — Voice-to-Text in ALL Homelab Apps ($0, 2-3 Weekends)

Every page on peachstatesavings.com gets a microphone button.
Speak a thought → transcribed → Claude processes it. No typing required.

### The Reusable Component: `utils/voice_input.py`

```python
# utils/voice_input.py
# Drop this into any Streamlit page with 2 lines of code
# Uses st.audio_input() (built into Streamlit 1.27+) + local Whisper

import streamlit as st
import tempfile
import os


def render_voice_input(
    label: str = "🎤 Speak",
    key: str = "voice_input"
) -> str:
    """
    Renders a voice input widget. Returns transcribed text or empty string.

    Usage in any page:
        from utils.voice_input import render_voice_input
        text = render_voice_input(label="Speak a note", key="notes_voice")
        if text:
            st.session_state.note_content = text
    """
    audio_bytes = st.audio_input(label, key=key)

    if audio_bytes:
        with st.spinner("Transcribing..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(audio_bytes.read())
                tmp_path = f.name
            try:
                text = _transcribe_whisper(tmp_path)
                st.success(f"Heard: *{text}*")
                return text
            finally:
                os.unlink(tmp_path)

    return ""


def _transcribe_whisper(audio_path: str) -> str:
    """Transcribe audio using local Whisper (runs on Mac or CT100)."""
    import whisper  # pip install openai-whisper

    model = whisper.load_model("base")  # base = fast, good accuracy
    result = model.transcribe(audio_path)
    return result["text"].strip()
```

### Plug Into Every Page (2 Lines of Code)

```python
# Any page — example for pages/25_notes.py:
from utils.voice_input import render_voice_input

# In your UI:
voice_text = render_voice_input(label="🎤 Speak your note", key="notes_voice")
if voice_text:
    st.session_state.new_note_content = voice_text
```

### Priority Rollout Order

| Page | Voice Feature | Why It Matters |
|------|---------------|----------------|
| `25_notes.py` | Speak a note → saves automatically | Fastest thought capture |
| `22_todo.py` | Speak a task → adds to list | Hands-free task entry |
| `17_personal_assistant.py` | Full voice chat with Jarvis | Core use case |
| `1_expenses.py` | "Spent $45 on groceries" → logs it | Fastest expense logging |
| `24_creator_companion.py` | Speak content ideas → saved to DB | Creative flow |
| `7_ai_insights.py` | Ask finance questions by voice | Voice financial advisor |

---

## 📋 PHASE 4 — Multi-Room Expansion (~$20–50, Optional)

Once Phase 1-3 are solid, expand your physical audio coverage:

### Where Each Speaker Lives

```
KITCHEN (your main zone — where the action happens)
    HomePod Mini
    → Morning playlist at 7:00 AM while you make breakfast
    → Cat dinner announcement + chime at 6:00 PM
    → Always-on Siri for quick questions while cooking
    → AirPlay target from iPhone or Mac

LIVING ROOM / COUCH (your actual sleep + chill zone)
    Echo Dot
    → "Alexa, goodnight" routine when you crash on the couch
    → Evening/sleep playlist at low volume
    → Voice control for lights when you don't want to get up
    → Jarvis morning briefing from the couch

DESK / OFFICE
    Bluedee Desktop Speaker
    → Work/focus music (lofi, instrumental)
    → Jarvis task notifications while working
    → Mac audio output via Bluetooth

MAIN ROOM
    Samsung Smart TV
    → Movies and TV
    → AirPlay from iPhone/Mac when needed
    → Can receive HA TTS announcements via AirPlay

PORTABLE / OUTDOOR
    JBL Xtreme 3
    → Balcony, outdoors, travel, parties
    → Connect from iPhone Spotify or Apple Music
    → Loudest speaker you own — use it for gatherings

BEDROOM (sleep only — keep it simple)
    No dedicated speaker needed
    → iPhone plays sleep sounds / white noise if needed
    → HomePod Mini in kitchen handles any Siri requests
    → Keep it dark and quiet — dedicated sleep zone
```

### Make Bluedee Smart: Snapcast (Free, Self-Hosted)

Snapcast turns ANY speaker into a synchronized multi-room audio node —
like Sonos, but running on your homelab for free:

```bash
# On CT100 — run Snapcast server:
docker run -d --name snapserver \
  -p 1704:1704 -p 1705:1705 \
  -v /opt/snapcast:/etc/snapcast \
  ghcr.io/badaix/snapcast:latest snapserver

# On a $15 Raspberry Pi Zero 2W connected to Bluedee via aux:
sudo apt install snapclient
snapclient -h [CT100-IP]

# Result: HomePod + Echo Dot + Bluedee all play the SAME music in sync
# Control all zones from Home Assistant Snapcast integration
```

### Alternative: Chromecast Audio ($20–35, Used)

If Raspberry Pi feels like too much setup:
- Chromecast Audio plugs into the 3.5mm jack on Bluedee
- Google Cast protocol — Home Assistant controls it natively
- Available on eBay/Facebook Marketplace for $20–35

---

## 📋 PHASE 5 — Full Jarvis Morning Experience (Ongoing)

The end goal: wake up to music, lights slowly coming on, then Jarvis
briefs you on your day using real data from your budget app.

### Complete Morning Routine Automation

```yaml
automation:
  - alias: "Jarvis Full Morning Briefing"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      # 1. Bedroom lights fade in slowly (sunrise simulation)
      - service: light.turn_on
        data:
          entity_id: light.bedroom
          brightness_pct: 15
          transition: 600  # 10 minute fade-in

      # 2. Morning playlist on HomePod in kitchen at low volume
      - service: music_assistant.play_media
        data:
          entity_id: media_player.homepod_mini_kitchen
          media_id: "playlist:Morning Vibes"
          volume: 20

      # 3. After 10 minutes, Jarvis speaks the daily briefing
      - delay: "00:10:00"

      - service: tts.speak
        data:
          entity_id: media_player.echo_dot_kitchen
          message: >
            Good morning, Darrian. It's {{ now().strftime('%A, %B %-d') }}.
            You have {{ states('sensor.calendar_events_today') }} events today.
            Your portfolio is {{ states('sensor.portfolio_daily_change') }}.
            The cats were last fed at {{ states('sensor.last_cat_feeding') }}.
          options:
            voice: en_GB-alan-medium  # British Jarvis voice via Piper
```

### Cat Dinner Full Routine

```yaml
automation:
  - alias: "Cat Dinner Full Routine"
    trigger:
      platform: time
      at: "18:00:00"
    action:
      # Play a chime first
      - service: media_player.play_media
        data:
          entity_id: media_player.echo_dot_kitchen
          media_content_id: "https://100.95.125.112/static/cat_dinner_chime.mp3"
          media_content_type: "music"

      - delay: "00:00:04"

      # Jarvis announcement
      - service: tts.speak
        data:
          entity_id: media_player.echo_dot_kitchen
          message: "Dinner time! Feeding the cats now."

      # Trigger the smart feeder
      - service: button.press
        target:
          entity_id: button.cat_feeder_dispense
```

### Full Voice Chat with Jarvis in Personal Assistant Page

```python
# In pages/17_personal_assistant.py
from utils.voice_input import render_voice_input
from utils.db import get_setting
from aura.jarvis import ask_jarvis

def render_voice_chat():
    st.subheader("🎤 Talk to Jarvis")
    st.caption("Ask anything — finances, todos, calendar, home status")

    voice_text = render_voice_input(
        label="Tap to speak...",
        key="jarvis_voice"
    )

    if voice_text:
        api_key = get_setting("anthropic_api_key")
        if not api_key:
            st.error("No API key configured.")
            return

        with st.spinner("Jarvis is thinking..."):
            response = ask_jarvis(voice_text)

        st.info(f"**Jarvis:** {response}")

        # Optional: speak it back (requires Piper TTS via HA webhook)
        # trigger_ha_tts(response)
```

---

## 💰 Phase Cost Summary

| Phase | What | Cost | Time Estimate |
|-------|------|------|---------------|
| **Phase 1** | Activate HomePod + Echo Dot + HA automations | **$0** | 1 weekend |
| **Phase 2** | Jarvis voice (Piper local = free / ElevenLabs = $5/mo) | **$0–$5/mo** | 1 weekend |
| **Phase 3** | Voice-to-text on all homelab apps (Whisper) | **$0** | 2 weekends |
| **Phase 4** | Multi-room Snapcast or Chromecast expansion | **$20–$50** | 1 weekend |
| **Phase 5** | Full morning briefing + advanced automations | **$0** | Ongoing |
| **TOTAL** | Complete Jarvis audio ecosystem | **$20–$100** | ~5 weekends |

---

## 🛒 The Only Hardware You Need to Buy

You already own everything for Phase 1-3. The only potential purchases:

| Item | Price | Purpose |
|------|-------|---------|
| Raspberry Pi Zero 2W | $15 | Snapcast node for Bluedee desktop speaker |
| Chromecast Audio (used) | $20–35 | Alternative to Pi — simpler setup |
| USB Microphone (optional) | $15–30 | If you want desktop voice input without phone |
| **Total new spending** | **$0–$80** | Everything else is already owned |

---

## ⚡ Quick Wins — Do These Tonight

1. **30 min — HomePod Mini:** Open the Home app. Add it. Create ONE Shortcut
   automation: morning playlist at 7 AM. Test it. Done.

2. **30 min — Echo Dot:** Open the Alexa app. Add the device. Create ONE Routine:
   cat dinner announcement at 6 PM. Test it. Done.

3. **This weekend:** Install Music Assistant in Home Assistant via HACS.
   Wire up morning and evening playlist automations across both speakers.

4. **Next weekend:** Add `render_voice_input()` to `pages/25_notes.py` and
   `pages/22_todo.py`. Install `openai-whisper` via pip. Test speaking a note.

5. **After that:** Install Piper TTS add-on in Home Assistant. Build the
   Jarvis morning briefing automation. Wake up like Tony Stark.

---

## 🔗 Integration Map — How This Connects to Your Homelab

| Component | Role in Audio Ecosystem |
|-----------|------------------------|
| **Home Assistant** | Master automation controller for all speakers |
| **Music Assistant (HACS)** | Unified music playback to HomePod + Echo Dot |
| **Piper TTS (HA add-on)** | Local Jarvis voice — $0, runs on CT100 |
| **ElevenLabs API** | Premium voice quality / voice cloning (optional) |
| **Whisper (local)** | Speech-to-text for all Streamlit pages |
| **Claude API (claude-opus-4-5)** | Jarvis intelligence — answers questions |
| **Frigate + cat cameras** | Trigger sounds when cat detected |
| **Petlibro feeder** | Cat dinner automation target |
| **Tailscale VPN** | Control all audio from your phone anywhere |
| **CT100 homelab** | Runs everything — HA, Whisper, Piper, Snapcast |

---

## 📦 pip Packages to Add

```bash
# Add to requirements.txt for voice-to-text support:
openai-whisper>=20231117        # Local speech recognition (Whisper base model)
# st.audio_input() is built into Streamlit 1.27+ — no extra package needed

# Optional — if using ElevenLabs instead of Piper:
elevenlabs>=1.0.0               # ElevenLabs TTS Python SDK
```

---

*Integrates with: HOME_CAT_AUTOMATION.md, AURA_HARDWARE_GUIDE.md, HOMELAB_USECASES.md*

*Suggested next page to build: `pages/27_voice_assistant.py` — dedicated Jarvis interface
with full voice input/output, chat history, and home status dashboard.*
