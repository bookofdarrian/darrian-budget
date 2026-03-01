"""
Connect Everything Wizard — Page 28
Guided step-by-step wizard to connect HomePod + Echo Dot + all future smart devices.
Starting point: HomePod (Apple Home) + Echo Dot (Alexa) already on iPhone 16 Pro Max.
"""
import streamlit as st
from datetime import datetime
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="Connect Everything — Peach State Savings",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",          icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="Todo",              icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="Creator",           icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="Notes",             icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="Media Library",     icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant",icon="🤖")
st.sidebar.page_link("pages/23_home_automation.py",     label="Home Automation",   icon="🐱")
st.sidebar.page_link("pages/27_home_assistant.py",      label="HA Setup",          icon="🏠")
render_sidebar_user_widget()

# ── Constants ──────────────────────────────────────────────────────────────────

PHASE1_STEPS = [
    ("homepod_hub_verify",    "Verify HomePod is your Apple Home hub",
     "Home app → tap house icon → Home Settings → Home Hubs & Bridges → HomePod should show Connected"),
    ("echo_alexa_online",     "Verify Echo Dot is online in Alexa app",
     "Alexa app → Devices → Echo & Alexa → Echo Dot should show green dot"),
    ("alexa_apple_skill",     "Link Alexa to Apple Home (Apple Home skill)",
     "Alexa app → More → Skills & Games → search Apple → enable Apple Home skill → sign in with Apple ID"),
    ("cross_platform_test",   "Test cross-platform: Siri controls Echo device, Alexa controls HomeKit device",
     "Once linked: say Hey Siri, turn on [Alexa device] and Alexa, turn on [HomeKit device] — both should work"),
    ("iphone_presence",       "Enable iPhone as presence sensor in Apple Home",
     "Home app → Home Settings → People → your name → Location: On. Triggers automations when you leave/arrive"),
    ("focus_automations",     "Link iPhone Focus Mode to Home scenes",
     "Settings → Focus → Sleep → Add Automation → Smart Home → set Goodnight scene"),
    ("morning_shortcut",      "Create Good Morning Siri Shortcut",
     "Shortcuts app → + → Add Action → Home → Set Scene → select Morning scene (create it in Home app first)"),
    ("goodnight_alexa",       "Create Alexa Goodnight routine",
     "Alexa app → More → Routines → + → Voice: goodnight → Actions: turn off lights + do not disturb + set alarm"),
]

PHASE2_STEPS = [
    ("ha_vm_created",         "Create Home Assistant VM on Proxmox",
     "qm create 200 --name homeassistant --memory 4096 --cores 2 → import HA OS qcow2 → start VM (see page 27)"),
    ("ha_onboarded",          "Complete HA onboarding wizard",
     "http://[VM-IP]:8123 → create user → set home location → done"),
    ("ha_hacs",               "Install HACS community store",
     "HA terminal: wget -O - https://get.hacs.xyz | bash - → restart → add HACS integration"),
    ("ha_tailscale",          "Install Tailscale add-on in HA",
     "HA → Add-on Store → Tailscale → Install → enable → access HA from iPhone via Tailscale IP anywhere"),
    ("ha_homekit_bridge",     "Add HomeKit integration in HA (links to HomePod)",
     "HA → Settings → Integrations → + → HomeKit → scan QR with iPhone Camera app → HA appears in Apple Home"),
    ("ha_alexa_linked",       "Link HA to Alexa Echo Dot",
     "Easiest: Nabu Casa $6.50/mo. Free: HA → Integrations → Emulated Hue → Alexa app → Discover devices"),
]

PHASE3_STEPS = [
    ("kasa_in_ha",            "Add Kasa smart plugs to HA",
     "Pair in Kasa app → HA → Integrations → TP-Link Kasa Smart → auto-discovers all plugs on LAN"),
    ("lifx_in_ha",            "Add LIFX bulbs to HA",
     "Pair in LIFX app → HA → Integrations → LIFX → auto-discovers on LAN (no hub needed)"),
    ("reolink_in_ha",         "Add Reolink camera to HA",
     "Set static IP for camera → HA → Integrations → Reolink → enter camera IP/user/pass → RTSP stream live"),
    ("petlibro_in_ha",        "Add Petlibro feeder + fountain to HA",
     "Pair in Petlibro app → HA → HACS → install Petlibro integration → feeding buttons + bowl + fountain entities"),
    ("switchbot_in_ha",       "Add SwitchBot blind tilt to HA",
     "Pair in SwitchBot app + set up Hub Mini → HA → Integrations → SwitchBot → blind tilt open/close/position"),
    ("frigate_cat_ai",        "Set up Frigate NVR for cat AI detection",
     "Deploy Frigate on CT100 → connect Reolink RTSP → create cat detection zone → HA gets real-time motion events"),
    ("ha_dashboard",          "Build unified HA dashboard",
     "HA → Overview → Edit → add cards: lights, blinds, feeder, fountain, camera feed, presence, cat health"),
]

