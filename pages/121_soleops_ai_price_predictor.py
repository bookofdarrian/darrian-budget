import streamlit as st
import json
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps AI Price Predictor", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_price_predictions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                shoe_name VARCHAR(255),
                predicted_price DECIMAL(10,2) NOT NULL,
                current_market_price DECIMAL(10,2),
                confidence_score DECIMAL(5,2),
                trend_direction VARCHAR(20),
                prediction_reasoning TEXT,
                factors_json TEXT,
                prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                valid_until TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_market_trends (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                shoe_name VARCHAR(255),
                avg_sold_price DECIMAL(10,2),
                min_sold_price DECIMAL(10,2),
                max_sold_price DECIMAL(10,2),
                price_7d_change DECIMAL(5,2),
                price_30d_change DECIMAL(5,2),
                price_90d_change DECIMAL(5,2),
                volume_7d INTEGER DEFAULT 0,
                volume_30d INTEGER DEFAULT 0,
                volume_trend VARCHAR(20),
                volatility_score DECIMAL(5,2),
                seasonality_factor DECIMAL(5,2),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, sku)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_price_alerts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                shoe_name VARCHAR(255),
                alert_type VARCHAR(20) NOT NULL,
                threshold_price DECIMAL(10,2) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                triggered_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_price_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                shoe_name TEXT,
                predicted_price REAL NOT NULL,
                current_market_price REAL,
                confidence_score REAL,
                trend_direction TEXT,
                prediction_reasoning TEXT,
                factors_json TEXT,
                prediction_date TEXT DEFAULT CURRENT_TIMESTAMP,
                valid_until TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_market_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                shoe_name TEXT,
                avg_sold_price REAL,
                min_sold_price REAL,
                max_sold_price REAL,
                price_7d_change REAL,
                price_30d_change REAL,
                price_90d_change REAL,
                volume_7d INTEGER DEFAULT 0,
                volume_30d INTEGER DEFAULT 0,
                volume_trend TEXT,
                volatility_score REAL,
                seasonality_factor REAL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, sku)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                shoe_name TEXT,
                alert_type TEXT NOT NULL,
                threshold_price REAL NOT NULL,
                is_active INTEGER DEFAULT 1,
                triggered_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

