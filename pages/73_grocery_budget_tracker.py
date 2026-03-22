import streamlit as st
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
import anthropic

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Grocery Budget Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

def _ph(count=1):
    if USE_POSTGRES:
        return ", ".join(["%s"] * count)
    return ", ".join(["?"] * count)

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS grocery_budgets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                weekly_budget DECIMAL(10,2) NOT NULL DEFAULT 150.00,
                month_year VARCHAR(7) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, month_year)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS grocery_trips (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                store_name VARCHAR(100) NOT NULL,
                trip_date DATE NOT NULL,
                total_amount DECIMAL(10,2) NOT NULL,
                receipt_image TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS grocery_items (
                id SERIAL PRIMARY KEY,
                trip_id INTEGER REFERENCES grocery_trips(id) ON DELETE CASCADE,
                item_name VARCHAR(200) NOT NULL,
                category VARCHAR(50) NOT NULL,
                quantity DECIMAL(10,2) DEFAULT 1,
                unit VARCHAR(20) DEFAULT 'each',
                price DECIMAL(10,2) NOT NULL,
                is_on_sale BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS shopping_lists (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                list_name VARCHAR(100) NOT NULL,
                items JSONB DEFAULT '[]',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS grocery_preferences (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                dietary_restrictions TEXT,
                household_size INTEGER DEFAULT 1,
                preferred_stores TEXT,
                meal_preferences TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS grocery_budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                weekly_budget REAL NOT NULL DEFAULT 150.00,
                month_year TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, month_year)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS grocery_trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                store_name TEXT NOT NULL,
                trip_date TEXT NOT NULL,
                total_amount REAL NOT NULL,
                receipt_image TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS grocery_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER REFERENCES grocery_trips(id) ON DELETE CASCADE,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                quantity REAL DEFAULT 1,
                unit TEXT DEFAULT 'each',
                price REAL NOT NULL,
                is_on_sale INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS shopping_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                list_name TEXT NOT NULL,
                items TEXT DEFAULT '[]',
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS grocery_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                dietary_restrictions TEXT,
                household_size INTEGER DEFAULT 1,
                preferred_stores TEXT,
                meal_preferences TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

GROCERY_CATEGORIES = [
    "Produce", "Meat & Seafood", "Dairy & Eggs", "Bakery",
    "Frozen", "Pantry", "Beverages", "Snacks", "Household",
    "Personal Care", "Baby", "Pet", "Other"
]

COMMON_STORES = [
    "Kroger", "Publix", "Walmart", "Costco", "Trader Joe's",
    "Whole Foods", "Aldi", "Target", "Sprouts", "Other"
]

def get_user_id():
    return st.session_state.get("user_id", 1)

def get_current_week_range():
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end

def get_weekly_budget(user_id, month_year=None):
    if month_year is None:
        month_year = date.today().strftime("%Y-%m")
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"SELECT weekly_budget FROM grocery_budgets WHERE user_id = {_ph()} AND month_year = {_ph()}",
        (user_id, month_year)
    )
    row = cur.fetchone()
    conn.close()
    
    if row:
        return float(row[0])
    return 150.00

def set_weekly_budget(user_id, budget, month_year=None):
    if month_year is None:
        month_year = date.today().strftime("%Y-%m")
    
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO grocery_budgets (user_id, weekly_budget, month_year)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, month_year) DO UPDATE SET weekly_budget = %s, updated_at = CURRENT_TIMESTAMP
        """, (user_id, budget, month_year, budget))
    else:
        cur.execute("""
            INSERT INTO grocery_budgets (user_id, weekly_budget, month_year)
            VALUES (?, ?, ?)
            ON CONFLICT (user_id, month_year) DO UPDATE SET weekly_budget = ?, updated_at = CURRENT_TIMESTAMP
        """, (user_id, budget, month_year, budget))
    
    conn.commit()
    conn.close()

def add_grocery_trip(user_id, store_name, trip_date, total_amount, notes=None, receipt_image=None):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO grocery_trips (user_id, store_name, trip_date, total_amount, notes, receipt_image)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (user_id, store_name, trip_date, total_amount, notes, receipt_image))
        trip_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO grocery_trips (user_id, store_name, trip_date, total_amount, notes, receipt_image)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, store_name, str(trip_date), total_amount, notes, receipt_image))
        trip_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return trip_id

def add_grocery_item(trip_id, item_name, category, quantity, unit, price, is_on_sale=False):
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        INSERT INTO grocery_items (trip_id, item_name, category, quantity, unit, price, is_on_sale)
        VALUES ({_ph(7)})
    """, (trip_id, item_name, category, quantity, unit, price, is_on_sale if USE_POSTGRES else int(is_on_sale)))
    
    conn.commit()
    conn.close()

