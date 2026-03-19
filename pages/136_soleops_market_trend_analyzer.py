import streamlit as st
import json
import datetime
from datetime import timedelta
import requests
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Market Trend Analyzer", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_market_trends (
                id SERIAL PRIMARY KEY,
                model VARCHAR(255) NOT NULL,
                platform VARCHAR(50) NOT NULL,
                avg_price DECIMAL(10,2),
                volume INTEGER DEFAULT 0,
                trend_direction VARCHAR(20),
                price_velocity DECIMAL(10,4),
                week_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(model, platform, week_date)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_trend_alerts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                model VARCHAR(255) NOT NULL,
                alert_type VARCHAR(50) NOT NULL,
                threshold DECIMAL(10,2),
                is_active BOOLEAN DEFAULT TRUE,
                last_triggered TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_market_snapshots (
                id SERIAL PRIMARY KEY,
                model VARCHAR(255) NOT NULL,
                platform VARCHAR(50) NOT NULL,
                price DECIMAL(10,2),
                snapshot_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_market_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                platform TEXT NOT NULL,
                avg_price REAL,
                volume INTEGER DEFAULT 0,
                trend_direction TEXT,
                price_velocity REAL,
                week_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(model, platform, week_date)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_trend_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                model TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                threshold REAL,
                is_active INTEGER DEFAULT 1,
                last_triggered TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                platform TEXT NOT NULL,
                price REAL,
                snapshot_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

def get_inventory_data():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT model, platform, purchase_price, sale_price, status, created_at
            FROM soleops_inventory
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        return rows
    except:
        return []
    finally:
        conn.close()

def get_sold_orders_data():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT model, platform, sale_price, sold_date
            FROM soleops_sold_orders
            ORDER BY sold_date DESC
        """)
        rows = cur.fetchall()
        return rows
    except:
        return []
    finally:
        conn.close()

def aggregate_market_data():
    inventory = get_inventory_data()
    sold_orders = get_sold_orders_data()
    
    model_data = {}
    
    for row in inventory:
        model, platform, purchase_price, sale_price, status, created_at = row
        if model not in model_data:
            model_data[model] = {"ebay": [], "mercari": [], "other": []}
        
        plat_key = "ebay" if "ebay" in str(platform).lower() else "mercari" if "mercari" in str(platform).lower() else "other"
        price = sale_price if sale_price else purchase_price
        if price:
            model_data[model][plat_key].append({"price": float(price), "date": created_at, "type": "inventory"})
    
    for row in sold_orders:
        model, platform, sale_price, sold_date = row
        if model not in model_data:
            model_data[model] = {"ebay": [], "mercari": [], "other": []}
        
        plat_key = "ebay" if "ebay" in str(platform).lower() else "mercari" if "mercari" in str(platform).lower() else "other"
        if sale_price:
            model_data[model][plat_key].append({"price": float(sale_price), "date": sold_date, "type": "sold"})
    
    return model_data

def calculate_moving_average(prices, days):
    if not prices:
        return None
    
    today = datetime.date.today()
    cutoff = today - timedelta(days=days)
    
    recent_prices = []
    for p in prices:
        try:
            if isinstance(p["date"], str):
                date_obj = datetime.datetime.strptime(p["date"][:10], "%Y-%m-%d").date()
            else:
                date_obj = p["date"] if isinstance(p["date"], datetime.date) else p["date"].date()
            
            if date_obj >= cutoff:
                recent_prices.append(p["price"])
        except:
            recent_prices.append(p["price"])
    
    if not recent_prices:
        return None
    
    return sum(recent_prices) / len(recent_prices)

def calculate_price_velocity(prices, days=30):
    if len(prices) < 2:
        return 0
    
    today = datetime.date.today()
    cutoff = today - timedelta(days=days)
    
    dated_prices = []
    for p in prices:
        try:
            if isinstance(p["date"], str):
                date_obj = datetime.datetime.strptime(p["date"][:10], "%Y-%m-%d").date()
            else:
                date_obj = p["date"] if isinstance(p["date"], datetime.date) else p["date"].date()
            
            if date_obj >= cutoff:
                dated_prices.append((date_obj, p["price"]))
        except:
            continue
    
    if len(dated_prices) < 2:
        return 0
    
    dated_prices.sort(key=lambda x: x[0])
    first_price = dated_prices[0][1]
    last_price = dated_prices[-1][1]
    
    if first_price == 0:
        return 0
    
    return ((last_price - first_price) / first_price) * 100

def determine_trend_direction(velocity):
    if velocity > 5:
        return "🔥 Hot"
    elif velocity > 0:
        return "📈 Rising"
    elif velocity < -5:
        return "❄️ Cold"
    elif velocity < 0:
        return "📉 Falling"
    else:
        return "➡️ Stable"

def detect_seasonal_patterns(model_data):
    patterns = {}
    
    for model, platforms in model_data.items():
        all_prices = []
        for plat_prices in platforms.values():
            all_prices.extend(plat_prices)
        
        monthly_data = {}
        for p in all_prices:
            try:
                if isinstance(p["date"], str):
                    date_obj = datetime.datetime.strptime(p["date"][:10], "%Y-%m-%d")
                else:
                    date_obj = p["date"] if isinstance(p["date"], datetime.datetime) else datetime.datetime.combine(p["date"], datetime.time())
                
                month = date_obj.month
                if month not in monthly_data:
                    monthly_data[month] = []
                monthly_data[month].append(p["price"])
            except:
                continue
        
        if monthly_data:
            monthly_avgs = {m: sum(prices)/len(prices) for m, prices in monthly_data.items()}
            if monthly_avgs:
                peak_month = max(monthly_avgs, key=monthly_avgs.get)
                low_month = min(monthly_avgs, key=monthly_avgs.get)
                patterns[model] = {
                    "peak_month": peak_month,
                    "low_month": low_month,
                    "monthly_avgs": monthly_avgs
                }
    
    return patterns

def get_claude_market_analysis(model_data, hot_models, cold_models, seasonal_patterns):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ Configure your Anthropic API key in settings to enable AI analysis."
    
    prompt = f"""You are a sneaker market analyst. Analyze the following market data and provide actionable buy/sell timing recommendations.

HOT MODELS (Rising prices, high demand):
{json.dumps(hot_models[:5], indent=2) if hot_models else "None identified"}

COLD MODELS (Falling prices, low demand):
{json.dumps(cold_models[:5], indent=2) if cold_models else "None identified"}

SEASONAL PATTERNS:
{json.dumps(dict(list(seasonal_patterns.items())[:5]), indent=2) if seasonal_patterns else "Insufficient data"}

Current Date: {datetime.date.today().strftime("%B %d, %Y")}

Provide:
1. **Market Summary** (2-3 sentences on overall market conditions)
2. **Top 3 Buy Recommendations** (models to acquire now with reasoning)
3. **Top 3 Sell Recommendations** (models to list now with reasoning)
4. **Seasonal Timing Advice** (what to watch for in the next 30 days)
5. **Risk Alerts** (any concerning trends)

Keep response concise and actionable for a reseller."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1500,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            return data["content"][0]["text"]
        else:
            return f"⚠️ API Error: {response.status_code}"
    except Exception as e:
        return f"⚠️ Error generating analysis: {str(e)}"

def save_trend_alert(user_id, model, alert_type, threshold):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        INSERT INTO soleops_trend_alerts (user_id, model, alert_type, threshold)
        VALUES ({ph}, {ph}, {ph}, {ph})
    """, (user_id, model, alert_type, threshold))
    conn.commit()
    conn.close()

def get_user_alerts(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT id, model, alert_type, threshold, is_active, created_at
        FROM soleops_trend_alerts
        WHERE user_id = {ph}
        ORDER BY created_at DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_alert(alert_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM soleops_trend_alerts WHERE id = {ph}", (alert_id,))
    conn.commit()
    conn.close()

def send_telegram_alert(message):
    bot_token = get_setting("telegram_bot_token")
    chat_id = get_setting("telegram_chat_id")
    
    if not bot_token or not chat_id:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        return response.status_code == 200
    except:
        return False

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

st.title("📈 SoleOps Market Trend Analyzer")
st.markdown("AI-powered sneaker market analysis with buy/sell timing recommendations")

model_data = aggregate_market_data()

hot_models = []
cold_models = []
all_trends = []

for model, platforms in model_data.items():
    all_prices = []
    for plat, prices in platforms.items():
        all_prices.extend(prices)
    
    if not all_prices:
        continue
    
    ma_7 = calculate_moving_average(all_prices, 7)
    ma_30 = calculate_moving_average(all_prices, 30)
    ma_90 = calculate_moving_average(all_prices, 90)
    velocity = calculate_price_velocity(all_prices, 30)
    direction = determine_trend_direction(velocity)
    
    trend_data = {
        "model": model,
        "ma_7": ma_7,
        "ma_30": ma_30,
        "ma_90": ma_90,
        "velocity": velocity,
        "direction": direction,
        "volume": len(all_prices),
        "platforms": {k: len(v) for k, v in platforms.items() if v}
    }
    
    all_trends.append(trend_data)
    
    if velocity > 5:
        hot_models.append(trend_data)
    elif velocity < -5:
        cold_models.append(trend_data)

hot_models.sort(key=lambda x: x["velocity"], reverse=True)
cold_models.sort(key=lambda x: x["velocity"])

seasonal_patterns = detect_seasonal_patterns(model_data)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Market Overview", 
    "🔥 Hot Models", 
    "❄️ Cold Models", 
    "📅 Seasonal Patterns",
    "🤖 AI Recommendations",
    "🔔 Alerts"
])

with tab1:
    st.subheader("Market Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Models Tracked", len(model_data))
    with col2:
        st.metric("Hot Models", len(hot_models), delta=f"+{len(hot_models)}" if hot_models else None)
    with col3:
        st.metric("Cold Models", len(cold_models), delta=f"-{len(cold_models)}" if cold_models else None, delta_color="inverse")
    with col4:
        total_volume = sum(t["volume"] for t in all_trends)
        st.metric("Total Data Points", total_volume)
    
    st.markdown("---")
    
    if all_trends:
        st.subheader("All Model Trends")
        
        trend_display = []
        for t in sorted(all_trends, key=lambda x: x["velocity"], reverse=True):
            trend_display.append({
                "Model": t["model"],
                "Trend": t["direction"],
                "7-Day Avg": f"${t['ma_7']:.2f}" if t["ma_7"] else "N/A",
                "30-Day Avg": f"${t['ma_30']:.2f}" if t["ma_30"] else "N/A",
                "90-Day Avg": f"${t['ma_90']:.2f}" if t["ma_90"] else "N/A",
                "Velocity": f"{t['velocity']:.1f}%",
                "Volume": t["volume"]
            })
        
        st.dataframe(trend_display, use_container_width=True)
        
        st.subheader("Price Velocity Distribution")
        
        velocities = [t["velocity"] for t in all_trends if t["velocity"] is not None]
        if velocities:
            import pandas as pd
            df = pd.DataFrame({"Velocity (%)": velocities})
            st.bar_chart(df)
    else:
        st.info("📭 No market data available. Add inventory or sold orders to see trends.")

with tab2:
    st.subheader("🔥 Hot Models - Rising Prices")
    st.markdown("*Models with >5% price increase over 30 days*")
    
    if hot_models:
        for i, model in enumerate(hot_models[:10]):
            with st.expander(f"**{model['model']}** - {model['direction']} ({model['velocity']:.1f}%)", expanded=(i < 3)):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("7-Day Avg", f"${model['ma_7']:.2f}" if model["ma_7"] else "N/A")
                with col2:
                    st.metric("30-Day Avg", f"${model['ma_30']:.2f}" if model["ma_30"] else "N/A")
                with col3:
                    st.metric("Volume", model["volume"])
                
                st.markdown(f"**Platforms:** {', '.join(model['platforms'].keys())}")
                
                st.success("💡 **Recommendation:** Consider holding inventory - prices are rising. Good time to list at premium prices.")
    else:
        st.info("No hot models identified. This could mean a stable market or insufficient data.")

with tab3:
    st.subheader("❄️ Cold Models - Falling Prices")
    st.markdown("*Models with >5% price decrease over 30 days*")
    
    if cold_models:
        for i, model in enumerate(cold_models[:10]):
            with st.expander(f"**{model['model']}** - {model['direction']} ({model['velocity']:.1f}%)", expanded=(i < 3)):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("7-Day Avg", f"${model['ma_7']:.2f}" if model["ma_7"] else "N/A")
                with col2:
                    st.metric("30-Day Avg", f"${model['ma_30']:.2f}" if model["ma_30"] else "N/A")
                with col3:
                    st.metric("Volume", model["volume"])
                
                st.markdown(f"**Platforms:** {', '.join(model['platforms'].keys())}")
                
                st.warning("⚠️ **Recommendation:** Consider liquidating - prices are dropping. List now before further decline.")
    else:
        st.info("No cold models identified. Market may be stable or trending upward.")

with tab4:
    st.subheader("📅 Seasonal Patterns")
    st.markdown("*Identify the best months to buy and sell each model*")
    
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }
    
    current_month = datetime.date.today().month
    
    if seasonal_patterns:
        st.markdown(f"**Current Month:** {month_names[current_month]}")
        st.markdown("---")
        
        buy_now = []
        sell_now = []
        
        for model, pattern in seasonal_patterns.items():
            if pattern["low_month"] == current_month:
                buy_now.append(model)
            if pattern["peak_month"] == current_month:
                sell_now.append(model)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🛒 Buy Now (Low Season)")
            if buy_now:
                for m in buy_now[:5]:
                    st.success(f"✅ {m}")
            else:
                st.info("No models at seasonal low this month")
        
        with col2:
            st.markdown("### 💰 Sell Now (Peak Season)")
            if sell_now:
                for m in sell_now[:5]:
                    st.warning(f"🔥 {m}")
            else:
                st.info("No models at seasonal peak this month")
        
        st.markdown("---")
        st.subheader("All Seasonal Data")
        
        seasonal_display = []
        for model, pattern in seasonal_patterns.items():
            seasonal_display.append({
                "Model": model,
                "Peak Month (Sell)": month_names.get(pattern["peak_month"], "Unknown"),
                "Low Month (Buy)": month_names.get(pattern["low_month"], "Unknown"),
                "Months Tracked": len(pattern["monthly_avgs"])
            })
        
        st.dataframe(seasonal_display, use_container_width=True)
    else:
        st.info("📭 Not enough historical data to detect seasonal patterns. Continue tracking for more insights.")

with tab5:
    st.subheader("🤖 AI Market Analysis")
    st.markdown("*Claude-powered buy/sell recommendations*")
    
    if st.button("🔄 Generate Fresh Analysis", type="primary"):
        with st.spinner("Analyzing market trends..."):
            analysis = get_claude_market_analysis(model_data, hot_models, cold_models, seasonal_patterns)
            st.session_state["market_analysis"] = analysis
            st.session_state["analysis_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if "market_analysis" in st.session_state:
        st.caption(f"Last updated: {st.session_state.get('analysis_time', 'Unknown')}")
        st.markdown(st.session_state["market_analysis"])
        
        if st.button("📤 Send to Telegram"):
            msg = f"📈 <b>SoleOps Market Analysis</b>\n\n{st.session_state['market_analysis'][:3000]}"
            if send_telegram_alert(msg):
                st.success("✅ Sent to Telegram!")
            else:
                st.error("❌ Failed to send. Check Telegram settings.")
    else:
        st.info("Click 'Generate Fresh Analysis' to get AI-powered market insights.")
    
    st.markdown("---")
    st.subheader("Quick Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Top 3 Rising Models**")
        for m in hot_models[:3]:
            st.success(f"📈 {m['model']} (+{m['velocity']:.1f}%)")
    
    with col2:
        st.markdown("**Top 3 Falling Models**")
        for m in cold_models[:3]:
            st.error(f"📉 {m['model']} ({m['velocity']:.1f}%)")

with tab6:
    st.subheader("🔔 Trend Alerts")
    st.markdown("*Get notified when models hit your thresholds*")
    
    user_id = st.session_state.get("user_id", 1)
    
    with st.form("new_alert"):
        st.markdown("### Create New Alert")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            model_options = list(model_data.keys()) if model_data else ["No models available"]
            selected_model = st.selectbox("Model", model_options)
        
        with col2:
            alert_type = st.selectbox("Alert Type", [
                "Price Up %",
                "Price Down %",
                "Volume Spike",
                "Trend Change to Hot",
                "Trend Change to Cold"
            ])
        
        with col3:
            threshold = st.number_input("Threshold", min_value=0.0, value=10.0, step=1.0)
        
        submit = st.form_submit_button("➕ Create Alert", type="primary")
        
        if submit and selected_model != "No models available":
            save_trend_alert(user_id, selected_model, alert_type, threshold)
            st.success(f"✅ Alert created for {selected_model}")
            st.rerun()
    
    st.markdown("---")
    st.markdown("### Active Alerts")
    
    alerts = get_user_alerts(user_id)
    
    if alerts:
        for alert in alerts:
            alert_id, model, alert_type, threshold, is_active, created_at = alert
            
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                st.markdown(f"**{model}**")
            with col2:
                st.markdown(f"{alert_type}")
            with col3:
                st.markdown(f"Threshold: {threshold}")
            with col4:
                if st.button("🗑️", key=f"del_{alert_id}"):
                    delete_alert(alert_id)
                    st.rerun()
    else:
        st.info("No alerts configured. Create one above to get notified of market changes.")
    
    st.markdown("---")
    st.markdown("### Telegram Settings")
    
    with st.expander("Configure Telegram Alerts"):
        bot_token = st.text_input("Bot Token", value=get_setting("telegram_bot_token") or "", type="password")
        chat_id = st.text_input("Chat ID", value=get_setting("telegram_chat_id") or "")
        
        if st.button("💾 Save Telegram Settings"):
            set_setting("telegram_bot_token", bot_token)
            set_setting("telegram_chat_id", chat_id)
            st.success("✅ Telegram settings saved!")
        
        if st.button("🧪 Test Telegram"):
            if send_telegram_alert("🧪 SoleOps Market Trend Analyzer test message!"):
                st.success("✅ Test message sent!")
            else:
                st.error("❌ Failed to send. Check your settings.")

st.markdown("---")
st.caption("📈 SoleOps Market Trend Analyzer | Data refreshes from your inventory and sold orders")