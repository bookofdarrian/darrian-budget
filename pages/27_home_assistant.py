"""
Home Assistant Setup Tracker — Page 27
Interactive tracker for Proxmox HA VM setup + smart home device onboarding.
"""
import streamlit as st
from datetime import datetime
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="🏠 Home Assistant Setup — Peach State Savings",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",          icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="✅ Todo",           icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="🎬 Creator",        icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="📝 Notes",          icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="🎵 Media Library",  icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant",icon="🤖")
st.sidebar.page_link("pages/23_home_automation.py",     label="🐱 Home Automation",icon="🐱")
render_sidebar_user_widget()

# ── Constants ──────────────────────────────────────────────────────────────────
WEEK_AT_A_GLANCE = [
    ("Tomorrow",     "🟢", "Set up Petlibro Fountain via app"),
    ("This week",    "🟢", "Start Home Assistant VM on Proxmox"),
    ("Next weekend", "🟡", "Set up Kasa plugs → LIFX bulbs → Reolink cam → SwitchBot blinds → Petlibro feeder"),
    ("Week after",   "🔵", "Connect everything into Home Assistant, build automations"),
]

HA_STEPS = [
    ("Download HA OS image on Proxmox node",     "proxmox_download"),
    ("Create VM: 2 cores, 4 GB RAM, 32 GB disk", "proxmox_vm_create"),
    ("Boot from HA OS image",                     "proxmox_boot"),
    ("Access HA at http://[VM-IP]:8123",          "ha_access"),
    ("Complete onboarding wizard",                "ha_onboarding"),
    ("Install HACS (community store)",            "ha_hacs"),
    ("Add Tailscale integration",                 "ha_tailscale"),
]

DEVICE_STEPS = [
    ("Petlibro Fountain",    "🐱", "petlibro_fountain", "$45", "Set up via Petlibro app, then add HA integration"),
    ("Kasa Smart Plugs",     "💡", "kasa_plugs",         "$40", "Install TP-Link Kasa integration in HA"),
    ("LIFX Bulbs",           "💡", "lifx_bulbs",         "$50", "Install LIFX integration in HA (auto-discovers on LAN)"),
    ("Reolink Camera",       "📷", "reolink_camera",     "$35", "Add RTSP stream to HA, optionally install Frigate NVR"),
    ("SwitchBot Blind Tilt", "🪟", "switchbot_blind",    "$45", "Install SwitchBot hub + HA integration"),
    ("Petlibro Feeder",      "🍽️", "petlibro_feeder",    "$65", "Pair feeder in Petlibro app, add to HA"),
    ("Echo Dot / Alexa",     "🔊", "echo_alexa",         "$0",  "Enable Alexa integration in HA"),
    ("Apple Home",           "🍎", "apple_home",         "$0",  "Enable HomeKit integration in HA"),
]

AUTOMATION_YAML = {
    "Morning Routine": ("☀️", """automation:
  - alias: "Morning routine"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      - service: light.turn_on
        target:
          entity_id: light.bedroom
        data:
          brightness_pct: 30
          transition: 1800
      - service: button.press
        target:
          entity_id: button.cat_feeder_dispense
      - service: switch.turn_on
        target:
          entity_id: switch.coffee_maker_plug"""),

    "Lights at Sunset": ("🌅", """automation:
  - alias: "Dim lights at sunset"
    trigger:
      platform: sun
      event: sunset
      offset: "-00:30:00"
    action:
      service: light.turn_on
      target:
        entity_id: light.living_room
      data:
        brightness_pct: 40
        color_temp: 3000"""),

    "Blinds Auto": ("🪟", """automation:
  - alias: "Open blinds at sunrise"
    trigger:
      platform: sun
      event: sunrise
    action:
      service: cover.open_cover
      target:
        entity_id: cover.bedroom_blinds

  - alias: "Close blinds at sunset"
    trigger:
      platform: sun
      event: sunset
    action:
      service: cover.close_cover
      target:
        entity_id: cover.bedroom_blinds"""),

    "Cat Feeding": ("🐱", """automation:
  - alias: "Cat breakfast"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      service: button.press
      target:
        entity_id: button.cat_feeder_dispense

  - alias: "Cat dinner"
    trigger:
      platform: time
      at: "18:00:00"
    action:
      service: button.press
      target:
        entity_id: button.cat_feeder_dispense"""),

    "Lights Off Midnight": ("🌙", """automation:
  - alias: "Lights off at midnight"
    trigger:
      platform: time
      at: "00:00:00"
    action:
      service: light.turn_off
      target:
        entity_id: all"""),

    "Cat Laser Play": ("🎮", """automation:
  - alias: "Cat play session midday"
    trigger:
      platform: time
      at: "12:00:00"
    action:
      service: switch.turn_on
      target:
        entity_id: switch.cat_laser_plug

  - alias: "Stop laser after 15 min"
    trigger:
      platform: time
      at: "12:15:00"
    action:
      service: switch.turn_off
      target:
        entity_id: switch.cat_laser_plug"""),
}

