import streamlit as st
import hashlib
import secrets
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Tuple
import json

st.set_page_config(page_title="SoleOps - User Registration", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()


def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subscription_status VARCHAR(50) DEFAULT 'inactive',
                stripe_customer_id VARCHAR(255),
                stripe_subscription_id VARCHAR(255),
                email_verified BOOLEAN DEFAULT FALSE,
                verification_token VARCHAR(255),
                subscription_tier VARCHAR(50) DEFAULT 'free',
                trial_ends_at TIMESTAMP,
                last_login_at TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                user_agent TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_subscription_events (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                event_type VARCHAR(100) NOT NULL,
                stripe_event_id VARCHAR(255),
                event_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_password_resets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                subscription_status TEXT DEFAULT 'inactive',
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                email_verified INTEGER DEFAULT 0,
                verification_token TEXT,
                subscription_tier TEXT DEFAULT 'free',
                trial_ends_at TEXT,
                last_login_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                token TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_subscription_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                stripe_event_id TEXT,
                event_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                token TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


_ensure_tables()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${pwd_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, pwd_hash = stored_hash.split('$')
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return new_hash.hex() == pwd_hash
    except Exception:
        return False


def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password: str) -> Tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    return True, "Password is valid"


def register_user(email: str, password: str) -> Tuple[bool, str]:
    if not validate_email(email):
        return False, "Invalid email format"
    
    is_valid, msg = validate_password(password)
    if not is_valid:
        return False, msg
    
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cur.execute("SELECT id FROM soleops_users WHERE email = %s", (email.lower(),))
        else:
            cur.execute("SELECT id FROM soleops_users WHERE email = ?", (email.lower(),))
        
        if cur.fetchone():
            conn.close()
            return False, "Email already registered"
        
        password_hash = hash_password(password)
        verification_token = secrets.token_urlsafe(32)
        
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO soleops_users (email, password_hash, verification_token)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (email.lower(), password_hash, verification_token))
        else:
            cur.execute("""
                INSERT INTO soleops_users (email, password_hash, verification_token)
                VALUES (?, ?, ?)
            """, (email.lower(), password_hash, verification_token))
        
        conn.commit()
        conn.close()
        return True, "Registration successful! Please check your email to verify your account."
    
    except Exception as e:
        conn.close()
        return False, f"Registration failed: {str(e)}"


def main():
    render_sidebar_brand()
    
    st.title("🍑 SoleOps User Registration")
    
    st.markdown("""
    Welcome to SoleOps! Create your account to get started.
    """)
    
    with st.form("registration_form"):
        email = st.text_input("Email Address")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        submitted = st.form_submit_button("Register")
        
        if submitted:
            if password != confirm_password:
                st.error("Passwords do not match")
            else:
                success, message = register_user(email, password)
                if success:
                    st.success(message)
                else:
                    st.error(message)
    
    st.markdown("---")
    st.markdown("Already have an account? [Login here](/soleops_login)")


if __name__ == "__main__":
    main()