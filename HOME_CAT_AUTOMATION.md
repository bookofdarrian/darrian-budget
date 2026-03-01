# Home & Cat Automation — Darrian's Roadmap
**Owner: Darrian Belcher | Created: 2026-02-28**

> Foundation guide for home automation and cat automation. You're moving within
> 3 months, so this is designed to work NOW in your current apartment and EXPAND
> when you move. Everything integrates with your existing homelab (Proxmox, CT100,
> Home Assistant, Tailscale).
>
> **⚠️ IMPORTANT — TOOL USE NOTE:** Always use Python (`python3`) via
> `execute_command` when writing large files. The `write_to_file` tool truncates
> long content. Use `execute_command` with a Python script file written first,
> then executed. Never use bash heredocs — they time out on large content.

---

## 🏗️ The Foundation: Home Assistant (Already in Your Homelab Plan)

Home Assistant is already listed in `HOMELAB_USECASES.md` as Tier 2, Item 6.
**This is the hub for everything below.** Deploy it first.

```
Proxmox → Create VM → Upload Home Assistant OS image
VM: 2 cores, 4GB RAM, 32GB disk
Access at http://[VM-IP]:8123
```

Once Home Assistant is running, every device below integrates into one dashboard.
You control lights, robot vacuum, blinds, cat feeder, fountain — all from one app,
with automations, AI, and Tailscale remote access.

---

## 💡 SECTION 1: Light Automation

### Recommended Smart Bulbs & Plugs

| Brand | Pros | Cons | Price |
|-------|------|------|-------|
| Philips Hue | Best HA integration, Zigbee, rock solid | Needs hub ($60) | $15–$50/bulb |
| LIFX | No hub, Wi-Fi direct, great colors | Slightly less reliable | $20–$45/bulb |
| Govee | Cheapest, good colors | Cloud-dependent | $8–$20/bulb |
| Kasa (TP-Link) | Reliable Wi-Fi, local API | Less color range | $10–$25/bulb |

**Recommendation for your setup:** Start with **Kasa smart plugs + LIFX bulbs**.
Kasa has a local API (no cloud required), works perfectly with Home Assistant,
and you already have TP-Link hardware (your switch).

### Automations to Build in Home Assistant

```yaml
# Auto-dim at sunset
automation:
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
        color_temp: 3000

  - alias: "Lights off at midnight"
    trigger:
      platform: time
      at: "00:00:00"
    action:
      service: light.turn_off
      target:
        entity_id: all

  - alias: "Morning wake-up lights"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      service: light.turn_on
      target:
        entity_id: light.bedroom
      data:
        brightness_pct: 10
        transition: 1800
```

### AI Light Features

Install **Adaptive Lighting** from HACS (Home Assistant Community Store) — it
automatically adjusts color temperature based on time of day (circadian rhythm).
No code needed. Alternatively, wire it to Ollama/Claude for smarter scheduling.

**Cost to start:** $30–$60 for 3–4 smart bulbs + 2 smart plugs

---

## 🤖 SECTION 2: Robot Vacuum / Mop

### Top Picks That Integrate with Home Assistant

| Model | Type | HA Integration | Price | Notes |
|-------|------|---------------|-------|-------|
| Roborock S8 Pro Ultra | Vacuum + Mop + Self-empty | Native | ~$900 | Best overall |
| Roborock Q5 Pro | Vacuum + Mop | Native | ~$350 | Best value for apartments |
| Dreame L10s Ultra | Vacuum + Mop + Self-empty | via HACS | ~$800 | Strong competitor |
| iRobot Roomba j7+ | Vacuum only | Native | ~$500 | Avoids cat toys/cables |

**Recommendation for your apartment:** **Roborock Q5 Pro (~$350)**
- Handles both vacuuming and mopping
- Native Home Assistant integration (local API, no cloud required)
- Perfect apartment size — covers 1,500 sq ft easily
- Specifically designed to handle pet hair without tangling

### Home Assistant + Roborock Automations

```yaml
automation:
  - alias: "Daily vacuum at 10 AM"
    trigger:
      platform: time
      at: "10:00:00"
    condition:
      condition: time
      weekday: [mon, tue, wed, thu, fri]
    action:
      service: vacuum.start
      target:
        entity_id: vacuum.roborock_q5

  - alias: "Pause vacuum near cat"
    trigger:
      platform: state
      entity_id: binary_sensor.cat_detected
      to: "on"
    action:
      service: vacuum.pause
      target:
        entity_id: vacuum.roborock_q5
```