def get_trips_for_period(user_id, start_date, end_date):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            SELECT id, store_name, trip_date, total_amount, notes, created_at
            FROM grocery_trips
            WHERE user_id = %s AND trip_date >= %s AND trip_date <= %s
            ORDER BY trip_date DESC
        """, (user_id, start_date, end_date))
    else:
        cur.execute("""
            SELECT id, store_name, trip_date, total_amount, notes, created_at
            FROM grocery_trips
            WHERE user_id = ? AND trip_date >= ? AND trip_date <= ?
            ORDER BY trip_date DESC
        """, (user_id, str(start_date), str(end_date)))
    
    rows = cur.fetchall()
    conn.close()
    return rows

def get_items_for_trip(trip_id):
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT id, item_name, category, quantity, unit, price, is_on_sale
        FROM grocery_items
        WHERE trip_id = {_ph()}
        ORDER BY category, item_name
    """, (trip_id,))
    
    rows = cur.fetchall()
    conn.close()
    return rows

def get_spending_by_category(user_id, start_date, end_date):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            SELECT gi.category, SUM(gi.price * gi.quantity) as total
            FROM grocery_items gi
            JOIN grocery_trips gt ON gi.trip_id = gt.id
            WHERE gt.user_id = %s AND gt.trip_date >= %s AND gt.trip_date <= %s
            GROUP BY gi.category
            ORDER BY total DESC
        """, (user_id, start_date, end_date))
    else:
        cur.execute("""
            SELECT gi.category, SUM(gi.price * gi.quantity) as total
            FROM grocery_items gi
            JOIN grocery_trips gt ON gi.trip_id = gt.id
            WHERE gt.user_id = ? AND gt.trip_date >= ? AND gt.trip_date <= ?
            GROUP BY gi.category
            ORDER BY total DESC
        """, (user_id, str(start_date), str(end_date)))
    
    rows = cur.fetchall()
    conn.close()
    return rows

def get_frequently_bought_items(user_id, limit=20):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            SELECT gi.item_name, gi.category, COUNT(*) as buy_count, AVG(gi.price) as avg_price
            FROM grocery_items gi
            JOIN grocery_trips gt ON gi.trip_id = gt.id
            WHERE gt.user_id = %s
            GROUP BY gi.item_name, gi.category
            ORDER BY buy_count DESC
            LIMIT %s
        """, (user_id, limit))
    else:
        cur.execute("""
            SELECT gi.item_name, gi.category, COUNT(*) as buy_count, AVG(gi.price) as avg_price
            FROM grocery_items gi
            JOIN grocery_trips gt ON gi.trip_id = gt.id
            WHERE gt.user_id = ?
            GROUP BY gi.item_name, gi.category
            ORDER BY buy_count DESC
            LIMIT ?
        """, (user_id, limit))
    
    rows = cur.fetchall()
    conn.close()
    return rows

