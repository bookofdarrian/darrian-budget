"""
SoleOps: Inventory Health Score
AI-powered dashboard that calculates a composite health score for your sneaker inventory
based on age, pricing competitiveness, sell-through rate, and market demand trends.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import anthropic

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps: Inventory Health Score", page_icon="🍑", layout="wide")
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
    """Create all required tables for inventory health scoring."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        # Main health scores table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_health_scores (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                health_score DECIMAL(5,2) DEFAULT 0,
                age_score DECIMAL(5,2) DEFAULT 0,
                price_score DECIMAL(5,2) DEFAULT 0,
                velocity_score DECIMAL(5,2) DEFAULT 0,
                demand_score DECIMAL(5,2) DEFAULT 0,
                details JSONB,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, sku, calculated_at::date)
            )
        """)
        
        # Weekly snapshots for trend tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_health_snapshots (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                snapshot_date DATE NOT NULL,
                avg_health_score DECIMAL(5,2) DEFAULT 0,
                total_items INTEGER DEFAULT 0,
                items_below_threshold INTEGER DEFAULT 0,
                score_breakdown JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, snapshot_date)
            )
        """)
        
        # Health alerts table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_health_alerts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                alert_type VARCHAR(50) NOT NULL,
                health_score DECIMAL(5,2),
                message TEXT,
                is_acknowledged BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User settings for health score thresholds
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_health_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                alert_threshold INTEGER DEFAULT 40,
                age_weight DECIMAL(3,2) DEFAULT 0.25,
                price_weight DECIMAL(3,2) DEFAULT 0.25,
                velocity_weight DECIMAL(3,2) DEFAULT 0.25,
                demand_weight DECIMAL(3,2) DEFAULT 0.25,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Ensure soleops_inventory exists for demo data
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                name VARCHAR(255),
                brand VARCHAR(100),
                size VARCHAR(20),
                condition VARCHAR(50),
                purchase_price DECIMAL(10,2),
                list_price DECIMAL(10,2),
                platform VARCHAR(50),
                status VARCHAR(50) DEFAULT 'active',
                date_acquired DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Ensure soleops_sales_velocity exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sales_velocity (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                avg_days_to_sell DECIMAL(10,2),
                total_sold INTEGER DEFAULT 0,
                last_sale_date DATE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    cur.close()


def get_ai_analysis(inventory_data, health_scores):
    """Get AI-powered analysis of inventory health."""
    try:
        client = anthropic.Anthropic()
        
        prompt = f"""You are a sneaker resale expert analyzing inventory health. 
Based on the following inventory data and health scores, provide actionable insights:

Inventory Summary:
{json.dumps(inventory_data, indent=2, default=str)}

Health Scores:
{json.dumps(health_scores, indent=2, default=str)}

Provide:
1. Top 3 items that need immediate attention
2. Recommended actions to improve overall inventory health
3. Market trend observations
4. Pricing strategy suggestions

Keep response concise and actionable."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text
    except Exception as e:
        return f"AI analysis unavailable: {str(e)}"


def main():
    st.title("🍑 SoleOps: Inventory Health Score")
    st.markdown("AI-powered dashboard for sneaker inventory health analysis")
    
    _ensure_tables()
    
    # Placeholder for main content
    st.info("Dashboard content goes here")


if __name__ == "__main__":
    main()