### AI Integration Ideas

- **Schedule optimizer:** Claude analyzes your Google Calendar (you already have
  `utils/calendar_client.py`) and schedules vacuum runs when you're out
- **Dirt tracking:** Log vacuum dustbin data over time → chart in budget app

**Cost:** $350–$900 depending on model

---

## 🪟 SECTION 3: Automatic Blinds

### Options

| Type | HA Integration | Price | Notes |
|------|---------------|-------|-------|
| IKEA FYRTUR | Zigbee native | $130–$180 | Best value, works with IKEA hub |
| Lutron Serena | Native | $200–$400 | Premium, very reliable |
| SwitchBot Blind Tilt | via SwitchBot hub | $40–$60 | Retrofits existing blinds |
| Soma Smart Shades 2 | Native | $130 | Retrofits existing roller shades |

**Recommendation for apartment:** **SwitchBot Blind Tilt ($40–$60)**
- Retrofits your EXISTING blinds — no new blinds needed
- Perfect for renters (no permanent installation)
- Battery powered — no wiring

### Blind Automations

```yaml
automation:
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
        entity_id: cover.bedroom_blinds

  - alias: "Privacy on arrival"
    trigger:
      platform: device_tracker
      entity_id: device_tracker.darrian_phone
      to: home
    action:
      service: cover.close_cover
      target:
        entity_id: group.all_blinds
```

**Cost:** $40–$180 per window depending on approach

---

## ☕ SECTION 4: Smart Coffee / Tea Machine

### Options

| Device | HA Integration | Price | Notes |
|--------|---------------|-------|-------|
| Fellow Stagg EKG+ Kettle | via API | $165 | Best smart kettle, precise temp |
| Smarter iKettle 3 | Native HA | $100 | Direct HA integration |
| Keurig K-Supreme Plus Smart | via Keurig app | $180 | Schedule brews |
| Kasa Smart Plug + Any Machine | Native | $15 + your maker | Simplest option |

**Simplest approach:** Kasa EP25 smart plug ($15) + your existing coffee maker.

```yaml
automation:
  - alias: "Start coffee at 7:15 AM"
    trigger:
      platform: time
      at: "07:15:00"
    condition:
      condition: time
      weekday: [mon, tue, wed, thu, fri]
    action:
      service: switch.turn_on
      target:
        entity_id: switch.coffee_maker_plug
```

**AI feature:** Connect to your Google Calendar (`utils/calendar_client.py`).
If you have an early meeting, coffee starts 15 minutes before. Claude reads
your schedule and adjusts the start time automatically.

**Cost:** $10–$180 depending on approach

---

## 🐱 SECTION 5: Cat Automation

### 5a. Smart Water Fountain

| Device | HA Integration | Price | Notes |
|--------|---------------|-------|-------|
| Petlibro Granary Fountain | via Petlibro + HA | $45 | Wi-Fi, filter alerts, flow control |
| PETKIT Eversweet Solo 2 | via PETKIT HA | $40 | Good app, HA community integration |
| Catit PIXI Smart Fountain | via Catit app | $60 | Multiple flow modes |

**Recommendation:** **Petlibro Granary Wi-Fi Fountain ($45)**
- Wi-Fi connected, no hub needed
- Home Assistant integration via community component
- Filter replacement alerts + flow schedule control

**Cost:** $40–$60

---

### 5b. Smart Cat Feeder

| Device | HA Integration | Price | Notes |
|--------|---------------|-------|-------|
| Petlibro Granary Feeder | via Petlibro + HA | $60 | Wi-Fi, portion control, camera |
| PETKIT YumShare | via PETKIT HA | $80 | Dual bowl, camera, voice recording |
| SureFeed Microchip Feeder | via SurePetCare HA | $150 | Microchip-locked — only your cat eats |

**Recommendation:** **Petlibro Granary Wi-Fi Feeder with Camera ($60–$80)**

```yaml
automation:
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
        entity_id: button.cat_feeder_dispense

  - alias: "Cat hasn't eaten alert"
    trigger:
      platform: time
      at: "09:00:00"
    condition:
      condition: state
      entity_id: binary_sensor.cat_feeder_bowl_empty
      state: "off"
    action:
      service: notify.mobile_app_darrian_iphone
      data:
        message: "Cat hasn't eaten breakfast yet — check the feeder camera"
```

**AI feature:** Log feeding times to Postgres. Claude analyzes patterns:
"Your cat eats 15% less on days when the vacuum runs."