def get_weekly_spending_trend(user_id, weeks=8):
    conn = get_conn()
    cur = conn.cursor()
    
    today = date.today()
    results = []
    
    for i in range(weeks):
        week_end = today - timedelta(days=today.weekday()) - timedelta(weeks=i-1) + timedelta(days=6)
        week_start = week_end - timedelta(days=6)
        
        if USE_POSTGRES:
            cur.execute("""
                SELECT COALESCE(SUM(total_amount), 0)
                FROM grocery_trips
                WHERE user_id = %s AND trip_date >= %s AND trip_date <= %s
            """, (user_id, week_start, week_end))
        else:
            cur.execute("""
                SELECT COALESCE(SUM(total_amount), 0)
                FROM grocery_trips
                WHERE user_id = ? AND trip_date >= ? AND trip_date <= ?
            """, (user_id, str(week_start), str(week_end)))
        
        total = cur.fetchone()[0]
        results.append({
            "week_start": week_start,
            "week_end": week_end,
            "total": float(total) if total else 0
        })
    
    conn.close()
    return list(reversed(results))

def create_shopping_list(user_id, list_name, items=None):
    if items is None:
        items = []
    
    conn = get_conn()
    cur = conn.cursor()
    
    items_json = json.dumps(items)
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO shopping_lists (user_id, list_name, items)
            VALUES (%s, %s, %s) RETURNING id
        """, (user_id, list_name, items_json))
        list_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO shopping_lists (user_id, list_name, items)
            VALUES (?, ?, ?)
        """, (user_id, list_name, items_json))
        list_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return list_id

def get_shopping_lists(user_id, active_only=True):
    conn = get_conn()
    cur = conn.cursor()
    
    if active_only:
        if USE_POSTGRES:
            cur.execute("""
                SELECT id, list_name, items, is_active, created_at, updated_at
                FROM shopping_lists
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY updated_at DESC
            """, (user_id,))
        else:
            cur.execute("""
                SELECT id, list_name, items, is_active, created_at, updated_at
                FROM shopping_lists
                WHERE user_id = ? AND is_active = 1
                ORDER BY updated_at DESC
            """, (user_id,))
    else:
        cur.execute(f"""
            SELECT id, list_name, items, is_active, created_at, updated_at
            FROM shopping_lists
            WHERE user_id = {_ph()}
            ORDER BY updated_at DESC
        """, (user_id,))
    
    rows = cur.fetchall()
    conn.close()
    return rows

def update_shopping_list(list_id, items):
    conn = get_conn()
    cur = conn.cursor()
    
    items_json = json.dumps(items)
    
    cur.execute(f"""
        UPDATE shopping_lists
        SET items = {_ph()}, updated_at = CURRENT_TIMESTAMP
        WHERE id = {_ph()}
    """, (items_json, list_id))
    
    conn.commit()
    conn.close()

def delete_shopping_list(list_id):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("UPDATE shopping_lists SET is_active = FALSE WHERE id = %s", (list_id,))
    else:
        cur.execute("UPDATE shopping_lists SET is_active = 0 WHERE id = ?", (list_id,))
    
    conn.commit()
    conn.close()

def delete_trip(trip_id):
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"DELETE FROM grocery_items WHERE trip_id = {_ph()}", (trip_id,))
    cur.execute(f"DELETE FROM grocery_trips WHERE id = {_ph()}", (trip_id,))
    
    conn.commit()
    conn.close()

def get_preferences(user_id):
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT dietary_restrictions, household_size, preferred_stores, meal_preferences
        FROM grocery_preferences
        WHERE user_id = {_ph()}
    """, (user_id,))
    
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "dietary_restrictions": row[0] or "",
            "household_size": row[1] or 1,
            "preferred_stores": row[2] or "",
            "meal_preferences": row[3] or ""
        }
    return None

def save_preferences(user_id, dietary_restrictions, household_size, preferred_stores, meal_preferences):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO grocery_preferences (user_id, dietary_restrictions, household_size, preferred_stores, meal_preferences)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                dietary_restrictions = %s,
                household_size = %s,
                preferred_stores = %s,
                meal_preferences = %s,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, dietary_restrictions, household_size, preferred_stores, meal_preferences,
              dietary_restrictions, household_size, preferred_stores, meal_preferences))
    else:
        cur.execute("""
            INSERT INTO grocery_preferences (user_id, dietary_restrictions, household_size, preferred_stores, meal_preferences)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (user_id) DO UPDATE SET
                dietary_restrictions = ?,
                household_size = ?,
                preferred_stores = ?,
                meal_preferences = ?,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, dietary_restrictions, household_size, preferred_stores, meal_preferences,
              dietary_restrictions, household_size, preferred_stores, meal_preferences))
    
    conn.commit()
    conn.close()

