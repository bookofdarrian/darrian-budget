import streamlit as st
import json
import requests
from datetime import datetime, timedelta
import subprocess
import os
import tempfile
from pathlib import Path

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Cloudflare Worker Edge Cache", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cf_worker_deployments (
                id SERIAL PRIMARY KEY,
                worker_name VARCHAR(255) NOT NULL,
                deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'active',
                routes TEXT,
                config_json TEXT,
                notes TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cf_cache_purge_logs (
                id SERIAL PRIMARY KEY,
                purge_type VARCHAR(50) NOT NULL,
                purge_target TEXT,
                purged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50),
                response_json TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cf_worker_analytics (
                id SERIAL PRIMARY KEY,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                requests_total BIGINT DEFAULT 0,
                requests_cached BIGINT DEFAULT 0,
                bandwidth_total BIGINT DEFAULT 0,
                bandwidth_cached BIGINT DEFAULT 0,
                cpu_time_avg FLOAT DEFAULT 0,
                errors_total INTEGER DEFAULT 0
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cf_worker_deployments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_name TEXT NOT NULL,
                deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                routes TEXT,
                config_json TEXT,
                notes TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cf_cache_purge_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purge_type TEXT NOT NULL,
                purge_target TEXT,
                purged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                response_json TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cf_worker_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                requests_total INTEGER DEFAULT 0,
                requests_cached INTEGER DEFAULT 0,
                bandwidth_total INTEGER DEFAULT 0,
                bandwidth_cached INTEGER DEFAULT 0,
                cpu_time_avg REAL DEFAULT 0,
                errors_total INTEGER DEFAULT 0
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# Constants
WORKER_SCRIPT_TEMPLATE = '''
// Peach State Savings - Cloudflare Worker Edge Cache
// Cold-start loading page + static asset caching

const LOADING_PAGE_HTML = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Peach State Savings - Loading...</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #ff6b35 0%, #f7931e 50%, #ffb347 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        .container {
            text-align: center;
            padding: 2rem;
        }
        .logo {
            font-size: 4rem;
            margin-bottom: 1rem;
            animation: bounce 1s ease-in-out infinite;
        }
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🍑</div>
        <h1>Loading...</h1>
    </div>
</body>
</html>
`;

export default {
    async fetch(request, env, ctx) {
        return new Response(LOADING_PAGE_HTML, {
            headers: { 'Content-Type': 'text/html' }
        });
    }
};
'''

# Main page content
st.title("🍑 Cloudflare Worker Edge Cache")
st.markdown("Manage Cloudflare Workers for edge caching and cold-start loading pages.")

# Tabs for different functionality
tab1, tab2, tab3, tab4 = st.tabs(["Deploy Worker", "Cache Management", "Analytics", "Deployment History"])

with tab1:
    st.subheader("Deploy New Worker")
    
    worker_name = st.text_input("Worker Name", value="peach-edge-cache")
    worker_route = st.text_input("Route Pattern", value="*.peachstatesavings.com/*")
    
    st.markdown("### Worker Script")
    worker_script = st.text_area("Worker Script", value=WORKER_SCRIPT_TEMPLATE, height=400)
    
    if st.button("Deploy Worker", type="primary"):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write worker script to temp file
            script_path = Path(tmpdir) / "worker.js"
            script_path.write_text(worker_script)
            
            st.success(f"Worker script prepared at {script_path}")
            st.info("Deployment would happen here with Cloudflare API")

with tab2:
    st.subheader("Cache Purge")
    
    purge_type = st.selectbox("Purge Type", ["Everything", "By URL", "By Tag", "By Prefix"])
    
    if purge_type != "Everything":
        purge_target = st.text_input(f"Enter {purge_type.replace('By ', '')}")
    
    if st.button("Purge Cache", type="secondary"):
        st.warning("Cache purge functionality requires Cloudflare API credentials")

with tab3:
    st.subheader("Worker Analytics")
    st.info("Analytics data will be displayed here once the worker is deployed and collecting metrics.")

with tab4:
    st.subheader("Deployment History")
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cf_worker_deployments ORDER BY deployed_at DESC LIMIT 20")
    deployments = cur.fetchall()
    conn.close()
    
    if deployments:
        for dep in deployments:
            st.write(dep)
    else:
        st.info("No deployments recorded yet.")