# 🐱 Cat Automation Setup Guide

## What's running
- **Aura** (`http://aura:8000`) now has `/cat/feeding` POST and `/cat/feedings` GET endpoints
- **budget-postgres** has a `cat_feedings` table (auto-created on Aura restart)
- **Home Assistant** triggers the feeds and calls Aura to log them

---

## Step 1 — Add rest_command to Home Assistant

SSH into your server and edit the HA config file:

```bash
ssh root@100.95.125.112
docker exec -it homeassistant bash
nano /config/configuration.yaml
```

Add this block:

```yaml
# configuration.yaml
rest_command:
  log_cat_breakfast:
    url: "http://aura:8000/cat/feeding"
    method: POST
    content_type: "application/json"
    payload: '{"meal": "breakfast", "portions": 1, "source": "home_assistant", "cat_name": "cat"}'

  log_cat_dinner:
    url: "http://aura:8000/cat/feeding"
    method: POST
    content_type: "application/json"
    payload: '{"meal": "dinner", "portions": 1, "source": "home_assistant", "cat_name": "cat"}'

  log_cat_manual:
    url: "http://aura:8000/cat/feeding"
    method: POST
    content_type: "application/json"
    payload: '{"meal": "manual", "portions": 0.5, "source": "manual_button", "cat_name": "cat"}'
```

---

## Step 2 — Create Automations

In HA: **Settings → Automations → Create → Edit as YAML**

### 🌅 7AM Breakfast

```yaml
alias: "🐱 Cat Breakfast 7AM"
description: "Dispense breakfast and log to Postgres"
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: button.press
    target:
      entity_id: button.YOUR_FEEDER_ENTITY_ID  # replace after adding Petlibro integration
  - service: rest_command.log_cat_breakfast
  - service: notify.mobile_app_your_phone
    data:
      title: "🐱 Breakfast served"
      message: "Cat fed at 7AM ✅"
mode: single
```

### 🌆 6PM Dinner

```yaml
alias: "🐱 Cat Dinner 6PM"
description: "Dispense dinner and log to Postgres"
trigger:
  - platform: time
    at: "18:00:00"
action:
  - service: button.press
    target:
      entity_id: button.YOUR_FEEDER_ENTITY_ID
  - service: rest_command.log_cat_dinner
  - service: notify.mobile_app_your_phone
    data:
      title: "🐱 Dinner served"
      message: "Cat fed at 6PM ✅"
mode: single
```

### ⚠️ Bowl Still Full Alert (2 hours after each feed)

```yaml
alias: "🐱 Bowl Still Full — Morning Check"
description: "Alert if cat hasn't eaten 2 hours after breakfast"
trigger:
  - platform: time
    at: "09:00:00"
condition:
  # Optional: add a condition if your feeder has a food-level sensor
  # - condition: state
  #   entity_id: binary_sensor.feeder_food_low
  #   state: "off"
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "🐱 Cat check needed"
      message: "2 hours since breakfast — did the cat eat? Check the camera."
mode: single
```

```yaml
alias: "🐱 Bowl Still Full — Evening Check"
trigger:
  - platform: time
    at: "20:00:00"
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "🐱 Cat check needed"
      message: "2 hours since dinner — did the cat eat? Check the camera."
mode: single
```

---

## Step 3 — Replace entity IDs

After adding the Petlibro HACS integration:
1. Go to **Settings → Devices & Services → Petlibro → your feeder**
2. Look for a **Button** entity called something like `button.granary_feeder_dispense`
3. Replace `button.YOUR_FEEDER_ENTITY_ID` in the automations above

---

## Step 4 — Add Petlibro to HA via HACS

```bash
# Install HACS (if not already installed)
docker exec -it homeassistant bash
wget -O - https://get.hacs.xyz | bash -
exit
docker restart homeassistant
```

Then in HA:
1. HACS → Integrations → ⋮ → Custom Repositories
2. Add: `https://github.com/jampez77/Petlibro` → Integration
3. Install → Restart HA
4. Settings → Devices & Services → Add Integration → Petlibro
5. Login with your Petlibro account

---

## Verify it's working

```bash
# Test the Aura endpoint directly
curl -X POST http://100.95.125.112:8000/cat/feeding \
  -H "Content-Type: application/json" \
  -d '{"meal": "test", "portions": 1, "source": "manual_test"}'

# View feeding history
curl http://100.95.125.112:8000/cat/feedings
```

---

## Query feeding history in Postgres

```sql
-- All feedings
SELECT cat_name, meal, portions, source, fed_at
FROM cat_feedings
ORDER BY fed_at DESC
LIMIT 30;

-- Feedings per day
SELECT DATE(fed_at) as day, COUNT(*) as meals
FROM cat_feedings
GROUP BY DATE(fed_at)
ORDER BY day DESC;

-- Days where a meal was skipped (< 2 meals logged)
SELECT DATE(fed_at) as day, COUNT(*) as meals
FROM cat_feedings
GROUP BY DATE(fed_at)
HAVING COUNT(*) < 2
ORDER BY day DESC;
```