AI_IDEAS = [
    ("☕ Smart Coffee",
     "Claude reads your Google Calendar (utils/calendar_client.py) and starts "
     "your coffee maker 15 minutes before your first meeting. Early meeting = "
     "earlier coffee. Late start = later coffee."),
    ("🐱 Bored Cat",
     "Frigate detects your cat hasn't moved in 30 minutes → HA triggers the "
     "laser toy for a 15-minute play session automatically."),
    ("🧹 Smart Vacuum",
     "Claude reads your calendar to schedule vacuum runs only when you're out. "
     "Frigate detects cat location → vacuum avoids that room in real-time."),
    ("🌡️ Adaptive Lighting",
     "Install Adaptive Lighting from HACS — automatically adjusts color "
     "temperature based on time of day (circadian rhythm). No code needed."),
    ("🏥 Cat Health",
     "Log litter box usage frequency to Postgres. Claude analyzes weekly "
     "patterns and alerts if usage drops (early UTI detection)."),
]


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _ensure_tables():
    conn = get_conn()
    if USE_POSTGRES:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS ha_setup_progress (
                id       SERIAL PRIMARY KEY,
                step_key TEXT UNIQUE NOT NULL,
                done     BOOLEAN DEFAULT FALSE,
                done_at  TEXT DEFAULT NULL,
                notes    TEXT DEFAULT ''
            )
        """)
    else:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS ha_setup_progress (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                step_key TEXT UNIQUE NOT NULL,
                done     INTEGER DEFAULT 0,
                done_at  TEXT DEFAULT NULL,
                notes    TEXT DEFAULT ''
            )
        """)
    conn.commit()
    conn.close()


def _load_progress() -> dict:
    """Returns {step_key: {done, done_at, notes}}."""
    conn = get_conn()
    c = db_exec(conn, "SELECT step_key, done, done_at, notes FROM ha_setup_progress")
    rows = c.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        result = {r[0]: dict(zip(cols, r)) for r in rows}
    else:
        result = {r["step_key"]: dict(r) for r in rows}
    conn.close()
    return result


def _set_step(step_key: str, done: bool, notes: str = ""):
    conn = get_conn()
    done_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if done else None
    if USE_POSTGRES:
        db_exec(conn, """
            INSERT INTO ha_setup_progress (step_key, done, done_at, notes)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (step_key) DO UPDATE
                SET done=EXCLUDED.done, done_at=EXCLUDED.done_at, notes=EXCLUDED.notes
        """, (step_key, done, done_at, notes))
    else:
        db_exec(conn, """
            INSERT INTO ha_setup_progress (step_key, done, done_at, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(step_key) DO UPDATE
                SET done=excluded.done, done_at=excluded.done_at, notes=excluded.notes
        """, (step_key, 1 if done else 0, done_at, notes))
    conn.commit()
    conn.close()


def _completion_pct(progress: dict, keys: list) -> int:
    if not keys:
        return 0
    done = sum(1 for k in keys if progress.get(k, {}).get("done"))
    return int(done / len(keys) * 100)


# ── Init ───────────────────────────────────────────────────────────────────────
_ensure_tables()
_progress = _load_progress()

