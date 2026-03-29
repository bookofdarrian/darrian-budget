# Router Port Forwarding — getsoleops.com SSL Setup
_Last updated: 2026-03-29_

## Current Status
- ✅ soleops.service: **active (running)** on CT100, port 8504
- ✅ NPM (Nginx Proxy Manager): listening on ports 80 & 443
- ✅ DNS: getsoleops.com → 74.113.167.8 (your public IP)
- ✅ NPM proxy config: getsoleops.com → 172.18.0.1:8504 ✓
- ✅ Internal test: `curl -H "Host: getsoleops.com" http://localhost` → HTTP 200 ✓
- ❌ **Public access blocked: router port forwarding not configured**

---

## Step 1 — Open Your Router Admin Panel

Open a browser and go to: **http://100.117.1.1**

_This is your router/gateway IP. Look for:_
- Xfinity: Advanced → Port Forwarding
- AT&T: Firewall → NAT/Gaming
- Netgear: Advanced → Port Forwarding/Port Triggering
- TP-Link: Advanced → NAT Forwarding → Port Forwarding
- Asus: WAN → Virtual Server/Port Forwarding
- Ubiquiti: Firewall & Security → Port Forwarding

---

## Step 2 — Add Port Forwarding Rules

Add **TWO** rules:

| Rule | External Port | Internal IP | Internal Port | Protocol |
|------|--------------|-------------|---------------|----------|
| HTTP | 80 | 100.117.1.127 | 80 | TCP |
| HTTPS | 443 | 100.117.1.127 | 443 | TCP |

**Internal IP = 100.117.1.127** (CT100 / docker-host)

---

## Step 3 — Get SSL Certificate (after port forwarding is live)

Once port 80 is forwarded, run this to get a free Let's Encrypt cert:

```bash
ssh root@100.95.125.112 "docker exec nginx-proxy-manager certbot certonly \
  --webroot -w /data/letsencrypt-acme-challenge \
  -d getsoleops.com -d www.getsoleops.com \
  --email darrianebelcher@gmail.com \
  --agree-tos --non-interactive --no-eff-email 2>&1"
```

If certbot succeeds, copy the certs to NPM:

```bash
ssh root@100.95.125.112 << 'EOF'
# Copy certs
mkdir -p /var/lib/docker/volumes/homelab_npm_data/_data/custom_ssl/
cp /etc/letsencrypt/live/getsoleops.com/fullchain.pem \
   /var/lib/docker/volumes/homelab_npm_data/_data/custom_ssl/getsoleops_fullchain.pem
cp /etc/letsencrypt/live/getsoleops.com/privkey.pem \
   /var/lib/docker/volumes/homelab_npm_data/_data/custom_ssl/getsoleops_privkey.pem
chmod 644 /var/lib/docker/volumes/homelab_npm_data/_data/custom_ssl/*.pem

# Insert cert into NPM DB
sqlite3 /var/lib/docker/volumes/homelab_npm_data/_data/database.sqlite \
  "INSERT OR IGNORE INTO certificate (provider, nice_name, domain_names, expires_on, meta, created_on, modified_on, owner_user_id) 
   VALUES ('letsencrypt', 'getsoleops.com', '[\"getsoleops.com\",\"www.getsoleops.com\"]', 
           datetime('now', '+90 days'), '{}', datetime('now'), datetime('now'), 1);"
CERT_ID=$(sqlite3 /var/lib/docker/volumes/homelab_npm_data/_data/database.sqlite \
  "SELECT id FROM certificate WHERE nice_name='getsoleops.com' ORDER BY id DESC LIMIT 1;")
echo "Cert ID: $CERT_ID"
EOF
```

Then update `/var/lib/docker/volumes/homelab_npm_data/_data/nginx/proxy_host/4.conf` to add SSL.

---

## Alternative: Cloudflare Tunnel (No Port Forwarding Needed)

If you can't access the router, use Cloudflare Tunnel instead:

```bash
# On CT100
ssh root@100.95.125.112

# Install cloudflared
curl -L --output cloudflared.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
dpkg -i cloudflared.deb

# Authenticate (will print a URL — open it in your browser)
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create soleops

# Configure
cat > /etc/cloudflared/config.yml << 'CONF'
tunnel: soleops
credentials-file: /root/.cloudflared/<TUNNEL-ID>.json
ingress:
  - hostname: getsoleops.com
    service: http://localhost:8504
  - service: http_status:404
CONF

# Route domain
cloudflared tunnel route dns soleops getsoleops.com

# Run as service
cloudflared service install
systemctl start cloudflared
systemctl enable cloudflared
```

Then update GoDaddy DNS:
- Delete the A record for getsoleops.com
- Add CNAME: `getsoleops.com` → `<TUNNEL-ID>.cfargotunnel.com`

---

## Verify After Port Forward

```bash
# Test from Mac
curl -s -o /dev/null -w "HTTP %{http_code}" http://getsoleops.com
# Should return: HTTP 200

# Test via Tailscale (always works)
curl -s -H "Host: getsoleops.com" http://100.95.125.112:80
```
