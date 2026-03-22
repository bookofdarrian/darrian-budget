import streamlit as st
import datetime
import json
from decimal import Decimal
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.set_page_config(page_title="SoleOps Stale Inventory Alerts", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS soleops_stale_inventory_config (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                threshold_warning INTEGER DEFAULT 30,
                threshold_stale INTEGER DEFAULT 60,
                threshold_critical INTEGER DEFAULT 90,
                auto_markdown_percent DECIMAL(5,2) DEFAULT 10.00,
                email_alerts_enabled BOOLEAN DEFAULT FALSE,
                email_frequency VARCHAR(20) DEFAULT 'weekly',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_stale_alerts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                inventory_id INTEGER NOT NULL,
                alert_type VARCHAR(20) NOT NULL,
                days_on_hand INTEGER NOT NULL,
                original_price DECIMAL(10,2),
                suggested_price DECIMAL(10,2),
                claude_recommendation TEXT,
                action_taken VARCHAR(50),
                action_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_stale_digest_log (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                items_count INTEGER,
                digest_content TEXT
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                sku VARCHAR(100),
                brand VARCHAR(100),
                model VARCHAR(200),
                colorway VARCHAR(200),
                size VARCHAR(20),
                condition VARCHAR(50),
                purchase_price DECIMAL(10,2),
                purchase_date DATE,
                list_price DECIMAL(10,2),
                listed_date DATE,
                platform VARCHAR(50),
                status VARCHAR(50) DEFAULT 'in_stock',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_stale_inventory_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                threshold_warning INTEGER DEFAULT 30,
                threshold_stale INTEGER DEFAULT 60,
                threshold_critical INTEGER DEFAULT 90,
                auto_markdown_percent REAL DEFAULT 10.00,
                email_alerts_enabled INTEGER DEFAULT 0,
                email_frequency TEXT DEFAULT 'weekly',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_stale_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                inventory_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                days_on_hand INTEGER NOT NULL,
                original_price REAL,
                suggested_price REAL,
                claude_recommendation TEXT,
                action_taken TEXT,
                action_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved INTEGER DEFAULT 0
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_stale_digest_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                items_count INTEGER,
                digest_content TEXT
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                sku TEXT,
                brand TEXT,
                model TEXT,
                colorway TEXT,
                size TEXT,
                condition TEXT,
                purchase_price REAL,
                purchase_date TEXT,
                list_price REAL,
                listed_date TEXT,
                platform TEXT,
                status TEXT DEFAULT 'in_stock',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

def get_user_config(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT * FROM soleops_stale_inventory_config WHERE user_id = {ph}", (user_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        cols = [desc[0] for desc in cur.description] if hasattr(cur, 'description') and cur.description else [
            'id', 'user_id', 'threshold_warning', 'threshold_stale', 'threshold_critical',
            'auto_markdown_percent', 'email_alerts_enabled', 'email_frequency', 'created_at', 'updated_at'
        ]
        return dict(zip(cols, row))
    return None

def save_user_config(user_id, warning, stale, critical, markdown_pct, email_enabled, email_freq):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    existing = get_user_config(user_id)
    
    if existing:
        if USE_POSTGRES:
            cur.execute(f"""
                UPDATE soleops_stale_inventory_config 
                SET threshold_warning = {ph}, threshold_stale = {ph}, threshold_critical = {ph},
                    auto_markdown_percent = {ph}, email_alerts_enabled = {ph}, email_frequency = {ph},
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = {ph}
            """, (warning, stale, critical, markdown_pct, email_enabled, email_freq, user_id))
        else:
            cur.execute(f"""
                UPDATE soleops_stale_inventory_config 
                SET threshold_warning = {ph}, threshold_stale = {ph}, threshold_critical = {ph},
                    auto_markdown_percent = {ph}, email_alerts_enabled = {ph}, email_frequency = {ph},
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = {ph}
            """, (warning, stale, critical, markdown_pct, 1 if email_enabled else 0, email_freq, user_id))
    else:
        if USE_POSTGRES:
            cur.execute(f"""
                INSERT INTO soleops_stale_inventory_config 
                (user_id, threshold_warning, threshold_stale, threshold_critical, auto_markdown_percent, email_alerts_enabled, email_frequency)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (user_id, warning, stale, critical, markdown_pct, email_enabled, email_freq))
        else:
            cur.execute(f"""
                INSERT INTO soleops_stale_inventory_config 
                (user_id, threshold_warning, threshold_stale, threshold_critical, auto_markdown_percent, email_alerts_enabled, email_frequency)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (user_id, warning, stale, critical, markdown_pct, 1 if email_enabled else 0, email_freq))
    
    conn.commit()
    conn.close()

def calculate_days_on_hand(listed_date):
    if not listed_date:
        return 0
    
    if isinstance(listed_date, str):
        try:
            listed_date = datetime.datetime.strptime(listed_date, "%Y-%m-%d").date()
        except ValueError:
            return 0
    elif isinstance(listed_date, datetime.datetime):
        listed_date = listed_date.date()
    
    today = datetime.date.today()
    delta = today - listed_date
    return max(0, delta.days)

def get_inventory_with_age(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT id, sku, brand, model, colorway, size, condition, purchase_price, 
               purchase_date, list_price, listed_date, platform, status, notes
        FROM soleops_inventory 
        WHERE user_id = {ph} AND status IN ('in_stock', 'listed', 'active')
        ORDER BY listed_date ASC
    """, (user_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    items = []
    for row in rows:
        item = {
            'id': row[0],
            'sku': row[1],
            'brand': row[2],
            'model': row[3],
            'colorway': row[4],
            'size': row[5],
            'condition': row[6],
            'purchase_price': float(row[7]) if row[7] else 0,
            'purchase_date': row[8],
            'list_price': float(row[9]) if row[9] else 0,
            'listed_date': row[10],
            'platform': row[11],
            'status': row[12],
            'notes': row[13],
            'days_on_hand': calculate_days_on_hand(row[10])
        }
        items.append(item)
    
    return items

def categorize_by_age(items, config):
    warning_threshold = config.get('threshold_warning', 30) if config else 30
    stale_threshold = config.get('threshold_stale', 60) if config else 60
    critical_threshold = config.get('threshold_critical', 90) if config else 90
    
    categories = {
        'fresh': [],
        'warning': [],
        'stale': [],
        'critical': []
    }
    
    for item in items:
        days = item['days_on_hand']
        if days >= critical_threshold:
            categories['critical'].append(item)
        elif days >= stale_threshold:
            categories['stale'].append(item)
        elif days >= warning_threshold:
            categories['warning'].append(item)
        else:
            categories['fresh'].append(item)
    
    return categories

def get_market_price_estimate(item):
    base_price = item.get('list_price', 100)
    days = item.get('days_on_hand', 0)
    
    if days > 90:
        adjustment = 0.75
    elif days > 60:
        adjustment = 0.85
    elif days > 30:
        adjustment = 0.92
    else:
        adjustment = 1.0
    
    ebay_estimate = base_price * adjustment * 0.98
    mercari_estimate = base_price * adjustment * 0.95
    
    return {
        'ebay': round(ebay_estimate, 2),
        'mercari': round(mercari_estimate, 2),
        'avg': round((ebay_estimate + mercari_estimate) / 2, 2)
    }

def get_claude_recommendation(item, market_prices):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return generate_fallback_recommendation(item, market_prices)
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""You are a sneaker resale expert. Analyze this stale inventory item and provide a markdown strategy.

Item Details:
- Brand/Model: {item.get('brand', 'Unknown')} {item.get('model', 'Unknown')}
- Colorway: {item.get('colorway', 'N/A')}
- Size: {item.get('size', 'N/A')}
- Condition: {item.get('condition', 'N/A')}
- Days Listed: {item.get('days_on_hand', 0)} days
- Current List Price: ${item.get('list_price', 0):.2f}
- Purchase Price: ${item.get('purchase_price', 0):.2f}
- Platform: {item.get('platform', 'Unknown')}

Market Estimates:
- eBay Current Market: ${market_prices['ebay']:.2f}
- Mercari Current Market: ${market_prices['mercari']:.2f}

Provide a brief, actionable recommendation (3-4 sentences) including:
1. Recommended price adjustment percentage
2. Which platform to prioritize
3. Specific action to take this week
4. Expected timeline to sell

Keep response under 150 words and be direct."""

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
    except Exception as e:
        return generate_fallback_recommendation(item, market_prices)

def generate_fallback_recommendation(item, market_prices):
    days = item.get('days_on_hand', 0)
    list_price = item.get('list_price', 0)
    purchase_price = item.get('purchase_price', 0)
    
    if days > 90:
        pct = 20
        urgency = "CRITICAL"
        action = "Immediate markdown required"
    elif days > 60:
        pct = 15
        urgency = "HIGH"
        action = "Consider cross-listing and markdown"
    elif days > 30:
        pct = 10
        urgency = "MODERATE"
        action = "Refresh listing and consider small price drop"
    else:
        pct = 5
        urgency = "LOW"
        action = "Monitor and refresh listing photos"
    
    suggested_price = list_price * (1 - pct / 100)
    profit = suggested_price - purchase_price
    
    recommendation = f"""**{urgency} Priority** - {days} days on hand

**Recommended Action:** {action}

**Suggested Price:** ${suggested_price:.2f} ({pct}% markdown)
- eBay Market: ${market_prices['ebay']:.2f}
- Mercari Market: ${market_prices['mercari']:.2f}

**Projected Profit at New Price:** ${profit:.2f}

**This Week:** Cross-list on {'Mercari' if item.get('platform') == 'eBay' else 'eBay'} at ${market_prices['avg']:.2f}"""
    
    return recommendation

def save_alert(user_id, item, alert_type, recommendation, suggested_price):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT id FROM soleops_stale_alerts 
        WHERE user_id = {ph} AND inventory_id = {ph} AND resolved = {ph}
    """, (user_id, item['id'], False if USE_POSTGRES else 0))
    
    existing = cur.fetchone()
    
    if not existing:
        cur.execute(f"""
            INSERT INTO soleops_stale_alerts 
            (user_id, inventory_id, alert_type, days_on_hand, original_price, suggested_price, claude_recommendation)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (user_id, item['id'], alert_type, item['days_on_hand'], item['list_price'], suggested_price, recommendation))
    
    conn.commit()
    conn.close()

def mark_action_taken(alert_id, action):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    if USE_POSTGRES:
        cur.execute(f"""
            UPDATE soleops_stale_alerts 
            SET action_taken = {ph}, action_date = CURRENT_TIMESTAMP, resolved = TRUE
            WHERE id = {ph}
        """, (action, alert_id))
    else:
        cur.execute(f"""
            UPDATE soleops_stale_alerts 
            SET action_taken = {ph}, action_date = CURRENT_TIMESTAMP, resolved = 1
            WHERE id = {ph}
        """, (action, alert_id))
    
    conn.commit()
    conn.close()

def update_inventory_price(inventory_id, new_price):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        UPDATE soleops_inventory SET list_price = {ph} WHERE id = {ph}
    """, (new_price, inventory_id))
    
    conn.commit()
    conn.close()

def get_active_alerts(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT id, inventory_id, alert_type, days_on_hand, original_price, 
               suggested_price, claude_recommendation, created_at
        FROM soleops_stale_alerts 
        WHERE user_id = {ph} AND resolved = {ph}
        ORDER BY days_on_hand DESC
    """, (user_id, False if USE_POSTGRES else 0))
    
    rows = cur.fetchall()
    conn.close()
    
    alerts = []
    for row in rows:
        alerts.append({
            'id': row[0],
            'inventory_id': row[1],
            'alert_type': row[2],
            'days_on_hand': row[3],
            'original_price': float(row[4]) if row[4] else 0,
            'suggested_price': float(row[5]) if row[5] else 0,
            'recommendation': row[6],
            'created_at': row[7]
        })
    
    return alerts

def generate_digest_email(user_id, stale_items):
    if not stale_items:
        return None
    
    total_value = sum(item.get('list_price', 0) for item in stale_items)
    critical_count = len([i for i in stale_items if i['days_on_hand'] >= 90])
    stale_count = len([i for i in stale_items if 60 <= i['days_on_hand'] < 90])
    warning_count = len([i for i in stale_items if 30 <= i['days_on_hand'] < 60])
    
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background: linear-gradient(135deg, #ff6b6b, #ff8e53); color: white; padding: 20px; border-radius: 10px; }}
            .stat-box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0; }}
            .critical {{ border-left: 4px solid #dc3545; }}
            .stale {{ border-left: 4px solid #ffc107; }}
            .warning {{ border-left: 4px solid #17a2b8; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; }}
            .action-btn {{ background: #ff6b6b; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚨 Weekly Stale Inventory Report</h1>
            <p>You have {len(stale_items)} items that need attention</p>
        </div>
        
        <div class="stat-box critical">
            <h3>🔴 Critical ({critical_count} items)</h3>
            <p>90+ days - Immediate action required</p>
        </div>
        
        <div class="stat-box stale">
            <h3>🟡 Stale ({stale_count} items)</h3>
            <p>60-89 days - Consider markdown</p>
        </div>
        
        <div class="stat-box warning">
            <h3>🔵 Warning ({warning_count} items)</h3>
            <p>30-59 days - Monitor closely</p>
        </div>
        
        <h2>Total Value at Risk: ${total_value:,.2f}</h2>
        
        <table>
            <tr>
                <th>Item</th>
                <th>Days Listed</th>
                <th>Current Price</th>
                <th>Suggested Price</th>
            </tr>
    """
    
    for item in sorted(stale_items, key=lambda x: x['days_on_hand'], reverse=True)[:10]:
        market = get_market_price_estimate(item)
        html_content += f"""
            <tr>
                <td>{item.get('brand', '')} {item.get('model', '')}<br><small>{item.get('size', '')}</small></td>
                <td>{item['days_on_hand']} days</td>
                <td>${item.get('list_price', 0):,.2f}</td>
                <td>${market['avg']:,.2f}</td>
            </tr>
        """
    
    html_content += """
        </table>
        
        <p style="text-align: center; margin-top: 30px;">
            <a href="https://peachstatesavings.com" class="action-btn">View Full Dashboard</a>
        </p>
        
        <p style="color: #666; font-size: 12px; margin-top: 40px;">
            This is an automated report from SoleOps Stale Inventory Alert System.<br>
            Manage your alert preferences in the SoleOps dashboard.
        </p>
    </body>
    </html>
    """
    
    return html_content

def send_digest_email(user_email, html_content):
    smtp_user = get_setting("smtp_user")
    smtp_pass = get_setting("smtp_password")
    
    if not smtp_user or not smtp_pass:
        return False, "SMTP credentials not configured"
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🚨 SoleOps Weekly Stale Inventory Report - {datetime.date.today().strftime('%B %d, %Y')}"
        msg['From'] = smtp_user
        msg['To'] = user_email
        
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)

def log_digest_sent(user_id, items_count, content):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        INSERT INTO soleops_stale_digest_log (user_id, items_count, digest_content)
        VALUES ({ph}, {ph}, {ph})
    """, (user_id, items_count, content[:5000]))
    
    conn.commit()
    conn.close()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

st.title("🚨 SoleOps Stale Inventory Alerts")
st.markdown("*Flag sneaker pairs sitting unsold and get AI-powered markdown strategies*")

user_id = st.session_state.get("user_id", 1)

config = get_user_config(user_id)
if not config:
    config = {
        'threshold_warning': 30,
        'threshold_stale': 60,
        'threshold_critical': 90,
        'auto_markdown_percent': 10.0,
        'email_alerts_enabled': False,
        'email_frequency': 'weekly'
    }

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "⚙️ Settings", "🤖 AI Recommendations", "📧 Email Digest", "📈 Analytics"])

with tab1:
    st.subheader("Stale Inventory Dashboard")
    
    inventory = get_inventory_with_age(user_id)
    
    if not inventory:
        st.info("📦 No inventory items found. Add items to your SoleOps inventory to start tracking stale items.")
        
        st.markdown("### Quick Add Sample Data")
        if st.button("➕ Add Sample Inventory Items"):
            conn = get_conn()
            cur = conn.cursor()
            ph = "%s" if USE_POSTGRES else "?"
            
            sample_items = [
                ('AJ1-001', 'Nike', 'Air Jordan 1 Retro High OG', 'Chicago', '10', 'New', 150, '2024-01-15', 280, '2024-01-20', 'eBay', 'listed'),
                ('YZY-001', 'Adidas', 'Yeezy Boost 350 V2', 'Zebra', '9.5', 'New', 220, '2024-02-01', 320, '2024-02-05', 'eBay', 'listed'),
                ('NB-001', 'New Balance', '550', 'White Green', '11', 'New', 110, '2023-12-01', 180, '2023-12-10', 'Mercari', 'listed'),
                ('DUNK-001', 'Nike', 'Dunk Low', 'Panda', '10.5', 'Used', 90, '2023-11-15', 150, '2023-11-20', 'eBay', 'listed'),
                ('AF1-001', 'Nike', 'Air Force 1 Low', 'White', '12', 'New', 90, '2023-10-01', 120, '2023-10-05', 'Mercari', 'listed'),
            ]
            
            for item in sample_items:
                cur.execute(f"""
                    INSERT INTO soleops_inventory 
                    (user_id, sku, brand, model, colorway, size, condition, purchase_price, purchase_date, list_price, listed_date, platform, status)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                """, (user_id, *item))
            
            conn.commit()
            conn.close()
            st.success("✅ Added 5 sample inventory items!")
            st.rerun()
    else:
        categories = categorize_by_age(inventory, config)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            fresh_value = sum(i['list_price'] for i in categories['fresh'])
            st.metric(
                "🟢 Fresh",
                f"{len(categories['fresh'])} items",
                f"${fresh_value:,.0f}",
                delta_color="normal"
            )
        
        with col2:
            warning_value = sum(i['list_price'] for i in categories['warning'])
            st.metric(
                "🔵 Warning",
                f"{len(categories['warning'])} items",
                f"${warning_value:,.0f}",
                delta_color="off"
            )
        
        with col3:
            stale_value = sum(i['list_price'] for i in categories['stale'])
            st.metric(
                "🟡 Stale",
                f"{len(categories['stale'])} items",
                f"-${stale_value:,.0f}" if stale_value > 0 else "$0",
                delta_color="inverse"
            )
        
        with col4:
            critical_value = sum(i['list_price'] for i in categories['critical'])
            st.metric(
                "🔴 Critical",
                f"{len(categories['critical'])} items",
                f"-${critical_value:,.0f}" if critical_value > 0 else "$0",
                delta_color="inverse"
            )
        
        st.markdown("---")
        
        if categories['critical']:
            st.markdown("### 🔴 Critical Items (90+ days)")
            st.warning(f"⚠️ You have {len(categories['critical'])} items that have been listed for over 90 days!")
            
            for item in categories['critical']:
                with st.expander(f"🔴 {item['brand']} {item['model']} - Size {item['size']} ({item['days_on_hand']} days)"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**SKU:** {item['sku']}")
                        st.write(f"**Colorway:** {item['colorway']}")
                        st