import streamlit as st
import os
import json
from datetime import datetime, date
from decimal import Decimal
import base64

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Charitable Donation Tracker", page_icon="🍑", layout="wide")
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

def get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS charitable_organizations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name VARCHAR(255) NOT NULL,
                ein VARCHAR(20),
                category VARCHAR(100),
                address TEXT,
                is_501c3 BOOLEAN DEFAULT TRUE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS charitable_donations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                organization_name VARCHAR(255) NOT NULL,
                ein VARCHAR(20),
                donation_date DATE NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                donation_type VARCHAR(50) NOT NULL,
                receipt_path TEXT,
                receipt_data BYTEA,
                receipt_filename VARCHAR(255),
                tax_deductible BOOLEAN DEFAULT TRUE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS charitable_organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                ein TEXT,
                category TEXT,
                address TEXT,
                is_501c3 INTEGER DEFAULT 1,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS charitable_donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                organization_name TEXT NOT NULL,
                ein TEXT,
                donation_date DATE NOT NULL,
                amount REAL NOT NULL,
                donation_type TEXT NOT NULL,
                receipt_path TEXT,
                receipt_data BLOB,
                receipt_filename TEXT,
                tax_deductible INTEGER DEFAULT 1,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

# Helper functions
def get_user_id():
    return st.session_state.get("user_id", 1)

def add_organization(user_id, name, ein, category, address, is_501c3, notes):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"""
        INSERT INTO charitable_organizations (user_id, name, ein, category, address, is_501c3, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, name, ein, category, address, is_501c3, notes))
    conn.commit()
    conn.close()

def get_organizations(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"""
        SELECT id, name, ein, category, address, is_501c3, notes, created_at
        FROM charitable_organizations
        WHERE user_id = {ph}
        ORDER BY name ASC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_organization(org_id, user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"DELETE FROM charitable_organizations WHERE id = {ph} AND user_id = {ph}", (org_id, user_id))
    conn.commit()
    conn.close()

