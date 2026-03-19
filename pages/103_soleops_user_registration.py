import streamlit as st
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import json
import os

st.set_page_config(page_title="SoleOps User Registration", page_icon="🍑", layout="wide")

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


def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                email_verified BOOLEAN DEFAULT FALSE,
                verification_token TEXT,
                verification_expires TIMESTAMP,
                stripe_customer_id TEXT,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_tier TEXT DEFAULT 'free',
                subscription_id TEXT,
                last_login TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                ip_address TEXT,
                user_agent TEXT
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_password_resets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_subscription_events (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES soleops_users(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                event_data TEXT,
                stripe_event_id TEXT,
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
                email_verified BOOLEAN DEFAULT 0,
                verification_token TEXT,
                verification_expires TIMESTAMP,
                stripe_customer_id TEXT,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_tier TEXT DEFAULT 'free',
                subscription_id TEXT,
                last_login TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES soleops_users(id) ON DELETE CASCADE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES soleops_users(id) ON DELETE CASCADE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_subscription_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                event_data TEXT,
                stripe_event_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES soleops_users(id) ON DELETE CASCADE
            )
        """)
    
    conn.commit()


_ensure_tables()

st.markdown("""
# SoleOps User Registration

Welcome to the SoleOps User Registration page.
""")