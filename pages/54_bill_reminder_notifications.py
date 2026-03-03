import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css
from datetime import datetime, timedelta
import json
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.set_page_config(page_title="Bill Reminder Notifications", page_icon="🍑", layout="wide")
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
            CREATE TABLE IF NOT EXISTS bill_reminders (
                id SERIAL PRIMARY KEY,
                bill_id INTEGER NOT NULL,
                bill_name VARCHAR(255) NOT NULL,
                due_date DATE NOT NULL,
                reminder_days INTEGER NOT NULL DEFAULT 7,
                notification_type VARCHAR(50) NOT NULL DEFAULT 'both',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notification_history (
                id SERIAL PRIMARY KEY,
                reminder_id INTEGER REFERENCES bill_reminders(id),
                bill_name VARCHAR(255) NOT NULL,
                notification_type VARCHAR(50) NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) NOT NULL,
                message TEXT,
                error_message TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notification_settings (
                id SERIAL PRIMARY KEY,
                setting_key VARCHAR(100) UNIQUE NOT NULL,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                amount DECIMAL(10,2),
                due_date DATE,
                category VARCHAR(100),
                is_recurring BOOLEAN DEFAULT FALSE,
                frequency VARCHAR(50),
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bill_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER NOT NULL,
                bill_name TEXT NOT NULL,
                due_date DATE NOT NULL,
                reminder_days INTEGER NOT NULL DEFAULT 7,
                notification_type TEXT NOT NULL DEFAULT 'both',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id INTEGER,
                bill_name TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                message TEXT,
                error_message TEXT,
                FOREIGN KEY (reminder_id) REFERENCES bill_reminders(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notification_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL,
                due_date DATE,
                category TEXT,
                is_recurring INTEGER DEFAULT 0,
                frequency TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()

def get_notification_setting(key, default=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT setting_value FROM notification_settings WHERE setting_key = {ph}", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else default

def set_notification_setting(key, value):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO notification_settings (setting_key, setting_value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (setting_key) DO UPDATE SET setting_value = %s, updated_at = CURRENT_TIMESTAMP
        """, (key, value, value))
    else:
        cur.execute("""
            INSERT OR REPLACE INTO notification_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))
    conn.commit()
    conn.close()

def get_bills():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, amount, due_date, category, status FROM bills ORDER BY due_date")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_reminders():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            SELECT id, bill_id, bill_name, due_date, reminder_days, notification_type, is_active
            FROM bill_reminders ORDER BY due_date
        """)
    else:
        cur.execute("""
            SELECT id, bill_id, bill_name, due_date, reminder_days, notification_type, is_active
            FROM bill_reminders ORDER BY due_date
        """)
    rows = cur.fetchall()
    conn.close()
    return rows

def add_reminder(bill_id, bill_name, due_date, reminder_days, notification_type):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO bill_reminders (bill_id, bill_name, due_date, reminder_days, notification_type)
            VALUES (%s, %s, %s, %s, %s)
        """, (bill_id, bill_name, due_date, reminder_days, notification_type))
    else:
        cur.execute("""
            INSERT INTO bill_reminders (bill_id, bill_name, due_date, reminder_days, notification_type)
            VALUES (?, ?, ?, ?, ?)
        """, (bill_id, bill_name, due_date, reminder_days, notification_type))
    conn.commit()
    conn.close()

def update_reminder(reminder_id, reminder_days, notification_type, is_active):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            UPDATE bill_reminders 
            SET reminder_days = %s, notification_type = %s, is_active = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (reminder_days, notification_type, is_active, reminder_id))
    else:
        cur.execute("""
            UPDATE bill_reminders 
            SET reminder_days = ?, notification_type = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (reminder_days, notification_type, is_active, reminder_id))
    conn.commit()
    conn.close()

def delete_reminder(reminder_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM bill_reminders WHERE id = {ph}", (reminder_id,))
    conn.commit()
    conn.close()

def log_notification(reminder_id, bill_name, notification_type, status, message, error_message=None):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO notification_history (reminder_id, bill_name, notification_type, status, message, error_message)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (reminder_id, bill_name, notification_type, status, message, error_message))
    else:
        cur.execute("""
            INSERT INTO notification_history (reminder_id, bill_name, notification_type, status, message, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (reminder_id, bill_name, notification_type, status, message, error_message))
    conn.commit()
    conn.close()

def get_notification_history(limit=50):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, reminder_id, bill_name, notification_type, sent_at, status, message, error_message
        FROM notification_history ORDER BY sent_at DESC LIMIT {limit}
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_upcoming_reminders():
    conn = get_conn()
    cur = conn.cursor()
    today = datetime.now().date()
    if USE_POSTGRES:
        cur.execute("""
            SELECT id, bill_id, bill_name, due_date, reminder_days, notification_type
            FROM bill_reminders 
            WHERE is_active = TRUE AND due_date >= %s
            ORDER BY due_date
        """, (today,))
    else:
        cur.execute("""
            SELECT id, bill_id, bill_name, due_date, reminder_days, notification_type
            FROM bill_reminders 
            WHERE is_active = 1 AND due_date >= ?
            ORDER BY due_date
        """, (str(today),))
    rows = cur.fetchall()
    conn.close()
    
    upcoming = []
    for row in rows:
        reminder_id, bill_id, bill_name, due_date, reminder_days, notification_type = row
        if isinstance(due_date, str):
            due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
        reminder_date = due_date - timedelta(days=reminder_days)
        days_until_due = (due_date - today).days
        days_until_reminder = (reminder_date - today).days
        upcoming.append({
            "id": reminder_id,
            "bill_id": bill_id,
            "bill_name": bill_name,
            "due_date": due_date,
            "reminder_days": reminder_days,
            "notification_type": notification_type,
            "reminder_date": reminder_date,
            "days_until_due": days_until_due,
            "days_until_reminder": days_until_reminder,
            "should_send": days_until_reminder <= 0 and days_until_due >= 0
        })
    return upcoming

def send_telegram_notification(message):
    bot_token = get_notification_setting("telegram_bot_token")
    chat_id = get_notification_setting("telegram_chat_id")
    if not bot_token or not chat_id:
        return False, "Telegram credentials not configured"
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True, "Message sent successfully"
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return False, str(e)

def send_email_notification(subject, message):
    smtp_server = get_notification_setting("smtp_server")
    smtp_port = get_notification_setting("smtp_port", "587")
    smtp_username = get_notification_setting("smtp_username")
    smtp_password = get_notification_setting("smtp_password")
    recipient_email = get_notification_setting("recipient_email")
    if not all([smtp_server, smtp_username, smtp_password, recipient_email]):
        return False, "Email credentials not fully configured"
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_username
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "html"))
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, recipient_email, msg.as_string())
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)

