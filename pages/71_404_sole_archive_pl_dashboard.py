import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from decimal import Decimal
import json
import csv
import io

st.set_page_config(page_title="404 Sole Archive P&L Dashboard", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sole_archive_inventory (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(100) NOT NULL,
                brand VARCHAR(100),
                model VARCHAR(255) NOT NULL,
                colorway VARCHAR(255),
                size VARCHAR(20),
                condition VARCHAR(50) DEFAULT 'New',
                purchase_price DECIMAL(10,2) NOT NULL,
                purchase_date DATE,
                purchase_source VARCHAR(255),
                shipping_to_me DECIMAL(10,2) DEFAULT 0,
                authentication_fee DECIMAL(10,2) DEFAULT 0,
                supplies_cost DECIMAL(10,2) DEFAULT 0,
                other_costs DECIMAL(10,2) DEFAULT 0,
                cost_notes TEXT,
                status VARCHAR(50) DEFAULT 'In Stock',
                listed_platforms TEXT,
                listed_date DATE,
                image_url TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sole_archive_sales (
                id SERIAL PRIMARY KEY,
                inventory_id INTEGER REFERENCES sole_archive_inventory(id),
                sale_date DATE NOT NULL,
                platform VARCHAR(50) NOT NULL,
                sale_price DECIMAL(10,2) NOT NULL,
                shipping_cost DECIMAL(10,2) DEFAULT 0,
                platform_fee_pct DECIMAL(5,2),
                platform_fee_amt DECIMAL(10,2),
                payment_processing_fee DECIMAL(10,2) DEFAULT 0,
                other_fees DECIMAL(10,2) DEFAULT 0,
                fee_notes TEXT,
                buyer_location VARCHAR(255),
                tracking_number VARCHAR(255),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sole_archive_platform_fees (
                id SERIAL PRIMARY KEY,
                platform VARCHAR(50) NOT NULL UNIQUE,
                base_fee_pct DECIMAL(5,2) NOT NULL,
                payment_processing_pct DECIMAL(5,2) DEFAULT 0,
                flat_fee DECIMAL(10,2) DEFAULT 0,
                seller_level VARCHAR(50),
                notes TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sole_archive_expenses (
                id SERIAL PRIMARY KEY,
                expense_date DATE NOT NULL,
                category VARCHAR(100) NOT NULL,
                description TEXT,
                amount DECIMAL(10,2) NOT NULL,
                receipt_url TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sole_archive_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                brand TEXT,
                model TEXT NOT NULL,
                colorway TEXT,
                size TEXT,
                condition TEXT DEFAULT 'New',
                purchase_price REAL NOT NULL,
                purchase_date TEXT,
                purchase_source TEXT,
                shipping_to_me REAL DEFAULT 0,
                authentication_fee REAL DEFAULT 0,
                supplies_cost REAL DEFAULT 0,
                other_costs REAL DEFAULT 0,
                cost_notes TEXT,
                status TEXT DEFAULT 'In Stock',
                listed_platforms TEXT,
                listed_date TEXT,
                image_url TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sole_archive_sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER,
                sale_date TEXT NOT NULL,
                platform TEXT NOT NULL,
                sale_price REAL NOT NULL,
                shipping_cost REAL DEFAULT 0,
                platform_fee_pct REAL,
                platform_fee_amt REAL,
                payment_processing_fee REAL DEFAULT 0,
                other_fees REAL DEFAULT 0,
                fee_notes TEXT,
                buyer_location TEXT,
                tracking_number TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inventory_id) REFERENCES sole_archive_inventory(id)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sole_archive_platform_fees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL UNIQUE,
                base_fee_pct REAL NOT NULL,
                payment_processing_pct REAL DEFAULT 0,
                flat_fee REAL DEFAULT 0,
                seller_level TEXT,
                notes TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sole_archive_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL,
                receipt_url TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    
    default_fees = [
        ('eBay', 13.25, 0, 0.30, 'Standard', 'Final value fee + $0.30 per order'),
        ('Mercari', 10.0, 0, 0, 'Standard', 'Flat 10% seller fee'),
        ('StockX', 9.5, 3.0, 0, 'Level 1', '9-10% transaction fee + 3% payment processing'),
        ('GOAT', 9.5, 2.9, 0, 'Standard', '9.5% commission + 2.9% cash out fee'),
        ('Depop', 10.0, 0, 0, 'Standard', '10% flat fee'),
        ('Poshmark', 20.0, 0, 0, 'Standard', '20% for sales over $15'),
        ('Local/Cash', 0, 0, 0, 'N/A', 'No fees for local sales'),
        ('Consignment', 15.0, 0, 0, 'Standard', 'Average consignment fee'),
    ]
    
    ph = "%s" if USE_POSTGRES else "?"
    for pf in default_fees:
        try:
            if USE_POSTGRES:
                cur.execute(f"""
                    INSERT INTO sole_archive_platform_fees (platform, base_fee_pct, payment_processing_pct, flat_fee, seller_level, notes)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                    ON CONFLICT (platform) DO NOTHING
                """, pf)
            else:
                cur.execute(f"""
                    INSERT OR IGNORE INTO sole_archive_platform_fees (platform, base_fee_pct, payment_processing_pct, flat_fee, seller_level, notes)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                """, pf)
        except:
            pass
    
    conn.commit()
    conn.close()

_ensure_tables()

def get_platform_fees():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT platform, base_fee_pct, payment_processing_pct, flat_fee FROM sole_archive_platform_fees")
    rows = cur.fetchall()
    conn.close()
    return {row[0]: {'base': float(row[1]), 'processing': float(row[2]), 'flat': float(row[3])} for row in rows}

def calculate_platform_fee(sale_price, platform, platform_fees):
    if platform not in platform_fees:
        return 0, 0
    fees = platform_fees[platform]
    base_fee = sale_price * (fees['base'] / 100)
    processing_fee = sale_price * (fees['processing'] / 100) + fees['flat']
    return base_fee, processing_fee

def calculate_cogs(item):
    return float(item['purchase_price'] or 0) + float(item['shipping_to_me'] or 0) + float(item['authentication_fee'] or 0) + float(item['supplies_cost'] or 0) + float(item['other_costs'] or 0)

def calculate_profit_metrics(sale_price, cogs, platform_fee, processing_fee, shipping_cost, other_fees=0):
    total_fees = platform_fee + processing_fee + shipping_cost + other_fees
    gross_profit = sale_price - cogs
    net_profit = sale_price - cogs - total_fees
    margin_pct = (net_profit / sale_price * 100) if sale_price > 0 else 0
    roi = (net_profit / cogs * 100) if cogs > 0 else 0
    return {
        'gross_profit': gross_profit,
        'net_profit': net_profit,
        'total_fees': total_fees,
        'margin_pct': margin_pct,
        'roi': roi
    }

def get_inventory_items(status_filter=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    if status_filter:
        cur.execute(f"SELECT * FROM sole_archive_inventory WHERE status = {ph} ORDER BY created_at DESC", (status_filter,))
    else:
        cur.execute("SELECT * FROM sole_archive_inventory ORDER BY created_at DESC")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

def get_sales(start_date=None, end_date=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    query = """
        SELECT s.*, i.sku, i.brand, i.model, i.colorway, i.size, i.purchase_price,
               i.shipping_to_me, i.authentication_fee, i.supplies_cost, i.other_costs
        FROM sole_archive_sales s
        LEFT JOIN sole_archive_inventory i ON s.inventory_id = i.id
        WHERE 1=1
    """
    params = []
    
    if start_date:
        query += f" AND s.sale_date >= {ph}"
        params.append(str(start_date))
    if end_date:
        query += f" AND s.sale_date <= {ph}"
        params.append(str(end_date))
    
    query += " ORDER BY s.sale_date DESC"
    
    cur.execute(query, params)
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

def add_inventory_item(data):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        INSERT INTO sole_archive_inventory (sku, brand, model, colorway, size, condition, purchase_price, purchase_date, purchase_source, shipping_to_me, authentication_fee, supplies_cost, other_costs, cost_notes, status, listed_platforms, listed_date, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (data['sku'], data['brand'], data['model'], data['colorway'], data['size'], data['condition'], data['purchase_price'], data['purchase_date'], data['purchase_source'], data['shipping_to_me'], data['authentication_fee'], data['supplies_cost'], data['other_costs'], data['cost_notes'], data['status'], data['listed_platforms'], data['listed_date'], data['notes']))
    
    conn.commit()
    conn.close()

def add_sale(data):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        INSERT INTO sole_archive_sales (inventory_id, sale_date, platform, sale_price, shipping_cost, platform_fee_pct, platform_fee_amt, payment_processing_fee, other_fees, fee_notes, buyer_location, tracking_number, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (data['inventory_id'], data['sale_date'], data['platform'], data['sale_price'], data['shipping_cost'], data['platform_fee_pct'], data['platform_fee_amt'], data['payment_processing_fee'], data['other_fees'], data['fee_notes'], data['buyer_location'], data['tracking_number'], data['notes']))
    
    cur.execute(f"UPDATE sole_archive_inventory SET status = 'Sold' WHERE id = {ph}", (data['inventory_id'],))
    
    conn.commit()
    conn.close()

def delete_inventory_item(item_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM sole_archive_inventory WHERE id = {ph}", (item_id,))
    conn.commit()
    conn.close()

def delete_sale(sale_id, inventory_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM sole_archive_sales WHERE id = {ph}", (sale_id,))
    cur.execute(f"UPDATE sole_archive_inventory SET status = 'In Stock' WHERE id = {ph}", (inventory_id,))
    conn.commit()
    conn.close()

def get_ai_insights(sales_data, inventory_data):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "Configure your Anthropic API key in settings to enable AI insights."
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        total_revenue = sum(float(s['sale_price'] or 0) for s in sales_data)
        total_profit = 0
        platform_profits = {}
        brand_profits = {}
        
        for sale in sales_data:
            cogs = float(sale['purchase_price'] or 0) + float(sale['shipping_to_me'] or 0) + float(sale['authentication_fee'] or 0) + float(sale['supplies_cost'] or 0) + float(sale['other_costs'] or 0)
            fees = float(sale['platform_fee_amt'] or 0) + float(sale['payment_processing_fee'] or 0) + float(sale['shipping_cost'] or 0) + float(sale['other_fees'] or 0)
            profit = float(sale['sale_price'] or 0) - cogs - fees
            total_profit += profit
            
            platform = sale['platform']
            if platform not in platform_profits:
                platform_profits[platform] = {'profit': 0, 'count': 0}
            platform_profits[platform]['profit'] += profit
            platform_profits[platform]['count'] += 1
            
            brand = sale.get('brand', 'Unknown')
            if brand not in brand_profits:
                brand_profits[brand] = {'profit': 0, 'count': 0}
            brand_profits[brand]['profit'] += profit
            brand_profits[brand]['count'] += 1
        
        in_stock_count = len([i for i in inventory_data if i['status'] == 'In Stock'])
        in_stock_value = sum(calculate_cogs(i) for i in inventory_data if i['status'] == 'In Stock')
        
        context = f"""
        404 Sole Archive P&L Summary:
        - Total Sales: {len(sales_data)}
        - Total Revenue: ${total_revenue:,.2f}
        - Total Net Profit: ${total_profit:,.2f}
        - Average Margin: {(total_profit/total_revenue*100) if total_revenue > 0 else 0:.1f}%
        - Current Inventory: {in_stock_count} pairs worth ${in_stock_value:,.2f} in COGS
        
        Platform Performance:
        {json.dumps(platform_profits, indent=2)}
        
        Brand Performance:
        {json.dumps(brand_profits, indent=2)}
        """
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": f"""You are a sneaker reselling business analyst for 404 Sole Archive. Analyze this P&L data and provide actionable insights:

{context}

Provide 3-5 specific, actionable recommendations for:
1. Pricing strategy optimization
2. Platform selection (which platforms are most profitable)
3. Inventory management (what to stock more/less of)
4. Fee reduction strategies
5. Growth opportunities

Keep it concise and focused on maximizing profit margins."""}
            ]
        )
        
        return message.content[0].text
    except Exception as e:
        return f"Error generating AI insights: {str(e)}"

st.title("👟 404 Sole Archive P&L Dashboard")
st.markdown("*Track profits, analyze margins, and optimize your sneaker reselling business*")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Dashboard", "📦 Inventory", "💰 Record Sale", "📈 Analytics", "🤖 AI Insights", "⚙️ Settings"])

with tab1:
    st.subheader("📊 Profit & Loss Overview")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        period = st.selectbox("Time Period", ["MTD", "QTD", "YTD", "All Time", "Custom"])
    
    today = date.today()
    if period == "MTD":
        start_date = today.replace(day=1)
        end_date = today
    elif period == "QTD":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start_date = today.replace(month=quarter_start_month, day=1)
        end_date = today
    elif period == "YTD":
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif period == "All Time":
        start_date = None
        end_date = None
    else:
        with col2:
            start_date = st.date_input("Start Date", today - timedelta(days=30))
        with col3:
            end_date = st.date_input("End Date", today)
    
    sales_data = get_sales(start_date, end_date)
    inventory_data = get_inventory_items()
    platform_fees = get_platform_fees()
    
    total_revenue = 0
    total_cogs = 0
    total_fees = 0
    total_shipping = 0
    sales_with_metrics = []
    
    for sale in sales_data:
        sale_price = float(sale['sale_price'] or 0)
        cogs = float(sale['purchase_price'] or 0) + float(sale['shipping_to_me'] or 0) + float(sale['authentication_fee'] or 0) + float(sale['supplies_cost'] or 0) + float(sale['other_costs'] or 0)
        platform_fee = float(sale['platform_fee_amt'] or 0)
        processing_fee = float(sale['payment_processing_fee'] or 0)
        shipping = float(sale['shipping_cost'] or 0)
        other_fees = float(sale['other_fees'] or 0)
        
        total_revenue += sale_price
        total_cogs += cogs
        total_fees += platform_fee + processing_fee + other_fees
        total_shipping += shipping
        
        metrics = calculate_profit_metrics(sale_price, cogs, platform_fee, processing_fee, shipping, other_fees)
        sale_with_metrics = {**sale, **metrics, 'cogs': cogs}
        sales_with_metrics.append(sale_with_metrics)
    
    total_gross_profit = total_revenue - total_cogs
    total_net_profit = total_revenue - total_cogs - total_fees - total_shipping
    avg_margin = (total_net_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Revenue", f"${total_revenue:,.2f}", f"{len(sales_data)} sales")
    with col2:
        st.metric("Total COGS", f"${total_cogs:,.2f}")
    with col3:
        st.metric("Total Fees", f"${total_fees + total_shipping:,.2f}")
    with col4:
        delta_color = "normal" if total_net_profit >= 0 else "inverse"
        st.metric("Net Profit", f"${total_net_profit:,.2f}", f"{avg_margin:.1f}% margin", delta_color=delta_color)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💵 P&L Breakdown")
        
        if total_revenue > 0:
            fig = go.Figure(go.Waterfall(
                name="P&L",
                orientation="v",
                measure=["absolute", "relative", "relative", "relative", "total"],
                x=["Revenue", "COGS", "Platform Fees", "Shipping", "Net Profit"],
                y=[total_revenue, -total_cogs, -total_fees, -total_shipping, total_net_profit],
                textposition="outside",
                text=[f"${total_revenue:,.0f}", f"-${total_cogs:,.0f}", f"-${total_fees:,.0f}", f"-${total_shipping:,.0f}", f"${total_net_profit:,.0f}"],
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                increasing={"marker": {"color": "#2ecc71"}},
                decreasing={"marker": {"color": "#e74c3c"}},
                totals={"marker": {"color": "#3498db"}}
            ))
            fig.update_layout(title="Profit Waterfall", showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sales data for the selected period")
    
    with col2:
        st.subheader("📊 Profit by Platform")
        
        if sales_with_metrics:
            platform_df = pd.DataFrame(sales_with_metrics)
            platform_summary = platform_df.groupby('platform').agg({
                'net_profit': 'sum',
                'sale_price': 'sum',
                'id': 'count'
            }).reset_index()
            platform_summary.columns = ['Platform', 'Net Profit', 'Revenue', 'Sales Count']
            platform_summary['Avg Margin'] = (platform_summary['Net Profit'] / platform_summary['Revenue'] * 100).round(1)
            
            fig = px.bar(platform_summary, x='Platform', y='Net Profit', color='Net Profit',
                        color_continuous_scale=['#e74c3c', '#f39c12', '#2ecc71'],
                        text='Net Profit')
            fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
            fig.update_layout(title="Net Profit by Platform", showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sales data for the selected period")
    
    st.markdown("---")
    st.subheader("📋 Recent Sales")
    
    if sales_with_metrics:
        low_margin_threshold = 15
        
        for sale in sales_with_metrics[:10]:
            with st.expander(f"**{sale.get('brand', '')} {sale.get('model', '')}** - {sale.get('size', '')} | ${sale['net_profit']:.2f} profit ({sale['margin_pct']:.1f}%)"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**Sale Details**")
                    st.write(f"- Date: {sale['sale_date']}")
                    st.write(f"- Platform: {sale['platform']}")
                    st.write(f"- Sale Price: ${float(sale['sale_price']):,.2f}")
                
                with col2:
                    st.write("**Costs**")
                    st.write(f"- COGS: ${sale['cogs']:,.2f}")
                    st.write(f"- Platform Fee: ${float(sale['platform_fee_amt'] or 0):,.2f}")
                    st.write(f"- Shipping: ${float(sale['shipping_cost'] or 0):,.2f}")
                
                with col3:
                    st.write("**Profit Metrics**")
                    st.write(f"- Gross Profit: ${sale['gross_profit']:,.2f}")
                    st.write(f"- Net Profit: ${sale['net_profit']:,.2f}")
                    st.write(f"- ROI: {sale['roi']:.1f}%")
                
                if sale['margin_pct'] < low_margin_threshold:
                    st.warning(f"⚠️ Low margin alert: {sale['margin_pct']:.1f}% is below {low_margin_threshold}% threshold")
    else:
        st.info("No sales recorded yet. Add inventory and record sales to see your P&L.")

with tab2:
    st.subheader("📦 Inventory Management")
    
    inv_tab1, inv_tab2 = st.tabs(["View Inventory", "Add New Item"])
    
    with inv_tab1:
        status_filter = st.selectbox("Filter by Status", ["All", "In Stock", "Listed", "Sold", "Consigned"])
        
        if status_filter == "All":
            items = get_inventory_items()
        else:
            items = get_inventory_items(status_filter)
        
        if items:
            for item in items:
                cogs = calculate_cogs(item)
                status_emoji = {"In Stock": "📦", "Listed": "🏷️", "Sold": "✅", "Consigned": "🤝"}.get(item['status'], "❓")
                
                with st.expander(f"{status_emoji} **{item.get('brand', '')} {item['model']}** - Size {item.get('size', 'N/A')} | COGS: ${cogs:,.2f}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**Item Details**")
                        st.write(f"- SKU: {item['sku']}")
                        st.write(f"- Colorway: {item.get('colorway', 'N/A')}")
                        st.write(f"- Condition: {item.get('condition', 'N/A')}")
                        st.write(f"- Status: {item['status']}")
                    
                    with col2:
                        st.write("**Cost Breakdown**")
                        st.write(f"- Purchase Price: ${float(item['purchase_price']):,.2f}")
                        st.write(f"- Shipping to Me: ${float(item.get('shipping_to_me') or 0):,.2f}")
                        st.write(f"- Auth Fee: ${float(item.get('authentication_fee') or 0):,.2f}")
                        st.write(f"- Supplies: ${float(item.get('supplies_cost') or 0):,.2f}")
                        st.write(f"- **Total COGS: ${cogs:,.2f}**")
                    
                    with col3:
                        st.write("**Purchase Info**")
                        st.write(f"- Date: {item.get('purchase_date', 'N/A')}")
                        st.write(f"- Source: {item.get('purchase_source', 'N/A')}")
                        if item.get('listed_platforms'):
                            st.write(f"- Listed On: {item['listed_platforms']}")
                    
                    if item['status'] != 'Sold':
                        if st.button(f"🗑️ Delete Item", key=f"del_inv_{item['id']}"):
                            delete_inventory_item(item['id'])
                            st.success("Item deleted!")
                            st.rerun()
        else:
            st.info("No inventory items found. Add your first sneaker!")
    
    with inv_tab2:
        st.write("### Add New Inventory Item")
        
        with st.form("add_inventory_form"):
            col1, col2 = st.columns