QUICK_WINS = [
    ("alexa_morning",    "Morning Routine (Alexa)",
     """**Say: 'Alexa, good morning'**

**Alexa app setup:**
1. Alexa app → More → Routines → +
2. When: Voice → type "good morning"
3. Actions:
   - Flash Briefing (weather + news)
   - Smart Home: turn on lights at 40%
   - Music: play your morning playlist on Spotify
4. Save → test by saying "Alexa, good morning" """),
    ("alexa_goodnight",  "Goodnight Routine (Alexa)",
     """**Say: 'Alexa, goodnight'**

**Alexa app setup:**
1. Alexa app → More → Routines → +
2. When: Voice → type "goodnight"
3. Actions:
   - Smart Home: turn off all lights
   - Do Not Disturb: enable
   - Alarm: set for your wake time tomorrow
4. Save → test by saying "Alexa, goodnight" """),
    ("homepod_morning",  "HomePod Morning Scene",
     """**Say: 'Hey Siri, good morning'**

**Home app setup:**
1. Home app → Automations tab → +
2. A Time of Day Occurs → 7:00 AM (weekdays only)
3. Set Scene: create 'Morning' scene first
   - In Home app → + → Add Scene → name it Morning
   - Set all lights to warm white 30% brightness
4. Save → also activates when you say 'Hey Siri, good morning' """),
    ("iphone_presence_auto", "iPhone Auto Leave/Arrive",
     """**Fully automatic — no button needed**

**Home app setup:**
1. Home app → Automations tab → +
2. "People Arrive" → select yourself
   - Action: turn on entry light, set Home mode
3. "People Leave" → select yourself (everyone leaves)
   - Action: turn off ALL lights, set Away mode

**Alexa app setup:**
1. More → Routines → + → When: Location → Arrives at Home
2. Actions: turn on welcome lights
3. When: Leaves Home → turn off all lights + announce "Everyone has left" """),
    ("cross_platform_link", "Link Echo + Apple Home Together",
     """**The big unlock: control any device from either assistant**

**Step 1 — Apple Home → Alexa:**
1. Alexa app → More → Skills & Games
2. Search "Apple" → tap Apple Home
3. Enable to Use → sign in with Apple ID
4. Say "Alexa, discover devices" → all HomeKit devices appear in Alexa

**Step 2 — Alexa devices → Apple Home:**
1. Works automatically after Step 1 (Alexa skill syncs both ways)
2. All Alexa-controlled devices now appear in Apple Home app
3. Hey Siri and Alexa both control the same devices

**Result:** One ecosystem, two voice assistants """),
    ("homepod_intercom", "HomePod Intercom + Announcements",
     """**Send voice messages to any HomePod in your home**

**Setup:**
1. Home app → house icon → Intercom
2. Add HomePod to a room (Bedroom, Living Room, etc.)

**Usage:**
- "Hey Siri, intercom: dinner is ready" → plays on all HomePods
- "Hey Siri, announce in the bedroom: I'm home" → plays in specific room
- Also works from iPhone or Apple Watch when away from home

**Bonus:** Set HomePod as alarm clock
- "Hey Siri, wake me up at 7am with [song/playlist]"
- Music fades in gradually for a gentle wake """),
]


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _ensure_tables():
    conn = get_conn()
    if USE_POSTGRES:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS smart_home_connect (
                id       SERIAL PRIMARY KEY,
                step_key TEXT UNIQUE NOT NULL,
                done     BOOLEAN DEFAULT FALSE,
                done_at  TEXT DEFAULT NULL,
                notes    TEXT DEFAULT ''
            )
        """)
    else:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS smart_home_connect (
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
    conn = get_conn()
    c = db_exec(conn, "SELECT step_key, done, done_at, notes FROM smart_home_connect")
    rows = c.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        result = {r[0]: dict(zip(cols, r)) for r in rows}
    else:
        result = {r["step_key"]: dict(r) for r in rows}
    conn.close()
    return result


def _set_step(step_key: str, done: bool):
    conn = get_conn()
    done_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if done else None
    if USE_POSTGRES:
        db_exec(conn, """
            INSERT INTO smart_home_connect (step_key, done, done_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (step_key) DO UPDATE
                SET done=EXCLUDED.done, done_at=EXCLUDED.done_at
        """, (step_key, done, done_at))
    else:
        db_exec(conn, """
            INSERT INTO smart_home_connect (step_key, done, done_at)
            VALUES (?, ?, ?)
            ON CONFLICT(step_key) DO UPDATE
                SET done=excluded.done, done_at=excluded.done_at
        """, (step_key, 1 if done else 0, done_at))
    conn.commit()
    conn.close()


def _pct(progress: dict, keys: list) -> int:
    if not keys:
        return 0
    return int(sum(1 for k in keys if progress.get(k, {}).get("done")) / len(keys) * 100)


def _render_checklist(steps, prefix: str, progress: dict):
    """Render (key, label, tip) checklist rows with checkboxes."""
    for step_key, label, tip in steps:
        prog = progress.get(step_key, {})
        is_done = bool(prog.get("done"))
        c_chk, c_lbl, c_ts = st.columns([0.5, 7, 2])
        new_val = c_chk.checkbox("", value=is_done, key=f"{prefix}_{step_key}", label_visibility="collapsed")
        if new_val and not is_done:
            _set_step(step_key, True)
            st.rerun()
        elif not new_val and is_done:
            _set_step(step_key, False)
            st.rerun()
        lbl_text = f"~~**{label}**~~" if is_done else f"**{label}**"
        c_lbl.markdown(lbl_text)
        c_lbl.caption(tip)
        if is_done and prog.get("done_at"):
            c_ts.caption(f"✅ {str(prog['done_at'])[:10]}")
        else:
            c_ts.caption("⏳ Pending")
        st.markdown("")


# ── Init ───────────────────────────────────────────────────────────────────────
_ensure_tables()
_progress = _load_progress()

p1_keys  = [s[0] for s in PHASE1_STEPS]
p2_keys  = [s[0] for s in PHASE2_STEPS]
p3_keys  = [s[0] for s in PHASE3_STEPS]
qw_keys  = [s[0] for s in QUICK_WINS]
all_keys = p1_keys + p2_keys + p3_keys

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("🔌 Connect Everything")
st.caption("HomePod + Echo Dot are live on your iPhone 16 Pro Max — here is the full path to a unified automated smart home.")

# ── Status dashboard ──────────────────────────────────────────────────────────
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("🍎 Apple Home Hub",  "✅ Live",   "HomePod connected")
mc2.metric("🔊 Alexa",           "✅ Live",   "Echo Dot connected")
mc3.metric("Phase 1",
           f"{_pct(_progress, p1_keys)}%",
           f"{sum(1 for k in p1_keys if _progress.get(k,{}).get('done'))}/{len(p1_keys)} done")
mc4.metric("Phase 2 — HA VM",
           f"{_pct(_progress, p2_keys)}%",
           f"{sum(1 for k in p2_keys if _progress.get(k,{}).get('done'))}/{len(p2_keys)} done")
mc5.metric("Phase 3 — Devices",
           f"{sum(1 for k in p3_keys if _progress.get(k,{}).get('done'))}/{len(p3_keys)}",
           "in Home Assistant")

st.progress(_pct(_progress, all_keys) / 100,
            text=f"Overall: {_pct(_progress, all_keys)}% connected")
st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⚡ Quick Wins — Do Now",
    "📱 Phase 1 — HomePod + Echo",
    "🖥️ Phase 2 — Home Assistant",
    "🏠 Phase 3 — All Devices",
    "🗺️ Connection Map",
])

# ── TAB 1: Quick Wins ─────────────────────────────────────────────────────────
with tab1:
    st.subheader("⚡ Do These Right Now — No New Hardware Required")
    st.success("HomePod and Echo Dot are already live. These 6 tasks take 5–15 minutes each and unlock real automation TODAY.")

    done_count = sum(1 for _, k, _ in [(s[0], s[0], s[2]) for s in QUICK_WINS] if _progress.get(k, {}).get("done"))
    st.progress(done_count / len(QUICK_WINS), text=f"Quick Wins: {done_count}/{len(QUICK_WINS)} completed")
    st.markdown("")

    for step_key, title, instructions in QUICK_WINS:
        prog      = _progress.get(step_key, {})
        is_done   = bool(prog.get("done"))
        icon      = "✅" if is_done else "⏳"
        with st.expander(f"{icon} {title}", expanded=not is_done):
            st.markdown(instructions)
            st.markdown("")
            cb1, cb2 = st.columns([2, 4])
            if not is_done:
                if cb1.button("Mark Done ✅", key=f"qwdone_{step_key}"):
                    _set_step(step_key, True)
                    st.rerun()
            else:
                cb1.success("Completed!")
                if cb2.button("Undo", key=f"qwundo_{step_key}"):
                    _set_step(step_key, False)
                    st.rerun()

    st.divider()
    st.subheader("🎯 Voice Commands You Can Use Right Now")
    col_s, col_a = st.columns(2)
    with col_s:
        st.markdown("### 🍎 Hey Siri / HomePod")
        st.markdown("""
- *"Hey Siri, good morning"* → morning scene
- *"Hey Siri, I'm leaving"* → away mode
- *"Hey Siri, goodnight"* → night scene
- *"Hey Siri, turn off all lights"*
- *"Hey Siri, set the mood"* → scene
- *"Hey Siri, intercom: [message]"* → PA system
- *"Hey Siri, what's on my calendar today?"*
- *"Hey Siri, play jazz in the living room"*
        """)
    with col_a:
        st.markdown("### 🔊 Alexa / Echo Dot")
        st.markdown("""
- *"Alexa, good morning"* → morning routine
- *"Alexa, goodnight"* → night routine
- *"Alexa, turn off everything"*
- *"Alexa, set a 20 minute timer"*
- *"Alexa, add milk to my shopping list"*
- *"Alexa, what's on my calendar?"*
- *"Alexa, announce: [message]"*
- *"Alexa, play [playlist] on Spotify"*
        """)


# ── TAB 2: Phase 1 ────────────────────────────────────────────────────────────
with tab2:
    st.subheader("📱 Phase 1 — Optimize What You Already Have")
    st.info("Maximum value from your existing HomePod + Echo Dot — no new hardware needed for any of these.")

    p1_pct = _pct(_progress, p1_keys)
    st.progress(p1_pct / 100, text=f"Phase 1: {p1_pct}% complete")
    st.markdown("")

    _render_checklist(PHASE1_STEPS, "p1", _progress)

    st.divider()
    st.subheader("🔗 Cross-Platform Connection Diagram")
    st.code("""iPhone 16 Pro Max
    ├── Apple Home app  (hub = HomePod)
    │     └── HomeKit devices
    │           └─── also visible in Alexa via Apple Home skill
    └── Alexa app  (hub = Echo Dot)
          └── Alexa devices
                └─── also visible in Apple Home via Alexa skill

Result: "Hey Siri, turn on [Alexa device]" works
        "Alexa, turn on [HomeKit device]" works
Both voice assistants control the same physical devices.""", language="text")

    with st.expander("Step-by-step: Link Apple Home to Alexa"):
        st.markdown("""
1. Open **Alexa app** on iPhone
2. More → Skills & Games → search **Apple** → tap **Apple Home**
3. Tap **Enable to Use** → sign in with Apple ID
4. Say *"Alexa, discover devices"*
5. All your HomeKit devices now appear in Alexa → control them by voice
        """)

    with st.expander("Step-by-step: iPhone Presence Automations (Leave/Arrive)"):
        st.markdown("""
**Apple Home:**
1. Home app → Automations → + → **People Arrive**
   - Action: turn on entry light, play welcome sound on HomePod
2. Home app → Automations → + → **People Leave**
   - Action: turn off ALL lights, set Away scene

**Alexa:**
1. More → Routines → + → When: **Location** → Arrives at [home address]
   - Action: turn on welcome lights + announce *"Welcome home, Darrian"*
2. Routines → + → When: Location → Leaves [home address]
   - Action: turn off lights + announce *"Goodbye, see you later"*

**Pro tip:** iPhone 16 Pro Max Ultra Wideband chip gives room-level precision in HA (Phase 2+)
        """)

    with st.expander("Step-by-step: Focus Mode → Smart Home"):
        st.markdown("""
| Focus Mode | Trigger | Smart Home Action |
|-----------|---------|-------------------|
| Sleep | When enabled | Goodnight scene (lights off, blinds closed) |
| Work | When enabled | Cool white desk light at 80%, DND |
| Personal | When enabled | Warm amber lights at 30%, relaxing music |
| Driving | When enabled | Away mode (lights off) |

**Setup:**
1. Settings → Focus → [Focus Name] → Add Automation → Smart Home
2. Select a Home scene to activate when Focus turns on
3. Done — it fires automatically every time Focus activates
        """)


# ── TAB 3: Phase 2 ────────────────────────────────────────────────────────────
with tab3:
    st.subheader("🖥️ Phase 2 — Set Up Home Assistant (This Week)")
    st.info("HA on Proxmox is the central hub that ties HomePod + Echo Dot + every future device together in one place.")

    p2_pct = _pct(_progress, p2_keys)
    st.progress(p2_pct / 100, text=f"Phase 2: {p2_pct}% complete")
    st.markdown("")

    _render_checklist(PHASE2_STEPS, "p2", _progress)

    st.divider()

    with st.expander("Proxmox Shell Commands — Create HA VM"):
        st.code("""# SSH into Proxmox (Beelink homelab)
ssh root@100.95.125.112

# Download Home Assistant OS image
cd /var/lib/vz/template/iso/
wget https://github.com/home-assistant/operating-system/releases/download/13.2/haos_ova-13.2.qcow2.xz
xz -d haos_ova-13.2.qcow2.xz

# Create VM 200
qm create 200 --name homeassistant --memory 4096 --cores 2 --net0 virtio,bridge=vmbr0
qm importdisk 200 haos_ova-13.2.qcow2 local-lvm
qm set 200 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-200-disk-0
qm set 200 --boot c --bootdisk scsi0
qm set 200 --serial0 socket --vga serial0
qm resize 200 scsi0 32G
qm start 200

# Find VM IP in Proxmox console → open http://[VM-IP]:8123""", language="bash")

    with st.expander("Connect HA to HomePod — HomeKit Bridge"):
        st.markdown("""
**In Home Assistant:**
1. Settings → Integrations → + Add → search **HomeKit**
2. Choose which devices to expose to HomeKit
3. A QR code appears in HA
4. On iPhone: open Camera app → scan QR → "Add to Home?" → tap **Add**
5. HA appears as a bridge device in Apple Home app
6. All HA devices (Kasa, LIFX, Petlibro, etc.) now visible in Apple Home
7. HomePod can now control everything via "Hey Siri"

**Result:** HomePod → Apple Home → HA Bridge → controls all smart devices
        """)

    with st.expander("Connect HA to Echo Dot — Alexa Integration"):
        st.markdown("""
**Option A — Nabu Casa (easiest, $6.50/month):**
1. HA → Settings → Home Assistant Cloud → sign up for Nabu Casa
2. Enable Alexa integration in cloud settings
3. Alexa app → Skills → search **Home Assistant** → enable → link account
4. Say *"Alexa, discover devices"* → all HA devices appear

**Option B — Free (Emulated Hue):**
```yaml
# Add to HA configuration.yaml:
emulated_hue:
  host_ip: YOUR_HA_IP
  listen_port: 80
  expose_by_default: true
```
Then: Alexa app → Devices → + → Other → Discover Devices

**Result:** Echo Dot can control everything in HA
        """)


# ── TAB 4: Phase 3 ────────────────────────────────────────────────────────────
with tab4:
    st.subheader("🏠 Phase 3 — Add All Smart Devices to HA (Next Weekend)")
    st.info("Once each device is in HA, it automatically shows up in BOTH Apple Home (HomePod) AND Alexa (Echo Dot).")

    p3_pct = _pct(_progress, p3_keys)
    st.progress(p3_pct / 100,
                text=f"Phase 3: {p3_pct}% — {sum(1 for k in p3_keys if _progress.get(k,{}).get('done'))}/{len(p3_keys)} devices in HA")
    st.markdown("")

    _render_checklist(PHASE3_STEPS, "p3", _progress)

    st.divider()
    st.subheader("🐱 Cat Automation Pack")
    st.caption("Activate these once Petlibro feeder + Reolink camera are in HA")

    cat_packs = [
        ("Auto Breakfast 7AM", "Cat feeder dispenses automatically — no manual feeding. YAML template on page 27."),
        ("Auto Dinner 6PM",    "Second feeding, fully automated."),
        ("Fountain Alert",     "iPhone notification if fountain flow sensor goes offline (filter clog / low water)."),
        ("Bored Cat Laser",    "Frigate detects no cat movement for 30 min → laser toy Kasa plug turns on for 15 min."),
        ("Cat Health Log",     "Log feeder dispense events to Postgres → Claude AI reviews weekly and alerts if abnormal."),
        ("Camera Live Card",   "Reolink RTSP stream embedded in HA dashboard → see the cat from peachstatesavings.com."),
    ]
    for title, desc in cat_packs:
        with st.expander(f"🐱 {title}"):
            st.write(desc)


# ── TAB 5: Connection Map ─────────────────────────────────────────────────────
with tab5:
    st.subheader("🗺️ Full Smart Home Connection Architecture")

    st.code("""iPhone 16 Pro Max (Darrian)
  │
  ├── Apple Home app
  │     ├── HomePod Mini (hub) — voice: "Hey Siri"
  │     ├── Phase 1: any HomeKit-native device
  │     └── Phase 2+: HA HomeKit Bridge
  │           └── exposes all HA devices to Siri + Apple automations
  │
  └── Alexa app
        ├── Echo Dot (hub) — voice: "Alexa"
        ├── Phase 1: any Alexa-native device
        └── Phase 2+: HA via Nabu Casa or Emulated Hue
              └── exposes all HA devices to Alexa routines

              Both connect to:

Beelink Homelab (100.95.125.112)
  ├── CT100 Docker
  │     ├── peachstatesavings.com (Budget App)
  │     └── Frigate NVR (cat AI detection)
  │           └── Reolink RTSP stream → object detection → HA events
  │
  └── VM200 — Home Assistant OS
        ├── Kasa EP25 Smart Plugs    (local TCP, no cloud)
        ├── LIFX A19 Bulbs           (LAN UDP, no cloud)
        ├── Reolink E1 Pro Camera    (RTSP, no cloud)
        ├── Petlibro Feeder          (Wi-Fi via HACS)
        ├── Petlibro Fountain        (Wi-Fi via HACS)
        ├── SwitchBot Blind Tilt     (Hub + SwitchBot cloud)
        ├── Frigate events           (cat detection triggers)
        └── Tailscale                (remote iPhone access, no port forwarding)""",
            language="text")

    st.divider()
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Control Matrix")
        st.markdown("""
| You say / do | Route | Controls |
|---|---|---|
| "Hey Siri…" | HomePod → Apple Home → HA bridge | Everything |
| "Alexa…" | Echo Dot → Alexa → HA (Nabu Casa) | Everything |
| iPhone automation | Home app trigger | All HomeKit + HA |
| Focus Mode change | iPhone → Home scene | Lights/blinds/scenes |
| Leave home (GPS) | iPhone → HA presence | Lights off, away mode |
| HA automation | HA scheduler | Kasa, LIFX, Petlibro, SwitchBot |
| Frigate detects cat | HA event | Laser toy, notifications |
        """)

    with col_r:
        st.subheader("4-Week End State")
        st.markdown("""
**Week 1 (now):** HomePod + Echo linked, presence automations, Focus modes

**Week 2:** HA VM running, HomeKit bridge live, Alexa linked

**Week 3 (next weekend):** All devices in HA — Kasa plugs, LIFX, Reolink, Petlibro feeder + fountain

**Week 4:** Cat automations running, Frigate cat AI active, unified dashboard live

**Final state:**
- Morning: lights ramp up, blinds open, cat fed, coffee on — all automatic
- Leave: lights off, cat feeder on schedule, camera armed
- Arrive: welcome lights on, HomePod plays your playlist
- Night: lights off, blinds down, goodnight routine fires
- Midday: cat laser play session (auto, 15 min)
- Cat dashboard visible on peachstatesavings.com
        """)

    st.divider()
    st.info("You are at Phase 1 right now. Start with the Quick Wins tab — 6 items, under 1 hour total, real automation today.")