def add_donation(user_id, org_name, ein, donation_date, amount, donation_type, receipt_data, receipt_filename, tax_deductible, notes):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"""
        INSERT INTO charitable_donations (user_id, organization_name, ein, donation_date, amount, donation_type, receipt_data, receipt_filename, tax_deductible, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, org_name, ein, donation_date, amount, donation_type, receipt_data, receipt_filename, tax_deductible, notes))
    conn.commit()
    conn.close()

def get_donations(user_id, year=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    if year:
        cur.execute(f"""
            SELECT id, organization_name, ein, donation_date, amount, donation_type, receipt_data, receipt_filename, tax_deductible, notes, created_at
            FROM charitable_donations
            WHERE user_id = {ph} AND strftime('%Y', donation_date) = {ph}
            ORDER BY donation_date DESC
        """, (user_id, str(year)))
    else:
        cur.execute(f"""
            SELECT id, organization_name, ein, donation_date, amount, donation_type, receipt_data, receipt_filename, tax_deductible, notes, created_at
            FROM charitable_donations
            WHERE user_id = {ph}
            ORDER BY donation_date DESC
        """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_donation(donation_id, user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"DELETE FROM charitable_donations WHERE id = {ph} AND user_id = {ph}", (donation_id, user_id))
    conn.commit()
    conn.close()

def get_donation_summary(user_id, year=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    if year:
        if USE_POSTGRES:
            cur.execute(f"""
                SELECT COALESCE(SUM(amount), 0), COUNT(*)
                FROM charitable_donations
                WHERE user_id = {ph} AND EXTRACT(YEAR FROM donation_date) = {ph}
            """, (user_id, year))
        else:
            cur.execute(f"""
                SELECT COALESCE(SUM(amount), 0), COUNT(*)
                FROM charitable_donations
                WHERE user_id = {ph} AND strftime('%Y', donation_date) = {ph}
            """, (user_id, str(year)))
    else:
        cur.execute(f"""
            SELECT COALESCE(SUM(amount), 0), COUNT(*)
            FROM charitable_donations
            WHERE user_id = {ph}
        """, (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

# Main UI
st.title("🎁 Charitable Donation Tracker")

user_id = get_user_id()

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "➕ Add Donation", "🏢 Organizations", "📋 Reports"])

with tab1:
    st.subheader("Donation Summary")
    
    current_year = datetime.now().year
    col1, col2, col3 = st.columns(3)
    
    summary = get_donation_summary(user_id, current_year)
    total_amount = float(summary[0]) if summary[0] else 0
    total_count = summary[1] if summary[1] else 0
    
    with col1:
        st.metric(f"Total Donations ({current_year})", f"${total_amount:,.2f}")
    with col2:
        st.metric("Number of Donations", total_count)
    with col3:
        avg = total_amount / total_count if total_count > 0 else 0
        st.metric("Average Donation", f"${avg:,.2f}")
    
    st.subheader("Recent Donations")
    donations = get_donations(user_id)
    if donations:
        for donation in donations[:10]:
            with st.expander(f"{donation[1]} - ${float(donation[4]):,.2f} on {donation[3]}"):
                st.write(f"**Type:** {donation[5]}")
                st.write(f"**Tax Deductible:** {'Yes' if donation[8] else 'No'}")
                if donation[9]:
                    st.write(f"**Notes:** {donation[9]}")
                if donation[6]:
                    st.download_button("Download Receipt", donation[6], file_name=donation[7] or "receipt")
                if st.button("Delete", key=f"del_don_{donation[0]}"):
                    delete_donation(donation[0], user_id)
                    st.rerun()
    else:
        st.info("No donations recorded yet. Add your first donation!")

with tab2:
    st.subheader("Add New Donation")
    
    with st.form("add_donation_form"):
        orgs = get_organizations(user_id)
        org_names = ["-- Enter manually --"] + [org[1] for org in orgs]
        
        selected_org = st.selectbox("Select Organization", org_names)
        
        if selected_org == "-- Enter manually --":
            org_name = st.text_input("Organization Name*")
            ein = st.text_input("EIN (Tax ID)")
        else:
            org_name = selected_org
            org_data = next((o for o in orgs if o[1] == selected_org), None)
            ein = org_data[2] if org_data else ""
            st.text_input("EIN (Tax ID)", value=ein, disabled=True)
        
        col1, col2 = st.columns(2)
        with col1:
            donation_date = st.date_input("Donation Date*", value=date.today())
        with col2:
            amount = st.number_input("Amount ($)*", min_value=0.01, step=0.01)
        
        donation_type = st.selectbox("Donation Type", ["Cash", "Check", "Credit Card", "Stock", "Property", "In-Kind", "Other"])
        tax_deductible = st.checkbox("Tax Deductible", value=True)
        
        receipt_file = st.file_uploader("Upload Receipt", type=["pdf", "jpg", "jpeg", "png"])
        notes = st.text_area("Notes")
        
        submitted = st.form_submit_button("Add Donation")
        
        if submitted:
            if not org_name:
                st.error("Please enter an organization name.")
            elif amount <= 0:
                st.error("Please enter a valid amount.")
            else:
                receipt_data = receipt_file.read() if receipt_file else None
                receipt_filename = receipt_file.name if receipt_file else None
                add_donation(user_id, org_name, ein, donation_date, amount, donation_type, receipt_data, receipt_filename, tax_deductible, notes)
                st.success("Donation added successfully!")
                st.rerun()

with tab3:
    st.subheader("Manage Organizations")
    
    with st.form("add_org_form"):
        st.write("**Add New Organization**")
        name = st.text_input("Organization Name*")
        col1, col2 = st.columns(2)
        with col1:
            ein = st.text_input("EIN (Tax ID)")
        with col2:
            category = st.selectbox("Category", ["Religious", "Educational", "Medical", "Environmental", "Social Services", "Arts & Culture", "Animal Welfare", "International", "Other"])
        
        address = st.text_area("Address")
        is_501c3 = st.checkbox("501(c)(3) Organization", value=True)
        notes = st.text_area("Notes", key="org_notes")
        
        if st.form_submit_button("Add Organization"):
            if name:
                add_organization(user_id, name, ein, category, address, is_501c3, notes)
                st.success("Organization added!")
                st.rerun()
            else:
                st.error("Please enter an organization name.")
    
    st.subheader("Saved Organizations")
    orgs = get_organizations(user_id)
    if orgs:
        for org in orgs:
            with st.expander(f"{org[1]} ({org[3] or 'Uncategorized'})"):
                st.write(f"**EIN:** {org[2] or 'N/A'}")
                st.write(f"**Address:** {org[4] or 'N/A'}")
                st.write(f"**501(c)(3):** {'Yes' if org[5] else 'No'}")
                if org[6]:
                    st.write(f"**Notes:** {org[6]}")
                if st.button("Delete", key=f"del_org_{org[0]}"):
                    delete_organization(org[0], user_id)
                    st.rerun()
    else:
        st.info("No organizations saved yet.")

with tab4:
    st.subheader("Donation Reports")
    
    current_year = datetime.now().year
    selected_year = st.selectbox("Select Year", range(current_year, current_year - 10, -1))
    
    donations = get_donations(user_id, selected_year)
    summary = get_donation_summary(user_id, selected_year)
    
    st.write(f"**Total for {selected_year}:** ${float(summary[0]):,.2f} ({summary[1]} donations)")
    
    if donations:
        st.subheader("Donations List")
        for donation in donations:
            st.write(f"- {donation[3]}: {donation[1]} - ${float(donation[4]):,.2f} ({donation[5]})")
        
        # Export option
        if st.button("Export to CSV"):
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Date", "Organization", "EIN", "Amount", "Type", "Tax Deductible", "Notes"])
            for d in donations:
                writer.writerow([d[3], d[1], d[2], d[4], d[5], "Yes" if d[8] else "No", d[9]])
            st.download_button("Download CSV", output.getvalue(), file_name=f"donations_{selected_year}.csv", mime="text/csv")
    else:
        st.info(f"No donations recorded for {selected_year}.")

st.markdown("""
---
*Track your charitable giving for tax purposes. Keep receipts for donations over $250.*
""")