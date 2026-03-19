import streamlit as st
import json
import base64
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import requests
import io

st.set_page_config(page_title="Life Experience & Travel Model", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS trips (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                destination TEXT NOT NULL,
                country TEXT,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                budget DECIMAL(12,2),
                actual_spent DECIMAL(12,2) DEFAULT 0,
                trip_type TEXT DEFAULT 'leisure',
                status TEXT DEFAULT 'planned',
                notes TEXT,
                rating INTEGER,
                highlights TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS flights (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                trip_id INTEGER REFERENCES trips(id) ON DELETE SET NULL,
                airline TEXT NOT NULL,
                flight_number TEXT,
                departure_airport TEXT NOT NULL,
                arrival_airport TEXT NOT NULL,
                departure_datetime TIMESTAMP NOT NULL,
                arrival_datetime TIMESTAMP NOT NULL,
                booking_reference TEXT,
                seat_class TEXT DEFAULT 'economy',
                seat_number TEXT,
                price DECIMAL(10,2),
                currency TEXT DEFAULT 'USD',
                booking_source TEXT,
                status TEXT DEFAULT 'booked',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hotels (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                trip_id INTEGER REFERENCES trips(id) ON DELETE SET NULL,
                hotel_name TEXT NOT NULL,
                address TEXT,
                city TEXT NOT NULL,
                country TEXT,
                check_in_date DATE NOT NULL,
                check_out_date DATE NOT NULL,
                room_type TEXT,
                confirmation_number TEXT,
                price_per_night DECIMAL(10,2),
                total_price DECIMAL(10,2),
                currency TEXT DEFAULT 'USD',
                booking_source TEXT,
                rating INTEGER,
                review TEXT,
                amenities TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                trip_id INTEGER REFERENCES trips(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                description TEXT,
                memory_date DATE NOT NULL,
                location TEXT,
                mood TEXT,
                photo_data TEXT,
                photo_filename TEXT,
                tags TEXT,
                is_favorite BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ubers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                trip_id INTEGER REFERENCES trips(id) ON DELETE SET NULL,
                service_type TEXT DEFAULT 'uber',
                ride_date TIMESTAMP NOT NULL,
                pickup_location TEXT NOT NULL,
                dropoff_location TEXT NOT NULL,
                distance_miles DECIMAL(6,2),
                duration_minutes INTEGER,
                fare DECIMAL(10,2) NOT NULL,
                tip DECIMAL(10,2) DEFAULT 0,
                total_cost DECIMAL(10,2),
                currency TEXT DEFAULT 'USD',
                ride_type TEXT DEFAULT 'UberX',
                purpose TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS life_milestones (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                milestone_date DATE NOT NULL,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
    
    cur.close()

_ensure_tables()

def get_travel_recommendations(user_profile: dict, preferences: dict) -> str:
    """Generate personalized travel recommendations using AI."""
    prompt = f"""You are a personalized travel advisor. Based on the following user profile and preferences, 
provide tailored travel recommendations.

User Profile:
- Past trips: {user_profile.get('past_trips', [])}
- Favorite destinations: {user_profile.get('favorites', [])}
- Travel style: {preferences.get('travel_style', 'balanced')}
- Budget range: {preferences.get('budget_range', 'moderate')}
- Interests: {preferences.get('interests', [])}

Please suggest 3 destination recommendations with brief explanations of why they would be a good fit."""
    
    return prompt

# Main app
st.title("🍑 Life Experience & Travel Model")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Trips", "Flights", "Hotels", "Memories", "Milestones"])

with tab1:
    st.header("My Trips")
    st.write("Track and plan your travel adventures.")

with tab2:
    st.header("Flights")
    st.write("Manage your flight bookings.")

with tab3:
    st.header("Hotels")
    st.write("Track your hotel reservations.")

with tab4:
    st.header("Memories")
    st.write("Capture and cherish your travel memories.")

with tab5:
    st.header("Life Milestones")
    st.write("Record important life events and achievements.")

render_sidebar_brand()
render_sidebar_user_widget()