import streamlit as st
import json
import uuid
from datetime import datetime, date
from decimal import Decimal
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Family Budget Sharing", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS households (
                id SERIAL PRIMARY KEY,
                household_code VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                monthly_budget DECIMAL(12,2) DEFAULT 0,
                settings JSONB DEFAULT '{}'::jsonb
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS household_members (
                id SERIAL PRIMARY KEY,
                household_id INTEGER REFERENCES households(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                display_name VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                role VARCHAR(20) DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'active',
                UNIQUE(household_id, user_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS shared_expense_categories (
                id SERIAL PRIMARY KEY,
                household_id INTEGER REFERENCES households(id) ON DELETE CASCADE,
                name VARCHAR(100) NOT NULL,
                color VARCHAR(7) DEFAULT '#6366f1',
                icon VARCHAR(10) DEFAULT '💰',
                monthly_budget DECIMAL(12,2) DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                UNIQUE(household_id, name)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS shared_expenses (
                id SERIAL PRIMARY KEY,
                household_id INTEGER REFERENCES households(id) ON DELETE CASCADE,
                category_id INTEGER REFERENCES shared_expense_categories(id),
                paid_by INTEGER NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                description VARCHAR(500),
                expense_date DATE NOT NULL,
                split_type VARCHAR(20) DEFAULT 'equal',
                split_data JSONB DEFAULT '[]'::jsonb,
                receipt_url VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS expense_splits (
                id SERIAL PRIMARY KEY,
                expense_id INTEGER REFERENCES shared_expenses(id) ON DELETE CASCADE,
                member_id INTEGER NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                percentage DECIMAL(5,2),
                is_settled BOOLEAN DEFAULT FALSE,
                settled_at TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settlements (
                id SERIAL PRIMARY KEY,
                household_id INTEGER REFERENCES households(id) ON DELETE CASCADE,
                from_member INTEGER NOT NULL,
                to_member INTEGER NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                settlement_date DATE NOT NULL,
                method VARCHAR(50),
                notes VARCHAR(500),
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS household_invites (
                id SERIAL PRIMARY KEY,
                household_id INTEGER REFERENCES households(id) ON DELETE CASCADE,
                invite_code VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(255),
                role VARCHAR(20) DEFAULT 'member',
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                used_at TIMESTAMP,
                used_by INTEGER
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS households (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                monthly_budget REAL DEFAULT 0,
                settings TEXT DEFAULT '{}'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS household_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER REFERENCES households(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                display_name TEXT NOT NULL,
                email TEXT,
                role TEXT DEFAULT 'member',
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                UNIQUE(household_id, user_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS shared_expense_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER REFERENCES households(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                color TEXT DEFAULT '#6366f1',
                icon TEXT DEFAULT '💰',
                monthly_budget REAL DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                UNIQUE(household_id, name)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS shared_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER REFERENCES households(id) ON DELETE CASCADE,
                category_id INTEGER REFERENCES shared_expense_categories(id),
                paid_by INTEGER NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                expense_date TEXT NOT NULL,
                split_type TEXT DEFAULT 'equal',
                split_data TEXT DEFAULT '[]',
                receipt_url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS expense_splits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_id INTEGER REFERENCES shared_expenses(id) ON DELETE CASCADE,
                member_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                percentage REAL,
                is_settled INTEGER DEFAULT 0,
                settled_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settlements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER REFERENCES households(id) ON DELETE CASCADE,
                from_member INTEGER NOT NULL,
                to_member INTEGER NOT NULL,
                amount REAL NOT NULL,
                settlement_date TEXT NOT NULL,
                method TEXT,
                notes TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS household_invites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER REFERENCES households(id) ON DELETE CASCADE,
                invite_code TEXT UNIQUE NOT NULL,
                email TEXT,
                role TEXT DEFAULT 'member',
                created_by INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT,
                used_at TEXT,
                used_by INTEGER
            )
        """)
    
    conn.commit()
    cur.close()
    conn.close()

def generate_household_code():
    return uuid.uuid4().hex[:8].upper()

def generate_invite_code():
    return uuid.uuid4().hex[:12].upper()

def get_user_households(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT h.id, h.household_code, h.name, h.monthly_budget, hm.role
        FROM households h
        JOIN household_members hm ON h.id = hm.household_id
        WHERE hm.user_id = {ph} AND hm.status = 'active'
        ORDER BY h.name
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_household_members(household_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT id, user_id, display_name, email, role, joined_at, status
        FROM household_members
        WHERE household_id = {ph} AND status = 'active'
        ORDER BY role DESC, display_name
    """, (household_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_household_categories(household_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    if USE_POSTGRES:
        cur.execute(f"""
            SELECT id, name, color, icon, monthly_budget, is_active
            FROM shared_expense_categories
            WHERE household_id = {ph} AND is_active = TRUE
            ORDER BY name
        """, (household_id,))
    else:
        cur.execute(f"""
            SELECT id, name, color, icon, monthly_budget, is_active
            FROM shared_expense_categories
            WHERE household_id = {ph} AND is_active = 1
            ORDER BY name
        """, (household_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def create_household(name, user_id, display_name, email=None, monthly_budget=0):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    code = generate_household_code()
    
    if USE_POSTGRES:
        cur.execute(f"""
            INSERT INTO households (household_code, name, created_by, monthly_budget)
            VALUES ({ph}, {ph}, {ph}, {ph})
            RETURNING id
        """, (code, name, user_id, monthly_budget))
        household_id = cur.fetchone()[0]
    else:
        cur.execute(f"""
            INSERT INTO households (household_code, name, created_by, monthly_budget)
            VALUES ({ph}, {ph}, {ph}, {ph})
        """, (code, name, user_id, monthly_budget))
        household_id = cur.lastrowid
    
    cur.execute(f"""
        INSERT INTO household_members (household_id, user_id, display_name, email, role)
        VALUES ({ph}, {ph}, {ph}, {ph}, 'admin')
    """, (household_id, user_id, display_name, email))
    
    default_categories = [
        ("🏠 Rent/Mortgage", "#ef4444", "🏠"),
        ("🛒 Groceries", "#22c55e", "🛒"),
        ("💡 Utilities", "#eab308", "💡"),
        ("🚗 Transportation", "#3b82f6", "🚗"),
        ("🍽️ Dining Out", "#f97316", "🍽️"),
        ("🎬 Entertainment", "#a855f7", "🎬"),
        ("🏥 Healthcare", "#ec4899", "🏥"),
        ("📱 Subscriptions", "#06b6d4", "📱"),
        ("🎁 Other", "#6b7280", "🎁")
    ]
    
    for cat_name, color, icon in default_categories:
        cur.execute(f"""
            INSERT INTO shared_expense_categories (household_id, name, color, icon)
            VALUES ({ph}, {ph}, {ph}, {ph})
        """, (household_id, cat_name, color, icon))
    
    conn.commit()
    cur.close()
    conn.close()
    return household_id, code

def join_household_by_code(household_code, user_id, display_name, email=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT id FROM households WHERE household_code = {ph}
    """, (household_code.upper(),))
    row = cur.fetchone()
    
    if not row:
        cur.close()
        conn.close()
        return None, "Household not found"
    
    household_id = row[0]
    
    cur.execute(f"""
        SELECT id FROM household_members 
        WHERE household_id = {ph} AND user_id = {ph}
    """, (household_id, user_id))
    existing = cur.fetchone()
    
    if existing:
        cur.close()
        conn.close()
        return None, "You are already a member of this household"
    
    cur.execute(f"""
        INSERT INTO household_members (household_id, user_id, display_name, email, role)
        VALUES ({ph}, {ph}, {ph}, {ph}, 'member')
    """, (household_id, user_id, display_name, email))
    
    conn.commit()
    cur.close()
    conn.close()
    return household_id, "Successfully joined household"

def leave_household(household_id, user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT role FROM household_members 
        WHERE household_id = {ph} AND user_id = {ph}
    """, (household_id, user_id))
    row = cur.fetchone()
    
    if not row:
        cur.close()
        conn.close()
        return False, "Not a member of this household"
    
    if row[0] == 'admin':
        cur.execute(f"""
            SELECT COUNT(*) FROM household_members 
            WHERE household_id = {ph} AND role = 'admin' AND status = 'active'
        """, (household_id,))
        admin_count = cur.fetchone()[0]
        
        if admin_count <= 1:
            cur.close()
            conn.close()
            return False, "Cannot leave: You are the only admin. Transfer admin rights first."
    
    cur.execute(f"""
        UPDATE household_members SET status = 'inactive'
        WHERE household_id = {ph} AND user_id = {ph}
    """, (household_id, user_id))
    
    conn.commit()
    cur.close()
    conn.close()
    return True, "Successfully left household"

def add_shared_expense(household_id, category_id, paid_by, amount, description, expense_date, split_type, split_data):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    split_json = json.dumps(split_data)
    
    if USE_POSTGRES:
        cur.execute(f"""
            INSERT INTO shared_expenses 
            (household_id, category_id, paid_by, amount, description, expense_date, split_type, split_data)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}::jsonb)
            RETURNING id
        """, (household_id, category_id, paid_by, amount, description, expense_date, split_type, split_json))
        expense_id = cur.fetchone()[0]
    else:
        cur.execute(f"""
            INSERT INTO shared_expenses 
            (household_id, category_id, paid_by, amount, description, expense_date, split_type, split_data)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (household_id, category_id, paid_by, amount, description, expense_date, split_type, split_json))
        expense_id = cur.lastrowid
    
    for split in split_data:
        cur.execute(f"""
            INSERT INTO expense_splits (expense_id, member_id, amount, percentage)
            VALUES ({ph}, {ph}, {ph}, {ph})
        """, (expense_id, split['member_id'], split['amount'], split.get('percentage')))
    
    conn.commit()
    cur.close()
    conn.close()
    return expense_id

def get_shared_expenses(household_id, start_date=None, end_date=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    query = f"""
        SELECT se.id, se.category_id, sec.name, sec.icon, se.paid_by, hm.display_name,
               se.amount, se.description, se.expense_date, se.split_type, se.split_data
        FROM shared_expenses se
        LEFT JOIN shared_expense_categories sec ON se.category_id = sec.id
        LEFT JOIN household_members hm ON se.paid_by = hm.id
        WHERE se.household_id = {ph}
    """
    params = [household_id]
    
    if start_date:
        query += f" AND se.expense_date >= {ph}"
        params.append(start_date)
    if end_date:
        query += f" AND se.expense_date <= {ph}"
        params.append(end_date)
    
    query += " ORDER BY se.expense_date DESC, se.created_at DESC"
    
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def calculate_balances(household_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    members = get_household_members(household_id)
    balances = {m[0]: {'name': m[2], 'paid': 0, 'owes': 0, 'balance': 0} for m in members}
    
    cur.execute(f"""
        SELECT paid_by, SUM(amount) as total_paid
        FROM shared_expenses
        WHERE household_id = {ph}
        GROUP BY paid_by
    """, (household_id,))
    
    for row in cur.fetchall():
        if row[0] in balances:
            balances[row[0]]['paid'] = float(row[1])
    
    cur.execute(f"""
        SELECT es.member_id, SUM(es.amount) as total_owes
        FROM expense_splits es
        JOIN shared_expenses se ON es.expense_id = se.id
        WHERE se.household_id = {ph}
        GROUP BY es.member_id
    """, (household_id,))
    
    for row in cur.fetchall():
        if row[0] in balances:
            balances[row[0]]['owes'] = float(row[1])
    
    cur.execute(f"""
        SELECT from_member, to_member, SUM(amount) as total
        FROM settlements
        WHERE household_id = {ph} AND status = 'completed'
        GROUP BY from_member, to_member
    """, (household_id,))
    
    settlements_made = {}
    for row in cur.fetchall():
        if row[0] not in settlements_made:
            settlements_made[row[0]] = {}
        settlements_made[row[0]][row[1]] = float(row[2])
    
    for member_id, data in balances.items():
        data['balance'] = data['paid'] - data['owes']
    
    cur.close()
    conn.close()
    return balances

def get_pending_settlements(household_id):
    balances = calculate_balances(household_id)
    
    creditors = []
    debtors = []
    
    for member_id, data in balances.items():
        if data['balance'] > 0.01:
            creditors.append((member_id, data['name'], data['balance']))
        elif data['balance'] < -0.01:
            debtors.append((member_id, data['name'], -data['balance']))
    
    creditors.sort(key=lambda x: -x[2])
    debtors.sort(key=lambda x: -x[2])
    
    settlements = []
    
    i, j = 0, 0
    while i < len(creditors) and j < len(debtors):
        creditor_id, creditor_name, credit = creditors[i]
        debtor_id, debtor_name, debt = debtors[j]
        
        amount = min(credit, debt)
        
        if amount > 0.01:
            settlements.append({
                'from_id': debtor_id,
                'from_name': debtor_name,
                'to_id': creditor_id,
                'to_name': creditor_name,
                'amount': round(amount, 2)
            })
        
        creditors[i] = (creditor_id, creditor_name, credit - amount)
        debtors[j] = (debtor_id, debtor_name, debt - amount)
        
        if creditors[i][2] < 0.01:
            i += 1
        if debtors[j][2] < 0.01:
            j += 1
    
    return settlements

def record_settlement(household_id, from_member, to_member, amount, method, notes):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        INSERT INTO settlements (household_id, from_member, to_member, amount, settlement_date, method, notes, status)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 'completed')
    """, (household_id, from_member, to_member, amount, date.today().isoformat(), method, notes))
    
    conn.commit()
    cur.close()
    conn.close()

def update_member_role(household_id, member_id, new_role):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        UPDATE household_members SET role = {ph}
        WHERE household_id = {ph} AND id = {ph}
    """, (new_role, household_id, member_id))
    
    conn.commit()
    cur.close()
    conn.close()

def delete_expense(expense_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"DELETE FROM expense_splits WHERE expense_id = {ph}", (expense_id,))
    cur.execute(f"DELETE FROM shared_expenses WHERE id = {ph}", (expense_id,))
    
    conn.commit()
    cur.close()
    conn.close()

_ensure_tables()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

st.title("👨‍👩‍👧‍👦 Family Budget Sharing")
st.markdown("Collaborate on household finances with shared expenses and split tracking")

user_id = st.session_state.get("user_id", 1)
user_email = st.session_state.get("email", "")
user_name = st.session_state.get("display_name", "User")

households = get_user_households(user_id)

if "current_household" not in st.session_state:
    st.session_state.current_household = None
if "show_create_form" not in st.session_state:
    st.session_state.show_create_form = False
if "show_join_form" not in st.session_state:
    st.session_state.show_join_form = False

if not households:
    st.info("You're not part of any household yet. Create or join one to get started!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏠 Create a Household")
        with st.form("create_household"):
            hh_name = st.text_input("Household Name", placeholder="The Smith Family")
            display_name = st.text_input("Your Display Name", value=user_name)
            monthly_budget = st.number_input("Monthly Budget", min_value=0.0, value=5000.0, step=100.0)
            
            if st.form_submit_button("Create Household", type="primary"):
                if hh_name and display_name:
                    hh_id, code = create_household(hh_name, user_id, display_name, user_email, monthly_budget)
                    st.success(f"Household created! Share code: **{code}**")
                    st.rerun()
                else:
                    st.error("Please fill in all fields")
    
    with col2:
        st.subheader("🔗 Join a Household")
        with st.form("join_household"):
            join_code = st.text_input("Household Code", placeholder="ABC12345")
            join_name = st.text_input("Your Display Name", value=user_name)
            
            if st.form_submit_button("Join Household", type="primary"):
                if join_code and join_name:
                    result, msg = join_household_by_code(join_code, user_id, join_name, user_email)
                    if result:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Please fill in all fields")

else:
    household_options = {f"{h[2]} ({h[1]})": h[0] for h in households}
    household_roles = {h[0]: h[4] for h in households}
    
    selected_hh = st.selectbox(
        "Select Household",
        options=list(household_options.keys()),
        key="household_selector"
    )
    
    current_hh_id = household_options[selected_hh]
    current_role = household_roles[current_hh_id]
    is_admin = current_role == 'admin'
    
    tabs = st.tabs(["📊 Dashboard", "💸 Add Expense", "📋 Expenses", "💰 Settle Up", "👥 Members", "⚙️ Settings"])
    
    with tabs[0]:
        st.subheader("Household Dashboard")
        
        members = get_household_members(current_hh_id)
        balances = calculate_balances(current_hh_id)
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_expenses = sum(b['owes'] for b in balances.values())
        total_paid = sum(b['paid'] for b in balances.values())
        
        with col1:
            st.metric("Total Expenses", f"${total_expenses:,.2f}")
        with col2:
            st.metric("Members", len(members))
        with col3:
            pending = get_pending_settlements(current_hh_id)
            st.metric("Pending Settlements", len(pending))
        with col4:
            avg_per_member = total_expenses / len(members) if members else 0
            st.metric("Avg per Member", f"${avg_per_member:,.2f}")
        
        st.markdown("---")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("### 💳 Individual Contributions")
            
            for member_id, data in balances.items():
                balance = data['balance']
                if balance > 0:
                    status = f"🟢 Owed ${balance:,.2f}"
                    color = "green"
                elif balance < 0:
                    status = f"🔴 Owes ${-balance:,.2f}"
                    color = "red"
                else:
                    status = "✅ Settled"
                    color = "gray"
                
                st.markdown(f"""
                <div style="padding: 10px; margin: 5px 0; border-radius: 8px; background: linear-gradient(90deg, #1e1e2e, #2d2d44);">
                    <strong>{data['name']}</strong><br>
                    <small>Paid: ${data['paid']:,.2f} | Share: ${data['owes']:,.2f}</small><br>
                    <span style="color: {color};">{status}</span>
                </div>
                """, unsafe_allow_html=True)
        
        with col_right:
            st.markdown("### 📈 Spending by Category")
            
            categories = get_household_categories(current_hh_id)
            expenses = get_shared_expenses(current_hh_id)
            
            category_totals = {}
            for exp in expenses:
                cat_name = exp[2] or "Uncategorized"
                cat_icon = exp[3] or "💰"
                key = f"{cat_icon} {cat_name}"
                category_totals[key] = category_totals.get(key, 0) + float(exp[6])
            
            if category_totals:
                sorted_cats = sorted(category_totals.items(), key=lambda x: -x[1])
                for cat, amount in sorted_cats[:8]:
                    pct = (amount / total_expenses * 100) if total_expenses > 0 else 0
                    st.markdown(f"""
                    <div style="padding: 8px; margin: 3px 0;">
                        <div style="display: flex; justify-content: space-between;">
                            <span>{cat}</span>
                            <span>${amount:,.2f} ({pct:.1f}%)</span>
                        </div>
                        <div style="background: #333; border-radius: 4px; height: 8px; margin-top: 4px;">
                            <div style="background: #6366f1; width: {min(pct, 100)}%; height: 100%; border-radius: 4px;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No expenses recorded yet")
    
    with tabs[1]:
        st.sub