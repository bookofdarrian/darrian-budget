import streamlit as st
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="Home & Cat Automation — Peach State Savings",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="auto"
)

inject_css()
require_login()
render_sidebar_brand()
render_sidebar_user_widget()

st.title("🏠 Home & Cat Automation")
st.caption("Your roadmap for smart home + cat automation — apartment-ready now, expands when you move")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Overview",
    "💡 Lights & Blinds",
    "🐱 Cat Devices",
    "🤖 Vacuum & Coffee",
    "🛒 Shopping List",
])

# ── TAB 1: Overview ───────────────────────────────────────────────────────────
with tab1:
    st.subheader("The Foundation: Home Assistant")
    st.info(
        "**Home Assistant** is the hub for everything on this page. "
        "Deploy it as a VM in Proxmox first — it's already in your homelab plan (Tier 2, Item 6). "
        "Once running, every device below integrates into one dashboard with automations, AI, and Tailscale remote access."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Deploy Home Assistant")
        st.code(
            "Proxmox → Create VM\n"
            "Upload Home Assistant OS image\n"
            "VM: 2 cores, 4GB RAM, 32GB disk\n"
            "Access at http://[VM-IP]:8123",
            language="text"
        )
        st.markdown("**Effort:** 2 hours | **Cost:** $0 (runs on your existing Beelink)")

    with col2:
        st.markdown("### Architecture")
        st.code(
            "Beelink (Proxmox)\n"
            "  ├── CT100 (Docker)\n"
            "  │     ├── Frigate NVR (cat AI)\n"
            "  │     └── Budget App\n"
            "  └── Home Assistant VM\n"
            "        ├── Lights (Kasa/LIFX)\n"
            "        ├── Blinds (SwitchBot)\n"
            "        ├── Vacuum (Roborock)\n"
            "        ├── Cat feeder (Petlibro)\n"
            "        ├── Cat fountain (Petlibro)\n"
            "        └── Litter box",
            language="text"
        )

    st.markdown("---")
    st.subheader("📅 Timeline — Moving in 3 Months")

    phases = [
        ("Week 1 — Foundation", "🟢 Do Now",
         "Deploy Home Assistant VM · Buy Kasa smart plugs · Set up light automations"),
        ("Week 2 — Cat Basics", "🟢 Do Now",
         "Petlibro feeder + fountain · Reolink camera · Frigate NVR for cat detection"),
        ("Week 3 — Comfort", "🟢 Do Now",
         "SwitchBot blind tilt · Smart plug for coffee maker · Morning routine automation"),
        ("Month 2 — Expand", "🟡 Soon",
         "LIFX color bulbs · Adaptive Lighting (HACS) · Cat health dashboard in budget app"),
        ("After Move — Permanent", "🔵 Later",
         "Roborock Q5 Pro · IKEA FYRTUR blinds · Litter-Robot 4 · Full camera setup"),
    ]

    for phase, status, details in phases:
        with st.expander(f"{status} **{phase}**"):
            st.write(details)

# ── TAB 2: Lights & Blinds ────────────────────────────────────────────────────
with tab2:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💡 Smart Lighting")
        st.markdown("""
**Recommended:** Kasa smart plugs + LIFX bulbs

| Brand | Price | Notes |
|-------|-------|-------|
| Kasa (TP-Link) | $10–$25/bulb | Local API, no cloud — best for HA |
| LIFX | $20–$45/bulb | No hub, Wi-Fi, great colors |
| Philips Hue | $15–$50/bulb | Best HA integration, needs hub |
| Govee | $8–$20/bulb | Cheapest, cloud-dependent |

**Key automations:**
- Auto-dim 30 min before sunset
- Turn off all lights at midnight
- Morning wake-up gradual brightness (30 min ramp)
- Circadian rhythm color temp (cool morning → warm evening)

**HACS add-on:** Install **Adaptive Lighting** — handles circadian rhythm automatically, no code needed.
        """)

    with col2:
        st.subheader("🪟 Automatic Blinds")
        st.markdown("""
**Recommended for apartment:** SwitchBot Blind Tilt ($40–$60)
- Clips onto existing blinds — no permanent install
- Battery powered — no wiring
- Works with Home Assistant via SwitchBot hub

**After moving:** IKEA FYRTUR ($130–$180/window)
- Full motorized roller blinds
- Zigbee native — rock solid HA integration
- Measure new windows first

| Type | Price | Notes |
|------|-------|-------|
| SwitchBot Blind Tilt | $40–$60 | Retrofits existing blinds |
| IKEA FYRTUR | $130–$180 | Full motorized, Zigbee |
| Soma Smart Shades 2 | $130 | Retrofits roller shades |
| Lutron Serena | $200–$400 | Premium, very reliable |

**Key automations:**
- Open at sunrise, close at sunset
- Privacy mode: close all when you arrive home
        """)

    st.markdown("---")
    st.subheader("☕ Smart Coffee / Tea")
    st.markdown("""
**Simplest approach:** Kasa EP25 smart plug ($15) + your existing coffee maker.

Schedule it in Home Assistant → coffee is ready when you wake up.

**AI upgrade:** Wire to `utils/calendar_client.py` — Claude reads your Google Calendar
and starts coffee 15 minutes before your first meeting.

| Device | Price | Notes |
|--------|-------|-------|
| Kasa Smart Plug + any machine | $15 | Simplest, works with anything you own |
| Smarter iKettle 3 | $100 | Native HA integration, precise temp |
| Fellow Stagg EKG+ | $165 | Best smart kettle for tea/pour-over |
| Keurig K-Supreme Plus Smart | $180 | Schedule brews from app |
    """)

# ── TAB 3: Cat Devices ────────────────────────────────────────────────────────
with tab3:
    st.subheader("🐱 Cat Automation Devices")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### 🍽️ Smart Feeder")
        st.markdown("""
**Recommended:** Petlibro Granary Wi-Fi Feeder ($60–$80)
- Scheduled feeding with portion control
- Built-in camera to verify cat ate
- Home Assistant integration
- Low food alerts

**Automations:**
- 7 AM breakfast + 6 PM dinner auto-dispense
- Alert if bowl still full 2 hours after scheduled feed
- Log feeding times to Postgres for health tracking
        """)

        st.markdown("### 💧 Smart Fountain")
        st.markdown("""
**Recommended:** Petlibro Granary Wi-Fi Fountain ($45)
- Wi-Fi connected, no hub needed
- Filter replacement alerts
- Flow schedule control (high flow mornings, low flow nights)
- Home Assistant integration via community component
        """)

        st.markdown("### 🎮 Interactive Toys")
        st.markdown("""
**Simplest:** PetSafe Bolt Laser ($20) + Kasa smart plug ($15)
- Schedule 15-min play sessions while you're away
- Frigate AI: trigger toy when cat hasn't moved in 30 min (bored cat detection)

| Device | Price | Notes |
|--------|-------|-------|
| PetSafe Bolt Laser + plug | $35 | Schedulable via HA |
| Cheerble Wicked Ball | $35 | Self-rolling, random patterns |
| Petronics Mousr | $100 | Autonomous robotic mouse |
        """)

    with c2:
        st.markdown("### 📷 Cat Cameras + Frigate AI")
        st.markdown("""
**Recommended:** Reolink E1 Pro ($35)
- Native Home Assistant integration
- Local RTSP stream — no cloud, no subscription
- 5MP — see your cat clearly
- Works with Frigate NVR for AI detection

**Frigate NVR** runs on CT100 (your Docker host):
- Real-time cat detection
- Motion clips saved to NAS
- Alerts when cat enters/leaves zones
- Triggers HA automations (pause vacuum, start toy)
        """)

        st.markdown("### 🚽 Smart Litter Box")
        st.markdown("""
**Mid-range:** Petlibro Capsule Smart ($200)
- Self-cleaning, HA integration
- Usage tracking

**Best in class:** Litter-Robot 4 ($700)
- Self-cleaning + self-emptying
- Health monitoring: usage frequency, weight tracking
- Detects UTI early (cat goes more often)
- Native Home Assistant integration

**Health alert automation:**
- Alert if cat hasn't used litter box in 24+ hours
- Track usage frequency over time → chart in budget app
        """)

    st.markdown("---")
    st.subheader("🏥 Cat Health Dashboard (Budget App Integration)")
    st.info(
        "Once Home Assistant is running, this page can pull live data from the HA API. "
        "Add `HA_TOKEN` to your `.env` file and the metrics below will show real data."
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🍽️ Last Fed", "—", help="From Petlibro feeder via Home Assistant")
    col2.metric("💧 Fountain", "—", help="From Petlibro fountain via Home Assistant")
    col3.metric("🚽 Last Litter Use", "—", help="From Litter-Robot/Petlibro via Home Assistant")
    col4.metric("📷 Cat Detected", "—", help="From Frigate NVR via Home Assistant")

    st.caption("Connect Home Assistant → add HA_TOKEN to .env → metrics will populate automatically")

# ── TAB 4: Vacuum & Coffee ────────────────────────────────────────────────────
with tab4:
    st.subheader("🤖 Robot Vacuum / Mop")

    st.markdown("""
**Recommended for apartment:** Roborock Q5 Pro (~$350)
- Vacuums AND mops
- Native Home Assistant integration (local API, no cloud)
- Covers 1,500 sq ft — perfect for apartments
- Handles cat hair without tangling

**Best overall (after move):** Roborock S8 Pro Ultra (~$900)
- Self-empties AND self-washes the mop pad
- Truly hands-off for weeks at a time

| Model | Type | Price | Notes |
|-------|------|-------|-------|
| Roborock Q5 Pro | Vacuum + Mop | ~$350 | Best value, native HA |
| Roborock S8 Pro Ultra | Vacuum + Mop + Self-empty | ~$900 | Best overall |
| Dreame L10s Ultra | Vacuum + Mop + Self-empty | ~$800 | Strong competitor |
| iRobot Roomba j7+ | Vacuum only | ~$500 | Avoids cat toys/cables |
    """)

    st.markdown("### Key Automations")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
**Schedule-based:**
- Run daily at 10 AM on weekdays
- Skip if you're home (presence detection via phone)
- Pause when cat is detected in the room (Frigate integration)
        """)
    with col2:
        st.markdown("""
**AI-powered:**
- Claude reads your Google Calendar → schedules vacuum when you're out
- Frigate detects cat location → vacuum avoids that room
- Log dustbin data → chart "dirtiest days" in budget app
        """)

    st.markdown("---")
    st.subheader("☕ Smart Coffee Setup")
    st.markdown("""
The simplest and most reliable approach: **Kasa EP25 smart plug ($15)** + your existing coffee maker.

Set a schedule in Home Assistant → coffee is ready when you wake up. No new hardware needed.

**AI calendar integration** (using your existing `utils/calendar_client.py`):
- Early meeting day → coffee starts earlier
- Late start day → coffee starts later
- Claude reads your schedule and adjusts automatically
    """)

# ── TAB 5: Shopping List ──────────────────────────────────────────────────────
with tab5:
    st.subheader("🛒 Shopping List")

    st.markdown("### ✅ Buy Now — Works in Current Apartment, Moves With You")
    st.markdown("""
| Item | Where to Buy | Price | Priority |
|------|-------------|-------|----------|
| 4x Kasa EP25 Smart Plugs | Amazon | ~$40 | 🔴 High |
| Petlibro Granary Wi-Fi Feeder | Amazon | ~$65 | 🔴 High |
| Petlibro Granary Wi-Fi Fountain | Amazon | ~$45 | 🔴 High |
| Reolink E1 Pro Camera | Amazon | ~$35 | 🔴 High |
| SwitchBot Blind Tilt (1 window) | Amazon | ~$45 | 🟡 Medium |
| 2x LIFX A19 Color Bulbs | Amazon/Best Buy | ~$50 | 🟡 Medium |
| PetSafe Bolt Laser | Amazon | ~$20 | 🟢 Low |
| **Total** | | **~$300** | |
    """)

    st.markdown("### ⏳ Buy After Moving — Permanent Installation")
    st.markdown("""
| Item | Where to Buy | Price | Notes |
|------|-------------|-------|-------|
| Roborock Q5 Pro | Amazon | ~$350 | Know your floor plan first |
| IKEA FYRTUR Blinds | IKEA | $130–$180/window | Measure new windows |
| Petlibro Capsule Litter Box | Amazon | ~$200 | Know where it'll live |
| Litter-Robot 4 (upgrade) | litterrobot.com | ~$700 | Best long-term investment |
| Additional Reolink cameras | Amazon | ~$35 each | Know your new layout |
| Smart thermostat (Ecobee) | Amazon/Best Buy | ~$180 | Check if landlord allows |
    """)

    st.markdown("---")
    st.subheader("💰 Total Cost Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("Starter Kit (Now)", "~$300", help="Portable devices that move with you")
    col2.metric("After Move (Permanent)", "~$1,000–$1,500", help="Roborock + blinds + litter box")
    col3.metric("Full Setup", "~$1,300–$3,200", help="Everything including Litter-Robot 4")

    st.info("**Home Assistant is free** — runs on your existing Beelink homelab. $0 software cost.")

    st.markdown("---")
    with st.expander("📖 Full Guide"):
        st.markdown(
            "See **`HOME_CAT_AUTOMATION.md`** in the repo root for the complete guide with "
            "all YAML automations, device comparisons, Frigate NVR setup, and integration architecture."
        )
