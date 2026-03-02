import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Monthly Financial Email Report", page_icon="🍑", layout="wide")

init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_reports (
                id SERIAL PRIMARY KEY,
                report_month VARCHAR(7) NOT NULL,
                recipient_email VARCHAR(255) NOT NULL,
                subject VARCHAR(500),
                narrative TEXT,
                total_income DECIMAL(12,2),
                total_expenses DECIMAL(12,2),
                savings_rate DECIMAL(5,2),
                category_breakdown JSONB,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'sent',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_preferences (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                enabled BOOLEAN DEFAULT TRUE,
                recipient_emails TEXT,
                send_day INTEGER DEFAULT 1,
                send_hour INTEGER DEFAULT 8,
                include_charts BOOLEAN DEFAULT TRUE,
                include_category_breakdown BOOLEAN DEFAULT TRUE,
                include_comparison BOOLEAN DEFAULT TRUE,
                gmail_address VARCHAR(255),
                gmail_app_password VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_recipients (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                email VARCHAR(255) NOT NULL,
                name VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_month TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                subject TEXT,
                narrative TEXT,
                total_income REAL,
                total_expenses REAL,
                savings_rate REAL,
                category_breakdown TEXT,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'sent',
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                enabled INTEGER DEFAULT 1,
                recipient_emails TEXT,
                send_day INTEGER DEFAULT 1,
                send_hour INTEGER DEFAULT 8,
                include_charts INTEGER DEFAULT 1,
                include_category_breakdown INTEGER DEFAULT 1,
                include_comparison INTEGER DEFAULT 1,
                gmail_address TEXT,
                gmail_app_password TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_recipients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                email TEXT NOT NULL,
                name TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()


_ensure_tables()

st.title("📧 Monthly Financial Email Report")

# Display metrics
col1, col2, col3 = st.columns(3)
col1.metric("💰 Income", "$0.00")
col2.metric("💸 Expenses", "$0.00")
col3.metric("📈 Savings Rate", "0%")