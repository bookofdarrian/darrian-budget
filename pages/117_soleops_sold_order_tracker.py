import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from decimal import Decimal
import json
import io
import csv

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Sold Order Tracker", page_icon="🍑", layout="wide")
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

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sold_orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                order_id VARCHAR(100),
                sku VARCHAR(100),
                shoe_name VARCHAR(255) NOT NULL,
                size VARCHAR(20),
                sale_price DECIMAL(10,2) NOT NULL,
                platform_fees DECIMAL(10,2) DEFAULT 0,
                shipping_cost DECIMAL(10,2) DEFAULT 0,
                cogs DECIMAL(10,2) DEFAULT 0,
                net_profit DECIMAL(10,2) DEFAULT 0,
                buyer_username VARCHAR(100),
                buyer_email VARCHAR(255),
                shipping_status VARCHAR(50) DEFAULT 'Pending',
                tracking_number VARCHAR(100),
                sold_date DATE,
                shipped_date DATE,
                delivered_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sold_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                order_id TEXT,
                sku TEXT,
                shoe_name TEXT NOT NULL,
                size TEXT,
                sale_price REAL NOT NULL,
                platform_fees REAL DEFAULT 0,
                shipping_cost REAL DEFAULT 0,
                cogs REAL DEFAULT 0,
                net_profit REAL DEFAULT 0,
                buyer_username TEXT,
                buyer_email TEXT,
                shipping_status TEXT DEFAULT 'Pending',
                tracking_number TEXT,
                sold_date TEXT,
                shipped_date TEXT,
                delivered_date TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