# ── Page Header ────────────────────────────────────────────────────────────────
st.title("🏠 Home Assistant Setup Tracker")
st.caption("Track your Proxmox HA VM setup + smart device onboarding — your path to a fully automated home 🐱")

# ── Overview Metrics ──────────────────────────────────────────────────────────
_ha_keys  = [s[1] for s in HA_STEPS]
_dev_keys = [s[2] for s in DEVICE_STEPS]
_all_keys = _ha_keys + _dev_keys
_total_done = sum(1 for k in _all_keys if _progress.get(k, {}).get("done"))

mc1, mc2, mc3, mc4 = st.columns(4)
_ha_done_count = sum(1 for k in _ha_keys if _progress.get(k, {}).get("done"))
mc1.metric("HA VM Steps Done",  f"{_completion_pct(_progress, _ha_keys)}%",
           f"{_ha_done_count}/{len(_ha_keys)}")
_dev_done_count = sum(1 for k in _dev_keys if _progress.get(k, {}).get("done"))
mc2.metric("Devices Connected", f"{_dev_done_count}/{len(_dev_keys)}",
           help="Smart devices added to Home Assistant")
mc3.metric("Overall Progress",  f"{_completion_pct(_progress, _all_keys)}%")
mc4.metric("Steps Remaining",   len(_all_keys) - _total_done)

