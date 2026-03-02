import streamlit as st
import datetime
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List
import json
import anthropic

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Monthly Financial Email Report", page_icon="🍑", layout="wide")
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

PH = "%s" if USE_POSTGRES else "?"


def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_reports (
                id SERIAL PRIMARY KEY,
                report_date DATE NOT NULL,
                recipient VARCHAR(255) NOT NULL,
                subject VARCHAR(500) NOT NULL,
                body_html TEXT NOT NULL,
                sent_at TIMESTAMP,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_config (
                id SERIAL PRIMARY KEY,
                config_key VARCHAR(100) UNIQUE NOT NULL,
                config_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date DATE NOT NULL,
                recipient TEXT NOT NULL,
                subject TEXT NOT NULL,
                body_html TEXT NOT NULL,
                sent_at TIMESTAMP,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_report_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


def get_email_config(key: str) -> Optional[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT config_value FROM email_report_config WHERE config_key = {PH}", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def set_email_config(key: str, value: str):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO email_report_config (config_key, config_value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (config_key) DO UPDATE SET config_value = EXCLUDED.config_value, updated_at = CURRENT_TIMESTAMP
        """, (key, value))
    else:
        cur.execute("""
            INSERT OR REPLACE INTO email_report_config (config_key, config_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))
    conn.commit()
    conn.close()


def aggregate_monthly_data(year: int, month: int) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    prev_start = f"{prev_year}-{prev_month:02d}-01"
    prev_end = start_date
    
    data = {
        "year": year,
        "month": month,
        "month_name": datetime.date(year, month, 1).strftime("%B %Y"),
        "total_income": 0,
        "total_expenses": 0,
        "net_savings": 0,
        "expense_categories": {},
        "income_sources": {},
        "net_worth_start": 0,
        "net_worth_end": 0,
        "net_worth_delta": 0,
        "goals": [],
        "prev_month_income": 0,
        "prev_month_expenses": 0,
        "top_expenses": []
    }
    
    try:
        cur.execute(f"""
            SELECT COALESCE(SUM(amount), 0) FROM income 
            WHERE date >= {PH} AND date < {PH}
        """, (start_date, end_date))
        row = cur.fetchone()
        data["total_income"] = float(row[0]) if row and row[0] else 0
    except Exception:
        pass
    
    try:
        cur.execute(f"""
            SELECT COALESCE(SUM(amount), 0) FROM income 
            WHERE date >= {PH} AND date < {PH}
        """, (prev_start, prev_end))
        row = cur.fetchone()
        data["prev_month_income"] = float(row[0]) if row and row[0] else 0
    except Exception:
        pass
    
    try:
        cur.execute(f"""
            SELECT COALESCE(SUM(amount), 0) FROM expenses 
            WHERE date >= {PH} AND date < {PH}
        """, (start_date, end_date))
        row = cur.fetchone()
        data["total_expenses"] = float(row[0]) if row and row[0] else 0
    except Exception:
        pass
    
    try:
        cur.execute(f"""
            SELECT COALESCE(SUM(amount), 0) FROM expenses 
            WHERE date >= {PH} AND date < {PH}
        """, (prev_start, prev_end))
        row = cur.fetchone()
        data["prev_month_expenses"] = float(row[0]) if row and row[0] else 0
    except Exception:
        pass
    
    try:
        cur.execute(f"""
            SELECT category, SUM(amount) as total FROM expenses 
            WHERE date >= {PH} AND date < {PH}
            GROUP BY category ORDER BY total DESC
        """, (start_date, end_date))
        rows = cur.fetchall()
        data["expense_categories"] = {row[0]: float(row[1]) for row in rows}
    except Exception:
        pass
    
    try:
        cur.execute(f"""
            SELECT description, amount, category, date FROM expenses 
            WHERE date >= {PH} AND date < {PH}
            ORDER BY amount DESC LIMIT 10
        """, (start_date, end_date))
        rows = cur.fetchall()
        data["top_expenses"] = [{"description": r[0], "amount": float(r[1]), "category": r[2], "date": str(r[3])} for r in rows]
    except Exception:
        pass
    
    try:
        cur.execute(f"""
            SELECT source, SUM(amount) as total FROM income 
            WHERE date >= {PH} AND date < {PH}
            GROUP BY source ORDER BY total DESC
        """, (start_date, end_date))
        rows = cur.fetchall()
        data["income_sources"] = {row[0]: float(row[1]) for row in rows}
    except Exception:
        pass
    
    try:
        cur.execute(f"""
            SELECT name, target_amount, current_amount, deadline FROM goals
            WHERE status = 'active' OR status IS NULL
        """)
        rows = cur.fetchall()
        data["goals"] = [
            {
                "name": r[0],
                "target": float(r[1]) if r[1] else 0,
                "current": float(r[2]) if r[2] else 0,
                "deadline": str(r[3]) if r[3] else None,
                "progress": (float(r[2]) / float(r[1]) * 100) if r[1] and float(r[1]) > 0 else 0
            }
            for r in rows
        ]
    except Exception:
        pass
    
    try:
        cur.execute(f"""
            SELECT COALESCE(SUM(balance), 0) FROM accounts 
            WHERE snapshot_date <= {PH}
            ORDER BY snapshot_date DESC LIMIT 1
        """, (start_date,))
        row = cur.fetchone()
        data["net_worth_start"] = float(row[0]) if row and row[0] else 0
        
        cur.execute(f"""
            SELECT COALESCE(SUM(balance), 0) FROM accounts 
            WHERE snapshot_date < {PH}
            ORDER BY snapshot_date DESC LIMIT 1
        """, (end_date,))
        row = cur.fetchone()
        data["net_worth_end"] = float(row[0]) if row and row[0] else 0
        data["net_worth_delta"] = data["net_worth_end"] - data["net_worth_start"]
    except Exception:
        pass
    
    data["net_savings"] = data["total_income"] - data["total_expenses"]
    
    conn.close()
    return data


def generate_claude_narrative(data: Dict[str, Any]) -> str:
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return generate_fallback_narrative(data)
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""You are a personal financial advisor writing a monthly financial summary email for a client named Darrian.
Write a warm, professional, and insightful narrative summary of their finances for {data['month_name']}.

Financial Data:
- Total Income: ${data['total_income']:,.2f}
- Total Expenses: ${data['total_expenses']:,.2f}
- Net Savings: ${data['net_savings']:,.2f}
- Previous Month Income: ${data['prev_month_income']:,.2f}
- Previous Month Expenses: ${data['prev_month_expenses']:,.2f}

Expense Categories:
{json.dumps(data['expense_categories'], indent=2)}

Income Sources:
{json.dumps(data['income_sources'], indent=2)}

Top 10 Expenses:
{json.dumps(data['top_expenses'], indent=2)}

Financial Goals:
{json.dumps(data['goals'], indent=2)}

Net Worth Change: ${data['net_worth_delta']:,.2f}

Please write a comprehensive but concise email that:
1. Opens with a friendly greeting
2. Summarizes the month's financial performance
3. Highlights key wins or areas of concern
4. Compares to last month's performance
5. Provides specific, actionable recommendations
6. Updates on goal progress
7. Ends with an encouraging note

Format the response as HTML suitable for an email. Use simple inline styles for formatting. Keep it professional but personable."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text
    except Exception as e:
        st.error(f"Claude API error: {str(e)}")
        return generate_fallback_narrative(data)


def generate_fallback_narrative(data: Dict[str, Any]) -> str:
    savings_rate = (data['net_savings'] / data['total_income'] * 100) if data['total_income'] > 0 else 0
    
    expense_list = ""
    for cat, amt in list(data['expense_categories'].items())[:5]:
        expense_list += f"<li><strong>{cat}:</strong> ${amt:,.2f}</li>"
    
    income_list = ""
    for src, amt in data['income_sources'].items():
        income_list += f"<li><strong>{src}:</strong> ${amt:,.2f}</li>"
    
    goals_section = ""
    if data['goals']:
        goals_section = "<h3>📎 Goal Progress</h3><ul>"
        for goal in data['goals']:
            goals_section += f"<li><strong>{goal['name']}:</strong> {goal['progress']:.1f}% complete (${goal['current']:,.2f} / ${goal['target']:,.2f})</li>"
        goals_section += "</ul>"
    
    income_change = data['total_income'] - data['prev_month_income']
    expense_change = data['total_expenses'] - data['prev_month_expenses']
    income_trend = "📈 up" if income_change > 0 else "📉 down" if income_change < 0 else "➡️ flat"
    expense_trend = "📈 up" if expense_change > 0 else "📉 down" if expense_change < 0 else "➡️ flat"
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px; margin-bottom: 20px;">
            <h1 style="color: white; margin: 0;">🍑 Monthly Financial Report</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">{data['month_name']}</p>
        </div>
        
        <p>Hi Darrian,</p>
        <p>Here's your financial summary for {data['month_name']}:</p>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h3 style="margin-top: 0;">💰 Monthly Summary</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0;"><strong>Total Income:</strong></td>
                    <td style="text-align: right; color: #28a745;">${data['total_income']:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;"><strong>Total Expenses:</strong></td>
                    <td style="text-align: right; color: #dc3545;">${data['total_expenses']:,.2f}</td>
                </tr>
                <tr style="border-top: 2px solid #dee2e6;">
                    <td style="padding: 8px 0;"><strong>Net Savings:</strong></td>
                    <td style="text-align: right; color: {'#28a745' if data['net_savings'] >= 0 else '#dc3545'}; font-weight: bold;">${data['net_savings']:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;"><strong>Savings Rate:</strong></td>
                    <td style="text-align: right;">{savings_rate:.1f}%</td>
                </tr>
            </table>
        </div>
        
        <div style="background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h3 style="margin-top: 0;">📊 Month-over-Month Comparison</h3>
            <p>Income: {income_trend} ${abs(income_change):,.2f}</p>
            <p>Expenses: {expense_trend} ${abs(expense_change):,.2f}</p>
        </div>
        
        <h3>📁 Expenses by Category</h3>
        <ul>{expense_list if expense_list else "<li>No expense data available</li>"}</ul>
        
        <h3>💵 Income Sources</h3>
        <ul>{income_list if income_list else "<li>No income data available</li>"}</ul>
        
        {goals_section}
        
        <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h3 style="margin-top: 0;">💡 Quick Tips</h3>
            <ul>
                <li>{'Great job saving this month! Keep it up!' if data['net_savings'] > 0 else 'Consider reviewing your expenses to find areas to cut back.'}</li>
                <li>{'Your largest expense category is ' + list(data['expense_categories'].keys())[0] + '. Review for optimization opportunities.' if data['expense_categories'] else 'Start tracking expenses to gain insights.'}</li>
            </ul>
        </div>
        
        <p style="color: #666; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">
            This report was automatically generated by Peach State Savings.<br>
            Generated on {datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')}
        </p>
    </body>
    </html>
    """
    return html


def send_email_smtp(recipient: str, subject: str, body_html: str) -> bool:
    smtp_host = get_email_config("smtp_host") or "smtp.gmail.com"
    smtp_port = int(get_email_config("smtp_port") or "587")
    smtp_user = get_email_config("smtp_user")
    smtp_pass = get_email_config("smtp_password")
    sender_name = get_email_config("sender_name") or "Peach State Savings"
    
    if not smtp_user or not smtp_pass:
        st.error("SMTP credentials not configured. Please set up email settings.")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{smtp_user}>"
        msg["To"] = recipient
        
        text_content = "Please view this email in an HTML-capable email client."
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(body_html, "html"))
        
        context = ssl.create_default_context()
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls(context=context)
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipient, msg.as_string())
        
        return True
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")
        return False


def save_report(report_date: datetime.date, recipient: str, subject: str, body_html: str, status: str = "pending", sent_at: Optional[datetime.datetime] = None):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO email_reports (report_date, recipient, subject, body_html, sent_at, status)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (report_date, recipient, subject, body_html, sent_at, status))
        report_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO email_reports (report_date, recipient, subject, body_html, sent_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (report_date, recipient, subject, body_html, sent_at, status))
        report_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return report_id


def update_report_status(report_id: int, status: str, sent_at: Optional[datetime.datetime] = None):
    conn = get_conn()
    cur = conn.cursor()
    
    if sent_at:
        cur.execute(f"UPDATE email_reports SET status = {PH}, sent_at = {PH} WHERE id = {PH}", (status, sent_at, report_id))
    else:
        cur.execute(f"UPDATE email_reports SET status = {PH} WHERE id = {PH}", (status, report_id))
    
    conn.commit()
    conn.close()


def get_all_reports() -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, report_date, recipient, subject, status, sent_at, created_at
        FROM email_reports ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    
    return [
        {
            "id": r[0],
            "report_date": r[1],
            "recipient": r[2],
            "subject": r[3],
            "status": r[4],
            "sent_at": r[5],
            "created_at": r[6]
        }
        for r in rows
    ]


def get_report_by_id(report_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT id, report_date, recipient, subject, body_html, status, sent_at, created_at FROM email_reports WHERE id = {PH}", (report_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "report_date": row[1],
            "recipient": row[2],
            "subject": row[3],
            "body_html": row[4],
            "status": row[5],
            "sent_at": row[6],
            "created_at": row[7]
        }
    return None


def delete_report(report_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM email_reports WHERE id = {PH}", (report_id,))
    conn.commit()
    conn.close()


def get_recipients_list() -> List[str]:
    recipients_str = get_email_config("recipients")
    if recipients_str:
        return [r.strip() for r in recipients_str.split(",") if r.strip()]
    return []


def check_if_should_run_cron() -> bool:
    today = datetime.date.today()
    if today.day != 1:
        return False
    
    last_run = get_email_config("last_cron_run")
    if last_run:
        last_run_date = datetime.datetime.fromisoformat(last_run).date()
        if last_run_date.year == today.year and last_run_date.month == today.month:
            return False
    
    return True


def run_monthly_cron():
    today = datetime.date.today()
    if today.month == 1:
        report_month = 12
        report_year = today.year - 1
    else:
        report_month = today.month - 1
        report_year = today.year
    
    recipients = get_recipients_list()
    if not recipients:
        return False, "No recipients configured"
    
    data = aggregate_monthly_data(report_year, report_month)
    body_html = generate_claude_narrative(data)
    subject = f"🍑 Your {data['month_name']} Financial Report"
    
    success_count = 0
    for recipient in recipients:
        report_id = save_report(
            report_date=datetime.date(report_year, report_month, 1),
            recipient=recipient,
            subject=subject,
            body_html=body_html,
            status="pending"
        )
        
        if send_email_smtp(recipient, subject, body_html):
            update_report_status(report_id, "sent", datetime.datetime.now())
            success_count += 1
        else:
            update_report_status(report_id, "failed")
    
    set_email_config("last_cron_run", datetime.datetime.now().isoformat())
    
    return True, f"Sent {success_count}/{len(recipients)} reports"


_ensure_tables()

if check_if_should_run_cron():
    auto_send = get_email_config("auto_send_enabled")
    if auto_send == "true":
        success, msg = run_monthly_cron()
        if success:
            st.toast(f"✅ Monthly report cron executed: {msg}")

st.title("📧 Monthly Financial Email Report")
st.markdown("Automated monthly financial summaries powered by Claude AI, delivered to your inbox.")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Generate Report", "📬 Past Reports", "⚙️ Settings", "🕐 Cron Status"])

with tab1:
    st.subheader("Generate Monthly Report")
    
    col1, col2 = st.columns(2)
    with col1:
        report_year = st.selectbox("Year", range(datetime.date.today().year, 2020, -1), index=0)
    with col2:
        report_month = st.selectbox("Month", range(1, 13), index=max(0, datetime.date.today().month - 2), format_func=lambda x: datetime.date(2000, x, 1).strftime("%B"))
    
    recipients = get_recipients_list()
    if recipients:
        selected_recipients = st.multiselect("Recipients", recipients, default=recipients)
    else:
        st.warning("No recipients configured. Please add recipients in Settings.")
        selected_recipients = []
        manual_recipient = st.text_input("Or enter email manually:")
        if manual_recipient:
            selected_recipients = [manual_recipient]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Preview Report", use_container_width=True):
            with st.spinner("Aggregating financial data..."):
                data = aggregate_monthly_data(report_year, report_month)
            
            st.session_state["preview_data"] = data
            st.session_state["preview_html"] = None
            
            with st.expander("📊 Raw Financial Data", expanded=True):
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Total Income", f"${data['total_income']:,.2f}", 
                             f"${data['total_income'] - data['prev_month_income']:,.2f} vs last month")
                with col_b:
                    st.metric("Total Expenses", f"${data['total_expenses']:,.2f}",
                             f"${data['total_expenses'] - data['prev_month_expenses']:,.2f} vs last month")
                with col_c:
                    st.metric("Net Savings", f"${data['net_savings']:,.2f}",
                             f"{(data['net_savings']/data['total_income']*100) if data['total_income'] > 0 else 0:.1f}% savings rate")
                
                if data['expense_categories']:
                    st.markdown("**Expense Categories:**")
                    for cat, amt in data['expense_categories'].items():
                        st.write(f"- {cat}: ${amt:,.2f}")
                
                if data['goals']:
                    st.markdown("**Goals:**")
                    for goal in data['goals']:
                        st.progress(min(goal['progress'] / 100, 1.0), text=f"{goal['name']}: {goal['progress']:.1f}%")
    
    with col2:
        if st.button("📝 Generate Narrative", use_container_width=True):
            if "preview_data" not in st.session_state:
                st.warning("Please preview the report data first.")
            else:
                with st.spinner("Generating Claude narrative..."):
                    html = generate_claude_narrative(st.session_state["preview_data"])
                    st.session_state["preview_html"] = html
                st.success("Narrative generated!")
    
    with col3:
        if st.button("📤 Send Report", type="primary", use_container_width=True, disabled=not selected_recipients):
            if "preview_html" not in st.session_state or not st.session_state.get("preview_html"):
                with st.spinner("Generating report..."):
                    data = aggregate_monthly_data(report_year, report_month)
                    html = generate_claude_narrative(data)
            else:
                data = st.session_state["preview_data"]
                html = st.session_state["preview_html"]
            
            subject = f"🍑 Your {data['month_name']} Financial Report"
            success_count = 0
            
            progress_bar = st.progress(0)
            for i, recipient in enumerate(selected_recipients):
                report_id = save_report(
                    report_date=datetime.date(report_year, report_month, 1),
                    recipient=recipient,
                    subject=subject,
                    body_html=html,
                    status="pending"
                )
                
                if send_email_smtp(recipient, subject, html):
                    update_report_status(report_id, "sent", datetime.datetime.now())
                    success_count += 1
                else:
                    update_report_status(report_id, "failed")
                
                progress_bar.progress((i + 1) / len(selected_recipients))
            
            if success_count == len(selected_recipients):
                st.success(f"✅ Successfully sent to {success_count} recipient(s)!")
            else:
                st.warning(f"Sent {success_count}/{len(selected_recipients)} emails. Check Past Reports for details.")
    
    if st.session_state.get("preview_html"):
        st.sub