def get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def add_order(user_id, platform, order_id, sku, shoe_name, size, sale_price, 
              platform_fees, shipping_cost, cogs, buyer_username, buyer_email,
              shipping_status, tracking_number, sold_date, shipped_date, 
              delivered_date, notes):
    net_profit = float(sale_price) - float(platform_fees) - float(shipping_cost) - float(cogs)
    
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"""
        INSERT INTO soleops_sold_orders 
        (user_id, platform, order_id, sku, shoe_name, size, sale_price, 
         platform_fees, shipping_cost, cogs, net_profit, buyer_username, 
         buyer_email, shipping_status, tracking_number, sold_date, 
         shipped_date, delivered_date, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 
                {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, platform, order_id, sku, shoe_name, size, sale_price,
          platform_fees, shipping_cost, cogs, net_profit, buyer_username,
          buyer_email, shipping_status, tracking_number, sold_date,
          shipped_date, delivered_date, notes))
    
    conn.commit()
    conn.close()
    return net_profit

def get_orders(user_id, platform=None, status=None, start_date=None, end_date=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    query = f"SELECT * FROM soleops_sold_orders WHERE user_id = {ph}"
    params = [user_id]
    
    if platform and platform != "All":
        query += f" AND platform = {ph}"
        params.append(platform)
    
    if status and status != "All":
        query += f" AND shipping_status = {ph}"
        params.append(status)
    
    if start_date:
        query += f" AND sold_date >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        query += f" AND sold_date <= {ph}"
        params.append(str(end_date))
    
    query += " ORDER BY sold_date DESC, created_at DESC"
    
    cur.execute(query, params)
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    
    return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame()

def update_order(order_id, **kwargs):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    # Recalculate net profit if relevant fields changed
    if any(k in kwargs for k in ['sale_price', 'platform_fees', 'shipping_cost', 'cogs']):
        cur.execute(f"SELECT sale_price, platform_fees, shipping_cost, cogs FROM soleops_sold_orders WHERE id = {ph}", (order_id,))
        row = cur.fetchone()
        if row:
            sale_price = kwargs.get('sale_price', row[0])
            platform_fees = kwargs.get('platform_fees', row[1])
            shipping_cost = kwargs.get('shipping_cost', row[2])
            cogs = kwargs.get('cogs', row[3])
            kwargs['net_profit'] = float(sale_price) - float(platform_fees) - float(shipping_cost) - float(cogs)
    
    set_clauses = ", ".join([f"{k} = {ph}" for k in kwargs.keys()])
    values = list(kwargs.values()) + [order_id]
    
    cur.execute(f"UPDATE soleops_sold_orders SET {set_clauses} WHERE id = {ph}", values)
    conn.commit()
    conn.close()

def delete_order(order_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"DELETE FROM soleops_sold_orders WHERE id = {ph}", (order_id,))
    conn.commit()
    conn.close()

def get_platform_stats(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"""
        SELECT platform, 
               COUNT(*) as total_orders,
               SUM(sale_price) as total_sales,
               SUM(net_profit) as total_profit,
               AVG(net_profit) as avg_profit
        FROM soleops_sold_orders 
        WHERE user_id = {ph}
        GROUP BY platform
    """, (user_id,))
    
    columns = ['platform', 'total_orders', 'total_sales', 'total_profit', 'avg_profit']
    rows = cur.fetchall()
    conn.close()
    
    return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame()

def get_monthly_stats(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    if USE_POSTGRES:
        cur.execute(f"""
            SELECT DATE_TRUNC('month', sold_date::date) as month,
                   COUNT(*) as total_orders,
                   SUM(sale_price) as total_sales,
                   SUM(net_profit) as total_profit
            FROM soleops_sold_orders 
            WHERE user_id = {ph} AND sold_date IS NOT NULL
            GROUP BY DATE_TRUNC('month', sold_date::date)
            ORDER BY month DESC
            LIMIT 12
        """, (user_id,))
    else:
        cur.execute(f"""
            SELECT strftime('%Y-%m', sold_date) as month,
                   COUNT(*) as total_orders,
                   SUM(sale_price) as total_sales,
                   SUM(net_profit) as total_profit
            FROM soleops_sold_orders 
            WHERE user_id = {ph} AND sold_date IS NOT NULL
            GROUP BY strftime('%Y-%m', sold_date)
            ORDER BY month DESC
            LIMIT 12
        """, (user_id,))
    
    columns = ['month', 'total_orders', 'total_sales', 'total_profit']
    rows = cur.fetchall()
    conn.close()
    
    return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame()

def calculate_platform_fees(platform, sale_price):
    """Calculate estimated platform fees based on platform"""
    sale_price = float(sale_price)
    if platform == "eBay":
        # eBay: ~13.25% final value fee
        return round(sale_price * 0.1325, 2)
    elif platform == "Mercari":
        # Mercari: 10% seller fee
        return round(sale_price * 0.10, 2)
    elif platform == "Depop":
        # Depop: 10% fee
        return round(sale_price * 0.10, 2)
    return 0

def get_ai_insights(user_id):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ Configure your Anthropic API key in Settings to get AI insights."
    
    # Get order data for analysis
    df = get_orders(user_id)
    if df.empty:
        return "📊 Add some orders to get AI-powered insights on your selling patterns!"
    
    platform_stats = get_platform_stats(user_id)
    monthly_stats = get_monthly_stats(user_id)
    
    # Prepare summary for Claude
    summary = f"""
    Total Orders: {len(df)}
    Total Sales: ${df['sale_price'].sum():.2f}
    Total Profit: ${df['net_profit'].sum():.2f}
    Average Profit per Sale: ${df['net_profit'].mean():.2f}
    
    Platform Breakdown:
    {platform_stats.to_string() if not platform_stats.empty else 'No data'}
    
    Top Selling Shoes:
    {df.groupby('shoe_name')['net_profit'].sum().sort_values(ascending=False).head(5).to_string()}
    
    Shipping Status:
    {df['shipping_status'].value_counts().to_string()}
    """
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""You are a sneaker resale business analyst. Analyze this seller's data and provide 3-4 actionable insights.
                Focus on: platform recommendations, pricing strategies, shipping efficiency, and profit optimization.
                Keep it concise and actionable.
                
                Data:
                {summary}"""
            }]
        )
        
        return response.content[0].text
    except Exception as e:
        return f"⚠️ Error getting AI insights: {str(e)}"

# Main UI
st.title("📦 SoleOps Sold Order Tracker")
st.markdown("Track all your sneaker sales across eBay, Mercari, and Depop")

user_id = st.session_state.get("user_id", 1)

# Summary Cards
df_all = get_orders(user_id)

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_sales = df_all['sale_price'].sum() if not df_all.empty else 0
    st.metric("💰 Total Sales", f"${total_sales:,.2f}")

with col2:
    total_profit = df_all['net_profit'].sum() if not df_all.empty else 0
    st.metric("📈 Total Profit", f"${total_profit:,.2f}")

with col3:
    avg_profit = df_all['net_profit'].mean() if not df_all.empty else 0
    st.metric("📊 Avg Profit/Sale", f"${avg_profit:,.2f}")

