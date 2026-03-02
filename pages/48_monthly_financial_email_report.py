import streamlit as st
import datetime
import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from decimal import Decimal
import anthropic

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
                narrative_summary TEXT,
                total_income DECIMAL(12,2),
                total_expenses DECIMAL(12,2),
                savings_rate DECIMAL(5,2),
                net_worth_start DECIMAL(14,2),
                net_worth_end DECIMAL(14,2),
                net_worth_delta DECIMAL(14,2),
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'sent',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_preferences (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                recipient_email VARCHAR(255),
                smtp_server VARCHAR(255) DEFAULT 'smtp.gmail.com',
                smtp_port INTEGER DEFAULT 587,
                sender_email VARCHAR(255),
                sender_password_encrypted VARCHAR(500),
                auto_send_enabled BOOLEAN DEFAULT FALSE,
                send_day_of_month INTEGER DEFAULT 1,
                include_income_breakdown BOOLEAN DEFAULT TRUE,
                include_expense_breakdown BOOLEAN DEFAULT TRUE,
                include_savings_analysis BOOLEAN DEFAULT TRUE,
                include_net_worth BOOLEAN DEFAULT TRUE,
                include_ai_insights BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_month TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                subject TEXT,
                narrative_summary TEXT,
                total_income REAL,
                total_expenses REAL,
                savings_rate REAL,
                net_worth_start REAL,
                net_worth_end REAL,
                net_worth_delta REAL,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'sent',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                recipient_email TEXT,
                smtp_server TEXT DEFAULT 'smtp.gmail.com',
                smtp_port INTEGER DEFAULT 587,
                sender_email TEXT,
                sender_password_encrypted TEXT,
                auto_send_enabled INTEGER DEFAULT 0,
                send_day_of_month INTEGER DEFAULT 1,
                include_income_breakdown INTEGER DEFAULT 1,
                include_expense_breakdown INTEGER DEFAULT 1,
                include_savings_analysis INTEGER DEFAULT 1,
                include_net_worth INTEGER DEFAULT 1,
                include_ai_insights INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


def get_email_preferences(user_id=1):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT * FROM email_report_preferences WHERE user_id = {ph}", (user_id,))
    row = cur.fetchone()
    
    if row:
        columns = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else []
        conn.close()
        return dict(zip(columns, row)) if columns else None
    
    conn.close()
    return None


def save_email_preferences(user_id, preferences):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"SELECT id FROM email_report_preferences WHERE user_id = {ph}", (user_id,))
    exists = cur.fetchone()
    
    if exists:
        cur.execute(f"""
            UPDATE email_report_preferences SET
                recipient_email = {ph},
                smtp_server = {ph},
                smtp_port = {ph},
                sender_email = {ph},
                sender_password_encrypted = {ph},
                auto_send_enabled = {ph},
                send_day_of_month = {ph},
                include_income_breakdown = {ph},
                include_expense_breakdown = {ph},
                include_savings_analysis = {ph},
                include_net_worth = {ph},
                include_ai_insights = {ph},
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = {ph}
        """, (
            preferences.get('recipient_email'),
            preferences.get('smtp_server', 'smtp.gmail.com'),
            preferences.get('smtp_port', 587),
            preferences.get('sender_email'),
            preferences.get('sender_password_encrypted'),
            preferences.get('auto_send_enabled', False),
            preferences.get('send_day_of_month', 1),
            preferences.get('include_income_breakdown', True),
            preferences.get('include_expense_breakdown', True),
            preferences.get('include_savings_analysis', True),
            preferences.get('include_net_worth', True),
            preferences.get('include_ai_insights', True),
            user_id
        ))
    else:
        cur.execute(f"""
            INSERT INTO email_report_preferences (
                user_id, recipient_email, smtp_server, smtp_port, sender_email,
                sender_password_encrypted, auto_send_enabled, send_day_of_month,
                include_income_breakdown, include_expense_breakdown, include_savings_analysis,
                include_net_worth, include_ai_insights
            ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (
            user_id,
            preferences.get('recipient_email'),
            preferences.get('smtp_server', 'smtp.gmail.com'),
            preferences.get('smtp_port', 587),
            preferences.get('sender_email'),
            preferences.get('sender_password_encrypted'),
            preferences.get('auto_send_enabled', False),
            preferences.get('send_day_of_month', 1),
            preferences.get('include_income_breakdown', True),
            preferences.get('include_expense_breakdown', True),
            preferences.get('include_savings_analysis', True),
            preferences.get('include_net_worth', True),
            preferences.get('include_ai_insights', True)
        ))
    
    conn.commit()
    conn.close()


def save_report_to_db(data, narrative, recipient_email, subject, status='sent'):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        INSERT INTO email_reports (
            report_month, recipient_email, subject, narrative_summary,
            total_income, total_expenses, savings_rate,
            net_worth_start, net_worth_end, net_worth_delta, status
        ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (
        data.get('report_month'),
        recipient_email,
        subject,
        narrative,
        data.get('total_income', 0),
        data.get('total_expenses', 0),
        data.get('savings_rate', 0),
        data.get('net_worth_start', 0),
        data.get('net_worth_end', 0),
        data.get('net_worth_delta', 0),
        status
    ))
    
    conn.commit()
    conn.close()


# Initialize tables
_ensure_tables()

# Main page content
st.title("📧 Monthly Financial Email Report")
st.markdown("Configure and send monthly financial summary reports via email.")

# Display preferences form
st.subheader("Email Settings")

prefs = get_email_preferences() or {}

with st.form("email_preferences_form"):
    recipient_email = st.text_input("Recipient Email", value=prefs.get('recipient_email', ''))
    sender_email = st.text_input("Sender Email", value=prefs.get('sender_email', ''))
    sender_password = st.text_input("Sender Password (App Password)", type="password")
    smtp_server = st.text_input("SMTP Server", value=prefs.get('smtp_server', 'smtp.gmail.com'))
    smtp_port = st.number_input("SMTP Port", value=prefs.get('smtp_port', 587), min_value=1, max_value=65535)
    
    st.markdown("**Report Options**")
    include_income = st.checkbox("Include Income Breakdown", value=prefs.get('include_income_breakdown', True))
    include_expenses = st.checkbox("Include Expense Breakdown", value=prefs.get('include_expense_breakdown', True))
    include_savings = st.checkbox("Include Savings Analysis", value=prefs.get('include_savings_analysis', True))
    include_net_worth = st.checkbox("Include Net Worth", value=prefs.get('include_net_worth', True))
    include_ai = st.checkbox("Include AI Insights", value=prefs.get('include_ai_insights', True))
    
    submitted = st.form_submit_button("Save Preferences")
    
    if submitted:
        new_prefs = {
            'recipient_email': recipient_email,
            'sender_email': sender_email,
            'sender_password_encrypted': sender_password if sender_password else prefs.get('sender_password_encrypted'),
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'include_income_breakdown': include_income,
            'include_expense_breakdown': include_expenses,
            'include_savings_analysis': include_savings,
            'include_net_worth': include_net_worth,
            'include_ai_insights': include_ai
        }
        save_email_preferences(1, new_prefs)
        st.success("Preferences saved!")
        st.rerun()