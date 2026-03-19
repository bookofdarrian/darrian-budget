import streamlit as st
import json
from datetime import datetime, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.set_page_config(page_title="SoleOps Weekly Reseller Report", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_weekly_reports (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                report_date DATE NOT NULL,
                report_content TEXT,
                stale_inventory_count INTEGER DEFAULT 0,
                best_opportunity TEXT,
                market_trend_summary TEXT,
                email_sent BOOLEAN DEFAULT FALSE,
                email_sent_at TIMESTAMP,
                email_opened BOOLEAN DEFAULT FALSE,
                email_opened_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_user_email_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                email_address TEXT,
                weekly_report_enabled BOOLEAN DEFAULT TRUE,
                preferred_day TEXT DEFAULT 'Sunday',
                preferred_time TEXT DEFAULT '18:00',
                include_stale_inventory BOOLEAN DEFAULT TRUE,
                include_market_trends BOOLEAN DEFAULT TRUE,
                include_opportunities BOOLEAN DEFAULT TRUE,
                stale_threshold_days INTEGER DEFAULT 30,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku TEXT,
                name TEXT,
                brand TEXT,
                size TEXT,
                purchase_price REAL,
                purchase_date DATE,
                list_price REAL,
                platform TEXT,
                status TEXT DEFAULT 'active',
                sold_date DATE,
                sold_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_market_data (
                id SERIAL PRIMARY KEY,
                sku TEXT,
                platform TEXT,
                avg_price REAL,
                price_trend REAL,
                volume INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_weekly_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                report_date DATE NOT NULL,
                report_content TEXT,
                stale_inventory_count INTEGER DEFAULT 0,
                best_opportunity TEXT,
                market_trend_summary TEXT,
                email_sent INTEGER DEFAULT 0,
                email_sent_at TEXT,
                email_opened INTEGER DEFAULT 0,
                email_opened_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_user_email_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                email_address TEXT,
                weekly_report_enabled INTEGER DEFAULT 1,
                preferred_day TEXT DEFAULT 'Sunday',
                preferred_time TEXT DEFAULT '18:00',
                include_stale_inventory INTEGER DEFAULT 1,
                include_market_trends INTEGER DEFAULT 1,
                include_opportunities INTEGER DEFAULT 1,
                stale_threshold_days INTEGER DEFAULT 30,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT,
                name TEXT,
                brand TEXT,
                size TEXT,
                purchase_price REAL,
                purchase_date DATE,
                list_price REAL,
                platform TEXT,
                status TEXT DEFAULT 'active',
                sold_date DATE,
                sold_price REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT,
                platform TEXT,
                avg_price REAL,
                price_trend REAL,
                volume INTEGER,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


def get_user_email_settings(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT * FROM soleops_user_email_settings WHERE user_id = {ph}", (user_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        cols = ['id', 'user_id', 'email_address', 'weekly_report_enabled', 'preferred_day',
                'preferred_time', 'include_stale_inventory', 'include_market_trends',
                'include_opportunities', 'stale_threshold_days', 'created_at', 'updated_at']
        return dict(zip(cols, row))
    return None


def save_user_email_settings(user_id, settings):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    existing = get_user_email_settings(user_id)
    
    if existing:
        if USE_POSTGRES:
            cur.execute(f"""
                UPDATE soleops_user_email_settings SET
                    email_address = {ph},
                    weekly_report_enabled = {ph},
                    preferred_day = {ph},
                    preferred_time = {ph},
                    include_stale_inventory = {ph},
                    include_market_trends = {ph},
                    include_opportunities = {ph},
                    stale_threshold_days = {ph},
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = {ph}
            """, (settings['email_address'], settings['weekly_report_enabled'],
                  settings['preferred_day'], settings['preferred_time'],
                  settings['include_stale_inventory'], settings['include_market_trends'],
                  settings['include_opportunities'], settings['stale_threshold_days'], user_id))
        else:
            cur.execute(f"""
                UPDATE soleops_user_email_settings SET
                    email_address = {ph},
                    weekly_report_enabled = {ph},
                    preferred_day = {ph},
                    preferred_time = {ph},
                    include_stale_inventory = {ph},
                    include_market_trends = {ph},
                    include_opportunities = {ph},
                    stale_threshold_days = {ph},
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = {ph}
            """, (settings['email_address'], 1 if settings['weekly_report_enabled'] else 0,
                  settings['preferred_day'], settings['preferred_time'],
                  1 if settings['include_stale_inventory'] else 0,
                  1 if settings['include_market_trends'] else 0,
                  1 if settings['include_opportunities'] else 0,
                  settings['stale_threshold_days'], user_id))
    else:
        if USE_POSTGRES:
            cur.execute(f"""
                INSERT INTO soleops_user_email_settings 
                (user_id, email_address, weekly_report_enabled, preferred_day, preferred_time,
                 include_stale_inventory, include_market_trends, include_opportunities, stale_threshold_days)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (user_id, settings['email_address'], settings['weekly_report_enabled'],
                  settings['preferred_day'], settings['preferred_time'],
                  settings['include_stale_inventory'], settings['include_market_trends'],
                  settings['include_opportunities'], settings['stale_threshold_days']))
        else:
            cur.execute(f"""
                INSERT INTO soleops_user_email_settings 
                (user_id, email_address, weekly_report_enabled, preferred_day, preferred_time,
                 include_stale_inventory, include_market_trends, include_opportunities, stale_threshold_days)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (user_id, settings['email_address'], 1 if settings['weekly_report_enabled'] else 0,
                  settings['preferred_day'], settings['preferred_time'],
                  1 if settings['include_stale_inventory'] else 0,
                  1 if settings['include_market_trends'] else 0,
                  1 if settings['include_opportunities'] else 0,
                  settings['stale_threshold_days']))
    
    conn.commit()
    conn.close()


def get_stale_inventory(user_id, threshold_days=30):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    today = datetime.now().date()
    
    cur.execute(f"""
        SELECT id, sku, name, brand, size, purchase_price, purchase_date, list_price, platform
        FROM soleops_inventory 
        WHERE user_id = {ph} AND status = 'active' AND purchase_date IS NOT NULL
    """, (user_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    buckets = {
        '30_days': [],
        '60_days': [],
        '90_days': [],
        '90_plus': []
    }
    
    for row in rows:
        cols = ['id', 'sku', 'name', 'brand', 'size', 'purchase_price', 'purchase_date', 'list_price', 'platform']
        item = dict(zip(cols, row))
        
        if item['purchase_date']:
            if isinstance(item['purchase_date'], str):
                purchase_date = datetime.strptime(item['purchase_date'], '%Y-%m-%d').date()
            else:
                purchase_date = item['purchase_date']
            
            days_old = (today - purchase_date).days
            item['days_old'] = days_old
            
            if days_old >= 90:
                buckets['90_plus'].append(item)
            elif days_old >= 60:
                buckets['90_days'].append(item)
            elif days_old >= 30:
                buckets['60_days'].append(item)
            elif days_old >= threshold_days:
                buckets['30_days'].append(item)
    
    return buckets


def get_market_trends(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT DISTINCT sku FROM soleops_inventory 
        WHERE user_id = {ph} AND status = 'active' AND sku IS NOT NULL
    """, (user_id,))
    
    skus = [row[0] for row in cur.fetchall()]
    
    trends = []
    for sku in skus[:10]:
        cur.execute(f"""
            SELECT sku, platform, avg_price, price_trend, volume 
            FROM soleops_market_data 
            WHERE sku = {ph}
            ORDER BY last_updated DESC LIMIT 1
        """, (sku,))
        row = cur.fetchone()
        if row:
            trends.append({
                'sku': row[0],
                'platform': row[1],
                'avg_price': row[2],
                'price_trend': row[3],
                'volume': row[4]
            })
    
    conn.close()
    return trends


def get_best_opportunity(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT i.id, i.sku, i.name, i.brand, i.size, i.purchase_price, i.list_price,
               m.avg_price, m.price_trend
        FROM soleops_inventory i
        LEFT JOIN soleops_market_data m ON i.sku = m.sku
        WHERE i.user_id = {ph} AND i.status = 'active'
    """, (user_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    best = None
    best_delta = 0
    
    for row in rows:
        cols = ['id', 'sku', 'name', 'brand', 'size', 'purchase_price', 'list_price', 'avg_price', 'price_trend']
        item = dict(zip(cols, row))
        
        if item['avg_price'] and item['purchase_price']:
            potential_profit = item['avg_price'] - item['purchase_price']
            if item['price_trend'] and item['price_trend'] > 0:
                potential_profit *= (1 + item['price_trend'] / 100)
            
            if potential_profit > best_delta:
                best_delta = potential_profit
                best = item
                best['potential_profit'] = potential_profit
    
    return best


def generate_claude_report(user_id, stale_buckets, market_trends, best_opportunity, settings):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ Anthropic API key not configured. Please set it in settings."
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        stale_count = sum(len(b) for b in stale_buckets.values())
        stale_summary = f"Total stale items: {stale_count}"
        if stale_buckets['90_plus']:
            stale_summary += f"\n- {len(stale_buckets['90_plus'])} items sitting 90+ days (URGENT)"
        if stale_buckets['90_days']:
            stale_summary += f"\n- {len(stale_buckets['90_days'])} items at 60-90 days"
        if stale_buckets['60_days']:
            stale_summary += f"\n- {len(stale_buckets['60_days'])} items at 30-60 days"
        
        trend_summary = "No market data available"
        if market_trends:
            up_trends = [t for t in market_trends if t.get('price_trend', 0) > 0]
            down_trends = [t for t in market_trends if t.get('price_trend', 0) < 0]
            trend_summary = f"{len(up_trends)} SKUs trending up, {len(down_trends)} trending down"
        
        opp_summary = "No clear opportunity identified"
        if best_opportunity:
            opp_summary = f"{best_opportunity.get('name', 'Unknown')} ({best_opportunity.get('sku', 'N/A')}) - Potential profit: ${best_opportunity.get('potential_profit', 0):.2f}"
        
        prompt = f"""You are a sneaker reselling expert writing a weekly inventory report for a reseller.

Generate a personalized, actionable weekly summary email. Be concise, friendly, and data-driven.

INVENTORY DATA:
{stale_summary}

MARKET TRENDS:
{trend_summary}

BEST OPPORTUNITY THIS WEEK:
{opp_summary}

Write the report in this format:
1. Opening greeting and quick week summary (2-3 sentences)
2. 🚨 Stale Inventory Alert (if any items need attention)
3. 📈 Market Trends (what's hot, what's not)
4. 💰 Best Opportunity (the #1 action to take this week)
5. Quick closing with motivation

Keep it under 300 words. Use emojis sparingly. Focus on actionable advice."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
    
    except Exception as e:
        return f"Error generating report: {str(e)}"


def create_email_html(report_content, user_name="Reseller"):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
            .content {{ background: #fff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; }}
            .footer {{ background: #f5f5f5; padding: 20px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 10px 10px; }}
            .cta-button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            pre {{ white-space: pre-wrap; font-family: inherit; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🍑 SoleOps Weekly Report</h1>
            <p>Week of {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        <div class="content">
            <pre>{report_content}</pre>
            <center>
                <a href="https://peachstatesavings.com" class="cta-button">View Full Dashboard →</a>
            </center>
        </div>
        <div class="footer">
            <p>You're receiving this because you opted in to SoleOps Weekly Reports.</p>
            <p><a href="https://peachstatesavings.com/pages/105_soleops_weekly_reseller_report">Manage preferences</a></p>
        </div>
    </body>
    </html>
    """
    return html


def send_email(to_email, subject, html_content):
    smtp_server = get_setting("smtp_server") or "smtp.gmail.com"
    smtp_port = int(get_setting("smtp_port") or 587)
    smtp_user = get_setting("smtp_user")
    smtp_password = get_setting("smtp_password")
    from_email = get_setting("smtp_from_email") or smtp_user
    
    if not smtp_user or not smtp_password:
        return False, "SMTP credentials not configured"
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        
        text_part = MIMEText(html_content, 'plain')
        html_part = MIMEText(html_content, 'html')
        msg.attach(text_part)
        msg.attach(html_part)
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, to_email, msg.as_string())
        
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)


def save_report(user_id, report_content, stale_count, best_opportunity, market_summary, email_sent=False):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    opp_text = json.dumps(best_opportunity) if best_opportunity else None
    
    if USE_POSTGRES:
        cur.execute(f"""
            INSERT INTO soleops_weekly_reports 
            (user_id, report_date, report_content, stale_inventory_count, best_opportunity, market_trend_summary, email_sent, email_sent_at)
            VALUES ({ph}, CURRENT_DATE, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            RETURNING id
        """, (user_id, report_content, stale_count, opp_text, market_summary, 
              email_sent, datetime.now() if email_sent else None))
        report_id = cur.fetchone()[0]
    else:
        cur.execute(f"""
            INSERT INTO soleops_weekly_reports 
            (user_id, report_date, report_content, stale_inventory_count, best_opportunity, market_trend_summary, email_sent, email_sent_at)
            VALUES ({ph}, DATE('now'), {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (user_id, report_content, stale_count, opp_text, market_summary,
              1 if email_sent else 0, datetime.now().isoformat() if email_sent else None))
        report_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return report_id


def get_report_history(user_id, limit=10):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT id, report_date, stale_inventory_count, email_sent, email_opened, created_at
        FROM soleops_weekly_reports 
        WHERE user_id = {ph}
        ORDER BY report_date DESC
        LIMIT {ph}
    """, (user_id, limit))
    
    rows = cur.fetchall()
    conn.close()
    
    cols = ['id', 'report_date', 'stale_inventory_count', 'email_sent', 'email_opened', 'created_at']
    return [dict(zip(cols, row)) for row in rows]


def get_report_by_id(report_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"SELECT * FROM soleops_weekly_reports WHERE id = {ph}", (report_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        cols = ['id', 'user_id', 'report_date', 'report_content', 'stale_inventory_count',
                'best_opportunity', 'market_trend_summary', 'email_sent', 'email_sent_at',
                'email_opened', 'email_opened_at', 'created_at']
        return dict(zip(cols, row))
    return None


_ensure_tables()

user_id = st.session_state.get("user_id", 1)

st.title("📧 SoleOps Weekly Reseller Report")
st.markdown("*Claude-generated weekly summaries covering stale inventory, market trends, and best opportunities*")

tab1, tab2, tab3, tab4 = st.tabs(["📝 Generate Report", "⚙️ Email Settings", "📊 Report History", "🔧 Cron Setup"])

with tab1:
    st.subheader("Generate Weekly Report")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        settings = get_user_email_settings(user_id) or {
            'include_stale_inventory': True,
            'include_market_trends': True,
            'include_opportunities': True,
            'stale_threshold_days': 30
        }
        
        stale_buckets = get_stale_inventory(user_id, settings.get('stale_threshold_days', 30))
        market_trends = get_market_trends(user_id)
        best_opportunity = get_best_opportunity(user_id)
        
        st.markdown("### 📊 Current Data Summary")
        
        total_stale = sum(len(b) for b in stale_buckets.values())
        
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Stale Items", total_stale, 
                     delta=f"+{len(stale_buckets['90_plus'])} urgent" if stale_buckets['90_plus'] else None,
                     delta_color="inverse")
        with m2:
            trending_up = len([t for t in market_trends if t.get('price_trend', 0) > 0])
            st.metric("SKUs Trending Up", trending_up)
        with m3:
            if best_opportunity:
                st.metric("Best Opportunity", f"${best_opportunity.get('potential_profit', 0):.0f}")
            else:
                st.metric("Best Opportunity", "N/A")
        
        st.markdown("---")
        
        if st.button("🤖 Generate Report with Claude", type="primary", use_container_width=True):
            with st.spinner("Generating personalized report..."):
                report = generate_claude_report(user_id, stale_buckets, market_trends, best_opportunity, settings)
                st.session_state['generated_report'] = report
                st.success("Report generated!")
        
        if 'generated_report' in st.session_state:
            st.markdown("### 📄 Generated Report Preview")
            st.markdown(st.session_state['generated_report'])
            
            email_settings = get_user_email_settings(user_id)
            
            col_send1, col_send2 = st.columns(2)
            with col_send1:
                if email_settings and email_settings.get('email_address'):
                    if st.button("📤 Send Email Now", use_container_width=True):
                        html = create_email_html(st.session_state['generated_report'])
                        success, msg = send_email(
                            email_settings['email_address'],
                            f"🍑 SoleOps Weekly Report - {datetime.now().strftime('%B %d')}",
                            html
                        )
                        if success:
                            save_report(
                                user_id,
                                st.session_state['generated_report'],
                                total_stale,
                                best_opportunity,
                                f"{len(market_trends)} SKUs tracked",
                                email_sent=True
                            )
                            st.success(f"✅ Email sent to {email_settings['email_address']}")
                        else:
                            st.error(f"❌ Failed to send: {msg}")
                else:
                    st.warning("⚠️ Configure your email in Settings tab first")
            
            with col_send2:
                if st.button("💾 Save Without Sending", use_container_width=True):
                    save_report(
                        user_id,
                        st.session_state['generated_report'],
                        total_stale,
                        best_opportunity,
                        f"{len(market_trends)} SKUs tracked",
                        email_sent=False
                    )
                    st.success("Report saved to history")
    
    with col2:
        st.markdown("### 📦 Stale Inventory Breakdown")
        
        if stale_buckets['90_plus']:
            with st.expander(f"🔴 90+ Days ({len(stale_buckets['90_plus'])} items)", expanded=True):
                for item in stale_buckets['90_plus'][:5]:
                    st.markdown(f"- **{item.get('name', 'Unknown')}** - {item.get('days_old', 0)} days")
        
        if stale_buckets['90_days']:
            with st.expander(f"🟠 60-90 Days ({len(stale_buckets['90_days'])} items)"):
                for item in stale_buckets['90_days'][:5]:
                    st.markdown(f"- **{item.get('name', 'Unknown')}** - {item.get('days_old', 0)} days")
        
        if stale_buckets['60_days']:
            with st.expander(f"🟡 30-60 Days ({len(stale_buckets['60_days'])} items)"):
                for item in stale_buckets['60_days'][:5]:
                    st.markdown(f"- **{item.get('name', 'Unknown')}** - {item.get('days_old', 0)} days")
        
        if not any(stale_buckets.values()):
            st.info("✨ No stale inventory! Great job keeping things moving.")

with tab2:
    st.subheader("⚙️ Email Settings")
    
    current_settings = get_user_email_settings(user_id) or {}
    
    with st.form("email_settings_form"):
        email = st.text_input("Email Address", value=current_settings.get('email_address', ''))
        
        weekly_enabled = st.checkbox("Enable Weekly Reports", 
                                     value=bool(current_settings.get('weekly_report_enabled', True)))
        
        col1, col