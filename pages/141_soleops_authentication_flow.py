import streamlit as st
import hashlib
import secrets
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Tuple
import re

st.set_page_config(page_title="SoleOps Authentication", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False

SUBSCRIPTION_TIERS = {
    "free": {"name": "Free", "price": 0, "features": ["Basic inventory tracking", "Up to 50 items", "Manual price lookup"]},
    "starter": {"name": "Starter", "price": 9.99, "price_id": "price_starter_monthly", "features": ["Up to 200 items", "Price alerts", "Basic analytics", "Email support"]},
    "pro": {"name": "Pro", "price": 24.99, "price_id": "price_pro_monthly", "features": ["Unlimited items", "AI pricing recommendations", "Arbitrage scanner", "Priority support", "API access"]},
    "pro_plus": {"name": "Pro+", "price": 49.99, "price_id": "price_pro_plus_monthly", "features": ["Everything in Pro", "White-glove onboarding", "Custom integrations", "Dedicated account manager", "Early feature access"]}
}

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
                subscription_tier VARCHAR(50) DEFAULT 'free',
                stripe_customer_id VARCHAR(255),
                stripe_subscription_id VARCHAR(255),
                last_login TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE,
                email_verified BOOLEAN DEFAULT FALSE,
                verification_token VARCHAR(255)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
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
                subscription_status TEXT DEFAULT 'inactive',
                subscription_tier TEXT DEFAULT 'free',
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                last_login TIMESTAMP,
                is_admin INTEGER DEFAULT 0,
                email_verified INTEGER DEFAULT 0,
                verification_token TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                session_token TEXT UNIQUE NOT NULL,
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
                event_type TEXT NOT NULL,
                stripe_event_id TEXT,
                event_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    if BCRYPT_AVAILABLE:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    else:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    if BCRYPT_AVAILABLE:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    else:
        return hashlib.sha256(password.encode('utf-8')).hexdigest() == password_hash

def render_page_links():
    st.page_link("pages/71_soleops_arb_scanner.py", label="🔍 Arbitrage Scanner", icon="🔍")

_ensure_tables()

st.title("🍑 SoleOps Authentication")
st.write("Authentication and subscription management for SoleOps.")