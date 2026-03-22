import streamlit as st
import datetime
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from anthropic import Anthropic
import json
import traceback

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Monthly Financial Email Report", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

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
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_history (
                id SERIAL PRIMARY KEY,
                report_date DATE NOT NULL,
                recipient VARCHAR(255) NOT NULL,
                subject VARCHAR(500) NOT NULL,
                body_html TEXT NOT NULL,
                sent_at TIMESTAMP,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_config (
                id SERIAL PRIMARY KEY,
                recipient_email VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_schedule (
                id SERIAL PRIMARY KEY,
                day_of_month INTEGER DEFAULT 1,
                hour INTEGER DEFAULT 8,
                minute INTEGER DEFAULT 0,
                is_enabled BOOLEAN DEFAULT TRUE,
                last_run TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date DATE NOT NULL,
                recipient TEXT NOT NULL,
                subject TEXT NOT NULL,
                body_html TEXT NOT NULL,
                sent_at TIMESTAMP,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_email TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_of_month INTEGER DEFAULT 1,
                hour INTEGER DEFAULT 8,
                minute INTEGER DEFAULT 0,
                is_enabled INTEGER DEFAULT 1,
                last_run TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


def get_monthly_financials(year: int, month: int) -> dict:
    """Aggregate monthly financial data from existing tables."""
    conn = get_conn()
    cur = conn.cursor()
    
    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1)
    else:
        end_date = datetime.date(year, month + 1, 1)
    
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    prev_start = datetime.date(prev_year, prev_month, 1)
    prev_end = start_date
    
    financials = {
        "year": year,
        "month": month,
        "month_name": start_date.strftime("%B %Y"),
        "total_income": 0,
        "total_expenses": 0,
        "net_savings": 0,
        "expense_categories": {},
        "income_sources": {},
        "net_worth_current": 0,
        "net_worth_previous": 0,
        "net_worth_delta": 0,
        "goals_progress": [],
        "top_expenses": [],
        "savings_rate": 0,
        "prev_month_income": 0,
        "prev_month_expenses": 0,
    }
    
    ph = "%s" if USE_POSTGRES else "?"
    
    try:
        cur.execute(f"""
            SELECT COALESCE(SUM(amount), 0) FROM income 
            WHERE date >= {ph} AND date < {ph}
        """, (start_date, end_date))
        row = cur.fetchone()
        financials["total_income"] = float(row[0]) if row else 0
    except Exception as e:
        st.warning(f"Error fetching income: {e}")
    
    conn.close()
    return financials


def get_schedule_config():
    """Get the current schedule configuration."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT day_of_month, hour, minute, is_enabled, last_run FROM email_report_schedule LIMIT 1")
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "day_of_month": row[0],
            "hour": row[1],
            "minute": row[2],
            "is_enabled": bool(row[3]),
            "last_run": row[4]
        }
    return {
        "day_of_month": 1,
        "hour": 8,
        "minute": 0,
        "is_enabled": False,
        "last_run": None
    }


def save_schedule_config(day_of_month, hour, minute, is_enabled):
    """Save the schedule configuration."""
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute("SELECT id FROM email_report_schedule LIMIT 1")
    row = cur.fetchone()
    
    if row:
        cur.execute(f"""
            UPDATE email_report_schedule 
            SET day_of_month = {ph}, hour = {ph}, minute = {ph}, is_enabled = {ph}, updated_at = CURRENT_TIMESTAMP
            WHERE id = {ph}
        """, (day_of_month, hour, minute, is_enabled, row[0]))
    else:
        cur.execute(f"""
            INSERT INTO email_report_schedule (day_of_month, hour, minute, is_enabled)
            VALUES ({ph}, {ph}, {ph}, {ph})
        """, (day_of_month, hour, minute, is_enabled))
    
    conn.commit()
    conn.close()


_ensure_tables()

st.title("📧 Monthly Financial Email Report")

tab1, tab2, tab3 = st.tabs(["Generate Report", "Schedule", "History"])

with tab1:
    st.subheader("Generate Monthly Report")
    
    col1, col2 = st.columns(2)
    with col1:
        year = st.number_input("Year", min_value=2020, max_value=2030, value=datetime.date.today().year)
    with col2:
        month = st.number_input("Month", min_value=1, max_value=12, value=datetime.date.today().month)
    
    if st.button("Generate Report"):
        financials = get_monthly_financials(year, month)
        st.json(financials)

with tab2:
    st.subheader("Schedule Settings")
    
    config = get_schedule_config()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        day_of_month = st.number_input(
            "Day of Month",
            min_value=1,
            max_value=28,
            value=config["day_of_month"]
        )
    with col2:
        hour = st.number_input(
            "Hour (24h)",
            min_value=0,
            max_value=23,
            value=config["hour"]
        )
    with col3:
        minute = st.number_input(
            "Minute",
            min_value=0,
            max_value=59,
            value=config["minute"]
        )
    
    is_enabled = st.checkbox("Enable Scheduled Reports", value=config["is_enabled"])
    
    if st.button("Save Schedule"):
        save_schedule_config(day_of_month, hour, minute, is_enabled)
        st.success("Schedule saved!")

with tab3:
    st.subheader("Report History")
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT report_date, recipient, subject, status, sent_at FROM email_report_history ORDER BY created_at DESC LIMIT 20")
    rows = cur.fetchall()
    conn.close()
    
    if rows:
        for row in rows:
            st.write(f"**{row[0]}** - {row[2]} ({row[3]})")
    else:
        st.info("No reports sent yet.")