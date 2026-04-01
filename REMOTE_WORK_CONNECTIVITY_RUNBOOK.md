# Remote Work Connectivity Runbook

This runbook standardizes remote-work setup for Mac + Windows laptops, portable monitor, and internet failover.

## Internet Priority Profile

Primary and fallback internet options:
- Verizon (unlimited)
- Gigstreem (new house)
- Verizon line backup
- Phone dual-SIM hotspot fallback

Recommended priority for work sessions:
1. Gigstreem (lowest latency when available)
2. Verizon unlimited home service
3. Verizon line backup
4. Phone dual-SIM hotspot

## macOS Quick Setup

Run the bootstrap script:

```bash
cd ~/Downloads/darrian-budget
bash scripts/remote_work_bootstrap_macos.sh
```

To apply preferred Wi-Fi ordering automatically:

```bash
cd ~/Downloads/darrian-budget
APPLY_WIFI_ORDER=1 PREFERRED_WIFI_SSIDS="Gigstreem,Verizon,Verizon Line,Dual-SIM Hotspot" bash scripts/remote_work_bootstrap_macos.sh
```

## Monitor Setup (KYY X90D)

Driver/software:
- DisplayLink Manager (macOS): installed via Homebrew cask `displaylink`
- DisplayLink Manager (Windows): https://www.synaptics.com/products/displaylink-graphics/downloads/windows

Connection order:
1. Use USB-C data/video cable to monitor data port
2. Use separate power to monitor power/PD port
3. If not detected, switch to HDMI (video) + USB power mode

## Browser Bookmarks

Bookmark source file:
- `PEACH_STATE_BOOKMARKS.html`

Installer:

```bash
cd ~/Downloads/darrian-budget
python3 install_bookmarks.py
```

If Safari automation is blocked by permissions:
- Open Safari
- File -> Import From -> Bookmarks HTML File
- Select `PEACH_STATE_BOOKMARKS.html`

## Plug-and-Play Tab Groups

Prebuilt workspace groups are defined in `config/work_tab_groups.json`.

Open Chrome groups now:

```bash
cd ~/Downloads/darrian-budget
python3 scripts/open_work_tab_groups_macos.py chrome
```

Open Safari group now:

```bash
cd ~/Downloads/darrian-budget
python3 scripts/open_work_tab_groups_macos.py safari
```

Open all groups:

```bash
cd ~/Downloads/darrian-budget
python3 scripts/open_work_tab_groups_macos.py all
```

## Validation Checklist

- Chrome opens with Peach State bookmarks present
- Safari shows Peach State bookmark folder
- KYY monitor detected in Display settings
- At least two internet paths available before work block starts
- Hotspot tested once weekly as fallback drill
