import streamlit as st

st.set_page_config(
    page_title="iPhone Setup — Peach State Savings",
    page_icon="📱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── Full-page iPhone setup wizard ─────────────────────────────────────────────
st.markdown("""
<style>
body { background: #0e1117; }
.setup-card {
    background: #12151c;
    border: 1px solid #1e2330;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 16px;
    text-decoration: none;
    color: inherit;
    cursor: pointer;
}
.setup-card:hover { border-color: #FFAB76; }
.setup-icon { font-size: 2.5rem; min-width: 50px; text-align: center; }
.setup-name { font-size: 1rem; font-weight: 700; color: #fafafa; }
.setup-url  { font-size: 0.72rem; color: #8892a4; word-break: break-all; }
.step-badge {
    background: #FFAB76;
    color: #000;
    font-size: 0.7rem;
    font-weight: 800;
    padding: 2px 8px;
    border-radius: 20px;
    display: inline-block;
    margin-bottom: 8px;
}
.tap-btn {
    display: block;
    background: linear-gradient(135deg, #FFAB76, #e8924f);
    color: #000 !important;
    font-weight: 700;
    font-size: 0.9rem;
    text-align: center;
    padding: 14px 20px;
    border-radius: 12px;
    text-decoration: none;
    margin-top: 8px;
    border: none;
    width: 100%;
}
.instructions {
    background: #1a1f2e;
    border: 1px solid #2d3550;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 24px;
    font-size: 0.85rem;
    color: #c8d0dc;
    line-height: 1.7;
}
.instructions b { color: #FFAB76; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 📱 iPhone Home Screen Setup")
st.markdown("**Open this page on your iPhone in Safari**, then follow the steps below for each app.")

st.markdown("""
<div class="instructions">
<b>How it works (30 seconds per app):</b><br>
1. Tap the link for each service below<br>
2. When it opens, tap the <b>Share button</b> (□↑) at the bottom of Safari<br>
3. Scroll down and tap <b>"Add to Home Screen"</b><br>
4. Tap <b>Add</b> — done! 🎉
</div>
""", unsafe_allow_html=True)

SERVICES = [
    {
        "icon": "🍑",
        "name": "Peach State Savings",
        "desc": "Budget · Finance · AI",
        "url": "https://peachstatesavings.com",
        "note": "✅ Works without Tailscale"
    },
    {
        "icon": "📸",
        "name": "Immich Photos",
        "desc": "Your private photo library",
        "url": "http://100.95.125.112:2283",
        "note": "⚠️ Tailscale required"
    },
    {
        "icon": "🔐",
        "name": "Vaultwarden",
        "desc": "Password manager",
        "url": "http://100.95.125.112:8888",
        "note": "⚠️ Tailscale required"
    },
    {
        "icon": "🤖",
        "name": "Open WebUI",
        "desc": "Chat with local AI",
        "url": "http://100.95.125.112:3002",
        "note": "⚠️ Tailscale required"
    },
    {
        "icon": "📊",
        "name": "Grafana",
        "desc": "Server monitoring",
        "url": "https://100.95.125.112:3000",
        "note": "⚠️ Tailscale required"
    },
    {
        "icon": "🐳",
        "name": "Portainer",
        "desc": "Docker management",
        "url": "http://100.95.125.112:9000",
        "note": "⚠️ Tailscale required"
    },
    {
        "icon": "💻",
        "name": "code-server",
        "desc": "VS Code in browser",
        "url": "http://100.95.125.112:8080",
        "note": "⚠️ Tailscale required"
    },
    {
        "icon": "🖥️",
        "name": "Proxmox",
        "desc": "Homelab hypervisor",
        "url": "https://100.95.125.112:8006",
        "note": "⚠️ Tailscale required"
    },
    {
        "icon": "🌐",
        "name": "Nginx Proxy Manager",
        "desc": "Reverse proxy & SSL",
        "url": "http://100.95.125.112:81",
        "note": "⚠️ Tailscale required"
    },
    {
        "icon": "🦙",
        "name": "Ollama API",
        "desc": "Local LLM endpoint",
        "url": "http://100.95.125.112:11434",
        "note": "⚠️ Tailscale required"
    },
]

for svc in SERVICES:
    st.markdown(f"""
    <div class="setup-card">
        <div class="setup-icon">{svc['icon']}</div>
        <div style="flex:1">
            <div class="setup-name">{svc['name']}</div>
            <div class="setup-url">{svc['desc']} · {svc['note']}</div>
            <div class="setup-url" style="color:#5a6a7a;">{svc['url']}</div>
        </div>
    </div>
    <a href="{svc['url']}" class="tap-btn">
        {svc['icon']} Open {svc['name']} →
    </a>
    <br>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div class="instructions">
<b>🔒 Tailscale reminder:</b><br>
Before opening any homelab URL, make sure <b>Tailscale is ON</b> on your iPhone.<br>
Tailscale app → toggle the VPN switch → then tap the links above.
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="instructions">
<b>💡 Pro tip — Better icons:</b><br>
After adding to home screen, you can change the icon image:<br>
1. Long-press the app icon on your home screen<br>
2. Tap <b>Edit</b> → tap the icon image<br>
3. Choose a photo from your camera roll (download official logos from Google Images)
</div>
""", unsafe_allow_html=True)
