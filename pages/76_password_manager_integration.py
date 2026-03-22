import streamlit as st
import json
import hashlib
import re
import math
import subprocess
import requests
from datetime import datetime, timedelta
from collections import Counter

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Password Manager Integration", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS password_audits (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                vault_source VARCHAR(50) NOT NULL,
                audit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_passwords INTEGER DEFAULT 0,
                weak_count INTEGER DEFAULT 0,
                reused_count INTEGER DEFAULT 0,
                compromised_count INTEGER DEFAULT 0,
                security_score INTEGER DEFAULT 0,
                audit_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS security_alerts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                alert_type VARCHAR(50) NOT NULL,
                severity VARCHAR(20) DEFAULT 'medium',
                title VARCHAR(255) NOT NULL,
                description TEXT,
                affected_item VARCHAR(255),
                is_resolved BOOLEAN DEFAULT FALSE,
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS password_health_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                record_date DATE NOT NULL,
                security_score INTEGER DEFAULT 0,
                total_passwords INTEGER DEFAULT 0,
                weak_count INTEGER DEFAULT 0,
                reused_count INTEGER DEFAULT 0,
                compromised_count INTEGER DEFAULT 0,
                avg_password_age_days INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS password_audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                vault_source TEXT NOT NULL,
                audit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_passwords INTEGER DEFAULT 0,
                weak_count INTEGER DEFAULT 0,
                reused_count INTEGER DEFAULT 0,
                compromised_count INTEGER DEFAULT 0,
                security_score INTEGER DEFAULT 0,
                audit_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS security_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT DEFAULT 'medium',
                title TEXT NOT NULL,
                description TEXT,
                affected_item TEXT,
                is_resolved INTEGER DEFAULT 0,
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS password_health_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                record_date DATE NOT NULL,
                security_score INTEGER DEFAULT 0,
                total_passwords INTEGER DEFAULT 0,
                weak_count INTEGER DEFAULT 0,
                reused_count INTEGER DEFAULT 0,
                compromised_count INTEGER DEFAULT 0,
                avg_password_age_days INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

# Sidebar navigation
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# Password Strength Analyzer
def calculate_entropy(password):
    charset_size = 0
    if re.search(r'[a-z]', password):
        charset_size += 26
    if re.search(r'[A-Z]', password):
        charset_size += 26
    if re.search(r'[0-9]', password):
        charset_size += 10
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        charset_size += 32
    if charset_size == 0:
        return 0
    entropy = len(password) * math.log2(charset_size)
    return entropy

def analyze_password_strength(password):
    score = 0
    feedback = []
    
    # Length check
    if len(password) >= 12:
        score += 25
    elif len(password) >= 8:
        score += 15
    else:
        feedback.append("Password is too short (minimum 8 characters)")
    
    # Character variety
    if re.search(r'[a-z]', password):
        score += 10
    else:
        feedback.append("Add lowercase letters")
    
    if re.search(r'[A-Z]', password):
        score += 10
    else:
        feedback.append("Add uppercase letters")
    
    if re.search(r'[0-9]', password):
        score += 10
    else:
        feedback.append("Add numbers")
    
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 15
    else:
        feedback.append("Add special characters")
    
    # Entropy bonus
    entropy = calculate_entropy(password)
    if entropy > 60:
        score += 30
    elif entropy > 40:
        score += 20
    elif entropy > 28:
        score += 10
    
    return min(score, 100), feedback, entropy

def check_password_breach(password):
    """Check if password has been compromised using Have I Been Pwned API"""
    sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix = sha1_hash[:5]
    suffix = sha1_hash[5:]
    
    try:
        response = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}", timeout=5)
        if response.status_code == 200:
            hashes = response.text.split('\r\n')
            for h in hashes:
                if h.split(':')[0] == suffix:
                    return True, int(h.split(':')[1])
        return False, 0
    except Exception:
        return None, 0

def parse_password_export(file_content, file_type):
    """Parse password exports from various password managers"""
    passwords = []
    
    try:
        if file_type == "csv":
            import csv
            import io
            reader = csv.DictReader(io.StringIO(file_content))
            for row in reader:
                # Try to detect format based on column names
                name = row.get('name') or row.get('title') or row.get('website') or row.get('url', '')
                username = row.get('username') or row.get('login') or row.get('email', '')
                password = row.get('password') or row.get('pass', '')
                url = row.get('url') or row.get('website') or row.get('login_uri', '')
                
                if password:
                    passwords.append({
                        'name': name,
                        'username': username,
                        'password': password,
                        'url': url
                    })
        elif file_type == "json":
            data = json.loads(file_content)
            # Handle different JSON formats
            if isinstance(data, list):
                for item in data:
                    passwords.append({
                        'name': item.get('name', ''),
                        'username': item.get('username', ''),
                        'password': item.get('password', ''),
                        'url': item.get('url', '')
                    })
            elif isinstance(data, dict) and 'items' in data:
                for item in data['items']:
                    login = item.get('login', {})
                    passwords.append({
                        'name': item.get('name', ''),
                        'username': login.get('username', ''),
                        'password': login.get('password', ''),
                        'url': login.get('uris', [{}])[0].get('uri', '') if login.get('uris') else ''
                    })
    except Exception as e:
        st.error(f"Error parsing file: {str(e)}")
    
    return passwords

# Main page content
st.title("🔐 Password Manager Integration")
st.markdown("Analyze and audit your password security")

