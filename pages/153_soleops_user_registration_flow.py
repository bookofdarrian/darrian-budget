import streamlit as st
import hashlib
import secrets
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
import os

st.set_page_config(page_title="SoleOps Registration", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()

# Constants
SUBSCRIPTION_TIERS = {
    "free": {"name": "Free", "price": 0, "features": ["Basic inventory tracking", "5 listings/month"]},
    "starter": {"name": "Starter", "price": 9.99, "features": ["Unlimited listings", "Price monitor", "Basic analytics"]},
    "pro": {"name": "Pro", "price": 19.99, "features": ["Everything in Starter", "AI listing generator", "Arbitrage scanner", "Priority support"]},
    "pro_plus": {"name": "Pro+", "price": 29.99, "features": ["Everything in Pro", "API access", "White-label reports", "Dedicated support"]}
}

def _ensure_tables():
    """Create SoleOps authentication tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                email_verified BOOLEAN DEFAULT FALSE,
                stripe_customer_id VARCHAR(255),
                subscription_status VARCHAR(50) DEFAULT 'inactive',
                subscription_tier VARCHAR(50) DEFAULT 'free',
                subscription_ends_at TIMESTAMP,
                last_login TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE,
                password_reset_token VARCHAR(255),
                password_reset_expires TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_email_verifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                token VARCHAR(255) NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                verified_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                session_token VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                ip_address VARCHAR(50),
                user_agent TEXT
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_subscription_events (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                event_type VARCHAR(100) NOT NULL,
                stripe_event_id VARCHAR(255),
                event_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                email_verified INTEGER DEFAULT 0,
                stripe_customer_id TEXT,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_tier TEXT DEFAULT 'free',
                subscription_ends_at TIMESTAMP,
                last_login TIMESTAMP,
                is_admin INTEGER DEFAULT 0,
                password_reset_token TEXT,
                password_reset_expires TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_email_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                token TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                verified_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                session_token TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                ip_address TEXT,
                user_agent TEXT
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_subscription_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                event_type VARCHAR(100) NOT NULL,
                stripe_event_id VARCHAR(255),
                event_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()

# Initialize tables
_ensure_tables()

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password strength."""
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
    """Register a new user."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Check if user already exists
        cur.execute("SELECT id FROM soleops_users WHERE email = ?", (email,))
        if cur.fetchone():
            return False, "Email already registered"
        
        # Create user
        password_hash = hash_password(password)
        cur.execute(
            "INSERT INTO soleops_users (email, password_hash) VALUES (?, ?)",
            (email, password_hash)
        )
        conn.commit()
        
        # Get user ID
        cur.execute("SELECT id FROM soleops_users WHERE email = ?", (email,))
        user_row = cur.fetchone()
        if user_row:
            user_id = user_row[0]
            
            # Create verification token
            token = generate_token()
            expires_at = datetime.now() + timedelta(hours=24)
            cur.execute(
                "INSERT INTO soleops_email_verifications (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user_id, token, expires_at)
            )
            conn.commit()
        
        return True, "Registration successful! Please check your email to verify your account."
    except Exception as e:
        return False, f"Registration failed: {str(e)}"

def login_user(email: str, password: str) -> Tuple[bool, str, Optional[dict]]:
    """Authenticate a user."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        password_hash = hash_password(password)
        cur.execute(
            "SELECT id, email, email_verified, subscription_tier, subscription_status FROM soleops_users WHERE email = ? AND password_hash = ?",
            (email, password_hash)
        )
        user = cur.fetchone()
        
        if not user:
            return False, "Invalid email or password", None
        
        user_data = {
            "id": user[0],
            "email": user[1],
            "email_verified": user[2],
            "subscription_tier": user[3],
            "subscription_status": user[4]
        }
        
        # Update last login
        cur.execute("UPDATE soleops_users SET last_login = ? WHERE id = ?", (datetime.now(), user[0]))
        conn.commit()
        
        return True, "Login successful!", user_data
    except Exception as e:
        return False, f"Login failed: {str(e)}", None

# Main UI
st.title("🍑 SoleOps Registration")

tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    st.subheader("Login to your account")
    login_email = st.text_input("Email", key="login_email")
    login_password = st.text_input("Password", type="password", key="login_password")
    
    if st.button("Login"):
        if login_email and login_password:
            success, message, user_data = login_user(login_email, login_password)
            if success:
                st.success(message)
                st.session_state["soleops_user"] = user_data
                st.rerun()
            else:
                st.error(message)
        else:
            st.warning("Please enter both email and password")

with tab2:
    st.subheader("Create a new account")
    reg_email = st.text_input("Email", key="reg_email")
    reg_password = st.text_input("Password", type="password", key="reg_password")
    reg_password_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm")
    
    if st.button("Register"):
        if not reg_email or not reg_password or not reg_password_confirm:
            st.warning("Please fill in all fields")
        elif not validate_email(reg_email):
            st.error("Please enter a valid email address")
        elif reg_password != reg_password_confirm:
            st.error("Passwords do not match")
        else:
            valid, msg = validate_password(reg_password)
            if not valid:
                st.error(msg)
            else:
                success, message = register_user(reg_email, reg_password)
                if success:
                    st.success(message)
                else:
                    st.error(message)

# Show logged in user info
if "soleops_user" in st.session_state:
    st.sidebar.success(f"Logged in as: {st.session_state['soleops_user']['email']}")
    if st.sidebar.button("Logout"):
        del st.session_state["soleops_user"]
        st.rerun()