def get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def get_historical_sold_data(user_id, sku=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    try:
        if sku:
            cur.execute(f"""
                SELECT sku, shoe_name, sale_price, platform, sold_date, cost_basis
                FROM soleops_sold_orders
                WHERE user_id = {ph} AND sku = {ph}
                ORDER BY sold_date DESC
            """, (user_id, sku))
        else:
            cur.execute(f"""
                SELECT sku, shoe_name, sale_price, platform, sold_date, cost_basis
                FROM soleops_sold_orders
                WHERE user_id = {ph}
                ORDER BY sold_date DESC
            """, (user_id,))
        
        rows = cur.fetchall()
        cols = ['sku', 'shoe_name', 'sale_price', 'platform', 'sold_date', 'cost_basis']
        return [dict(zip(cols, row)) for row in rows]
    except Exception:
        return []
    finally:
        conn.close()

def calculate_price_trends(sold_data):
    if not sold_data:
        return None
    
    df = pd.DataFrame(sold_data)
    df['sale_price'] = pd.to_numeric(df['sale_price'], errors='coerce')
    df['sold_date'] = pd.to_datetime(df['sold_date'], errors='coerce')
    
    now = datetime.now()
    day_7 = now - timedelta(days=7)
    day_30 = now - timedelta(days=30)
    day_90 = now - timedelta(days=90)
    
    recent_7d = df[df['sold_date'] >= day_7]
    recent_30d = df[df['sold_date'] >= day_30]
    recent_90d = df[df['sold_date'] >= day_90]
    older = df[df['sold_date'] < day_30]
    
    avg_price = df['sale_price'].mean() if len(df) > 0 else 0
    min_price = df['sale_price'].min() if len(df) > 0 else 0
    max_price = df['sale_price'].max() if len(df) > 0 else 0
    
    avg_7d = recent_7d['sale_price'].mean() if len(recent_7d) > 0 else avg_price
    avg_30d = recent_30d['sale_price'].mean() if len(recent_30d) > 0 else avg_price
    avg_90d = recent_90d['sale_price'].mean() if len(recent_90d) > 0 else avg_price
    avg_older = older['sale_price'].mean() if len(older) > 0 else avg_price
    
    price_7d_change = ((avg_7d - avg_30d) / avg_30d * 100) if avg_30d > 0 else 0
    price_30d_change = ((avg_30d - avg_older) / avg_older * 100) if avg_older > 0 else 0
    price_90d_change = ((avg_90d - avg_older) / avg_older * 100) if avg_older > 0 else 0
    
    volatility = df['sale_price'].std() / avg_price * 100 if avg_price > 0 else 0
    
    volume_7d = len(recent_7d)
    volume_30d = len(recent_30d)
    
    if volume_7d > volume_30d / 4:
        volume_trend = "increasing"
    elif volume_7d < volume_30d / 6:
        volume_trend = "decreasing"
    else:
        volume_trend = "stable"
    
    current_month = now.month
    if current_month in [11, 12, 8]:
        seasonality = 1.15
    elif current_month in [1, 2, 6, 7]:
        seasonality = 0.95
    else:
        seasonality = 1.0
    
    return {
        'avg_sold_price': round(avg_price, 2),
        'min_sold_price': round(min_price, 2),
        'max_sold_price': round(max_price, 2),
        'price_7d_change': round(price_7d_change, 2),
        'price_30d_change': round(price_30d_change, 2),
        'price_90d_change': round(price_90d_change, 2),
        'volume_7d': volume_7d,
        'volume_30d': volume_30d,
        'volume_trend': volume_trend,
        'volatility_score': round(volatility, 2),
        'seasonality_factor': seasonality
    }

def get_ai_price_prediction(sku, shoe_name, trends, sold_data):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return None
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        recent_sales = sold_data[:10] if sold_data else []
        sales_summary = "\n".join([
            f"- {s.get('sold_date', 'N/A')}: ${s.get('sale_price', 0)} on {s.get('platform', 'Unknown')}"
            for s in recent_sales
        ])
        
        prompt = f"""You are an expert sneaker resale market analyst. Analyze the following data and provide a price prediction.

SKU: {sku}
Shoe Name: {shoe_name}

Market Trends:
- Average Sold Price: ${trends.get('avg_sold_price', 0)}
- Price Range: ${trends.get('min_sold_price', 0)} - ${trends.get('max_sold_price', 0)}
- 7-Day Price Change: {trends.get('price_7d_change', 0)}%
- 30-Day Price Change: {trends.get('price_30d_change', 0)}%
- 90-Day Price Change: {trends.get('price_90d_change', 0)}%
- Volume Trend: {trends.get('volume_trend', 'unknown')}
- Volatility Score: {trends.get('volatility_score', 0)}%
- Seasonality Factor: {trends.get('seasonality_factor', 1.0)}

Recent Sales:
{sales_summary if sales_summary else "No recent sales data available"}

Provide your analysis in the following JSON format:
{{
    "predicted_price": <number>,
    "confidence_score": <0-100>,
    "trend_direction": "<up|down|stable>",
    "reasoning": "<2-3 sentence explanation>",
    "factors": {{
        "market_demand": "<high|medium|low>",
        "price_momentum": "<positive|negative|neutral>",
        "seasonality_impact": "<favorable|unfavorable|neutral>",
        "volatility_risk": "<high|medium|low>",
        "recommended_action": "<list_now|wait|price_aggressively>"
    }},
    "price_range": {{
        "low": <number>,
        "high": <number>
    }},
    "optimal_listing_price": <number>,
    "days_to_sell_estimate": <number>
}}

Only respond with valid JSON, no other text."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = response.content[0].text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        
        return json.loads(result_text)
    except Exception as e:
        st.error(f"AI prediction error: {str(e)}")
        return None

def save_prediction(user_id, sku, shoe_name, prediction, trends):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    valid_until = (datetime.now() + timedelta(days=7)).isoformat()
    factors_json = json.dumps(prediction.get('factors', {}))
    
    cur.execute(f"""
        INSERT INTO soleops_price_predictions 
        (user_id, sku, shoe_name, predicted_price, current_market_price, 
         confidence_score, trend_direction, prediction_reasoning, factors_json, valid_until)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (
        user_id, sku, shoe_name,
        prediction.get('predicted_price', 0),
        trends.get('avg_sold_price', 0),
        prediction.get('confidence_score', 0),
        prediction.get('trend_direction', 'stable'),
        prediction.get('reasoning', ''),
        factors_json,
        valid_until
    ))
    
    conn.commit()
    conn.close()