def send_reminder(reminder):
    bill_name = reminder["bill_name"]
    due_date = reminder["due_date"]
    days_until_due = reminder["days_until_due"]
    notification_type = reminder["notification_type"]
    
    if days_until_due == 0:
        urgency = "🚨 DUE TODAY"
    elif days_until_due == 1:
        urgency = "⚠️ DUE TOMORROW"
    elif days_until_due <= 3:
        urgency = f"⏰ Due in {days_until_due} days"
    else:
        urgency = f"📅 Due in {days_until_due} days"
    
    message = f"""
<b>{urgency}</b>

<b>Bill:</b> {bill_name}
<b>Due Date:</b> {due_date.strftime("%B %d, %Y")}
<b>Days Until Due:</b> {days_until_due}

Don't forget to pay this bill to avoid late fees!
    """.strip()
    
    results = []
    if notification_type in ["telegram", "both"]:
        success, msg = send_telegram_notification(message)
        log_notification(reminder["id"], bill_name, "telegram", "success" if success else "failed", message, None if success else msg)
        results.append(("Telegram", success, msg))
    
    if notification_type in ["email", "both"]:
        subject = f"Bill Reminder: {bill_name} - {urgency}"
        success, msg = send_email_notification(subject, message)
        log_notification(reminder["id"], bill_name, "email", "success" if success else "failed", message, None if success else msg)
        results.append(("Email", success, msg))
    
    return results

_ensure_tables()

st.title("🔔 Bill Reminder Notifications")
st.markdown("Automated bill payment reminder system with Telegram/email alerts to prevent late fees.")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "➕ Add Reminder", "⚙️ Settings", "📜 History"])

