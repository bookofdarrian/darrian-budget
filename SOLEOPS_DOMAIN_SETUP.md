# SoleOps — Domain Setup Guide
**Domain: getsoleops.com ✅ REGISTERED**
**Updated: 2026-03-19 | Owner: Darrian Belcher**

---

## ✅ Domain Status

| Domain | Status | Registrar |
|--------|--------|-----------|
| `getsoleops.com` | ✅ **REGISTERED** — Auto-renew ON, exp Mar 2029 | GoDaddy |
| `soleops.net` | Available — grab as backup redirect if desired | — |
| `soleops.com` | ❌ TAKEN (NY registrant, expires May 2026) | — |

**Your public home IP:** `74.113.167.8`

---

## 🌐 Step 1 — Configure DNS in GoDaddy (5 minutes)

1. Go to: https://dcc.godaddy.com/manage/getsoleops.com/dns
   *(or: GoDaddy dashboard → SoleOps → DNS tab)*
2. Delete any default GoDaddy placeholder A records
3. Add these records:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| `A` | `@` | `74.113.167.8` | 600 sec |
| `A` | `www` | `74.113.167.8` | 600 sec |
| `CNAME` | `app` | `getsoleops.com` | 1 Hour |

4. Save. DNS propagates in 5–30 minutes (usually fast with GoDaddy).

> **Verify propagation:**
> ```bash
> dig getsoleops.com A +short
> # Should return: 74.113.167.8
> ```

---

## 🔧 Step 2 — Verify Router Port Forward (Already Done ✅)

Since `peachstatesavings.com` already works on this IP, ports 80 and 443 are already forwarded to CT100. **Skip this step.**

If you ever need to re-verify:
```bash
# From outside your network (phone data), test:
curl -I http://74.113.167.8
# Should hit CT100 Nginx
```

---

## ⚙️ Step 3 — Deploy SoleOps on CT100 (10 minutes)

```bash
# SSH into CT100
ssh root@100.95.125.112

# Pull latest code
cd /opt/darrian-budget
git pull origin main

# Run the one-click deploy
bash deploy_soleops.sh getsoleops.com
```

When certbot asks for an SSL email, use: `darrian@peachstatesavings.com`

The script handles:
- ✅ Python requirements install
- ✅ `soleops.service` systemd unit (port 8502)
- ✅ Nginx config for `getsoleops.com` + `www.getsoleops.com`
- ✅ Let's Encrypt SSL certificate (auto-renews)
- ✅ HTTPS redirect (HTTP → HTTPS)

---

## 🌐 Step 3b — ALTERNATIVE: Use Nginx Proxy Manager

If you prefer NPM over raw certbot (same way peachstatesavings.com is set up):

1. Go to: http://100.95.125.112:81
2. **Proxy Hosts** → **Add Proxy Host**

| Setting | Value |
|---------|-------|
| Domain Names | `getsoleops.com`, `www.getsoleops.com` |
| Scheme | `http` |
| Forward Hostname / IP | `127.0.0.1` |
| Forward Port | `8502` |
| Websockets Support | ✅ ON |
| Block Common Exploits | ✅ ON |

3. **SSL tab** → Request Let's Encrypt cert → ✅ Force SSL → ✅ HTTP/2
4. Save → cert provisions automatically

---

## 🔐 Step 4 — Verify SSL + Site is Live

```bash
# Test HTTPS response
curl -I https://getsoleops.com
# Expected: HTTP/2 200

# Check SoleOps service status on CT100
ssh root@100.95.125.112 "systemctl status soleops"

# Watch live logs
ssh root@100.95.125.112 "journalctl -u soleops -f"
```

Visit: **https://getsoleops.com** → you should see the SoleOps landing page (dark theme, "Stop Leaving Money on the Table" hero).

---

## 📊 Step 5 — Add to Uptime Monitoring

1. Open the budget app → page 42 (Uptime Kuma) or go to http://100.95.125.112
2. Add monitor:
   - Type: **HTTP(s)**
   - Name: `SoleOps — getsoleops.com`
   - URL: `https://getsoleops.com`
   - Interval: **60 seconds**
   - Notifications: Telegram + Pushover

---

## 💸 Cost Summary

| Item | Cost | Notes |
|------|------|-------|
| `getsoleops.com` | $22.99/yr (GoDaddy) | Already registered ✅ |
| SSL Certificate | **FREE** | Let's Encrypt via certbot |
| CDN / DDoS | — | Consider Cloudflare free tier (point GoDaddy nameservers to Cloudflare) |
| Hosting | **FREE** | CT100 already running 24/7 |
| **Total** | **$22.99/yr** | |

> **Optional upgrade:** Transfer DNS management to Cloudflare for free CDN + DDoS protection.
> GoDaddy dashboard → DNS tab → change nameservers to:
> `ns1.cloudflare.com` / `ns2.cloudflare.com`
> Then manage all DNS in the Cloudflare dashboard (same as peachstatesavings.com).

---

## ⚡ Quick Reference

| URL | What It Is |
|-----|-----------|
| https://getsoleops.com | Public SoleOps landing page |
| https://www.getsoleops.com | Redirects to apex |
| http://100.95.125.112:8502 | Direct Tailscale access (dev/debug) |

### Service Management on CT100
```bash
sudo systemctl status soleops      # Check status
sudo systemctl restart soleops     # Restart
sudo journalctl -u soleops -f      # Live logs
sudo journalctl -u soleops -n 50   # Last 50 lines
```

---

## 🚀 Launch Checklist

- [x] Register `getsoleops.com` (GoDaddy, auto-renew on, exp 2029)
- [ ] Set DNS A records: `@` + `www` → `74.113.167.8`
- [ ] Wait for DNS propagation (`dig getsoleops.com A +short`)
- [ ] SSH into CT100 → `git pull && bash deploy_soleops.sh getsoleops.com`
- [ ] Verify https://getsoleops.com loads SoleOps landing page
- [ ] Add to Uptime Kuma monitoring
- [ ] (Optional) Point DNS to Cloudflare for free CDN
- [ ] Post in r/flipping: "SoleOps is live — first 20 users get 30-day Pro free"
- [ ] Post in Reseller Discord servers

---

*SoleOps Domain Setup | Updated: 2026-03-19*
*Public IP: 74.113.167.8 | CT100: 100.95.125.112*
*Owner: Darrian Belcher | darrian@peachstatesavings.com*