def save_market_trends(user_id, sku, shoe_name, trends):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    if USE_POSTGRES:
        cur.execute(f"""
            INSERT INTO soleops_market_trends 
            (user_id, sku, shoe_name, avg_sold_price, min_sold_price, max_sold_price,
             price_7d_change, price_30d_change, price_90d_change, volume_7d, volume_30d,
             volume_trend, volatility_score, seasonality_factor, last_updated)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            ON CONFLICT (user_id, sku) DO UPDATE SET
                avg_sold_price = EXCLUDED.avg_sold_price,
                min_sold_price = EXCLUDED.min_sold_price,
                max_sold_price = EXCLUDED.max_sold_price,
                price_7d_change = EXCLUDED.price_7d_change,
                price_30d_change = EXCLUDED.price_30d_change,
                price_90d_change = EXCLUDED.price_90d_change,
                volume_7d = EXCLUDED.volume_7d,
                volume_30d = EXCLUDED.volume_30d,
                volume_trend = EXCLUDED.volume_trend,
                volatility_score = EXCLUDED.volatility_score,
                seasonality_factor = EXCLUDED.seasonality_factor,
                last_updated = CURRENT_TIMESTAMP
        """, (
            user_id, sku, shoe_name,
            trends.get('avg_sold_price', 0),
            trends.get('min_sold_price', 0),
            trends.get('max_sold_price', 0),
            trends.get('price_7d_change', 0),
            trends.get('price_30d_change', 0),
            trends.get('price_90d_change', 0),
            trends.get('volume_7d', 0),
            trends.get('volume_30d', 0),
            trends.get('volume_trend', 'stable'),
            trends.get('volatility_score', 0),
            trends.get('seasonality_factor', 1.0),
            datetime.now().isoformat()
        ))
    else:
        cur.execute(f"""
            INSERT OR REPLACE INTO soleops_market_trends 
            (user_id, sku, shoe_name, avg_sold_price, min_sold_price, max_sold_price,
             price_7d_change, price_30d_change, price_90d_change, volume_7d, volume_30d,
             volume_trend, volatility_score, seasonality_factor, last_updated)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (
            user_id, sku, shoe_name,
            trends.get('avg_sold_price', 0),
            trends.get('min_sold_price', 0),
            trends.get('max_sold_price', 0),
            trends.get('price_7d_change', 0),
            trends.get('price_30d_change', 0),
            trends.get('price_90d_change', 0),
            trends.get('volume_7d', 0),
            trends.get('volume_30d', 0),
            trends.get('volume_trend', 'stable'),
            trends.get('volatility_score', 0),
            trends.get('seasonality_factor', 1.0),
            datetime.now().isoformat()
        ))
    
    conn.commit()
    conn.close()

def get_inventory_items(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    try:
        cur.execute(f"""
            SELECT DISTINCT sku, shoe_name, size, cost_basis, list_price
            FROM soleops_inventory
            WHERE user_id = {ph} AND status = 'active'
            ORDER BY shoe_name
        """, (user_id,))
        rows = cur.fetchall()
        cols = ['sku', 'shoe_name', 'size', 'cost_basis', 'list_price']
        return [dict(zip(cols, row)) for row in rows]
    except Exception:
        return []
    finally:
        conn.close()

def get_recent_predictions(user_id, limit=10):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"""
        SELECT sku, shoe_name, predicted_price, confidence_score, trend_direction,
               prediction_reasoning, prediction_date, valid_until
        FROM soleops_price_predictions
        WHERE user_id = {ph}
        ORDER BY prediction_date DESC
        LIMIT {ph}
    """, (user_id, limit))
    
    rows = cur.fetchall()
    cols = ['sku', 'shoe_name', 'predicted_price', 'confidence_score', 'trend_direction',
            'prediction_reasoning', 'prediction_date', 'valid_until']
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

def get_price_alerts(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    if USE_POSTGRES:
        cur.execute(f"""
            SELECT id, sku, shoe_name, alert_type, threshold_price, is_active, created_at
            FROM soleops_price_alerts
            WHERE user_id = {ph} AND is_active = TRUE
            ORDER BY created_at DESC
        """, (user_id,))
    else:
        cur.execute(f"""
            SELECT id, sku, shoe_name, alert_type, threshold_price, is_active, created_at
            FROM soleops_price_alerts
            WHERE user_id = {ph} AND is_active = 1
            ORDER BY created_at DESC
        """, (user_id,))
    
    rows = cur.fetchall()
    cols = ['id', 'sku', 'shoe_name', 'alert_type', 'threshold_price', 'is_active', 'created_at']
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

def add_price_alert(user_id, sku, shoe_name, alert_type, threshold_price):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"""
        INSERT INTO soleops_price_alerts (user_id, sku, shoe_name, alert_type, threshold_price)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, sku, shoe_name, alert_type, threshold_price))
    
    conn.commit()
    conn.close()