st.progress(_completion_pct(_progress, _all_keys) / 100)
st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📅 Week at a Glance",
    "🖥️ HA VM Setup",
    "📱 Device Onboarding",
    "⚙️ Automations",
    "🏗️ Architecture",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Week at a Glance
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("📅 Your Week-At-A-Glance")
    st.info("Hardware is arriving — here's what to do and when. Track each step in the other tabs.")

    for day, icon, task in WEEK_AT_A_GLANCE:
        c1, c2 = st.columns([1, 4])
        c1.markdown(f"**{day}**")
        c2.markdown(f"{icon} {task}")
    st.divider()

    st.subheader("🚀 Quick-Start: Home Assistant on Proxmox")
    st.markdown("""
This is a **2-hour project** that unlocks tying everything together:
- Kasa, Petlibro, LIFX, Reolink, SwitchBot — all in **one dashboard** instead of 5 separate apps
- Echo Dot and Apple Home both sync in automatically
- Build automations: morning routine, cat feeding, blind schedules, vacuum scheduling
    """)
    st.code(
        "# On your Proxmox node — download HA OS image\n"
        "# Create VM: 2 cores, 4GB RAM, 32GB disk\n"
        "# Boot from HA OS image\n"
        "# Access at http://[VM-IP]:8123",
        language="bash",
    )

    st.subheader("💰 Cost Summary")
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Starter Kit (Now)",       "~$300",         help="Portable devices that move with you")
    cc2.metric("After Move (Permanent)",  "~$1,000–1,500", help="Roborock + blinds + litter box")
    cc3.metric("HA Software",             "$0",            help="Runs free on your existing Beelink homelab")

    with st.expander("📦 Buy-Now Shopping List"):
        st.markdown("""
| Item | Price | Priority |
|------|-------|----------|
| 4× Kasa EP25 Smart Plugs | ~$40 | 🔴 High |
| Petlibro Granary Wi-Fi Feeder | ~$65 | 🔴 High |
| Petlibro Granary Wi-Fi Fountain | ~$45 | 🔴 High |
| Reolink E1 Pro Camera | ~$35 | 🔴 High |
| SwitchBot Blind Tilt (1 window) | ~$45 | 🟡 Medium |
| 2× LIFX A19 Color Bulbs | ~$50 | 🟡 Medium |
| PetSafe Bolt Laser | ~$20 | 🟢 Low |
| **Total** | **~$300** | |
        """)

    with st.expander("⏳ Buy After Moving"):
        st.markdown("""
| Item | Price | Notes |
|------|-------|-------|
| Roborock Q5 Pro | ~$350 | Know your floor plan first |
| IKEA FYRTUR Blinds | $130–$180/window | Measure new windows |
| Petlibro Capsule Litter Box | ~$200 | Know where it'll live |
| Litter-Robot 4 (upgrade) | ~$700 | Best long-term investment |
| Smart thermostat (Ecobee) | ~$180 | Check if landlord allows |
        """)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — HA VM Setup
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("🖥️ Home Assistant VM Setup on Proxmox")
    st.markdown("Check off each step as you complete it. Progress is saved to the database.")

    _ha_pct = _completion_pct(_progress, _ha_keys)
    st.progress(_ha_pct / 100, text=f"HA VM Setup: {_ha_pct}% complete")
    st.markdown("")

    for _label, _key in HA_STEPS:
        _prog    = _progress.get(_key, {})
        _is_done = bool(_prog.get("done"))
        col_chk, col_lbl, col_when = st.columns([0.5, 6, 2.5])
        _new_val = col_chk.checkbox("", value=_is_done, key=f"ha_{_key}",
                                    label_visibility="collapsed")
        if _new_val and not _is_done:
            _set_step(_key, True)
            st.rerun()
        elif not _new_val and _is_done:
            _set_step(_key, False)
            st.rerun()
        _style = "~~" if _is_done else "**"
        col_lbl.markdown(f"{_style}{_label}{_style}")
        if _is_done and _prog.get("done_at"):
            col_when.caption(f"✅ {str(_prog['done_at'])[:10]}")

    st.divider()
    st.subheader("📖 Setup Reference")

    with st.expander("Step 1 — Download Home Assistant OS Image"):
        st.markdown("""
1. Go to [home-assistant.io/installation/alternative](https://www.home-assistant.io/installation/alternative/)
2. Download the **KVM/Proxmox (.qcow2)** image
3. Transfer to Proxmox: `scp haos_ova-*.qcow2 root@[PROXMOX-IP]:/var/lib/vz/images/`
        """)
        st.code(
            "# Or wget directly on Proxmox shell:\n"
            "wget https://github.com/home-assistant/operating-system/releases/"
            "latest/download/haos_ova-12.3.qcow2.xz",
            language="bash",
        )

    with st.expander("Step 2 — Create the VM in Proxmox"):
        st.code("""# Proxmox shell — create VM (ID 200)
qm create 200 --name homeassistant --memory 4096 --cores 2 --net0 virtio,bridge=vmbr0
qm importdisk 200 haos_ova-*.qcow2 local-lvm
qm set 200 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-200-disk-0
qm set 200 --boot c --bootdisk scsi0
qm set 200 --serial0 socket --vga serial0
qm resize 200 scsi0 32G
qm start 200""", language="bash")

    with st.expander("Step 3 — Access Home Assistant"):
        st.markdown("""
1. Check Proxmox console for the HA IP address (or check your router DHCP table)
2. Open `http://[VM-IP]:8123` in your browser
3. Complete the onboarding wizard (create user, name your home, set location)
4. Install the **Tailscale add-on** from the HA add-on store for remote access
        """)

    with st.expander("Step 4 — Install HACS (Community Store)"):
        st.code("""# In HA → Settings → Add-ons → SSH & Web Terminal → Open Web UI:
wget -O - https://get.hacs.xyz | bash -
# Then restart HA, and add HACS from Settings → Integrations""", language="bash")
        st.markdown(
            "HACS gives you **Adaptive Lighting**, **Petlibro**, and hundreds of "
            "community integrations not in the official store."
        )

    with st.expander("Proxmox Architecture"):
        st.code("""Beelink (Proxmox)
  ├── CT100 (Docker)
  │     ├── Frigate NVR (cat AI)
  │     └── Budget App (peachstatesavings.com)
  └── VM200 — Home Assistant OS
        ├── Kasa Plugs  (local TCP)
        ├── LIFX Bulbs  (LAN UDP)
        ├── SwitchBot Blinds
        ├── Petlibro Feeder + Fountain
        ├── Reolink Camera → Frigate NVR
        ├── Echo Dot (Alexa)
        └── Apple Home (HomeKit)""", language="text")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Device Onboarding
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📱 Smart Device Onboarding")
    st.markdown("Track each device as you add it to Home Assistant. Check the box when it's live in HA.")

    _dev_pct = _completion_pct(_progress, _dev_keys)
    st.progress(
        _dev_pct / 100,
        text=f"Devices Connected: {_dev_pct}% ({_dev_done_count}/{len(_dev_keys)})",
    )
    st.markdown("")

    for _name, _emoji, _key, _price, _tip in DEVICE_STEPS:
        _prog    = _progress.get(_key, {})
        _is_done = bool(_prog.get("done"))
        with st.container():
            c1, c2, c3, c4 = st.columns([0.5, 3, 5, 1.5])
            _new_val = c1.checkbox("", value=_is_done, key=f"dev_{_key}",
                                   label_visibility="collapsed")
            if _new_val and not _is_done:
                _set_step(_key, True)
                st.rerun()
            elif not _new_val and _is_done:
                _set_step(_key, False)
                st.rerun()
            _lbl = (f"~~{_emoji} {_name}~~ ({_price})" if _is_done
                    else f"**{_emoji} {_name}** ({_price})")
            c2.markdown(_lbl)
            c3.caption(_tip)
            if _is_done and _prog.get("done_at"):
                c4.caption(f"✅ {str(_prog['done_at'])[:10]}")
            else:
                c4.caption("⏳ Pending")

    st.divider()
    st.subheader("📖 Integration Notes")

    with st.expander("🐱 Petlibro (Feeder + Fountain)"):
        st.markdown("""
1. Pair devices in the **Petlibro app** first
2. HA → Settings → Integrations → Add → search **Petlibro**
3. If not listed natively, use HACS to install the community Petlibro integration
4. Entities: feeding schedule buttons, bowl sensor, fountain flow control
        """)

    with st.expander("💡 Kasa Smart Plugs"):
        st.markdown("""
1. Pair plugs in the **Kasa (TP-Link) app** first
2. HA → Settings → Integrations → Add → **TP-Link Kasa Smart**
3. Auto-discovers all Kasa devices on your LAN — no cloud required
        """)

    with st.expander("💡 LIFX Bulbs"):
        st.markdown("""
1. Pair bulbs in the **LIFX app** first
2. HA → Settings → Integrations → Add → **LIFX**
3. Bulbs auto-discover on LAN (no hub needed), full RGB + color temp control
        """)

    with st.expander("📷 Reolink Camera"):
        st.markdown("""
1. Set up camera in **Reolink app**, note the local IP
2. HA → Settings → Integrations → Add → **Reolink**
3. Enter camera IP, username, password → RTSP stream, no cloud, no subscription
4. Optionally add **Frigate NVR** on CT100 for AI cat detection
        """)

    with st.expander("🪟 SwitchBot Blind Tilt"):
        st.markdown("""
1. Pair in **SwitchBot app**, set up SwitchBot Hub Mini
2. HA → Settings → Integrations → Add → **SwitchBot**
3. Entities: open/close/tilt position control
        """)

    with st.expander("🔊 Echo Dot / Alexa"):
        st.markdown("""
1. HA → Settings → Integrations → Add → **Amazon Alexa**
2. Easiest: **Nabu Casa** cloud ($6.50/month) — instant Alexa + Google Home sync
3. Free alternative: **emulated_hue** in configuration.yaml (local, no subscription)
        """)

    with st.expander("🍎 Apple Home (HomeKit)"):
        st.markdown("""
1. HA → Settings → Integrations → Add → **HomeKit**
2. Scan the QR code with your iPhone → HA becomes a HomeKit hub
3. All HA devices appear in Apple Home and respond to Siri — 100% local
        """)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Automations
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("⚙️ Automation Templates")
    st.markdown(
        "Copy these YAML snippets into HA → Settings → Automations → ⋮ → Edit in YAML"
    )

    for _name, (_icon, _yaml) in AUTOMATION_YAML.items():
        with st.expander(f"{_icon} {_name}"):
            st.code(_yaml, language="yaml")

    st.divider()
    st.subheader("🤖 AI-Powered Automation Ideas")
    st.info(
        "These use your existing Claude API key + Google Calendar integration "
        "already built into the budget app."
    )
    for _title, _desc in AI_IDEAS:
        with st.expander(_title):
            st.write(_desc)

    st.divider()
    st.subheader("📅 Automation Roadmap")
    _phases = [
        ("Week 1 — Foundation",  "🟢", "Light on/off schedules · Cat feeding times · Blinds sunrise/sunset"),
        ("Week 2 — Cat Basics",  "🟢", "Feeder + fountain automation · Camera alerts · Laser play sessions"),
        ("Week 3 — Comfort",     "🟡", "Morning routine (coffee + lights + blinds) · Vacuum schedule · Presence detection"),
        ("Month 2 — AI Layer",   "🔵", "Calendar-aware automations · Adaptive Lighting · Cat health dashboard"),
        ("After Move",           "⚪", "Multi-room vacuum maps · Full camera coverage · Litter-Robot health tracking"),
    ]
    for _phase, _icon, _details in _phases:
        ci, cp, cd = st.columns([0.3, 1.8, 5])
        ci.markdown(_icon)
        cp.markdown(f"**{_phase}**")
        cd.markdown(_details)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Architecture
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("🏗️ Full Integration Architecture")
    st.code("""Your Homelab (Beelink @ 100.95.125.112)
  │
  ├── CT100 (Docker)
  │     ├── Budget App → peachstatesavings.com
  │     ├── Frigate NVR (cat AI detection)
  │     │     ├── Reolink E1 Pro (RTSP stream)
  │     │     ├── Motion clips → local storage
  │     │     └── Cat zone detection → triggers HA
  │     └── Nginx (reverse proxy)
  │
  ├── VM200 — Home Assistant OS
  │     ├── Kasa Smart Plugs (local TCP API)
  │     ├── LIFX Bulbs (LAN UDP auto-discover)
  │     ├── SwitchBot Blind Tilt (SwitchBot Hub)
  │     ├── Petlibro Feeder (Wi-Fi)
  │     ├── Petlibro Fountain (Wi-Fi)
  │     ├── Reolink Camera (RTSP local)
  │     ├── Echo Dot → Alexa integration
  │     ├── Apple Home → HomeKit bridge
  │     └── Tailscale → remote access from iPhone
  │
  └── Tailscale VPN
        └── Access HA at http://homeassistant:8123 from anywhere""", language="text")

    st.divider()
    cl, cr = st.columns(2)

    with cl:
        st.subheader("🔑 Local-First Principle")
        st.markdown("""
Every device recommendation uses **local API access** — not cloud dependency:

| Device | Protocol | Cloud Required? |
|--------|----------|----------------|
| Kasa Plugs | Local TCP | ❌ No |
| LIFX Bulbs | LAN UDP | ❌ No |
| Reolink Camera | RTSP | ❌ No |
| Roborock Vacuum | Local API | ❌ No |
| Home Assistant | 100% local | ❌ No |
| Frigate NVR | Local | ❌ No |
| SwitchBot | Hub required | ⚠️ Hub needed |

**Your home automation works even if the internet is down.**
        """)

    with cr:
        st.subheader("📡 Network Setup Notes")
        st.markdown("""
**Recommended:**
- Put IoT devices on a separate VLAN (isolates from main LAN)
- Home Assistant on IoT VLAN with firewall rules
- Tailscale on HA → no port forwarding needed
- Static DHCP lease for HA's IP in your router

**Proxmox VM networking:**
- VM gets its own IP on `vmbr0` (your home bridge)
- HA auto-discovers LAN devices via mDNS
- Use VM ID 200 so it doesn't conflict with CT100
        """)

    st.divider()
    st.subheader("📊 Cat Health Dashboard (Coming Soon)")
    st.info(
        "Once Home Assistant is running, add `HA_TOKEN` to your `.env` file. "
        "This page will pull live data from the HA API and show real-time cat metrics."
    )
    dm1, dm2, dm3, dm4 = st.columns(4)
    dm1.metric("🍽️ Last Fed",       "—", help="From Petlibro feeder via HA API")
    dm2.metric("💧 Fountain",        "—", help="From Petlibro fountain via HA API")
    dm3.metric("🚽 Last Litter Use", "—", help="From Litter-Robot / Petlibro via HA API")
    dm4.metric("📷 Cat Detected",    "—", help="From Frigate NVR via HA API")
    st.caption("Connect Home Assistant → add HA_TOKEN to .env → metrics will populate automatically")
