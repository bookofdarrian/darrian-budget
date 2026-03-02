import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import os

st.set_page_config(page_title="Monthly Financial Email Report", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

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
                user_id INTEGER NOT NULL,
                month VARCHAR(7) NOT NULL,
                html_content TEXT,
                narrative TEXT,
                total_income DECIMAL(12,2) DEFAULT 0,
                total_expenses DECIMAL(12,2) DEFAULT 0,
                savings_rate DECIMAL(5,2) DEFAULT 0,
                sent_at TIMESTAMP,
                status VARCHAR(20) DEFAULT 'draft',
                recipient_email VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                recipient_email VARCHAR(255),
                smtp_host VARCHAR(255) DEFAULT 'smtp.gmail.com',
                smtp_port INTEGER DEFAULT 587,
                smtp_username VARCHAR(255),
                smtp_password VARCHAR(255),
                auto_send_enabled BOOLEAN DEFAULT FALSE,
                send_day INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                month TEXT NOT NULL,
                html_content TEXT,
                narrative TEXT,
                total_income REAL DEFAULT 0,
                total_expenses REAL DEFAULT 0,
                savings_rate REAL DEFAULT 0,
                sent_at TEXT,
                status TEXT DEFAULT 'draft',
                recipient_email TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                recipient_email TEXT,
                smtp_host TEXT DEFAULT 'smtp.gmail.com',
                smtp_port INTEGER DEFAULT 587,
                smtp_username TEXT,
                smtp_password TEXT,
                auto_send_enabled INTEGER DEFAULT 0,
                send_day INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


def get_user_id():
    return st.session_state.get("user_id", 1)


def get_monthly_data(year: int, month: int):
    conn = get_conn()
    cur = conn.cursor()
    
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    user_id = get_user_id()
    ph = "%s" if USE_POSTGRES else "?"
    
    total_expenses = 0
    expenses_by_category = {}
    try:
        cur.execute(f"""
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE user_id = {ph} AND date >= {ph} AND date < {ph}
            GROUP BY category
            ORDER BY total DESC
        """, (user_id, start_date, end_date))
        rows = cur.fetchall()
        for row in rows:
            cat = row[0] or "Uncategorized"
            amt = float(row[1] or 0)
            expenses_by_category[cat] = amt
            total_expenses += amt
    except Exception:
        pass
    
    conn.close()
    return {
        "total_expenses": total_expenses,
        "expenses_by_category": expenses_by_category
    }


def get_report_by_id(report_id):
    conn = get_conn()
    cur = conn.cursor()
    user_id = get_user_id()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT id, month, html_content, narrative, total_income, total_expenses, 
               savings_rate, sent_at, status, recipient_email, created_at
        FROM email_reports
        WHERE id = {ph} AND user_id = {ph}
    """, (report_id, user_id))
    
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "month": row[1],
            "html_content": row[2],
            "narrative": row[3],
            "total_income": row[4],
            "total_expenses": row[5],
            "savings_rate": row[6],
            "sent_at": row[7],
            "status": row[8],
            "recipient_email": row[9],
            "created_at": row[10]
        }
    return None


# Initialize tables
_ensure_tables()

# Main page content
st.title("📧 Monthly Financial Email Report")
st.write("Generate and send monthly financial reports via email.")