with col4:
    total_orders = len(df_all)
    st.metric("📦 Total Orders", total_orders)

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["➕ Add Order", "📋 Order History", "📊 Platform Breakdown", "💹 Profit Analysis", "🤖 AI Insights"])

with tab1:
    st.subheader("Add New Sold Order")
    
    with st.form("add_order_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            platform = st.selectbox("Platform *", ["eBay", "Mercari", "Depop"])
            order_id = st.text_input("Order ID")
            sku = st.text_input("SKU")
            shoe_name = st.text_input("Shoe Name *")
            size = st.text_input("Size")
        
        with col2:
            sale_price = st.number_input("Sale Price ($) *", min_value=0.0, step=0.01)
            
            # Auto-calculate platform fees
            auto_fees = calculate_platform_fees(platform, sale_price)
            platform_fees = st.number_input("Platform Fees ($)", min_value=0.0, value=auto_fees, step=0.01,
                                           help=f"Auto-calculated: ${auto_fees:.2f}")
            
            shipping_cost = st.number_input("Shipping Cost ($)", min_value=0.0, step=0.01)
            cogs = st.number_input("Cost of Goods (COGS) ($)", min_value=0.0, step=0.01,
                                  help="What you paid for the shoe")
            
            # Show calculated profit
            calc_profit = sale_price - platform_fees - shipping_cost - cogs
            st.info(f"💰 Calculated Net Profit: **${calc_profit:.2f}**")
        
        with col3:
            buyer_username = st.text_input("Buyer Username")
            buyer_email = st.text_input("Buyer Email")
            shipping_status = st.selectbox("Shipping Status", ["Pending", "Shipped", "Delivered"])
            tracking_number = st.text_input("Tracking Number")
            sold_date = st.date_input("Sold Date", value=datetime.now().date())
            shipped_date = st.date_input("Shipped Date", value=None)
            delivered_date = st.date_input("Delivered Date", value=None)
        
        notes = st.text_area("Notes")
        
        submitted = st.form_submit_button("➕ Add Order", type="primary", use_container_width=True)
        
        if submitted:
            if not shoe_name:
                st.error("Please enter a shoe name")
            elif sale_price <= 0:
                st.error("Please enter a valid sale price")
            else:
                net_profit = add_order(
                    user_id, platform, order_id, sku, shoe_name, size,
                    sale_price, platform_fees, shipping_cost, cogs,
                    buyer_username, buyer_email, shipping_status, tracking_number,
                    str(sold_date), str(shipped_date) if shipped_date else None,
                    str(delivered_date) if delivered_date else None, notes
                )
                st.success(f"✅ Order added! Net Profit: ${net_profit:.2f}")
                st.rerun()
    
    # Bulk Import Section
    st.markdown("---")
    st.subheader("📥 Bulk Import Orders")
    
    st.markdown("""
    Upload a CSV file with the following columns:
    `platform, order_id, sku, shoe_name, size, sale_price, platform_fees, shipping_cost, cogs, buyer_username, buyer_email, shipping_status, tracking_number, sold_date, shipped_date, delivered_date, notes`
    """)
    
    uploaded_file = st.file_uploader("Choose CSV file", type=['csv'])
    
    if uploaded_file:
        try:
            import_df = pd.read_csv(uploaded_file)
            st.dataframe(import_df.head())
            
            if st.button("Import Orders", type="primary"):
                success_count = 0
                error_count = 0
                
                for _, row in import_df.iterrows():
                    try:
                        add_order(
                            user_id,
                            row.get('platform', 'eBay'),
                            row.get('order_id', ''),
                            row.get('sku', ''),
                            row.get('shoe_name', 'Unknown'),
                            row.get('size', ''),
                            float(row.get('sale_price', 0)),
                            float(row.get('platform_fees', 0)),
                            float(row.get('shipping_cost', 0)),
                            float(row.get('cogs', 0)),
                            row.get('buyer_username', ''),
                            row.get('buyer_email', ''),
                            row.get('shipping_status', 'Pending'),
                            row.get('tracking_number', ''),
                            row.get('sold_date', str(datetime.now().date())),
                            row.get('shipped_date'),
                            row.get('delivered_date'),
                            row.get('notes', '')
                        )
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                
                st.success(f"✅ Imported {success_count} orders successfully!")
                if error_count > 0:
                    st.warning(f"⚠️ {error_count} orders failed to import")
                st.rerun()
        except Exception as e:
            st.error(f"Error reading CSV: {str(e)}")
    
    # Download Template
    template_data = {
        'platform': ['eBay'],
        'order_id': ['123456789'],
        'sku': ['AJ1-ROYAL-10'],
        'shoe_name': ['Air Jordan 1 Royal'],
        'size': ['10'],
        'sale_price': [250.00],
        'platform_fees': [33.13],
        'shipping_cost': [15.00],
        'cogs': [150.00],
        'buyer_username': ['sneakerhead99'],
        'buyer_email': ['buyer@email.com'],
        'shipping_status': ['Shipped'],
        'tracking_number': ['1Z999AA10123456784'],
        'sold_date': ['2026-03-19'],
        'shipped_date': ['2026-03-20'],
        'delivered_date': [''],
        'notes': ['Great buyer!']
    }
    template_df = pd.DataFrame(template_data)
    csv_template = template_df.to_csv(index=False)
    
    st.download_button(
        label="📄 Download CSV Template",
        data=csv_template,
        file_name="soleops_orders_template.csv",
        mime="text/csv"
    )

with tab2:
    st.subheader("📋 Order History")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filter_platform = st.selectbox("Filter by Platform", ["All", "eBay", "Mercari", "Depop"])
    
    with col2:
        filter_status = st.selectbox("Filter by Status", ["All", "Pending", "Shipped", "Delivered"])
    
    with col3:
        filter_start = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=30))
    
    with col4:
        filter_end = st.date_input("End Date", value=datetime.now().date())
    
    # Get filtered orders
    df = get_orders(user_id, filter_platform, filter_status, filter_start, filter_end)
    
    if df.empty:
        st.info("📦 No orders found. Add your first sale above!")
    else:
        # Status badges
        def status_badge(status):
            colors = {
                'Pending': '🟡',
                'Shipped': '🔵',
                'Delivered': '🟢'
            }
            return f"{colors.get(status, '⚪')} {status}"
        
        # Display orders
        for idx, row in df.iterrows():
            with st.expander(f"{status_badge(row['shipping_status'])} {row['shoe_name']} - {row['platform']} - ${row['sale_price']:.2f}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"**Order ID:** {row['order_id'] or 'N/A'}")
                    st.markdown(f"**SKU:** {row['sku'] or 'N/A'}")
                    st.markdown(f"**Size:** {row['size'] or 'N/A'}")
                    st.markdown(f"**Sold Date:** {row['sold_date']}")
                
                with col2:
                    st.markdown(f"**Sale Price:** ${row['sale_price']:.2f}")
                    st.markdown(f"**Platform Fees:** ${row['platform_fees']:.2f}")
                    st.markdown(f"**Shipping Cost:** ${row['shipping_cost']:.2f}")
                    st.markdown(f"**COGS:** ${row['cogs']:.2f}")
                    profit_color = "green" if row['net_profit'] >= 0 else "red"
                    st.markdown(f"**Net Profit:** :{profit_color}[${row['net_profit']:.2f}]")
                
                with col3:
                    st.markdown(f"**Buyer:** {row['buyer_username'] or 'N/A'}")
                    st.markdown(f"**Email:** {row['buyer_email'] or 'N/A'}")
                    st.markdown(f"**Tracking:** {row['tracking_number'] or 'N/A'}")
                    if row['notes']:
                        st.markdown(f"**Notes:** {row['notes']}")
                
                # Update shipping status
                st.markdown("---")
                col_a, col_b, col_c = st.columns([2, 1, 1])
                
                with col_a:
                    new_status = st.selectbox(
                        "Update Status",
                        ["Pending", "Shipped", "Delivered"],
                        index=["Pending", "Shipped", "Delivered"].index(row['shipping_status']),
                        key=f"status_{row['id']}"
                    )
                    new_tracking = st.text_input(
                        "Update Tracking",
                        value=row['tracking_number'] or '',
                        key=f"tracking_{row['id']}"
                    )
                
                with col_b:
                    if st.button("💾 Save", key=f"save_{row['id']}"):
                        updates = {'shipping_status': new_status, 'tracking_number': new_tracking}
                        if new_status == "Shipped" and row['shipped_date'] is None:
                            updates['shipped_date'] = str(datetime.now().date())
                        elif new_status == "Delivered" and row['delivered_date'] is None:
                            updates['delivered_date'] = str(datetime.now().date())
                        
                        update_order(row['id'], **updates)
                        st.success("Updated!")
                        st.rerun()
                
                with col_c:
                    if st.button("🗑️ Delete", key=f"delete_{row['id']}"):
                        delete_order(row['id'])
                        st.success("Deleted!")
                        st.rerun()
        
        # Export functionality
        st.markdown("---")
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="📥 Export to CSV",
            data=csv_data,
            file_name=f"soleops_orders_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

with tab3:
    st.subheader("📊 Platform Breakdown")
    
    platform_stats = get_platform_stats(user_id)
    
    if platform_stats.empty:
        st.info("📦 No orders yet. Add some sales to see platform breakdown!")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            # Sales volume pie chart
            fig_volume = px.pie(
                platform_stats,
                values='total_orders',
                names='platform',
                title='Sales Volume by Platform',
                color='platform',
                color_discrete_map={'eBay': '#0064D2', 'Mercari': '#4A9CFF', 'Depop': '#FF2300'}
            )
            st.plotly_chart(fig_volume, use_container_width=True)
        
        with col2:
            # Profit by platform
            fig_profit = px.bar(
                platform_stats,
                x='platform',
                y='total_profit',
                title='Total Profit by Platform',
                color='platform',
                color_discrete_map={'eBay': '#0064D2', 'Mercari': '#4A9CFF', 'Depop': '#FF2300'}
            )
            fig_profit.update_layout(showlegend=False)
            st.plotly_chart(fig_profit, use_container_width=True)
        
        # Platform stats table
        st.markdown("### Platform Performance Summary")
        
        stats_display = platform_stats.copy()
        stats_display['total_sales'] = stats_display['total_sales'].apply(lambda x: f"${x:,.2f}")
        stats_display['total_profit'] = stats_display['total_profit'].apply(lambda x: f"${x:,.2f}")
        stats_display['avg_profit'] = stats_display['avg_profit'].apply(lambda x: f"${x:,.2f}")
        stats_display.columns = ['Platform', 'Total Orders', 'Total Sales', 'Total Profit', 'Avg Profit']
        
        st.dataframe(stats_display, use_container_width=True, hide_index=True)
        
        # Best performing platform
        if not platform_stats.empty:
            best_platform = platform_stats.loc[platform_stats['avg_profit'].idxmax(), 'platform']
            best_avg = platform_stats['avg_profit'].max()
            st.success(f"🏆 **Best Performing Platform:** {best_platform} with ${best_avg:.2f} average profit per sale")

with tab4:
    st.subheader("💹 Profit Analysis")
    
    monthly_stats = get_monthly_stats(user_id)
    
    if monthly_stats.empty:
        st.info("📦 No orders yet. Add some sales to see profit analysis!")
    else:
        # Monthly profit trend
        fig_monthly = go.Figure()
        
        fig_monthly.add_trace(go.Scatter(
            x=monthly_stats['month'],
            y=monthly_stats['total_sales'],
            name='Total Sales',
            line=dict(color='#0064D2', width=2)
        ))
        
        fig_monthly.add_trace(go.Scatter(
            x=monthly_stats['month'],
            y=monthly_stats['total_profit'],
            name='Net Profit',
            line=dict(color='#00C853', width=2)
        ))
        
        fig_monthly.update_layout(
            title='Monthly Sales & Profit Trend',
            xaxis_title='Month',
            yaxis_title='Amount ($)',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_monthly, use_container_width=True)
        
        # Profit margin analysis
        if not df_all.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # Profit margin distribution
                df_all['profit_margin'] = (df_all['net_profit'] / df_all['sale_price'] * 100).fillna(0)
                
                fig_margin = px.histogram(
                    df_all,
                    x='profit_margin',
                    nbins=20,
                    title='Profit Margin Distribution',
                    labels={'profit_margin': 'Profit Margin (%)'}
                )
                st.plotly_chart(fig_margin, use_container_width=True)
            
            with col2:
                # Top profitable shoes
                top_shoes = df_all.groupby('shoe_name').agg({
                    'net_profit': 'sum',
                    'sale_price': 'sum',
                    'id': 'count'
                }).reset_index()
                top_shoes.columns = ['Shoe', 'Total Profit', 'Total Sales', 'Units Sold']
                top_shoes = top_shoes.sort_values('Total Profit', ascending=False).head(10)