tab1, tab2, tab3, tab4 = st.tabs(["Password Analyzer", "Vault Audit", "Security Alerts", "Health History"])

with tab1:
    st.subheader("Password Strength Analyzer")
    
    password_input = st.text_input("Enter a password to analyze", type="password")
    
    if password_input:
        score, feedback, entropy = analyze_password_strength(password_input)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Strength Score", f"{score}/100")
        with col2:
            st.metric("Entropy", f"{entropy:.1f} bits")
        with col3:
            if score >= 80:
                st.success("Strong Password")
            elif score >= 50:
                st.warning("Moderate Password")
            else:
                st.error("Weak Password")
        
        if feedback:
            st.markdown("**Suggestions:**")
            for f in feedback:
                st.markdown(f"- {f}")
        
        # Check for breaches
        if st.button("Check for Data Breaches"):
            with st.spinner("Checking..."):
                is_breached, count = check_password_breach(password_input)
                if is_breached is None:
                    st.warning("Could not check breach status")
                elif is_breached:
                    st.error(f"⚠️ This password has been found in {count:,} data breaches!")
                else:
                    st.success("✅ This password has not been found in known data breaches")

with tab2:
    st.subheader("Vault Audit")
    st.markdown("Upload your password export to analyze your vault security")
    
    uploaded_file = st.file_uploader("Upload password export (CSV or JSON)", type=['csv', 'json'])
    
    if uploaded_file:
        file_content = uploaded_file.read().decode('utf-8')
        file_type = uploaded_file.name.split('.')[-1].lower()
        
        passwords = parse_password_export(file_content, file_type)
        
        if passwords:
            st.success(f"Found {len(passwords)} passwords")
            
            if st.button("Run Security Audit"):
                with st.spinner("Analyzing passwords..."):
                    weak_passwords = []
                    reused_passwords = []
                    password_hashes = Counter()
                    
                    for p in passwords:
                        score, _, _ = analyze_password_strength(p['password'])
                        if score < 50:
                            weak_passwords.append(p['name'])
                        password_hashes[hashlib.sha256(p['password'].encode()).hexdigest()] += 1
                    
                    for hash_val, count in password_hashes.items():
                        if count > 1:
                            reused_passwords.extend([p['name'] for p in passwords 
                                if hashlib.sha256(p['password'].encode()).hexdigest() == hash_val])
                    
                    # Calculate security score
                    total = len(passwords)
                    weak_pct = len(weak_passwords) / total if total > 0 else 0
                    reused_pct = len(reused_passwords) / total if total > 0 else 0
                    security_score = max(0, 100 - (weak_pct * 50) - (reused_pct * 30))
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Passwords", total)
                    with col2:
                        st.metric("Weak Passwords", len(weak_passwords))
                    with col3:
                        st.metric("Reused Passwords", len(set(reused_passwords)))
                    with col4:
                        st.metric("Security Score", f"{security_score:.0f}/100")
                    
                    if weak_passwords:
                        with st.expander("Weak Passwords"):
                            for name in weak_passwords[:20]:
                                st.markdown(f"- {name}")
                    
                    if reused_passwords:
                        with st.expander("Reused Passwords"):
                            for name in set(reused_passwords)[:20]:
                                st.markdown(f"- {name}")

with tab3:
    st.subheader("Security Alerts")
    
    user_id = st.session_state.get('user_id', 1)
    conn = get_conn()
    c = conn.cursor()
    
    if USE_POSTGRES:
        c.execute("""
            SELECT id, alert_type, severity, title, description, affected_item, is_resolved, created_at
            FROM security_alerts WHERE user_id = %s ORDER BY created_at DESC LIMIT 50
        """, (user_id,))
    else:
        c.execute("""
            SELECT id, alert_type, severity, title, description, affected_item, is_resolved, created_at
            FROM security_alerts WHERE user_id = ? ORDER BY created_at DESC LIMIT 50
        """, (user_id,))
    
    alerts = c.fetchall()
    conn.close()
    
    if alerts:
        for alert in alerts:
            alert_id, alert_type, severity, title, description, affected_item, is_resolved, created_at = alert
            
            if severity == 'high':
                st.error(f"🔴 **{title}**")
            elif severity == 'medium':
                st.warning(f"🟡 **{title}**")
            else:
                st.info(f"🔵 **{title}**")
            
            st.markdown(f"{description}")
            if affected_item:
                st.markdown(f"*Affected: {affected_item}*")
    else:
        st.info("No security alerts at this time")

with tab4:
    st.subheader("Password Health History")
    
    user_id = st.session_state.get('user_id', 1)
    conn = get_conn()
    c = conn.cursor()
    
    if USE_POSTGRES:
        c.execute("""
            SELECT record_date, security_score, total_passwords, weak_count, reused_count
            FROM password_health_history WHERE user_id = %s ORDER BY record_date DESC LIMIT 30
        """, (user_id,))
    else:
        c.execute("""
            SELECT record_date, security_score, total_passwords, weak_count, reused_count
            FROM password_health_history WHERE user_id = ? ORDER BY record_date DESC LIMIT 30
        """, (user_id,))
    
    history = c.fetchall()
    conn.close()
    
    if history:
        import pandas as pd
        df = pd.DataFrame(history, columns=['Date', 'Security Score', 'Total', 'Weak', 'Reused'])
        st.line_chart(df.set_index('Date')['Security Score'])
    else:
        st.info("No health history data yet. Run a vault audit to start tracking.")