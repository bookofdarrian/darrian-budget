import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from decimal import Decimal
import json
import io

st.set_page_config(page_title="Social Security Estimator", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS social_security_earnings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                earnings DECIMAL(12,2) NOT NULL,
                credits INTEGER DEFAULT 0,
                is_estimated BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, year)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ss_estimates (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                age_scenario INTEGER NOT NULL,
                monthly_benefit DECIMAL(10,2) NOT NULL,
                aime DECIMAL(10,2),
                pia DECIMAL(10,2),
                total_credits INTEGER,
                break_even_age DECIMAL(4,1),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ss_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                birth_date DATE,
                expected_retirement_age INTEGER DEFAULT 67,
                spouse_birth_date DATE,
                spouse_expected_retirement_age INTEGER,
                spouse_pia DECIMAL(10,2),
                life_expectancy INTEGER DEFAULT 85,
                spouse_life_expectancy INTEGER DEFAULT 85,
                include_spouse_benefits BOOLEAN DEFAULT FALSE,
                cola_assumption DECIMAL(4,2) DEFAULT 2.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS social_security_earnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                earnings REAL NOT NULL,
                credits INTEGER DEFAULT 0,
                is_estimated INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, year)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ss_estimates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                age_scenario INTEGER NOT NULL,
                monthly_benefit REAL NOT NULL,
                aime REAL,
                pia REAL,
                total_credits INTEGER,
                break_even_age REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ss_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                birth_date TEXT,
                expected_retirement_age INTEGER DEFAULT 67,
                spouse_birth_date TEXT,
                spouse_expected_retirement_age INTEGER,
                spouse_pia REAL,
                life_expectancy INTEGER DEFAULT 85,
                spouse_life_expectancy INTEGER DEFAULT 85,
                include_spouse_benefits INTEGER DEFAULT 0,
                cola_assumption REAL DEFAULT 2.5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
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

SS_WAGE_BASE = {
    2024: 168600, 2023: 160200, 2022: 147000, 2021: 142800, 2020: 137700,
    2019: 132900, 2018: 128400, 2017: 127200, 2016: 118500, 2015: 118500,
    2014: 117000, 2013: 113700, 2012: 110100, 2011: 106800, 2010: 106800,
    2009: 106800, 2008: 102000, 2007: 97500, 2006: 94200, 2005: 90000,
    2004: 87900, 2003: 87000, 2002: 84900, 2001: 80400, 2000: 76200,
    1999: 72600, 1998: 68400, 1997: 65400, 1996: 62700, 1995: 61200,
    1994: 60600, 1993: 57600, 1992: 55500, 1991: 53400, 1990: 51300,
    1989: 48000, 1988: 45000, 1987: 43800, 1986: 42000, 1985: 39600,
    1984: 37800, 1983: 35700, 1982: 32400, 1981: 29700, 1980: 25900
}

AWI = {
    2022: 63795.13, 2021: 60575.07, 2020: 55628.60, 2019: 54099.99, 2018: 52145.80,
    2017: 50321.89, 2016: 48642.15, 2015: 48098.63, 2014: 46481.52, 2013: 44888.16,
    2012: 44321.67, 2011: 42979.61, 2010: 41673.83, 2009: 40711.61, 2008: 41334.97,
    2007: 40405.48, 2006: 38651.41, 2005: 36952.94, 2004: 35648.55, 2003: 34064.95,
    2002: 33252.09, 2001: 32921.92, 2000: 32154.82, 1999: 30469.84, 1998: 28861.44,
    1997: 27426.00, 1996: 25913.90, 1995: 24705.66, 1994: 23753.53, 1993: 23132.67,
    1992: 22935.42, 1991: 22217.31, 1990: 21027.98, 1989: 20099.55, 1988: 19334.04,
    1987: 18426.51, 1986: 17321.82, 1985: 16822.51, 1984: 16135.07, 1983: 15239.24,
    1982: 14531.34, 1981: 13773.10, 1980: 12513.46
}

BEND_POINTS_2024 = (1174, 7078)
PIA_FACTORS = (0.90, 0.32, 0.15)

def get_user_id():
    return st.session_state.get("user_id", 1)