**Cost:** $60–$150

---

### 5c. Cat Cameras

| Device | HA Integration | Price | Notes |
|--------|---------------|-------|-------|
| Reolink E1 Pro | Native HA | $35 | Best value, 5MP, local RTSP stream |
| Wyze Cam v3 | via Wyze HA | $35 | Popular, good night vision |
| Amcrest IP8M | Native HA (ONVIF) | $60 | Professional grade, local only |

**Recommendation:** **Reolink E1 Pro ($35)**
- Native Home Assistant integration
- Local RTSP stream — no cloud, no subscription
- Works with Frigate NVR for AI cat detection

**Frigate NVR — AI Cat Detection on Your Homelab:**

```yaml
# Add to CT100 docker-compose.yml
  frigate:
    image: ghcr.io/blakeblackshear/frigate:stable
    privileged: true
    ports:
      - "5000:5000"
      - "8554:8554"
    volumes:
      - /opt/frigate/config:/config
      - /opt/frigate/storage:/media/frigate
    restart: unless-stopped
```

```yaml
# /opt/frigate/config/config.yml
cameras:
  cat_cam:
    ffmpeg:
      inputs:
        - path: rtsp://admin:password@192.168.1.x:554/stream1
          roles: [detect, record]
    detect:
      width: 1920
      height: 1080
    objects:
      track: [cat, person]
```

**What Frigate gives you:**
- Real-time cat detection (knows when your cat is in frame)
- Motion clips saved to your homelab NAS
- Alerts when cat enters/leaves specific zones
- Integrates with Home Assistant for automations

**Cost:** $35–$60 per camera + Frigate runs free on your homelab

---

### 5d. Smart Litter Box

| Device | HA Integration | Price | Notes |
|--------|---------------|-------|-------|
| Litter-Robot 4 | Native HA | $700 | Best in class, self-cleaning, health tracking |
| Petlibro Capsule Smart | via Petlibro + HA | $200 | Good mid-range option |
| PETKIT Pura X | via PETKIT HA | $350 | Strong competitor to Litter-Robot |

**Recommendation:** Start with **Petlibro Capsule ($200)** or save up for
**Litter-Robot 4 ($700)** — the Litter-Robot is genuinely worth it long-term.

**What Litter-Robot 4 tracks (health monitoring):**
- Usage frequency per day (detects UTI early — cat goes more often)
- Weight tracking (detects weight loss/gain)
- Waste drawer full alerts

```yaml
automation:
  - alias: "Cat litter box health alert"
    trigger:
      platform: time_pattern
      hours: "/6"
    condition:
      condition: template
      value_template: >
        {{ (now() - states.sensor.litter_robot_last_use.last_changed).total_seconds() > 86400 }}
    action:
      service: notify.mobile_app_darrian_iphone
      data:
        message: "Cat hasn't used the litter box in 24+ hours — vet check?"
```

**Cost:** $200–$700

---

### 5e. Interactive Cat Toys

| Device | HA Integration | Price | Notes |
|--------|---------------|-------|-------|
| PetSafe Bolt Laser | via smart plug | $20 | Automatic laser, smart plug schedules it |
| Cheerble Wicked Ball | App only | $35 | Self-rolling ball, random patterns |
| Petronics Mousr | Bluetooth only | $100 | Autonomous robotic mouse |

**Simplest smart toy setup:** PetSafe Bolt Laser ($20) + Kasa smart plug ($15)

```yaml
automation:
  - alias: "Cat play session midday"
    trigger:
      platform: time
      at: "12:00:00"
    action:
      service: switch.turn_on
      target:
        entity_id: switch.cat_laser_plug

  - alias: "Stop laser after 15 minutes"
    trigger:
      platform: time
      at: "12:15:00"
    action:
      service: switch.turn_off
      target:
        entity_id: switch.cat_laser_plug
```

**AI feature:** Use Frigate cat detection + Home Assistant to trigger toys when
your cat hasn't moved in 30 minutes (bored cat detection).

**Cost:** $35–$115

---

## 🏠 SECTION 6: Integration Architecture

### How Everything Connects

