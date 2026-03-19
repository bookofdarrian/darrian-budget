# SoleOps — Domain Setup Guide
**Domain: getsoleops.com | Backup: soleops.net**
**Created: 2026-03-19 | Owner: Darrian Belcher**

---

## ✅ Domain Status

| Domain | Status | Action |
|--------|--------|--------|
| `getsoleops.com` | ✅ **AVAILABLE** — register immediately | → Cloudflare Registrar |
| `soleops.net` | ✅ **AVAILABLE** — grab as backup redirect | → Cloudflare Registrar |
| `soleops.com` | ❌ TAKEN (NY registrant, expires May 2026) | Backorder only |
| `soleops.io` | ⚠️ Status unclear — check Cloudflare UI | Verify first |

---

## 🛒 Step 1 — Register the Domain (5 minutes)

**Use Cloudflare Registrar — at-cost pricing, no markup, free WHOIS privacy.**

1. Go to: https://dash.cloudflare.com → **Domain Registration** → **Register Domains**
2. Search: `getsoleops.com`
3. Add to cart → Checkout → ~$10.44/yr
4. Also search: `soleops.net` → ~$13/yr (grab as redirect backup)
5. Auto-renew: **ON** — you don't want this to expire

> **Why Cloudflare?** Same registrar you use for peachstatesavings.com. One dashboard.
> At-cost pricing = no GoDaddy markup. WHOIS privacy included free.

---

## 🌐 Step 2 — Configure Cloudflare DNS (10 minutes)

After registration, go to: https://dash.cloudflare.com → **getsoleops.com** → **DNS**

### Get Your Public IP First
```bash
# Run this from CT100 or your Mac on home network
curl ifconfig.me
```

### DNS Records to Add

| Type | Name | Content | TTL | Proxy |
|------|------|---------|-----|-------|
| `A` | `@` | `<your_public_ip>` | Auto | ✅ Proxied |
| `A` | `www` | `<your_public_ip>` | Auto | ✅ Proxied |
| `CNAME` | `app` | `getsoleops.com` | Auto | ✅ Proxied |

> **Proxied = ON (orange cloud)** — Cloudflare hides your home IP and gives you DDoS protection, free CDN, and better SSL.

### Cloudflare SSL/TLS Settings
Go to: **SSL/TLS** → Set mode to **Full (strict)**

> This ensures the Cloudflare → CT100 leg is also encrypted (matches peachstatesavings.com setup).

---

## 🔧 Step 3 — Home Router Port Forward (5 minutes)

Your router must forward ports 80 and 443 to CT100.

> If peachstatesavings.com already works, this is **already done** — skip this step.

If not already configured:
1. Log into your router: `http://172.17.84.1` (admin credentials in your password manager)
2. Find: **Port Forwarding** / **Virtual Server** / **NAT Rules**
3. Add these rules:

| External Port | Internal IP | Internal Port | Protocol |
|--------------|-------------|---------------|----------|
| 80 | 100.117.1.171 | 80 | TCP |
| 443 | 100.117.1.171 | 443 | TCP |

---

## ⚙️ Step 4 — Deploy SoleOps on CT100 (10 minutes)

SSH into CT100 and run the deploy script:

```bash
ssh root@100.95.125.112

# Navigate to app directory
cd /opt/darrian-budget

# Pull latest code (includes this domain update)
git pull origin main

# Run the deployment script
bash deploy_soleops.sh getsoleops.com
```

The script will:
1. Pull latest code
2. Install requirements
3. Create systemd service (`soleops.service`) on port 8502
4. Configure Nginx for `getsoleops.com`
5. Request Let's Encrypt SSL certificate via certbot

> **Note:** When certbot asks for an email, use `darrian@peachstatesavings.com`

---

## 🌐 Step 5 — Add Nginx Proxy Manager Entry (Alternative to certbot)

If you prefer Nginx Proxy Manager (like peachstatesavings.com setup):

1. Go to: http://100.95.125.112:81 (Nginx Proxy Manager)
2. **Proxy Hosts** → **Add Proxy Host**

