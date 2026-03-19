import streamlit as st
import json
import os
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
import io
import hashlib

st.set_page_config(page_title="Health & Wellness AI Hub", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS health_profiles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                name VARCHAR(255),
                age INTEGER,
                height_inches DECIMAL(5,2),
                weight_lbs DECIMAL(6,2),
                body_type VARCHAR(100),
                fitness_level VARCHAR(100),
                preferred_exercises TEXT,
                health_conditions TEXT,
                allergies TEXT,
                blood_type VARCHAR(10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                workout_date DATE NOT NULL,
                workout_type VARCHAR(100),
                exercise_name VARCHAR(255),
                sets INTEGER,
                reps INTEGER,
                weight_lbs DECIMAL(6,2),
                duration_minutes INTEGER,
                calories_burned INTEGER,
                heart_rate_avg INTEGER,
                heart_rate_max INTEGER,
                notes TEXT,
                source VARCHAR(50) DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS medications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                medication_name VARCHAR(255) NOT NULL,
                dosage VARCHAR(100),
                frequency VARCHAR(100),
                time_of_day VARCHAR(255),
                prescribing_doctor VARCHAR(255),
                pharmacy VARCHAR(255),
                refill_date DATE,
                pills_remaining INTEGER,
                purpose VARCHAR(255),
                side_effects TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS medication_logs (
                id SERIAL PRIMARY KEY,
                medication_id INTEGER REFERENCES medications(id) ON DELETE CASCADE,
                taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'taken',
                notes TEXT
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mood_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                log_date DATE NOT NULL,
                log_time TIME DEFAULT CURRENT_TIME,
                mood_score INTEGER CHECK (mood_score >= 1 AND mood_score <= 10),
                energy_level INTEGER CHECK (energy_level >= 1 AND energy_level <= 10),
                anxiety_level INTEGER CHECK (anxiety_level >= 1 AND anxiety_level <= 10),
                sleep_quality INTEGER CHECK (sleep_quality >= 1 AND sleep_quality <= 10),
                sleep_hours DECIMAL(4,2),
                stress_level INTEGER CHECK (stress_level >= 1 AND stress_level <= 10),
                journal_entry TEXT,
                triggers TEXT,
                coping_strategies TEXT,
                activities TEXT,
                weather VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS health_goals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                goal_type VARCHAR(100),
                goal_name VARCHAR(255) NOT NULL,
                target_value DECIMAL(10,2),
                current_value DECIMAL(10,2) DEFAULT 0,
                unit VARCHAR(50),
                start_date DATE,
                target_date DATE,
                status VARCHAR(50) DEFAULT 'active',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    cur.close()

# Field mapping for data imports
FIELD_MAPPINGS = {
    'source': ['sourceName', 'source_name', 'source'],
    'date': ['date', 'log_date', 'workout_date', 'created_at'],
    'value': ['value', 'amount', 'quantity']
}

_ensure_tables()

# Main app
st.title("🍑 Health & Wellness AI Hub")
st.write("Track your workouts, medications, mood, and health goals all in one place.")

# Sidebar
with st.sidebar:
    render_sidebar_brand()
    render_sidebar_user_widget()
    
    st.header("Navigation")
    section = st.radio("Go to:", [
        "Dashboard",
        "Workouts",
        "Medications",
        "Mood Tracker",
        "Health Goals",
        "Health Profile"
    ])

if section == "Dashboard":
    st.header("📊 Dashboard")
    st.info("Welcome to your Health & Wellness Dashboard. Select a section from the sidebar to get started.")
    
elif section == "Workouts":
    st.header("🏋️ Workouts")
    st.info("Track your workouts and exercise routines here.")
    
elif section == "Medications":
    st.header("💊 Medications")
    st.info("Manage your medications and track your doses here.")
    
elif section == "Mood Tracker":
    st.header("😊 Mood Tracker")
    st.info("Log your daily mood, energy, and sleep patterns here.")
    
elif section == "Health Goals":
    st.header("🎯 Health Goals")
    st.info("Set and track your health and fitness goals here.")
    
elif section == "Health Profile":
    st.header("👤 Health Profile")
    st.info("Manage your health profile information here.")