```
Your Homelab (CT100 @ 100.95.125.112)
  ├── Home Assistant VM (Proxmox)
  │     ├── Light automations (Kasa/LIFX)
  │     ├── Blind automations (SwitchBot)
  │     ├── Vacuum control (Roborock)
  │     ├── Coffee maker (smart plug)
  │     ├── Cat feeder (Petlibro)
  │     ├── Cat fountain (Petlibro)
  │     ├── Cat cameras → Frigate NVR
  │     └── Litter box (Litter-Robot/Petlibro)
  │
  ├── Frigate NVR (Docker on CT100)
  │     ├── Cat detection AI
  │     ├── Motion clips → NAS storage
  │     └── Triggers HA automations
  │
  ├── Budget App (Streamlit)
  │     ├── Cat health dashboard (pages/23_home_automation.py)
  │     ├── Feeding logs from Postgres
  │     └── Litter box usage charts
  │
  └── Tailscale VPN
        └── Control everything from iPhone anywhere
```

---

## 📦 SECTION 7: Apartment-Friendly Starter Kit

Since you're moving in 3 months, here's what to buy NOW vs LATER:

### Buy Now (Works in Current Apartment, Moves With You)

| Item | Price | Why Now |
|------|-------|---------|
| 4x Kasa smart plugs (EP25) | $40 | Control any device, no permanent install |
| 2x LIFX bulbs | $50 | Screw in, take with you |
| SwitchBot Blind Tilt (1 window) | $45 | Clips on, no damage to apartment |
| Petlibro Wi-Fi Feeder | $65 | Portable, cat needs it now |
| Petlibro Wi-Fi Fountain | $45 | Portable, cat needs it now |
| Reolink E1 Pro camera | $35 | Check on cat remotely |
| PetSafe Bolt Laser + smart plug | $35 | Cat entertainment while away |
| **Total** | **~$315** | |

### Buy After Moving (Permanent Installation)

| Item | Price | Why Wait |
|------|-------|---------|
| IKEA FYRTUR motorized blinds | $130–$180/window | Measure new windows first |
| Roborock Q5 Pro | $350 | Know your new floor plan |
| Litter-Robot 4 | $700 | Know where it'll live permanently |
| Additional cameras | $35 each | Know your new layout |
| Smart thermostat (Ecobee) | $180 | Check if landlord allows |

---

## 🚀 SECTION 8: Setup Order

```
WEEK 1 — Foundation:
  1. Deploy Home Assistant VM in Proxmox (2 hours)
  2. Buy and set up Kasa smart plugs (30 min)
  3. Connect plugs to Home Assistant
  4. Set up basic light automations

WEEK 2 — Cat Basics:
  5. Set up Petlibro feeder + fountain
  6. Integrate with Home Assistant
  7. Set up feeding schedule automations
  8. Install Reolink camera + Frigate NVR

WEEK 3 — Comfort:
  9. Add SwitchBot blind tilt
  10. Set up blind automations (sunrise/sunset)
  11. Smart plug for coffee maker
  12. Morning routine automation

MONTH 2 — Expand:
  13. Add LIFX bulbs for color/dimming
  14. Set up Adaptive Lighting (HACS)
  15. Build cat health dashboard in budget app
  16. Add litter box monitoring

AFTER MOVE — Permanent:
  17. Roborock robot vacuum
  18. IKEA FYRTUR blinds
  19. Litter-Robot 4
  20. Full multi-room camera setup with Frigate
```

---

## 💰 Cost Summary

| Category | Starter Cost | Full Setup |
|----------|-------------|-----------|
| Lighting | $40–$90 | $150–$300 |
| Robot Vacuum | — | $350–$900 |
| Blinds | $45–$90 | $200–$600 |
| Coffee/Tea | $10–$30 | $100–$180 |
| Cat Feeder | $60–$80 | $60–$150 |
| Cat Fountain | $40–$60 | $40–$60 |
| Cat Cameras | $35–$70 | $100–$200 |
| Litter Box | — | $200–$700 |
| Cat Toys | $35 | $35–$115 |
| **Total Starter** | **~$315** | |
| **Total Full Setup** | | **~$1,300–$3,200** |

**Home Assistant runs free on your existing homelab — $0 software cost.**

---

## 🔑 Key Principle: Local-First, Cloud-Free

Every device recommendation above prioritizes **local API access** over cloud
dependency. Your homelab philosophy (self-hosted, private, no subscriptions)
applies to home automation too:

- Kasa plugs: local API, no cloud required
- Roborock: local API via Home Assistant integration
- Reolink cameras: local RTSP stream, no cloud subscription
- Frigate: runs on YOUR hardware, no cloud AI
- Home Assistant: 100% local, no subscription

**The goal:** Your home automation works even if the internet is down.
Everything talks to your homelab, not someone else's cloud.