def get_claude_meal_suggestions(budget, preferences, frequently_bought):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "Please configure your Anthropic API key in settings to get AI meal suggestions."
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        pref_text = ""
        if preferences:
            pref_text = f"""
Household size: {preferences.get('household_size', 1)}
Dietary restrictions: {preferences.get('dietary_restrictions', 'None')}
Meal preferences: {preferences.get('meal_preferences', 'No specific preferences')}
"""
        
        freq_items = ", ".join([item[0] for item in frequently_bought[:10]]) if frequently_bought else "No purchase history yet"
        
        prompt = f"""You are a helpful meal planning assistant. Based on the following information, suggest a week of meals that fit within the grocery budget.

Weekly grocery budget: ${budget:.2f}
{pref_text}
Frequently purchased items: {freq_items}

Please provide:
1. A 7-day meal plan (breakfast, lunch, dinner) that fits the budget
2. A consolidated shopping list with estimated costs
3. Tips to save money on groceries
4. One batch cooking suggestion to save time

Keep suggestions practical and budget-conscious. Format your response clearly with sections."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text
    except Exception as e:
        return f"Error getting AI suggestions: {str(e)}"

def get_smart_shopping_suggestions(user_id, budget):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return None
    
    frequently_bought = get_frequently_bought_items(user_id, 15)
    preferences = get_preferences(user_id)
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        items_list = "\n".join([f"- {item[0]} (bought {item[2]}x, avg ${item[3]:.2f})" for item in frequently_bought]) if frequently_bought else "No purchase history"
        
        pref_text = ""
        if preferences:
            pref_text = f"Household: {preferences.get('household_size', 1)} people, Dietary: {preferences.get('dietary_restrictions', 'None')}"
        
        prompt = f"""Based on this shopper's history, suggest a smart shopping list for their next trip.

Budget: ${budget:.2f}
{pref_text}

Frequently bought items:
{items_list}

Generate a JSON array of suggested items with this format:
[{{"item": "item name", "category": "category", "estimated_price": 0.00, "quantity": 1}}]

Include their regular items plus any complementary items. Stay within budget. Return ONLY the JSON array, no other text."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        return json.loads(response_text)
    except:
        return None

# Main UI
st.title("🛒 Grocery Budget Tracker")
st.markdown("Track weekly grocery spending, build smart shopping lists, and get AI meal planning suggestions.")

user_id = get_user_id()
week_start, week_end = get_current_week_range()

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🛍️ Log Trip", "📝 Shopping Lists", "🤖 Meal Planner", "⚙️ Settings"])