| Setting | Value |
|---------|-------|
| Domain Names | `getsoleops.com`, `www.getsoleops.com` |
| Scheme | `http` |
| Forward Hostname / IP | `127.0.0.1` |
| Forward Port | `8502` |
| Websockets Support | ✅ ON |
| Block Common Exploits | ✅ ON |

3. **SSL** tab → Let's Encrypt → check **Force SSL** + **HTTP/2 Support**
4. Save → certificate auto-provisions

---

## 🔀 Step 6 — Set Up soleops.net Redirect (5 minutes)

Point `soleops.net` → `getsoleops.com` via Cloudflare redirect rule:

1. In Cloudflare dashboard → **soleops.net** → **Rules** → **Redirect Rules**
2. **Create Rule:**

| Setting | Value |
|---------|-------|
| Rule name | `Redirect to getsoleops.com` |
| Field | Hostname |
| Operator | equals |
| Value | `soleops.net` |
| Action | Dynamic Redirect |
| Expression | `https://getsoleops.com${http.request.uri.path}` |
| Status Code | 301 (permanent) |

---

## 🔐 Step 7 — Verify SSL + Uptime (2 minutes)

```bash
# Test HTTPS from your Mac
curl -I https://getsoleops.com
# Should return: HTTP/2 200 (or 302 if landing page redirects)

# Check systemd service on CT100
ssh root@100.95.125.112 "systemctl status soleops"

# Watch live logs
ssh root@100.95.125.112 "journalctl -u soleops -f"
```

---

## 📊 Step 8 — Add to Uptime Monitoring

Add `https://getsoleops.com` to your existing uptime monitor:

1. Go to: http://100.95.125.112 → **Uptime Kuma** (or page 42 in the app)
2. Add monitor:
   - Type: HTTP(s)
   - Name: `SoleOps - getsoleops.com`
   - URL: `https://getsoleops.com`
   - Heartbeat: every 60 seconds
   - Notifications: Telegram + Pushover

---

## 💸 Total Cost

| Item | Cost | Where |
|------|------|-------|
| `getsoleops.com` | ~$10.44/yr | Cloudflare Registrar |
| `soleops.net` | ~$13/yr | Cloudflare Registrar (optional backup) |
| SSL Certificate | **FREE** | Let's Encrypt via certbot/NPM |
| CDN + DDoS | **FREE** | Cloudflare free tier |
| Hosting | **FREE** | Already running CT100 |
| **Total** | **~$23/yr** | |

---

## ⚡ Quick Reference — After Setup

| URL | What It Is |
|-----|-----------|
| https://getsoleops.com | Public landing page (no auth) |
| https://getsoleops.com/login | Login page |
| https://www.getsoleops.com | www redirect → apex |
| https://soleops.net | Redirects to getsoleops.com |
| http://100.95.125.112:8502 | Direct Tailscale access (dev/debug) |

### Service Management on CT100
```bash
# Status
sudo systemctl status soleops

# Restart
sudo systemctl restart soleops

# Logs (live)
sudo journalctl -u soleops -f

# Logs (last 50 lines)
sudo journalctl -u soleops -n 50
```

---

## 🚀 Post-Launch Checklist

- [ ] Register `getsoleops.com` on Cloudflare Registrar
- [ ] Register `soleops.net` on Cloudflare Registrar (redirect backup)
- [ ] Set DNS A records pointing to home public IP
- [ ] Cloudflare SSL/TLS → Full (strict)
- [ ] SSH into CT100 → `git pull && bash deploy_soleops.sh getsoleops.com`
- [ ] Verify https://getsoleops.com loads SoleOps landing page
- [ ] Add to Uptime Kuma monitoring
- [ ] Post in r/flipping: "SoleOps is live — first 20 users get 30-day Pro free"
- [ ] Post in Reseller Discord servers

---

*SoleOps Domain Setup Guide | Updated: 2026-03-19*
*Owner: Darrian Belcher | darrian@peachstatesavings.com*