with tab1:
    st.subheader("Upcoming Bill Reminders")
    
    upcoming = get_upcoming_reminders()
    
    if not upcoming:
        st.info("No active reminders configured. Add reminders in the 'Add Reminder' tab.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        due_today = sum(1 for r in upcoming if r["days_until_due"] == 0)
        due_this_week = sum(1 for r in upcoming if 0 < r["days_until_due"] <= 7)
        due_this_month = sum(1 for r in upcoming if 7 < r["days_until_due"] <= 30)
        total_active = len(upcoming)
        
        col1.metric("🚨 Due Today", due_today)
        col2.metric("📅 This Week", due_this_week)
        col3.metric("📆 This Month", due_this_month)
        col4.metric("✅ Total Active", total_active)
        
        st.markdown("---")
        
        needs_sending = [r for r in upcoming if r["should_send"]]
        if needs_sending:
            st.warning(f"⚠️ {len(needs_sending)} reminder(s) ready to send!")
            if st.button("📤 Send All Due Reminders", type="primary"):
                with st.spinner("Sending notifications..."):
                    for reminder in needs_sending:
                        results = send_reminder(reminder)
                        for channel, success, msg in results:
                            if success:
                                st.success(f"✅ {channel}: {reminder['bill_name']} - {msg}")
                            else:
                                st.error(f"❌ {channel}: {reminder['bill_name']} - {msg}")
                st.rerun()
        
        st.markdown("### 📋 All Upcoming Reminders")
        for reminder in upcoming:
            days = reminder["days_until_due"]
            if days == 0:
                color = "🔴"
                urgency = "TODAY"
            elif days <= 3:
                color = "🟠"
                urgency = f"{days} days"
            elif days <= 7:
                color = "🟡"
                urgency = f"{days} days"
            else:
                color = "🟢"
                urgency = f"{days} days"
            
            with st.expander(f"{color} {reminder['bill_name']} - Due: {reminder['due_date']} ({urgency})"):
                col1, col2, col3 = st.columns(3)
                col1.write(f"**Reminder:** {reminder['reminder_days']} days before")
                col2.write(f"**Channel:** {reminder['notification_type'].title()}")
                col3.write(f"**Reminder Date:** {reminder['reminder_date']}")
                
                btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
                with btn_col1:
                    if st.button("📤 Send Now", key=f"send_{reminder['id']}"):
                        with st.spinner("Sending..."):
                            results = send_reminder(reminder)
                            for channel, success, msg in results:
                                if success:
                                    st.success(f"✅ {channel}: {msg}")
                                else:
                                    st.error(f"❌ {channel}: {msg}")
                with btn_col2:
                    if st.button("🗑️ Delete", key=f"del_{reminder['id']}"):
                        delete_reminder(reminder["id"])
                        st.success("Reminder deleted!")
                        st.rerun()

with tab2:
    st.subheader("Add New Bill Reminder")
    
    bills = get_bills()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### From Existing Bills")
        if bills:
            bill_options = {f"{b[1]} (Due: {b[3]})": b for b in bills}
            selected_bill = st.selectbox("Select a bill", options=list(bill_options.keys()))
            
            if selected_bill:
                bill = bill_options[selected_bill]
                st.write(f"**Amount:** ${bill[2]:.2f}" if bill[2] else "**Amount:** Not set")
                st.write(f"**Category:** {bill[4]}" if bill[4] else "**Category:** Not set")
        else:
            st.info("No bills found. Add bills in the Bills page or create a custom reminder below.")
            selected_bill = None
    
    with col2:
        st.markdown("#### Custom Reminder")
        custom_bill_name = st.text_input("Bill Name", placeholder="e.g., Rent, Electric Bill")
        custom_due_date = st.date_input("Due Date", value=datetime.now().date() + timedelta(days=7))
    
    st.markdown("---")
    st.markdown("#### Reminder Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        reminder_days = st.selectbox(
            "Remind me before due date",
            options=[1, 3, 7, 14, 30],
            index=2,
            format_func=lambda x: f"{x} day{'s' if x > 1 else ''} before"
        )
    
    with col2:
        notification_type = st.selectbox(
            "Notification Channel",
            options=["telegram", "email", "both"],
            index=2,
            format_func=lambda x: {"telegram": "📱 Telegram Only", "email": "📧 Email Only", "both": "📱📧 Both"}[x]
        )
    
    if st.button("➕ Add Reminder", type="primary"):
        if selected_bill and bills:
            bill = bill_options[selected_bill]
            bill_id = bill[0]
            bill_name = bill[1]
            due_date = bill[3]
            if isinstance(due_date, str):
                due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
        elif custom_bill_name:
            bill_id = 0
            bill_name = custom_bill_name
            due_date = custom_due_date
        else:
            st.error("Please select a bill or enter a custom bill name.")
            st.stop()
        
        add_reminder(bill_id, bill_name, due_date, reminder_days, notification_type)
        st.success(f"✅ Reminder added for {bill_name}!")
        st.rerun()

with tab3:
    st.subheader("Notification Settings")
    
    st.markdown("### 📱 Telegram Configuration")
    with st.form("telegram_settings"):
        telegram_bot_token = st.text_input(
            "Bot Token",
            value=get_notification_setting("telegram_bot_token", ""),
            type="password",
            help="Get this from @BotFather on Telegram"
        )
        telegram_chat_id = st.text_input(
            "Chat ID",
            value=get_notification_setting("telegram_chat_id", ""),
            help="Your Telegram user ID or group chat ID"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Save Telegram Settings"):
                set_notification_setting("telegram_bot_token", telegram_bot_token)
                set_notification_setting("telegram_chat_id", telegram_chat_id)
                st.success("Telegram settings saved!")
        with col2:
            test_telegram = st.form_submit_button("🧪 Test Telegram")
    
    if test_telegram:
        success, msg = send_telegram_notification("🧪 Test notification from Bill Reminder System!")
        if success:
            st.success(f"✅ Telegram test successful: {msg}")
        else:
            st.error(f"❌ Telegram test failed: {msg}")
    
    st.markdown("---")
    st.markdown("### 📧 Email Configuration")
    with st.form("email_settings"):
        smtp_server = st.text_input(
            "SMTP Server",
            value=get_notification_setting("smtp_server", "smtp.gmail.com"),
            help="e.g., smtp.gmail.com"
        )
        smtp_port = st.text_input(
            "SMTP Port",
            value=get_notification_setting("smtp_port", "587"),
            help="Usually 587 for TLS"
        )
        smtp_username = st.text_input(
            "SMTP Username/Email",
            value=get_notification_setting("smtp_username", ""),
            help="Your email address"
        )
        smtp_password = st.text_input(
            "SMTP Password/App Password",
            value=get_notification_setting("smtp_password", ""),
            type="password",
            help="For Gmail, use an App Password"
        )
        recipient_email = st.text_input(
            "Recipient Email",
            value=get_notification_setting("recipient_email", ""),
            help="Where to send reminders"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Save Email Settings"):
                set_notification_setting("smtp_server", smtp_server)
                set_notification_setting("smtp_port", smtp_port)
                set_notification_setting("smtp_username", smtp_username)
                set_notification_setting("smtp_password", smtp_password)
                set_notification_setting("recipient_email", recipient_email)
                st.success("Email settings saved!")
        with col2:
            test_email = st.form_submit_button("🧪 Test Email")
    
    if test_email:
        success, msg = send_email_notification(
            "🧪 Test - Bill Reminder System",
            "<h2>Test Notification</h2><p>Your Bill Reminder System is configured correctly!</p>"
        )
        if success:
            st.success(f"✅ Email test successful: {msg}")
        else:
            st.error(f"❌ Email test failed: {msg}")
    
    st.markdown("---")
    st.markdown("### ⏰ Default Reminder Preferences")
    with st.form("default_settings"):
        default_reminder_days = st.multiselect(
            "Default reminder intervals",
            options=[1, 3, 7, 14, 30],
            default=[3, 7],
            format_func=lambda x: f"{x} day{'s' if x > 1 else ''}"
        )
        default_channel = st.selectbox(
            "Default notification channel",
            options=["telegram", "email", "both"],
            index=2,
            format_func=lambda x: {"telegram": "Telegram", "email": "Email", "both": "Both"}[x]
        )
        if st.form_submit_button("💾 Save Defaults"):
            set_notification_setting("default_reminder_days", json.dumps(default_reminder_days))
            set_notification_setting("default_channel", default_channel)
            st.success("Default settings saved!")

with tab4:
    st.subheader("Notification History")
    
    history = get_notification_history(100)
    
    if not history:
        st.info("No notifications have been sent yet.")
    else:
        col1, col2 = st.columns(2)
        successful = sum(1 for h in history if h[5] == "success")
        failed = sum(1 for h in history if h[5] == "failed")
        col1.metric("✅ Successful", successful)
        col2.metric("❌ Failed", failed)
        
        st.markdown("---")
        
        for h in history:
            hist_id, reminder_id, bill_name, notif_type, sent_at, status, message, error = h
            icon = "✅" if status == "success" else "❌"
            channel_icon = "📱" if notif_type == "telegram" else "📧"
            
            with st.expander(f"{icon} {channel_icon} {bill_name} - {sent_at}"):
                st.write(f"**Status:** {status.title()}")
                st.write(f"**Channel:** {notif_type.title()}")
                st.write(f"**Sent At:** {sent_at}")
                if error:
                    st.error(f"**Error:** {error}")
                st.text_area("Message Content", value=message, height=100, disabled=True, key=f"msg_{hist_id}")

st.markdown("---")
st.caption("💡 Tip: Set up reminders for 3, 7, and 14 days before due dates to ensure you never miss a payment!")