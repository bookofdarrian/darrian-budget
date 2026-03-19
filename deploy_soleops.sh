#!/bin/bash
# ============================================================
# SoleOps — One-Click Deployment Script
# Run this on CT100 (100.95.125.112) after git pull origin main
# Usage: bash deploy_soleops.sh [--domain soleops.io]
#
# Starts SoleOps on port 8502, configures Nginx, requests SSL
# ============================================================

set -e  # Exit on any error

# ── Config ────────────────────────────────────────────────────
DOMAIN="${1:-soleops.io}"           # Override: bash deploy_soleops.sh --domain 404soleops.com
PORT=8502
APP_DIR="/opt/darrian-budget"
APP_FILE="soleops_app.py"
SERVICE_NAME="soleops"

echo ""
echo "👟 SoleOps — Deployment Script"
echo "================================"
echo "  Domain : $DOMAIN"
echo "  Port   : $PORT"
echo "  App    : $APP_DIR/$APP_FILE"
echo ""

# ── 1. Git pull latest code ──────────────────────────────────
echo "📥 Step 1/5: Pulling latest code from main..."
cd "$APP_DIR"
git pull origin main
echo "✅ Code updated."
echo ""

# ── 2. Install/verify requirements ──────────────────────────
echo "📦 Step 2/5: Checking Python requirements..."
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -q -r requirements.txt
    echo "✅ Requirements up to date."
else
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
    echo "✅ Virtual environment created and requirements installed."
fi
echo ""

# ── 3. Create systemd service ────────────────────────────────
echo "⚙️  Step 3/5: Creating systemd service for SoleOps..."

VENV_PYTHON="$APP_DIR/venv/bin/python"
STREAMLIT="$APP_DIR/venv/bin/streamlit"

sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null << SERVICE_EOF
[Unit]
Description=SoleOps Sneaker Reseller Platform (port $PORT)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=$STREAMLIT run $APP_FILE \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
Restart=always
RestartSec=5
EnvironmentFile=$APP_DIR/.env

[Install]
WantedBy=multi-user.target
SERVICE_EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

# Wait a moment then check
sleep 3
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✅ SoleOps service running on port $PORT."
else
    echo "⚠️  Service may have failed. Check: sudo journalctl -u $SERVICE_NAME -n 50"
fi
echo ""

# ── 4. Configure Nginx ───────────────────────────────────────
echo "🌐 Step 4/5: Configuring Nginx for $DOMAIN..."

NGINX_CONF="/etc/nginx/sites-available/$DOMAIN"

sudo tee "$NGINX_CONF" > /dev/null << NGINX_EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
        proxy_buffering off;
    }

    # Streamlit websocket stream
    location /_stcore/stream {
        proxy_pass http://127.0.0.1:$PORT/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    location = /robots.txt {
        add_header Content-Type text/plain;
        return 200 "User-agent: *\nAllow: /\nSitemap: https://$DOMAIN/sitemap.xml\n";
    }
}
NGINX_EOF

# Enable site
if [ ! -f "/etc/nginx/sites-enabled/$DOMAIN" ]; then
    sudo ln -s "$NGINX_CONF" "/etc/nginx/sites-enabled/$DOMAIN"
    echo "✅ Nginx site enabled."
else
    echo "✅ Nginx site already enabled."
fi

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
echo "✅ Nginx reloaded."
echo ""

# ── 5. SSL Certificate via Let's Encrypt ─────────────────────
echo "🔐 Step 5/5: Setting up SSL certificate..."

if ! command -v certbot &> /dev/null; then
    echo "  Installing certbot..."
    sudo apt-get install -y certbot python3-certbot-nginx -q
fi

if sudo certbot certificates 2>/dev/null | grep -q "$DOMAIN"; then
    echo "✅ SSL certificate already exists. Renewing if needed..."
    sudo certbot renew --quiet
else
    echo "  Requesting new SSL certificate for $DOMAIN..."
    read -p "  Enter your email for SSL certificate notifications: " SSL_EMAIL
    sudo certbot --nginx \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --email "$SSL_EMAIL" \
        --redirect
    echo "✅ SSL certificate installed. HTTPS enabled!"
fi
echo ""

# ── Done ──────────────────────────────────────────────────────
echo "================================"
echo "🎉 SoleOps deployment complete!"
echo ""
echo "📍 Live at:"
echo "   https://$DOMAIN"
echo ""
echo "🔧 Service management:"
echo "   sudo systemctl status $SERVICE_NAME"
echo "   sudo systemctl restart $SERVICE_NAME"
echo "   sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "⚠️  DNS REQUIRED — Add these records at your registrar:"
echo "   A    @      → <your public IP>  (curl ifconfig.me)"
echo "   A    www    → <your public IP>"
echo "   CNAME or A via Cloudflare if using Cloudflare DNS"
echo "================================"