with tab1:
    st.subheader("Weekly Budget Overview")
    
    col1, col2, col3 = st.columns(3)
    
    weekly_budget = get_weekly_budget(user_id)
    trips = get_trips_for_period(user_id, week_start, week_end)
    weekly_spent = sum([float(t[3]) for t in trips])
    remaining = weekly_budget - weekly_spent
    
    with col1:
        st.metric("Weekly Budget", f"${weekly_budget:.2f}")
    
    with col2:
        st.metric("Spent This Week", f"${weekly_spent:.2f}", 
                  delta=f"-${weekly_spent:.2f}" if weekly_spent > 0 else None,
                  delta_color="inverse")
    
    with col3:
        color = "normal" if remaining >= 0 else "inverse"
        st.metric("Remaining", f"${remaining:.2f}", 
                  delta="On Track" if remaining >= 0 else "Over Budget",
                  delta_color=color)
    
    # Progress bar
    progress = min(weekly_spent / weekly_budget, 1.0) if weekly_budget > 0 else 0
    st.progress(progress)
    st.caption(f"Week of {week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}")
    
    # Budget adjustment
    with st.expander("📝 Adjust Weekly Budget"):
        new_budget = st.number_input("Weekly Budget ($)", min_value=0.0, value=weekly_budget, step=10.0)
        if st.button("Update Budget"):
            set_weekly_budget(user_id, new_budget)
            st.success("Budget updated!")
            st.rerun()
    
    st.markdown("---")
    
    # Weekly trend chart
    st.subheader("📈 Spending Trends (Last 8 Weeks)")
    
    trend_data = get_weekly_spending_trend(user_id, 8)
    
    if trend_data and any(w["total"] > 0 for w in trend_data):
        import pandas as pd
        
        df = pd.DataFrame(trend_data)
        df["week_label"] = df["week_start"].apply(lambda x: x.strftime("%b %d"))
        df["budget"] = weekly_budget
        
        chart_data = df[["week_label", "total", "budget"]].set_index("week_label")
        st.bar_chart(chart_data["total"])
        st.caption(f"Weekly budget target: ${weekly_budget:.2f}")
    else:
        st.info("No spending data yet. Log your first grocery trip to see trends!")
    
    st.markdown("---")
    
    # Category breakdown
    st.subheader("📊 Spending by Category (This Month)")
    
    month_start = date.today().replace(day=1)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    category_data = get_spending_by_category(user_id, month_start, month_end)
    
    if category_data:
        import pandas as pd
        
        df = pd.DataFrame(category_data, columns=["Category", "Amount"])
        df["Amount"] = df["Amount"].astype(float)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.bar_chart(df.set_index("Category"))
        
        with col2:
            st.dataframe(df.style.format({"Amount": "${:.2f}"}), hide_index=True)
    else:
        st.info("No category data for this month yet.")
    
    st.markdown("---")
    
    # Recent trips
    st.subheader("🧾 Recent Trips")
    
    recent_trips = get_trips_for_period(user_id, date.today() - timedelta(days=30), date.today())
    
    if recent_trips:
        for trip in recent_trips[:5]:
            trip_id, store, trip_date, amount, notes, created = trip
            trip_date_obj = trip_date if isinstance(trip_date, date) else datetime.strptime(str(trip_date), "%Y-%m-%d").date()
            
            with st.expander(f"🏪 {store} - ${float(amount):.2f} ({trip_date_obj.strftime('%b %d')})"):
                items = get_items_for_trip(trip_id)
                
                if items:
                    for item in items:
                        item_id, name, cat, qty, unit, price, on_sale = item
                        sale_badge = " 🏷️ SALE" if on_sale else ""
                        st.write(f"• {name} ({cat}) - {qty} {unit} @ ${float(price):.2f}{sale_badge}")
                
                if notes:
                    st.caption(f"Notes: {notes}")
                
                if st.button("🗑️ Delete Trip", key=f"del_trip_{trip_id}"):
                    delete_trip(trip_id)
                    st.success("Trip deleted!")
                    st.rerun()
    else:
        st.info("No recent trips. Log your first grocery trip!")

with tab2:
    st.subheader("🛍️ Log Grocery Trip")
    
    with st.form("trip_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            store = st.selectbox("Store", COMMON_STORES)
            if store == "Other":
                store = st.text_input("Store Name")
        
        with col2:
            trip_date = st.date_input("Date", value=date.today())
        
        total_amount = st.number_input("Total Amount ($)", min_value=0.0, step=1.0)
        notes = st.text_area("Notes (optional)", placeholder="Any notes about this trip...")
        
        st.markdown("---")
        st.markdown("**Add Items (optional)**")
        
        num_items = st.number_input("Number of items to add", min_value=0, max_value=20, value=0)
        
        items_to_add = []
        for i in range(int(num_items)):
            st.markdown(f"**Item {i+1}**")
            col1, col2, col3 = st.columns(3)