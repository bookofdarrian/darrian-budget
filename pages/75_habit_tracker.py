import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import json
import calendar

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Habit Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

def _get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                name VARCHAR(255) NOT NULL,
                icon VARCHAR(50) DEFAULT '✅',
                category VARCHAR(100) DEFAULT 'general',
                target_frequency INTEGER DEFAULT 1,
                description TEXT,
                reminder_time TIME,
                reminder_enabled BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS habit_logs (
                id SERIAL PRIMARY KEY,
                habit_id INTEGER REFERENCES habits(id) ON DELETE CASCADE,
                logged_date DATE NOT NULL,
                completed BOOLEAN DEFAULT TRUE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(habit_id, logged_date)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS habit_streaks (
                id SERIAL PRIMARY KEY,
                habit_id INTEGER REFERENCES habits(id) ON DELETE CASCADE UNIQUE,
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_logged DATE,
                total_completions INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS habit_milestones (
                id SERIAL PRIMARY KEY,
                habit_id INTEGER REFERENCES habits(id) ON DELETE CASCADE,
                milestone_type VARCHAR(50) NOT NULL,
                milestone_value INTEGER NOT NULL,
                achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                celebrated BOOLEAN DEFAULT FALSE,
                UNIQUE(habit_id, milestone_type, milestone_value)
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                name TEXT NOT NULL,
                icon TEXT DEFAULT '✅',
                category TEXT DEFAULT 'general',
                target_frequency INTEGER DEFAULT 1,
                description TEXT,
                reminder_time TEXT,
                reminder_enabled INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS habit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER REFERENCES habits(id) ON DELETE CASCADE,
                logged_date TEXT NOT NULL,
                completed INTEGER DEFAULT 1,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(habit_id, logged_date)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS habit_streaks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER REFERENCES habits(id) ON DELETE CASCADE UNIQUE,
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_logged TEXT,
                total_completions INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS habit_milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER REFERENCES habits(id) ON DELETE CASCADE,
                milestone_type TEXT NOT NULL,
                milestone_value INTEGER NOT NULL,
                achieved_at TEXT DEFAULT CURRENT_TIMESTAMP,
                celebrated INTEGER DEFAULT 0,
                UNIQUE(habit_id, milestone_type, milestone_value)
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

# Constants
HABIT_CATEGORIES = {
    "fitness": {"icon": "🏋️", "name": "Fitness", "color": "#FF6B6B"},
    "hydration": {"icon": "💧", "name": "Hydration", "color": "#4ECDC4"},
    "sleep": {"icon": "😴", "name": "Sleep", "color": "#9B59B6"},
    "mindfulness": {"icon": "🧘", "name": "Mindfulness", "color": "#F39C12"},
    "finance": {"icon": "💰", "name": "Finance", "color": "#27AE60"},
    "nutrition": {"icon": "🥗", "name": "Nutrition", "color": "#E74C3C"},
    "learning": {"icon": "📚", "name": "Learning", "color": "#3498DB"},
    "social": {"icon": "👥", "name": "Social", "color": "#E91E63"},
    "productivity": {"icon": "⚡", "name": "Productivity", "color": "#FF9800"},
    "general": {"icon": "✅", "name": "General", "color": "#607D8B"}
}

PRESET_HABITS = [
    {"name": "Go to Gym", "icon": "🏋️", "category": "fitness"},
    {"name": "Drink 8 Glasses of Water", "icon": "💧", "category": "hydration"},
    {"name": "Sleep 8 Hours", "icon": "😴", "category": "sleep"},
    {"name": "Meditate 10 Minutes", "icon": "🧘", "category": "mindfulness"},
    {"name": "Journal", "icon": "📝", "category": "mindfulness"},
    {"name": "Track Expenses", "icon": "💰", "category": "finance"},
    {"name": "Read 30 Minutes", "icon": "📚", "category": "learning"},
    {"name": "Take Vitamins", "icon": "💊", "category": "nutrition"},
    {"name": "No Social Media", "icon": "📵", "category": "productivity"},
    {"name": "Walk 10,000 Steps", "icon": "🚶", "category": "fitness"},
    {"name": "Stretch", "icon": "🤸", "category": "fitness"},
    {"name": "Call Family/Friend", "icon": "📞", "category": "social"}
]

MILESTONE_BADGES = {
    7: {"name": "Week Warrior", "icon": "🌟", "description": "7 days strong!"},
    14: {"name": "Fortnight Fighter", "icon": "⭐", "description": "14 days of dedication!"},
    21: {"name": "Habit Former", "icon": "🏅", "description": "21 days - habit is forming!"},
    30: {"name": "Monthly Master", "icon": "🥉", "description": "30 days of consistency!"},
    60: {"name": "Double Down", "icon": "🥈", "description": "60 days unstoppable!"},
    90: {"name": "Quarter Champion", "icon": "🥇", "description": "90 days of excellence!"},
    100: {"name": "Century Club", "icon": "💯", "description": "100 days achieved!"},
    180: {"name": "Half Year Hero", "icon": "🏆", "description": "180 days of commitment!"},
    365: {"name": "Year Legend", "icon": "👑", "description": "365 days - legendary!"}
}

# Database helper functions
def get_all_habits(user_id=1, active_only=True):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    if active_only:
        if USE_POSTGRES:
            cur.execute(f"SELECT * FROM habits WHERE user_id = {ph} AND is_active = TRUE ORDER BY created_at", (user_id,))
        else:
            cur.execute(f"SELECT * FROM habits WHERE user_id = {ph} AND is_active = 1 ORDER BY created_at", (user_id,))
    else:
        cur.execute(f"SELECT * FROM habits WHERE user_id = {ph} ORDER BY created_at", (user_id,))
    
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

def get_habit_by_id(habit_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    cur.execute(f"SELECT * FROM habits WHERE id = {ph}", (habit_id,))
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    conn.close()
    return dict(zip(columns, row)) if row else None

def create_habit(name, icon, category, target_frequency=1, description="", reminder_time=None, reminder_enabled=False, user_id=1):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    cur.execute(f"""
        INSERT INTO habits (user_id, name, icon, category, target_frequency, description, reminder_time, reminder_enabled)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, name, icon, category, target_frequency, description, reminder_time, 1 if reminder_enabled else 0))
    
    if USE_POSTGRES:
        cur.execute("SELECT lastval()")
        habit_id = cur.fetchone()[0]
    else:
        habit_id = cur.lastrowid
    
    # Initialize streak record
    cur.execute(f"""
        INSERT INTO habit_streaks (habit_id, current_streak, longest_streak, total_completions)
        VALUES ({ph}, 0, 0, 0)
    """, (habit_id,))
    
    conn.commit()
    conn.close()
    return habit_id

def update_habit(habit_id, name, icon, category, target_frequency, description, reminder_time, reminder_enabled):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    cur.execute(f"""
        UPDATE habits 
        SET name = {ph}, icon = {ph}, category = {ph}, target_frequency = {ph}, 
            description = {ph}, reminder_time = {ph}, reminder_enabled = {ph}
        WHERE id = {ph}
    """, (name, icon, category, target_frequency, description, reminder_time, 1 if reminder_enabled else 0, habit_id))
    
    conn.commit()
    conn.close()

def delete_habit(habit_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    cur.execute(f"DELETE FROM habits WHERE id = {ph}", (habit_id,))
    conn.commit()
    conn.close()

def archive_habit(habit_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    if USE_POSTGRES:
        cur.execute(f"UPDATE habits SET is_active = FALSE WHERE id = {ph}", (habit_id,))
    else:
        cur.execute(f"UPDATE habits SET is_active = 0 WHERE id = {ph}", (habit_id,))
    conn.commit()
    conn.close()

def log_habit(habit_id, logged_date, completed=True, notes=""):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    date_str = logged_date.isoformat() if isinstance(logged_date, date) else logged_date
    
    if USE_POSTGRES:
        cur.execute(f"""
            INSERT INTO habit_logs (habit_id, logged_date, completed, notes)
            VALUES ({ph}, {ph}, {ph}, {ph})
            ON CONFLICT (habit_id, logged_date) 
            DO UPDATE SET completed = {ph}, notes = {ph}
        """, (habit_id, date_str, completed, notes, completed, notes))
    else:
        cur.execute(f"""
            INSERT OR REPLACE INTO habit_logs (habit_id, logged_date, completed, notes)
            VALUES ({ph}, {ph}, {ph}, {ph})
        """, (habit_id, date_str, 1 if completed else 0, notes))
    
    conn.commit()
    conn.close()
    
    # Update streak
    update_streak(habit_id)

def get_habit_log(habit_id, logged_date):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    date_str = logged_date.isoformat() if isinstance(logged_date, date) else logged_date
    cur.execute(f"SELECT * FROM habit_logs WHERE habit_id = {ph} AND logged_date = {ph}", (habit_id, date_str))
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    conn.close()
    return dict(zip(columns, row)) if row else None

def get_habit_logs(habit_id, start_date=None, end_date=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    query = f"SELECT * FROM habit_logs WHERE habit_id = {ph}"
    params = [habit_id]
    
    if start_date:
        query += f" AND logged_date >= {ph}"
        params.append(start_date.isoformat() if isinstance(start_date, date) else start_date)
    if end_date:
        query += f" AND logged_date <= {ph}"
        params.append(end_date.isoformat() if isinstance(end_date, date) else end_date)
    
    query += " ORDER BY logged_date DESC"
    cur.execute(query, params)
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

def get_streak(habit_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    cur.execute(f"SELECT * FROM habit_streaks WHERE habit_id = {ph}", (habit_id,))
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    conn.close()
    return dict(zip(columns, row)) if row else None

def update_streak(habit_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    # Get all completed logs for this habit, ordered by date descending
    if USE_POSTGRES:
        cur.execute(f"""
            SELECT logged_date FROM habit_logs 
            WHERE habit_id = {ph} AND completed = TRUE 
            ORDER BY logged_date DESC
        """, (habit_id,))
    else:
        cur.execute(f"""
            SELECT logged_date FROM habit_logs 
            WHERE habit_id = {ph} AND completed = 1 
            ORDER BY logged_date DESC
        """, (habit_id,))
    
    rows = cur.fetchall()
    
    if not rows:
        cur.execute(f"""
            UPDATE habit_streaks 
            SET current_streak = 0, updated_at = CURRENT_TIMESTAMP
            WHERE habit_id = {ph}
        """, (habit_id,))
        conn.commit()
        conn.close()
        return
    
    # Calculate current streak
    today = date.today()
    current_streak = 0
    dates = [datetime.strptime(str(row[0])[:10], '%Y-%m-%d').date() if isinstance(row[0], str) else row[0] for row in rows]
    
    # Check if today or yesterday is logged
    check_date = today
    if dates and dates[0] != today:
        check_date = today - timedelta(days=1)
    
    for d in dates:
        if d == check_date:
            current_streak += 1
            check_date -= timedelta(days=1)
        elif d < check_date:
            break
    
    # Get current longest streak
    cur.execute(f"SELECT longest_streak, total_completions FROM habit_streaks WHERE habit_id = {ph}", (habit_id,))
    streak_row = cur.fetchone()
    longest_streak = streak_row[0] if streak_row else 0
    total_completions = len(dates)
    
    # Update longest if current is higher
    if current_streak > longest_streak:
        longest_streak = current_streak
    
    last_logged = dates[0].isoformat() if dates else None
    
    cur.execute(f"""
        UPDATE habit_streaks 
        SET current_streak = {ph}, longest_streak = {ph}, last_logged = {ph}, 
            total_completions = {ph}, updated_at = CURRENT_TIMESTAMP
        WHERE habit_id = {ph}
    """, (current_streak, longest_streak, last_logged, total_completions, habit_id))
    
    # Check for milestone achievements
    check_milestones(habit_id, current_streak, cur, ph)
    
    conn.commit()
    conn.close()

def check_milestones(habit_id, current_streak, cur, ph):
    for streak_count, badge_info in MILESTONE_BADGES.items():
        if current_streak >= streak_count:
            try:
                if USE_POSTGRES:
                    cur.execute(f"""
                        INSERT INTO habit_milestones (habit_id, milestone_type, milestone_value)
                        VALUES ({ph}, 'streak', {ph})
                        ON CONFLICT (habit_id, milestone_type, milestone_value) DO NOTHING
                    """, (habit_id, streak_count))
                else:
                    cur.execute(f"""
                        INSERT OR IGNORE INTO habit_milestones (habit_id, milestone_type, milestone_value)
                        VALUES ({ph}, 'streak', {ph})
                    """, (habit_id, streak_count))
            except:
                pass

def get_uncelebrated_milestones(habit_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    if USE_POSTGRES:
        cur.execute(f"""
            SELECT * FROM habit_milestones 
            WHERE habit_id = {ph} AND celebrated = FALSE
            ORDER BY milestone_value DESC
        """, (habit_id,))
    else:
        cur.execute(f"""
            SELECT * FROM habit_milestones 
            WHERE habit_id = {ph} AND celebrated = 0
            ORDER BY milestone_value DESC
        """, (habit_id,))
    
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

def mark_milestone_celebrated(milestone_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    if USE_POSTGRES:
        cur.execute(f"UPDATE habit_milestones SET celebrated = TRUE WHERE id = {ph}", (milestone_id,))
    else:
        cur.execute(f"UPDATE habit_milestones SET celebrated = 1 WHERE id = {ph}", (milestone_id,))
    
    conn.commit()
    conn.close()

def get_all_milestones(habit_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    cur.execute(f"""
        SELECT * FROM habit_milestones 
        WHERE habit_id = {ph}
        ORDER BY milestone_value ASC
    """, (habit_id,))
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

def calculate_completion_rate(habit_id, days=30):
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    start_date = (date.today() - timedelta(days=days)).isoformat()
    
    if USE_POSTGRES:
        cur.execute(f"""
            SELECT COUNT(*) FROM habit_logs 
            WHERE habit_id = {ph} AND logged_date >= {ph} AND completed = TRUE
        """, (habit_id, start_date))
    else:
        cur.execute(f"""
            SELECT COUNT(*) FROM habit_logs 
            WHERE habit_id = {ph} AND logged_date >= {ph} AND completed = 1
        """, (habit_id, start_date))
    
    completed = cur.fetchone()[0]
    conn.close()
    
    return (completed / days) * 100 if days > 0 else 0

def get_heatmap_data(habit_id, year=None):
    if year is None:
        year = date.today().year
    
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    if USE_POSTGRES:
        cur.execute(f"""
            SELECT logged_date, completed FROM habit_logs 
            WHERE habit_id = {ph} AND logged_date >= {ph} AND logged_date <= {ph}
            ORDER BY logged_date
        """, (habit_id, start_date, end_date))
    else:
        cur.execute(f"""
            SELECT logged_date, completed FROM habit_logs 
            WHERE habit_id = {ph} AND logged_date >= {ph} AND logged_date <= {ph}
            ORDER BY logged_date
        """, (habit_id, start_date, end_date))
    
    rows = cur.fetchall()
    conn.close()
    
    heatmap = {}
    for row in rows:
        date_str = str(row[0])[:10]
        completed = row[1] if isinstance(row[1], bool) else bool(row[1])
        heatmap[date_str] = completed
    
    return heatmap

def get_claude_insights(habits_data, streaks_data, completion_rates):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return None
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        habits_summary = []
        for h in habits_data:
            streak = streaks_data.get(h['id'], {})
            rate = completion_rates.get(h['id'], 0)
            habits_summary.append({
                "name": h['name'],
                "category": h['category'],
                "current_streak": streak.get('current_streak', 0),
                "longest_streak": streak.get('longest_streak', 0),
                "completion_rate_30d": round(rate, 1)
            })
        
        prompt = f"""Analyze these habit tracking patterns and provide personalized insights:

Habits Summary:
{json.dumps(habits_summary, indent=2)}

Please provide:
1. A brief overall assessment of habit consistency
2. Identify which habits are thriving and which need attention
3. Specific, actionable tips to improve struggling habits
4. Motivational insight based on their best performing habit
5. One habit stacking suggestion (pairing habits together)

Keep response concise, friendly, and actionable. Use emojis sparingly."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
    except Exception as e:
        return f"Could not generate insights: {str(e)}"

# UI Components
def render_habit_card(habit, streak_info, today_logged, completion_rate):
    cat_info = HABIT_CATEGORIES.get(habit['category'], HABIT_CATEGORIES['general'])
    
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        
        with col1:
            st.markdown(f"### {habit['icon']} {habit['name']}")
            st.caption(f"{cat_info['icon']} {cat_info['name']}")
        
        with col2:
            current = streak_info.get('current_streak', 0) if streak_info else 0
            longest = streak_info.get('longest_streak', 0) if streak_info else 0
            st.metric("🔥 Current Streak", f"{current} days", f"Best: {longest}")
        
        with col3:
            st.metric("📊 30-Day Rate", f"{completion_rate:.1f}%")
        
        with col4:
            if today_logged:
                st.success("✅ Done!")
            else:
                if st.button("Complete", key=f"complete_{habit['id']}", type="primary"):
                    log_habit(habit['id'], date.today(), True)
                    st.rerun()
        
        st.divider()

def render_calendar_heatmap(habit_id, habit_name):
    today = date.today()
    heatmap_data = get_heatmap_data(habit_id, today.year)
    
    st.subheader(f"📅 {habit_name} - Activity Heatmap")
    
    # Build calendar grid
    months_html = ""
    for month in range(1, 13):
        month_name = calendar.month_abbr[month]
        cal = calendar.monthcalendar(today.year, month)
        
        days_html = ""
        for week in cal:
            for day in week:
                if day == 0:
                    days_html += '<div class="heatmap-day empty"></div>'
                else:
                    day_date = f"{today.year}-{month:02d}-{day:02d}"
                    is_completed = heatmap_data.get(day_date, False)
                    is_future = date(today.year, month, day) > today
                    
                    if is_future:
                        css_class = "heatmap-day future"
                    elif is_completed:
                        css_class = "heatmap-day completed"
                    else:
                        css_class = "heatmap-day missed"
                    
                    days_html += f'<div class="{css_class}" title="{day_date}"></div>'
        
        months_html += f'''
        <div class="heatmap-month">
            <div class="month-label">{month_name}</div>
            <div class="days-grid">{days_html}</div>
        </div>
        '''
    
    st.markdown(f"""
    <style>
    .heatmap-container {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        padding: 10px;
        background: #1a1a2e;
        border-radius: 10px;
    }}
    .heatmap-month {{
        flex: 1;
        min-width: 80px;
    }}
    .month-label {{
        font-size: 12px;
        color: #888;
        margin-bottom: 5px;
        text-align: center;
    }}
    .days-grid {{
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 2px;
    }}
    .heatmap-day {{
        width: 10px;
        height: 10px;
        border-radius: 2px;
    }}
    .heatmap-day.empty {{
        background: transparent;
    }}
    .heatmap-day.completed {{
        background: #4CAF50;
    }}
    .heatmap-day.missed {{
        background: #333;
    }}
    .heatmap-day.future {{
        background: #222;
    }}
    .legend {{
        display: flex;
        gap: 15px;
        margin-top: 10px;
        font-size: 12px;
        color: #888;
    }}
    .legend-item {{
        display: flex;
        align-items: center;
        gap: 5px;
    }}
    .legend-box {{
        width: 12px;
        height: 12px;
        border-radius: 2px;
    }}
    </style>
    <div class="heatmap-container">{months_html}</div>
    <div class="legend">
        <div class="legend-item"><div class="legend-box" style="background:#4CAF50"></div> Completed</div>
        <div class="legend-item"><div class="legend-box" style="background:#333"></div> Missed</div>
        <div class="legend-item"><div class="legend-box" style="background:#222"></div> Future</div>
    </div>
    """, unsafe_allow_html=True)

def render_weekly_chart(habit_id):
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    
    week_data = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        log = get_habit_log(habit_id, day)
        completed = log and (log['completed'] if isinstance(log['completed'], bool) else bool(log['completed']))
        week_data.append({
            "Day": calendar.day_abbr[i],
            "Completed": 1 if completed else 0,
            "Date": day.strftime("%m/%d")
        })
    
    df = pd.DataFrame(week_data)
    st.bar_chart(df.set_index("Day")["Completed"])

def render_milestone_badges(habit_id):
    milestones = get_all_milestones(habit_id)
    streak = get_streak(habit_id)
    current = streak.get