def delete_price_alert(alert_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"DELETE FROM soleops_price_alerts WHERE id = {ph}", (alert_id,))
    conn.commit()
    conn.close()

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

# Main content
st.title("🔮 SoleOps AI Price Predictor")
st.markdown("*Claude-powered price predictions based on market trends, seasonality, and historical data*")

user_id = st.session_state.get("user_id", 1)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Single Prediction", "📦 Batch Predictions", "📈 Market Trends", "🔔 Price Alerts"])

with tab1:
    st.subheader("Get AI Price Prediction")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        inventory = get_inventory_items(user_id)
        
        input_method = st.radio("Select Input Method", ["From Inventory", "Manual Entry"])
        
        if input_method == "From Inventory" and inventory:
            inventory_options = {f"{i['shoe_name']} ({i['sku']}) - Size {i['size']}": i for i in inventory}
            selected = st.selectbox("Select from Inventory", list(inventory_options.keys()))
            
            if selected:
                item = inventory_options[selected]
                sku = item['sku']
                shoe_name = item['shoe_name']
                st.info(f"**Cost Basis:** ${item.get('cost_basis', 0):.2f}")
                st.info(f"**Current List Price:** ${item.get('list_price', 0):.2f}")
        else:
            sku = st.text_input("SKU / Style Code", placeholder="e.g., DZ5485-612")
            shoe_name = st.text_input("Shoe Name", placeholder="e.g., Air Jordan 1 Retro High OG Chicago")
        
        if st.button("🔮 Generate Prediction", type="primary", use_container_width=True):
            if not sku or not shoe_name:
                st.error("Please enter both SKU and shoe name")
            else:
                with st.spinner("Analyzing market data..."):
                    sold_data = get_historical_sold_data(user_id, sku)
                    
                    if not sold_data:
                        st.warning("No historical sold data found for this SKU. Using general market estimates.")
                        trends = {
                            'avg_sold_price': 150,
                            'min_sold_price': 100,
                            'max_sold_price': 250,
                            'price_7d_change': 0,
                            'price_30d_change': 0,
                            'price_90d_change': 0,
                            'volume_7d': 0,
                            'volume_30d': 0,
                            'volume_trend': 'unknown',
                            'volatility_score': 15,
                            'seasonality_factor': 1.0
                        }
                    else:
                        trends = calculate_price_trends(sold_data)
                    
                    prediction = get_ai_price_prediction(sku, shoe_name, trends, sold_data)
                    
                    if prediction:
                        save_prediction(user_id, sku, shoe_name, prediction, trends)
                        save_market_trends(user_id, sku, shoe_name, trends)
                        st.session_state['last_prediction'] = prediction
                        st.session_state['last_trends'] = trends
                        st.session_state['last_sku'] = sku
                        st.session_state['last_shoe_name'] = shoe_name
                        st.success("Prediction generated!")
                    else:
                        st.error("Failed to generate prediction. Check API key.")
    
    with col2:
        if 'last_prediction' in st.session_state:
            prediction = st.session_state['last_prediction']
            trends = st.session_state['last_trends']
            
            st.markdown("### 📊 Price Prediction Results")
            
            # Main metrics
            met_col1, met_col2, met_col3 = st.columns(3)
            
            with met_col1:
                st.metric(
                    "Predicted Price",
                    f"${prediction.get('predicted_price', 0):.2f}",
                    delta=f"{prediction.get('trend_direction', 'stable').upper()}"
                )
            
            with met_col2:
                confidence = prediction.get('confidence_score', 0)
                st.metric("Confidence", f"{confidence}%")
                if confidence >= 80:
                    st.success("High confidence")
                elif confidence >= 60:
                    st.warning("Medium confidence")
                else:
                    st.error("Low confidence")
            
            with met_col3:
                optimal = prediction.get('optimal_listing_price', prediction.get('predicted_price', 0))
                st.metric("Optimal List Price", f"${optimal:.2f}")
            
            # Price range
            price_range = prediction.get('price_range', {})
            if price_range:
                st.markdown(f"**Expected Price Range:** ${price_range.get('low', 0):.2f} - ${price_range.get('high', 0):.2f}")
            
            # Days to sell
            days_est = prediction.get('days_to_sell_estimate', 0)
            if days_est:
                st.markdown(f"**Estimated Days to Sell:** {days_est} days")
            
            # AI Reasoning
            st.markdown("### 🤖 AI Analysis")
            st.info(prediction.get('reasoning', 'No reasoning provided'))
            
            # Factors
            factors = prediction.get('factors', {})
            if factors:
                st.markdown("### 📈 Market Factors")
                
                factor_cols = st.columns(5)
                
                factor_items = [
                    ("Market Demand", factors.get('market_demand', 'N/A')),
                    ("Price Momentum", factors.get('price_momentum', 'N/A')),
                    ("Seasonality", factors.get('seasonality_impact', 'N/A')),
                    ("Volatility Risk", factors.get('volatility_risk', 'N/A')),
                    ("Action", factors.get('recommended_action', 'N/A'))
                ]
                
                for col, (label, value) in zip(factor_cols, factor_items):
                    with col:
                        color = "green" if value in ['high', 'positive', 'favorable', 'low', 'list_now'] else \
                                "red" if value in ['low', 'negative', 'unfavorable', 'high', 'wait'] else "orange"
                        st.markdown(f"**{label}**")
                        st.markdown(f":{color}[{value.replace('_', ' ').title()}]")
            
            # Historical comparison
            st.markdown("### 📉 Historical Context")
            hist_cols = st.columns(4)
            
            with hist_cols[0]:
                st.metric("Avg Sold", f"${trends.get('avg_sold_price', 0):.2f}")
            with hist_cols[1]:
                st.metric("7-Day Change", f"{trends.get('price_7d_change', 0):.1f}%")
            with hist_cols[2]:
                st.metric("30-Day Change", f"{trends.get('price_30d_change', 0):.1f}%")
            with hist_cols[3]:
                st.metric("Volume Trend", trends.get('volume_trend', 'N/A').title())
        else:
            st.info("Select a shoe and generate a prediction to see results here.")

with tab2:
    st.subheader("Batch Price Predictions")
    st.markdown("Generate predictions for your entire inventory at once.")
    
    inventory = get_inventory_items(user_id)
    
    if not inventory:
        st.warning("No inventory items found. Add items to your inventory first.")
    else:
        st.info(f"Found {len(inventory)} items in your inventory")
        
        if st.button("🚀 Generate Batch Predictions", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            
            for i, item in enumerate(inventory):
                status_text.text(f"Processing {item['shoe_name']}...")
                
                sold_data = get_historical_sold_data(user_id, item['sku'])
                trends = calculate_price_trends(sold_data) if sold_data else {
                    'avg_sold_price': 150, 'min_sold_price': 100, 'max_sold_price': 250,
                    'price_7d_change': 0, 'price_30d_change': 0, 'price_90d_change': 0,
                    'volume_7d': 0, 'volume_30d': 0, 'volume_trend': 'unknown',
                    'volatility_score': 15, 'seasonality_factor': 1.0
                }
                
                prediction = get_