def get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def get_ss_settings(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"SELECT * FROM ss_settings WHERE user_id = {ph}", (user_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        cols = [desc[0] for desc in cur.description] if hasattr(cur, 'description') and cur.description else [
            'id', 'user_id', 'birth_date', 'expected_retirement_age', 'spouse_birth_date',
            'spouse_expected_retirement_age', 'spouse_pia', 'life_expectancy',
            'spouse_life_expectancy', 'include_spouse_benefits', 'cola_assumption',
            'created_at', 'updated_at'
        ]
        return dict(zip(cols, row))
    return None

def save_ss_settings(user_id, settings):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    existing = get_ss_settings(user_id)
    
    if existing:
        if USE_POSTGRES:
            cur.execute(f"""
                UPDATE ss_settings SET
                    birth_date = {ph}, expected_retirement_age = {ph},
                    spouse_birth_date = {ph}, spouse_expected_retirement_age = {ph},
                    spouse_pia = {ph}, life_expectancy = {ph},
                    spouse_life_expectancy = {ph}, include_spouse_benefits = {ph},
                    cola_assumption = {ph}, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = {ph}
            """, (
                settings['birth_date'], settings['expected_retirement_age'],
                settings.get('spouse_birth_date'), settings.get('spouse_expected_retirement_age'),
                settings.get('spouse_pia'), settings['life_expectancy'],
                settings.get('spouse_life_expectancy'), settings['include_spouse_benefits'],
                settings['cola_assumption'], user_id
            ))
        else:
            cur.execute(f"""
                UPDATE ss_settings SET
                    birth_date = {ph}, expected_retirement_age = {ph},
                    spouse_birth_date = {ph}, spouse_expected_retirement_age = {ph},
                    spouse_pia = {ph}, life_expectancy = {ph},
                    spouse_life_expectancy = {ph}, include_spouse_benefits = {ph},
                    cola_assumption = {ph}, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = {ph}
            """, (
                str(settings['birth_date']) if settings['birth_date'] else None,
                settings['expected_retirement_age'],
                str(settings.get('spouse_birth_date')) if settings.get('spouse_birth_date') else None,
                settings.get('spouse_expected_retirement_age'),
                settings.get('spouse_pia'), settings['life_expectancy'],
                settings.get('spouse_life_expectancy'),
                1 if settings['include_spouse_benefits'] else 0,
                settings['cola_assumption'], user_id
            ))
    else:
        if USE_POSTGRES:
            cur.execute(f"""
                INSERT INTO ss_settings (user_id, birth_date, expected_retirement_age,
                    spouse_birth_date, spouse_expected_retirement_age, spouse_pia,
                    life_expectancy, spouse_life_expectancy, include_spouse_benefits, cola_assumption)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (
                user_id, settings['birth_date'], settings['expected_retirement_age'],
                settings.get('spouse_birth_date'), settings.get('spouse_expected_retirement_age'),
                settings.get('spouse_pia'), settings['life_expectancy'],
                settings.get('spouse_life_expectancy'), settings['include_spouse_benefits'],
                settings['cola_assumption']
            ))
        else:
            cur.execute(f"""
                INSERT INTO ss_settings (user_id, birth_date, expected_retirement_age,
                    spouse_birth_date, spouse_expected_retirement_age, spouse_pia,
                    life_expectancy, spouse_life_expectancy, include_spouse_benefits, cola_assumption)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (
                user_id,
                str(settings['birth_date']) if settings['birth_date'] else None,
                settings['expected_retirement_age'],
                str(settings.get('spouse_birth_date')) if settings.get('spouse_birth_date') else None,
                settings.get('spouse_expected_retirement_age'),
                settings.get('spouse_pia'), settings['life_expectancy'],
                settings.get('spouse_life_expectancy'),
                1 if settings['include_spouse_benefits'] else 0,
                settings['cola_assumption']
            ))
    
    conn.commit()
    conn.close()

def get_earnings_history(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"""
        SELECT id, year, earnings, credits, is_estimated
        FROM social_security_earnings
        WHERE user_id = {ph}
        ORDER BY year DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def add_earnings_record(user_id, year, earnings, credits, is_estimated=False):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    try:
        if USE_POSTGRES:
            cur.execute(f"""
                INSERT INTO social_security_earnings (user_id, year, earnings, credits, is_estimated)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
                ON CONFLICT (user_id, year) DO UPDATE SET
                    earnings = EXCLUDED.earnings,
                    credits = EXCLUDED.credits,
                    is_estimated = EXCLUDED.is_estimated
            """, (user_id, year, earnings, credits, is_estimated))
        else:
            cur.execute(f"""
                INSERT OR REPLACE INTO social_security_earnings (user_id, year, earnings, credits, is_estimated)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
            """, (user_id, year, earnings, credits, 1 if is_estimated else 0))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error saving earnings: {e}")
        return False
    finally:
        conn.close()

def delete_earnings_record(record_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"DELETE FROM social_security_earnings WHERE id = {ph}", (record_id,))
    conn.commit()
    conn.close()

def calculate_credits(earnings, year):
    credit_amount = 1730 if year >= 2024 else 1640
    credits = min(4, int(earnings / credit_amount))
    return credits

def calculate_indexing_factor(year, indexing_year=2022):
    if year >= indexing_year:
        return 1.0
    awi_year = AWI.get(year, AWI.get(min(AWI.keys())))
    awi_index = AWI.get(indexing_year, AWI[2022])
    return awi_index / awi_year

def calculate_aime(earnings_history, birth_year):
    indexed_earnings = []
    indexing_year = birth_year + 60 - 2
    
    for record in earnings_history:
        year = record[1]
        earnings = float(record[2])
        wage_base = SS_WAGE_BASE.get(year, SS_WAGE_BASE.get(min(SS_WAGE_BASE.keys())))
        capped_earnings = min(earnings, wage_base)
        
        if year <= indexing_year:
            factor = calculate_indexing_factor(year, min(indexing_year, max(AWI.keys())))
            indexed = capped_earnings * factor
        else:
            indexed = capped_earnings
        
        indexed_earnings.append((year, indexed))
    
    indexed_earnings.sort(key=lambda x: x[1], reverse=True)
    top_35 = indexed_earnings[:35]
    
    while len(top_35) < 35:
        top_35.append((0, 0))
    
    total = sum(e[1] for e in top_35)
    aime = total / (35 * 12)
    
    return aime

def calculate_pia(aime, bend_points=BEND_POINTS_2024):
    bp1, bp2 = bend_points
    
    if aime <= bp1:
        pia = aime * PIA_FACTORS[0]
    elif aime <= bp2:
        pia = (bp1 * PIA_FACTORS[0]) + ((aime - bp1) * PIA_FACTORS[1])
    else:
        pia = (bp1 * PIA_FACTORS[0]) + ((bp2 - bp1) * PIA_FACTORS[1]) + ((aime - bp2) * PIA_FACTORS[2])
    
    return round(pia, 2)

def calculate_benefit_at_age(pia, claiming_age, fra=67):
    if claiming_age < 62:
        return 0
    
    months_diff = (claiming_age - fra) * 12
    
    if claiming_age < fra:
        if months_diff >= -36:
            reduction = abs(months_diff) * (5/9) / 100
        else:
            reduction = 36 * (5/9) / 100 + (abs(months_diff) - 36) * (5/12) / 100
        benefit = pia * (1 - reduction)
    elif claiming_age > fra:
        increase = min(months_diff, 36) * (2/3) / 100
        benefit = pia * (1 + increase)
    else:
        benefit = pia
    
    return round(benefit, 2)

def calculate_break_even_age(benefit_early, benefit_later, early_age, later_age):
    if benefit_later <= benefit_early:
        return None
    
    months_diff = (later_age - early_age) * 12
    lost_benefits = benefit_early * months_diff
    monthly_gain = benefit_later - benefit_early
    
    if monthly_gain <= 0:
        return None
    
    months_to_break_even = lost_benefits / monthly_gain
    break_even_age = later_age + (months_to_break_even / 12)
    
    return round(break_even_age, 1)

def calculate_lifetime_benefits(monthly_benefit, claiming_age, life_expectancy, cola=2.5):
    total = 0
    current_benefit = monthly_benefit
    
    for age in range(int(claiming_age), int(life_expectancy) + 1):
        annual_benefit = current_benefit * 12
        total += annual_benefit
        current_benefit *= (1 + cola / 100)
    
    return round(total, 2)

def calculate_spousal_benefit(worker_pia, spouse_own_pia=0):
    spousal_max = worker_pia / 2
    excess = max(0, spousal_max - spouse_own_pia)
    return round(excess, 2)

def get_ai_recommendations(settings, earnings_data, estimates):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ Configure your Anthropic API key in settings to get AI recommendations."
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        birth_date = settings.get('birth_date')
        if birth_date:
            if isinstance(birth_date, str):
                birth_year = int(birth_date.split('-')[0])
            else:
                birth_year = birth_date.year
            current_age = datetime.now().year - birth_year
        else:
            current_age = 50
        
        total_earnings = sum(float(e[2]) for e in earnings_data) if earnings_data else 0
        total_credits = sum(int(e[3]) for e in earnings_data) if earnings_data else 0
        
        context = f"""
        User Social Security Profile:
        - Current Age: {current_age}
        - Expected Retirement Age: {settings.get('expected_retirement_age', 67)}
        - Life Expectancy: {settings.get('life_expectancy', 85)}
        - Total Career Earnings: ${total_earnings:,.2f}
        - Total SS Credits: {total_credits}
        - Has Spouse Benefits: {settings.get('include_spouse_benefits', False)}
        - COLA Assumption: {settings.get('cola_assumption', 2.5)}%
        
        Benefit Estimates:
        """
        
        for est in estimates:
            context += f"\n- Age {est['age']}: ${est['monthly']:,.2f}/month (Lifetime: ${est['lifetime']:,.2f})"
        
        prompt = f"""
        Based on this Social Security profile, provide personalized claiming strategy recommendations:
        
        {context}
        
        Consider:
        1. Break-even analysis between claiming ages
        2. Health and longevity factors
        3. Spousal benefits optimization if applicable
        4. Tax implications of different claiming strategies
        5. Impact on other retirement income sources
        
        Provide 3-5 specific, actionable recommendations with reasoning.
        Format your response in clear sections with bullet points.
        """
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
        
    except Exception as e:
        return f"⚠️ Error getting AI recommendations: {str(e)}"

st.title("🏛️ Social Security Benefits Estimator")
st.markdown("Estimate your future Social Security retirement benefits and optimize your claiming strategy")

user_id = get_user_id()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⚙️ Settings", "💰 Earnings History", "📊 Benefit Estimates",
    "🎯 Claiming Strategy", "🤖 AI Insights"
])

with tab1:
    st.subheader("Personal Information")
    
    settings = get_ss_settings(user_id) or {}
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Your Information")
        
        default_birth = None
        if settings.get('birth_date'):
            if isinstance(settings['birth_date'], str):
                try:
                    default_birth = datetime.strptime(settings['birth_date'], '%Y-%m-%d').date()
                except:
                    default_birth = None
            else:
                default_birth = settings['birth_date']
        
        birth_date = st.date_input(
            "Birth Date",
            value=default_birth,
            min_value=date(1940, 1, 1),
            max_value=date(2010, 12, 31),
            help="Your date of birth for calculating Full Retirement Age"
        )
        
        expected_ret_age = st.slider(
            "Expected Retirement Age",
            min_value=62, max_value=70,
            value=settings.get('expected_retirement_age', 67),
            help="Age you plan to start claiming Social Security"
        )
        
        life_expectancy = st.slider(
            "Life Expectancy",
            min_value=70, max_value=100,
            value=settings.get('life_expectancy', 85),
            help="Estimated life expectancy for benefit calculations"
        )
        
        cola_assumption = st.number_input(
            "COLA Assumption (%)",
            min_value=0.0, max_value=10.0,
            value=float(settings.get('cola_assumption', 2.5)),
            step=0.1,
            help="Expected annual Cost of Living Adjustment"
        )
    
    with col2:
        st.markdown("#### Spouse Information")
        
        include_spouse = st.checkbox(
            "Include Spouse Benefits",
            value=bool(settings.get('include_spouse_benefits', False))
        )
        
        spouse_birth_date = None
        spouse_ret_age = None
        spouse_pia = None
        spouse_life_exp = None
        
        if include_spouse:
            default_spouse_birth = None
            if settings.get('spouse_birth_date'):
                if isinstance(settings['spouse_birth_date'], str):
                    try:
                        default_spouse_birth = datetime.strptime(settings['spouse_birth_date'], '%Y-%m-%d').date()
                    except:
                        default_spouse_birth = None
                else:
                    default_spouse_birth = settings['spouse_birth_date']
            
            spouse_birth_date = st.date_input(
                "Spouse Birth Date",
                value=default_spouse_birth,
                min_value=date(1940, 1, 1),
                max_value=date(2010, 12, 31)
            )
            
            spouse_ret_age = st.slider(
                "Spouse Expected Retirement Age",
                min_value=62, max_value=70,
                value=settings.get('spouse_expected_retirement_age', 67)
            )
            
            spouse_pia = st.number_input(
                "Spouse's PIA (Primary Insurance Amount)",
                min_value=0.0, max_value=5000.0,
                value=float(settings.get('spouse_pia', 0) or 0),
                step=50.0,
                help="Spouse's benefit at Full Retirement Age"
            )
            
            spouse_life_exp = st.slider(
                "Spouse Life Expectancy",
                min_value=70, max_value=100,
                value=settings.get('spouse_life_expectancy', 85)
            )
    
    if st.button("💾 Save Settings", type="primary"):
        new_settings = {
            'birth_date': birth_date,
            'expected_retirement_age': expected_ret_age,
            'life_expectancy': life_expectancy,
            'cola_assumption': cola_assumption,
            'include_spouse_benefits': include_spouse,
            'spouse_birth_date': spouse_birth_date if include_spouse else None,
            'spouse_expected_retirement_age': spouse_ret_age if include_spouse else None,
            'spouse_pia': spouse_pia if include_spouse else None,
            'spouse_life_expectancy': spouse_life_exp if include_spouse else None
        }
        save_ss_settings(user_id, new_settings)
        st.success("✅ Settings saved successfully!")
        st.rerun()

with tab2:
    st.subheader("Earnings History")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### Add Earnings Record")
        
        with st.form("add_earnings"):
            form_col1, form_col2, form_col3 = st.columns(3)
            
            with form_col1:
                year = st.number_input(
                    "Year",
                    min_value=1980,
                    max_value=datetime.now().year,
                    value=datetime.now().year - 1
                )
            
            with form_col2:
                earnings = st.number_input(
                    "Earnings ($)",
                    min_value=0.0,
                    max_value=500000.0,
                    value=50000.0,
                    step=1000.0
                )
            
            with form_col3:
                credits = st.number_input(
                    "Credits (auto-calc if 0)",
                    min_value=0, max_value=4,
                    value=0
                )
            
            is_estimated = st.checkbox("This is an estimated value")
            
            if st.form_submit_button("➕ Add Record"):
                if credits == 0:
                    credits = calculate_credits(earnings, year)
                if add_earnings_record(user_id, year, earnings, credits, is_estimated):
                    st.success(f"✅ Added {year} earnings: ${earnings:,.2f} ({credits} credits)")
                    st.rerun()
    
    with col2:
        st.markdown("#### Import SSA Statement")
        
        uploaded_file = st.file_uploader(
            "Upload CSV from SSA",
            type=['csv'],
            help="Export your earnings history from ssa.gov"
        )
        
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.write("Preview:", df.head())
                
                if st.button("📥 Import All Records"):
                    imported = 0
                    for _, row in df.iterrows():
                        year = int(row.get('Year', row.get('year', 0)))
                        earnings = float(row.get('Earnings', row.get('earnings', row.get('Taxed Medicare Earnings', 0))))
                        if year > 0 and earnings > 0:
                            credits = calculate_credits(earnings, year)
                            if add_earnings_record(user_id, year, earnings, credits, False):
                                imported += 1
                    st.success(f"✅ Imported {imported} records")
                    st.rerun()
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
    st.markdown("---")
    st.markdown("#### Your Earnings History")
    
    earnings_data = get_earnings_history(user_id)
    
    if earnings_data:
        df = pd.DataFrame(earnings_data, columns=['ID', 'Year', 'Earnings', 'Credits', 'Estimated'])
        df['Estimated'] = df['Estimated'].apply(lambda x: '📝' if x else '')
        df['Earnings'] = df['Earnings'].apply(lambda x: f"${float(x):,.2f}")
        
        st.dataframe(
            df[['Year', 'Earnings', 'Credits', 'Estimated']],
            use_container_width=True,
            hide_index=True
        )
        
        total_credits = sum(int(e[3]) for e in earnings_data)
        st.info(f"📊 **Total Credits:** {total_credits}/40 required for eligibility")
        
        if total_credits < 40:
            credits_needed = 40