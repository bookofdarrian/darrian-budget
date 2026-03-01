import streamlit as st
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="Homelab Dashboard — Peach State Savings",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="auto"
)

inject_css()
require_login()
render_sidebar_brand()
render_sidebar_user_widget()

# ── Custom CSS for service cards ──────────────────────────────────────────────
st.markdown("""
<style>
.service-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #2d2d4e;
    border-radius: 16px;
    padding: 20px;
    text-align: center;
    transition: all 0.2s ease;
    cursor: pointer;
    text-decoration: none;
    display: block;
    margin-bottom: 12px;
}
.service-card:hover {
    border-color: #ff6b35;
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(255, 107, 53, 0.2);
}
.service-icon {
    font-size: 2.5rem;
    margin-bottom: 8px;
    display: block;
}
.service-name {
    color: #ffffff;
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 4px;
}
.service-desc {
    color: #8888aa;
    font-size: 0.75rem;
}
.service-status-up {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: #21c354;
    border-radius: 50%;
    margin-right: 4px;
}
.section-header {
    color: #ff6b35;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin: 24px 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #2d2d4e;
}
</style>
""", unsafe_allow_html=True)

st.title("🖥️ Homelab Dashboard")
st.caption("All your self-hosted services — accessible via Tailscale from anywhere")

BASE = "http://100.95.125.112"
PROXY = f"{BASE}:8090"  # favicon proxy — injects emoji icons into browser tabs

# ── Service definitions ───────────────────────────────────────────────────────
SERVICES = {
    "📱 Apps": [
        {
            "icon": "🍑",
            "name": "Peach State Savings",
            "desc": "Budget · Finance · AI Insights",
            "url": f"{BASE}:8501",
            "public": "https://peachstatesavings.com",
        },
        {
            "icon": "📸",
            "name": "Immich",
            "desc": "Photo library · AI search · Face recognition",
            "url": f"{PROXY}/photos/",
        },
        {
            "icon": "🔐",
            "name": "Vaultwarden",
            "desc": "Password manager · Bitwarden-compatible",
            "url": f"https://100.95.125.112:8443",
        },
        {
            "icon": "🤖",
            "name": "Open WebUI",
            "desc": "Chat with local AI models",
            "url": f"{PROXY}/ai/",
        },
        {
            "icon": "✅",
            "name": "Todo App",
            "desc": "Task management",
            "url": f"{BASE}:3456",
        },
    ],
    "🔧 Dev Tools": [
        {
            "icon": "💻",
            "name": "code-server",
            "desc": "VS Code in the browser",
            "url": f"{PROXY}/code/",
        },
        {
            "icon": "🦙",
            "name": "Ollama",
            "desc": "Local LLM API · Llama · Mistral · Phi",
            "url": f"{BASE}:11434",
        },
        {
            "icon": "🌐",
            "name": "Nginx Proxy Manager",
            "desc": "Reverse proxy · SSL · Domain routing",
            "url": f"{BASE}:81",
        },
    ],
    "📊 Monitoring": [
        {
            "icon": "📊",
            "name": "Grafana",
            "desc": "Metrics · Dashboards · Alerts",
            "url": f"https://100.95.125.112:3000",
        },
        {
            "icon": "🔥",
            "name": "Prometheus",
            "desc": "Metrics collection",
            "url": f"{BASE}:9090",
        },
        {
            "icon": "🐳",
            "name": "Portainer",
            "desc": "Docker container management",
            "url": f"{PROXY}/portainer/",
        },
        {
            "icon": "🖥️",
            "name": "Proxmox",
            "desc": "VM & container hypervisor",
            "url": "https://100.95.125.112:8006",
        },
    ],
}

# ── Render sections ───────────────────────────────────────────────────────────
for section, services in SERVICES.items():
    st.markdown(f'<div class="section-header">{section}</div>', unsafe_allow_html=True)
    
    cols = st.columns(len(services) if len(services) <= 4 else 4)
    for i, svc in enumerate(services):
        with cols[i % 4]:
            public_link = svc.get("public", "")
            public_badge = f'<br><span style="color:#ff6b35;font-size:0.65rem;">🌐 Public</span>' if public_link else ""
            
            st.markdown(f"""
            <a href="{svc['url']}" target="_blank" class="service-card">
                <span class="service-icon">{svc['icon']}</span>
                <div class="service-name"><span class="service-status-up"></span>{svc['name']}</div>
                <div class="service-desc">{svc['desc']}{public_badge}</div>
            </a>
            """, unsafe_allow_html=True)

st.markdown("---")

# ── Quick stats ───────────────────────────────────────────────────────────────
st.subheader("⚡ Quick Info")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Tailscale IP", "100.95.125.112")
c2.metric("Local IP", "100.117.1.171")
c3.metric("Services Running", "13")
c4.metric("Public Domain", "peachstatesavings.com")

st.markdown("---")

# ── iPhone Shortcuts guide ────────────────────────────────────────────────────
with st.expander("📱 iPhone Home Screen Setup — Custom Icons via Shortcuts"):
    st.markdown("""
    ### Add Custom Icons to iPhone Home Screen
    
    **For each service, follow these steps:**
    
    1. Open **Shortcuts** app on iPhone
    2. Tap **+** (top right) → **Add Action**
    3. Search for **"Open URL"** → select it
    4. Enter the service URL (e.g. `http://100.95.125.112:2283`)
    5. Tap the **icon area** (top left of the shortcut) → **Choose Photo** or use an emoji
    6. Tap **Add to Home Screen** → set the name → **Add**
    
    **Recommended icon images to download:**
    
    | Service | Icon Source |
    |---------|------------|
    | Immich | [immich.app](https://immich.app) — use their logo |
    | Grafana | Orange flame logo — search "Grafana logo PNG" |
    | Portainer | Teal whale — search "Portainer logo PNG" |
    | Vaultwarden | Blue shield — use Bitwarden logo |
    | Open WebUI | Dark AI icon — search "Open WebUI logo" |
    | code-server | VS Code blue logo |
    | Proxmox | Orange/black server logo |
    
    **Pro tip:** Use [macOS Shortcuts](https://support.apple.com/guide/shortcuts-mac/welcome/mac) 
    to batch-create all shortcuts at once, then AirDrop to iPhone.
    """)

with st.expander("🔒 Tailscale Required"):
    st.markdown("""
    All `100.95.125.112` URLs only work when **Tailscale is active** on your device.
    
    - **iPhone:** Tailscale app → toggle ON
    - **Mac:** Tailscale menu bar → Connect
    - **Account:** dbelcher003@gmail.com
    
    `peachstatesavings.com` works without Tailscale (public via Cloudflare Tunnel).
    """)
