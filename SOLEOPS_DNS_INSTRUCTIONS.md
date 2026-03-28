# 🌐 SoleOps DNS Update Instructions
# getsoleops.com → 74.113.167.8

## ✅ Server Stack Status (ALL DONE — no action needed here)
| Component | Status |
|-----------|--------|
| soleops.service port 8504 | ✅ Active (running, auto-restart) |
| NPM nginx proxy (getsoleops.com → port 8504) | ✅ HTTP 200 verified |
| NPM DB proxy_host id=4 | ✅ Inserted |
| SOLEOPS_APP_URL=https://getsoleops.com | ✅ In .env + committed to main |
| Docker disk | ✅ Pruned (90% → was 98%) |

---

## 🚨 ONE MANUAL STEP: Update GoDaddy DNS

**Your server public IP: `74.113.167.8`**

### Step 1 — Go to GoDaddy DNS Manager
Open: https://dcc.godaddy.com/control/getsoleops.com/dns

### Step 2 — Delete the old WebsiteBuilder A record
Find this row:
| Type | Name | Data | TTL |
|------|------|------|-----|
| A | @ | WebsiteBuilder Site | 1 Hour |

Click the trash icon → Delete → Confirm

### Step 3 — Add 2 new A records

**Record 1:**
- Type: A
- Name: @
- Value: 74.113.167.8
- TTL: 600 seconds

**Record 2:**
- Type: A
- Name: www
- Value: 74.113.167.8
- TTL: 600 seconds

Click Save ✅

---

## ⏳ After DNS Propagates (5–30 min)

Verify with: `dig getsoleops.com A +short` → should return `74.113.167.8`

Then add SSL via NPM UI:
1. Open http://100.95.125.112:81
2. Login: darrianebelcher@gmail.com
3. Find proxy host: getsoleops.com → Edit → SSL tab
4. Request Let's Encrypt cert → Force SSL → HTTP/2 → Save
