import streamlit as st
import datetime
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List, Tuple
import calendar

st.set_page_config(page_title="Monthly Financial Email Report", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_reports (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                report_month DATE NOT NULL,
                html_content TEXT,
                sent_at TIMESTAMP,
                status VARCHAR(50) DEFAULT 'pending',
                recipient_email VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_preferences (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                recipient_email VARCHAR(255),
                send_time VARCHAR(10) DEFAULT '08:00',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                report_month DATE NOT NULL,
                html_content TEXT,
                sent_at TIMESTAMP,
                status VARCHAR(50) DEFAULT 'pending',
                recipient_email VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                recipient_email VARCHAR(255),
                send_time VARCHAR(10) DEFAULT '08:00',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

def get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def get_user_id() -> int:
    return st.session_state.get("user_id", 1)

def get_email_preferences(user_id: int) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"SELECT enabled, recipient_email, send_time FROM email_preferences WHERE user_id = {ph}", (user_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "enabled": bool(row[0]),
            "recipient_email": row[1] or "",
            "send_time": row[2] or "08:00"
        }
    return {"enabled": True, "recipient_email": "", "send_time": "08:00"}

def save_email_preferences(user_id: int, enabled: bool, recipient_email: str, send_time: str):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    if USE_POSTGRES:
        cur.execute(f"""
            INSERT INTO email_preferences (user_id, enabled, recipient_email, send_time, updated_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                enabled = EXCLUDED.enabled,
                recipient_email = EXCLUDED.recipient_email,
                send_time = EXCLUDED.send_time,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, enabled, recipient_email, send_time))
    else:
        cur.execute(f"SELECT id FROM email_preferences WHERE user_id = {ph}", (user_id,))
        if cur.fetchone():
            cur.execute(f"""
                UPDATE email_preferences 
                SET enabled = {ph}, recipient_email = {ph}, send_time = {ph}, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = {ph}
            """, (enabled, recipient_email, send_time, user_id))
        else:
            cur.execute(f"""
                INSERT INTO email_preferences (user_id, enabled, recipient_email, send_time)
                VALUES ({ph}, {ph}, {ph}, {ph})
            """, (user_id, enabled, recipient_email, send_time))
    
    conn.commit()
    conn.close()

def get_monthly_expenses(user_id: int, year: int, month: int) -> List[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    start_date = f"{year}-{month:02d}-01"
    last_day = calendar.monthrange(year, month)[1]
    end_date = f"{year}-{month:02d}-{last_day}"
    
    try:
        cur.execute(f"""
            SELECT id, amount, category, description, date 
            FROM expenses 
            WHERE user_id = {ph} AND date >= {ph} AND date <= {ph}
            ORDER BY date DESC
        """, (user_id, start_date, end_date))
        rows = cur.fetchall()
        expenses = []
        for row in rows:
            expenses.append({
                "id": row[0],
                "amount": row[1],
                "category": row[2],
                "description": row[3],
                "date": row[4]
            })
        return expenses
    except Exception as e:
        st.error(f"Error fetching expenses: {e}")
        return []
    finally:
        conn.close()

# Main page content
st.title("📧 Monthly Financial Email Report")

user_id = get_user_id()
prefs = get_email_preferences(user_id)

st.subheader("Email Preferences")

with st.form("email_prefs_form"):
    enabled = st.checkbox("Enable monthly email reports", value=prefs["enabled"])
    recipient_email = st.text_input("Recipient Email", value=prefs["recipient_email"])
    send_time = st.text_input("Send Time (HH:MM)", value=prefs["send_time"])
    
    if st.form_submit_button("Save Preferences"):
        save_email_preferences(user_id, enabled, recipient_email, send_time)
        st.success("Preferences saved successfully!")

st.subheader("Preview Report")

today = datetime.date.today()
col1, col2 = st.columns(2)
with col1:
    year = st.selectbox("Year", range(today.year - 5, today.year + 1), index=5)
with col2:
    month = st.selectbox("Month", range(1, 13), index=today.month - 1, format_func=lambda x: calendar.month_name[x])

expenses = get_monthly_expenses(user_id, year, month)

if expenses:
    st.write(f"Found {len(expenses)} expenses for {calendar.month_name[month]} {year}")
    total = sum(e["amount"] for e in expenses)
    st.metric("Total Expenses", f"${total:,.2f}")
    
    for expense in expenses:
        st.write(f"- {expense['date']}: {expense['category']} - ${expense['amount']:,.2f} ({expense['description']})")
else:
    st.info(f"No expenses found for {calendar.month_name[month]} {year}")