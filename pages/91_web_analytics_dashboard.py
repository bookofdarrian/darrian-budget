import streamlit as st
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json

from utils.db import get_conn, USE_POSTGRES, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Web Analytics Dashboard", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


def _ensure_tables():
    conn = get_conn()
    cursor = conn.cursor()
    if USE_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plausible_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                api_url TEXT NOT NULL,
                api_key TEXT NOT NULL,
                site_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_cache (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                cache_key TEXT NOT NULL,
                cache_data TEXT NOT NULL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                UNIQUE(user_id, cache_key)
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plausible_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                api_url TEXT NOT NULL,
                api_key TEXT NOT NULL,
                site_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                cache_key TEXT NOT NULL,
                cache_data TEXT NOT NULL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                UNIQUE(user_id, cache_key)
            )
        """)
    conn.commit()
    conn.close()


_ensure_tables()


class PlausibleClient:
    def __init__(self, api_url: str, api_key: str, site_id: str):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.site_id = site_id
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        try:
            url = f"{self.api_url}/api/v1/stats/{endpoint}"
            params = params or {}
            params["site_id"] = self.site_id
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API Error: {str(e)}")
            return None
    
    def get_realtime_visitors(self) -> Optional[int]:
        result = self._make_request("realtime/visitors")
        return result if isinstance(result, int) else None
    
    def get_aggregate(self, period: str = "30d", metrics: List[str] = None) -> Optional[Dict]:
        if metrics is None:
            metrics = ["visitors", "pageviews", "bounce_rate", "visit_duration", "visits"]
        params = {
            "period": period,
            "metrics": ",".join(metrics)
        }
        return self._make_request("aggregate", params)
    
    def get_timeseries(self, period: str = "30d", interval: str = "date") -> Optional[List[Dict]]:
        params = {
            "period": period,
            "interval": interval,
            "metrics": "visitors,pageviews"
        }
        return self._make_request("timeseries", params)
    
    def get_breakdown(self, property_name: str, period: str = "30d", limit: int = 10) -> Optional[List[Dict]]:
        params = {
            "period": period,
            "property": property_name,
            "limit": limit,
            "metrics": "visitors,pageviews"
        }
        return self._make_request("breakdown", params)


def get_plausible_settings(user_id: int) -> Optional[Dict[str, str]]:
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT api_url, api_key, site_id FROM plausible_settings WHERE user_id = %s" if USE_POSTGRES else
        "SELECT api_url, api_key, site_id FROM plausible_settings WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"api_url": row[0], "api_key": row[1], "site_id": row[2]}
    return None


def save_plausible_settings(user_id: int, api_url: str, api_key: str, site_id: str):
    conn = get_conn()
    cursor = conn.cursor()
    if USE_POSTGRES:
        cursor.execute("""
            INSERT INTO plausible_settings (user_id, api_url, api_key, site_id, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                api_url = EXCLUDED.api_url,
                api_key = EXCLUDED.api_key,
                site_id = EXCLUDED.site_id,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, api_url, api_key, site_id))
    else:
        cursor.execute("""
            INSERT OR REPLACE INTO plausible_settings (user_id, api_url, api_key, site_id, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, api_url, api_key, site_id))
    conn.commit()
    conn.close()


# Main page content
st.title("📊 Web Analytics Dashboard")

user_id = st.session_state.get("user_id", 1)
settings = get_plausible_settings(user_id)

with st.expander("⚙️ Plausible Settings", expanded=not settings):
    api_url = st.text_input("Plausible API URL", value=settings.get("api_url", "https://plausible.io") if settings else "https://plausible.io")
    api_key = st.text_input("API Key", value=settings.get("api_key", "") if settings else "", type="password")
    site_id = st.text_input("Site ID", value=settings.get("site_id", "") if settings else "")
    
    if st.button("Save Settings"):
        if api_url and api_key and site_id:
            save_plausible_settings(user_id, api_url, api_key, site_id)
            st.success("Settings saved!")
            st.rerun()
        else:
            st.error("Please fill in all fields")

if settings:
    client = PlausibleClient(settings["api_url"], settings["api_key"], settings["site_id"])
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        realtime = client.get_realtime_visitors()
        if realtime is not None:
            st.metric("Realtime Visitors", realtime)
    
    period = st.selectbox("Time Period", ["7d", "30d", "6mo", "12mo"], index=1)
    
    aggregate = client.get_aggregate(period=period)
    if aggregate and "results" in aggregate:
        results = aggregate["results"]
        cols = st.columns(5)
        metrics_display = [
            ("visitors", "Visitors"),
            ("pageviews", "Pageviews"),
            ("visits", "Visits"),
            ("bounce_rate", "Bounce Rate"),
            ("visit_duration", "Avg Duration")
        ]
        for i, (key, label) in enumerate(metrics_display):
            if key in results:
                value = results[key]
                if key == "bounce_rate":
                    value = f"{value}%"
                elif key == "visit_duration":
                    value = f"{value}s"
                cols[i].metric(label, value)
    
    st.subheader("📈 Traffic Over Time")
    timeseries = client.get_timeseries(period=period)
    if timeseries and "results" in timeseries:
        import pandas as pd
        df = pd.DataFrame(timeseries["results"])
        if not df.empty:
            st.line_chart(df.set_index("date")[["visitors", "pageviews"]])
    
    st.subheader("🔝 Top Pages")
    pages = client.get_breakdown("event:page", period=period)
    if pages and "results" in pages:
        import pandas as pd
        df = pd.DataFrame(pages["results"])
        if not df.empty:
            st.dataframe(df, use_container_width=True)
else:
    st.info("Please configure your Plausible settings above to view analytics.")