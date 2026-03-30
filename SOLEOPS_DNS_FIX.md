# getsoleops.com DNS Fix — Permanent Solution
# Last Updated: 2026-03-29

## STATUS: Server-side is 100% READY ✅

The cloudflared tunnel already routes `getsoleops.com → http://localhost:8504`.
SoleOps service is active. Tunnel is active.

**Only DNS is broken.** GoDaddy A record → `74.113.167.8` fails (NAT hairpin).
Fix: Switch to Cloudflare Tunnel via CNAME.

---

## TUNNEL ID (copy this)
```
1814c511-5d48-4b71-b31e-7acece6fe9f1
```

## CNAME TARGET (copy this)
```
1814c511-5d48-4b71-b31e-7acece6fe9f1.cfargotunnel.com
```

---

## STEP 1 — Add getsoleops.com to Cloudflare (2 min)

1. Go to: https://dash.cloudflare.com
2. Click **"Add a domain"**
3. Enter: `getsoleops.com` → Continue
4. Select **Free plan** → Continue
5. Cloudflare scans DNS → Continue
6. **WRITE DOWN the 2 nameservers Cloudflare gives you** (needed for Step 2)

---

## STEP 2 — Update GoDaddy Nameservers (2 min)

1. Go to: https://dcc.godaddy.com/manage/getsoleops.com/dns
2. Scroll to **Nameservers** section → Click **"Change"**
3. Select **"Enter my own nameservers"**
4. Remove old nameservers:
   - ~~ns47.domaincontrol.com~~
   - ~~ns48.domaincontrol.com~~
5. Enter the **2 Cloudflare nameservers from Step 1**
6. Click **Save**

---

## STEP 3 — Add CNAME Records in Cloudflare (1 min)

In Cloudflare dashboard → getsoleops.com → **DNS** → **Add record** (do this TWICE):

### Record 1 (root domain):
| Field | Value |
|-------|-------|
| Type | CNAME |
| Name | getsoleops.com |
| Target | `1814c511-5d48-4b71-b31e-7acece6fe9f1.cfargotunnel.com` |
| Proxy | ✅ Proxied (orange cloud ON) |

### Record 2 (www):
| Field | Value |
|-------|-------|
| Type | CNAME |
| Name | www |
| Target | `1814c511-5d48-4b71-b31e-7acece6fe9f1.cfargotunnel.com` |
| Proxy | ✅ Proxied (orange cloud ON) |

### ⚠️ IMPORTANT: Delete any A records pointing to 74.113.167.8

---

## STEP 4 — Verify (after ~5 min)

```bash
# Check DNS propagated
dig getsoleops.com CNAME +short

# Test HTTP response
curl -I https://getsoleops.com

# Expected: HTTP/2 200
```

---

## WHY THIS WORKS

```
User → getsoleops.com
     → Cloudflare CDN (CNAME → tunnel)
     → cloudflared tunnel (running on CT100)
     → localhost:8504 (SoleOps streamlit app)
     ← HTTP 200 ✅
```

No home IP exposed. Free SSL. DDoS protection. No NAT hairpin.

---

## FALLBACK: Quick local test (while waiting for DNS propagation)

Add to /etc/hosts on your Mac (remove after DNS works):
```
100.95.125.112 getsoleops.com www.getsoleops.com
```
Then open http://getsoleops.com in browser — should load SoleOps immediately.
