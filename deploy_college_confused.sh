#!/bin/bash
# ============================================================
# College Confused — One-Click Deployment Script
# Run this on CT100 (100.95.125.112) after git pull origin main
# Usage: bash deploy_college_confused.sh
# ============================================================

set -e  # Exit on any error

echo ""
echo "🎓 College Confused — Deployment Script"
echo "========================================"
echo ""

# ── 1. Git pull latest code ──────────────────────────────────
echo "📥 Step 1/4: Pulling latest code from main..."
cd /opt/darrian-budget
git pull origin main
echo "✅ Code updated."
echo ""

# ── 2. Install/verify requirements ──────────────────────────
echo "📦 Step 2/4: Checking Python requirements..."
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

# ── 3. Write Nginx vhost for collegeconfused.org ─────────────
echo "🌐 Step 3/4: Configuring Nginx for collegeconfused.org..."

NGINX_CONF="/etc/nginx/sites-available/collegeconfused.org"

sudo tee "$NGINX_CONF" > /dev/null << 'NGINX_EOF'
server {
    listen 80;
    server_name collegeconfused.org www.collegeconfused.org;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_buffering off;
    }

    # Streamlit websocket support
    location /_stcore/stream {
        proxy_pass http://127.0.0.1:8501/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    # SEO: robots.txt
    location = /robots.txt {
        add_header Content-Type text/plain;
        return 200 "User-agent: *\nAllow: /\nSitemap: https://collegeconfused.org/sitemap.xml\n";
    }
}
NGINX_EOF

# Enable the site
if [ ! -f "/etc/nginx/sites-enabled/collegeconfused.org" ]; then
    sudo ln -s "$NGINX_CONF" /etc/nginx/sites-enabled/collegeconfused.org
    echo "✅ Nginx site enabled."
else
    echo "✅ Nginx site already enabled."
fi

# Test and reload Nginx
sudo nginx -t
sudo systemctl reload nginx
echo "✅ Nginx reloaded."
echo ""

# ── 4. SSL Certificate via Let's Encrypt ─────────────────────
echo "🔐 Step 4/4: Setting up SSL certificate..."

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo "  Installing certbot..."
    sudo apt-get install -y certbot python3-certbot-nginx -q
fi

# Check if cert already exists
if sudo certbot certificates 2>/dev/null | grep -q "collegeconfused.org"; then
    echo "✅ SSL certificate already exists. Renewing if needed..."
    sudo certbot renew --quiet
else
    echo "  Requesting new SSL certificate..."
    # Non-interactive: use --agree-tos and --email
    read -p "  Enter your email for SSL certificate notifications: " SSL_EMAIL
    sudo certbot --nginx \
        -d collegeconfused.org \
        -d www.collegeconfused.org \
        --non-interactive \
        --agree-tos \
        --email "$SSL_EMAIL" \
        --redirect
    echo "✅ SSL certificate installed. HTTPS enabled!"
fi
echo ""

# ── 5. Restart Streamlit ──────────────────────────────────────
echo "🚀 Restarting Streamlit..."

# Try systemctl first, fall back to supervisorctl, fall back to manual
if systemctl is-active --quiet streamlit 2>/dev/null; then
    sudo systemctl restart streamlit
    echo "✅ Streamlit restarted via systemctl."
elif command -v supervisorctl &> /dev/null && supervisorctl status streamlit 2>/dev/null | grep -q RUNNING; then
    sudo supervisorctl restart streamlit
    echo "✅ Streamlit restarted via supervisorctl."
else
    echo "⚠️  Could not auto-restart Streamlit. Please restart it manually:"
    echo "   cd /opt/darrian-budget && source venv/bin/activate"
    echo "   streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &"
fi
echo ""

# ── Done ──────────────────────────────────────────────────────
echo "========================================"
echo "🎉 College Confused deployment complete!"
echo ""
echo "📍 Pages live at:"
echo "   https://collegeconfused.org              → 🏠 Homepage"
echo "   https://collegeconfused.org/CC_Home      → 🏠 Homepage"
echo "   https://collegeconfused.org/My_Timeline  → 📅 Timeline"
echo "   https://collegeconfused.org/Scholarships → 💰 Scholarships"
echo "   https://collegeconfused.org/Essay_Station → ✍️ Essays"
echo "   https://collegeconfused.org/SATACT_Prep  → 📚 SAT/ACT Prep"
echo ""
echo "⏰ DNS propagation can take up to 24 hours if you just"
echo "   updated GoDaddy. The site will appear once DNS resolves."
echo "========================================"
