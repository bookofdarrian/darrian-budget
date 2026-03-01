import streamlit as st
import pandas as pd
from datetime import datetime, date
from utils.db import get_conn, init_db, execute, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css
from utils.voice_input import render_voice_input
from aura.jarvis import ask_jarvis

st.set_page_config(
    page_title="Personal Assistant — Peach State Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="auto"
)
init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                         label="Overview",            icon="📊")
st.sidebar.page_link("pages/18_real_estate_bot.py", label="🏠 Real Estate Bot", icon="🏠")
st.sidebar.page_link("pages/22_todo.py",            label="✅ Todo",             icon="✅")
st.sidebar.page_link("pages/1_expenses.py",            label="Expenses",            icon="📋")
st.sidebar.page_link("pages/2_income.py",              label="Income",              icon="💵")
st.sidebar.page_link("pages/3_business_tracker.py",    label="Business Tracker 🔒", icon="💼")
st.sidebar.page_link("pages/4_trends.py",              label="Monthly Trends",      icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",         label="Bank Import",         icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",            label="Receipts & HSA",      icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",         label="AI Insights",         icon="🤖")
st.sidebar.page_link("pages/8_goals.py",               label="Financial Goals",     icon="🎯")
st.sidebar.page_link("pages/9_net_worth.py",           label="Net Worth",           icon="💎")
st.sidebar.page_link("pages/15_bills.py",              label="Bill Calendar",       icon="📅")
st.sidebar.page_link("pages/16_paycheck.py",           label="Paycheck Allocator",  icon="💸")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant",  icon="🤖")
render_sidebar_user_widget()

st.title("🤖 Personal Assistant")
st.caption("Gmail inbox, auto-log purchases, task manager, and smart notification rules.")


# ── Gmail helpers ─────────────────────────────────────────────────────────────

def _get_gmail_token():
    return get_setting("gmail_oauth_token", "")

def _save_gmail_token(token_json):
    set_setting("gmail_oauth_token", token_json)

def _gmail_is_connected():
    return bool(_get_gmail_token())

def _render_gmail_setup():
    st.subheader("📧 Connect Your Gmail")
    st.markdown("""
**One-time setup — takes about 2 minutes:**

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → **New Project**
2. Enable the **Gmail API** (APIs & Services → Library → search "Gmail API")
3. **OAuth consent screen** → External → add your Gmail as a test user
4. **Credentials** → Create → OAuth 2.0 Client ID → **Desktop App** → Download JSON
5. Save the downloaded file as `credentials.json` in your project root folder
6. Click **Generate Auth Link** below, approve, then paste the code back here
""")
    import os as _os
    creds_exist = _os.path.exists("credentials.json")
    if not creds_exist:
        st.warning("⚠️ `credentials.json` not found. Complete steps 1–5 above first, then refresh.")
        return
    st.success("✅ `credentials.json` found — ready to authorize!")
    if "gmail_flow" not in st.session_state:
        st.session_state["gmail_flow"] = None
    col_gen, col_code = st.columns([1, 2])
    with col_gen:
        if st.button("🔗 Generate Auth Link", type="primary"):
            try:
                from utils.gmail_client import get_auth_url
                auth_url, flow = get_auth_url()
                st.session_state["gmail_flow"] = flow
                st.session_state["gmail_auth_url"] = auth_url
            except Exception as e:
                st.error(f"Error: {e}")
    if st.session_state.get("gmail_auth_url"):
        st.markdown(f"**[👉 Click here to authorize Gmail]({st.session_state['gmail_auth_url']})**")
        st.caption("After approving, Google shows a code. Copy and paste it below.")
    with col_code:
        auth_code = st.text_input("Paste authorization code", placeholder="4/0AX4XfWh...", key="gmail_auth_code_input")
        if st.button("✅ Connect Gmail", type="primary", disabled=not auth_code):
            flow = st.session_state.get("gmail_flow")
            if not flow:
                st.error("Generate the auth link first.")
            else:
                try:
                    from utils.gmail_client import exchange_code_for_token
                    token_json = exchange_code_for_token(flow, auth_code.strip())
                    _save_gmail_token(token_json)
                    st.session_state.pop("gmail_flow", None)
                    st.session_state.pop("gmail_auth_url", None)
                    st.success("🎉 Gmail connected!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Authorization failed: {e}")


# ── Tab 1: Email Inbox ────────────────────────────────────────────────────────

def _render_inbox_tab():
    st.subheader("📬 Email Inbox")
    if not _gmail_is_connected():
        st.info("Connect Gmail first using the **Gmail Setup** tab.")
        return
    col_q, col_n, col_fetch = st.columns([3, 1, 1])
    with col_q:
        query = st.text_input("Search query", value="newer_than:7d", key="inbox_query",
                              help="Gmail search syntax: newer_than:7d, from:amazon, is:unread, etc.")
    with col_n:
        max_results = st.number_input("Max emails", min_value=5, max_value=100, value=25, step=5, key="inbox_max")
    with col_fetch:
        st.markdown("<br>", unsafe_allow_html=True)
        fetch_btn = st.button("🔄 Fetch Emails", type="primary", use_container_width=True)

    if fetch_btn:
        with st.spinner("Fetching emails..."):
            try:
                from utils.gmail_client import get_gmail_service, fetch_emails, classify_email
                service, new_token = get_gmail_service(_get_gmail_token())
                _save_gmail_token(new_token)
                emails = fetch_emails(service, query=query, max_results=int(max_results))
                enriched = []
                for em in emails:
                    cl = classify_email(em)
                    enriched.append({**em, **cl})
                st.session_state["pa_inbox_emails"] = enriched
                st.success(f"Fetched {len(enriched)} emails.")
            except RuntimeError as e:
                if "AUTH_REQUIRED" in str(e):
                    st.error("Gmail token expired. Re-connect in the Gmail Setup tab.")
                    _save_gmail_token("")
                else:
                    st.error(f"Error: {e}")
            except Exception as e:
                st.error(f"Error fetching emails: {e}")

    emails = st.session_state.get("pa_inbox_emails", [])
    if not emails:
        st.info("Click **Fetch Emails** to load your inbox.")
        return

    # KPI strip
    purchases = [e for e in emails if e.get("is_purchase")]
    tasks_em  = [e for e in emails if e.get("is_task")]
    unread    = [e for e in emails if e.get("is_unread")]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📧 Emails", len(emails))
    k2.metric("🛒 Purchases", len(purchases))
    k3.metric("✅ Action Items", len(tasks_em))
    k4.metric("🔵 Unread", len(unread))
    st.markdown("---")

    # Filter
    filter_type = st.selectbox("Filter by type", ["All", "Purchases", "Tasks", "Newsletters", "Unread"], key="inbox_filter")
    filtered = emails
    if filter_type == "Purchases":
        filtered = [e for e in emails if e.get("is_purchase")]
    elif filter_type == "Tasks":
        filtered = [e for e in emails if e.get("is_task")]
    elif filter_type == "Newsletters":
        filtered = [e for e in emails if e.get("is_newsletter")]
    elif filter_type == "Unread":
        filtered = [e for e in emails if e.get("is_unread")]

    for em in filtered:
        unread_dot = "🔵 " if em.get("is_unread") else ""
        badges = []
        if em.get("is_purchase"):   badges.append("🛒 Purchase")
        if em.get("is_task"):       badges.append("✅ Task")
        if em.get("is_newsletter"): badges.append("📰 Newsletter")
        badge_str = "  ".join(badges)
        amt = em.get("extracted_amount")
        amt_str = f"  💰 ${amt:,.2f}" if amt else ""
        with st.expander(f"{unread_dot}{em['date']}  |  {em['subject'][:70]}  {badge_str}{amt_str}"):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(f"**From:** {em['sender']}")
                st.markdown(f"**Subject:** {em['subject']}")
                st.caption(em.get("snippet", ""))
            with c2:
                if em.get("is_purchase") and amt:
                    st.metric("Amount", f"${amt:,.2f}")
                if em.get("suggested_category"):
                    st.caption(f"Category: {em['suggested_category']}")
            if em.get("is_purchase"):
                if st.button("➕ Log as Expense", key=f"log_exp_{em['id']}"):
                    st.session_state[f"prefill_expense_{em['id']}"] = em
                    st.info("Switch to the **Purchase Log** tab to review and save.")
            if em.get("is_task"):
                if st.button("📋 Create Task", key=f"create_task_{em['id']}"):
                    st.session_state[f"prefill_task_{em['id']}"] = em
                    st.info("Switch to the **Task Manager** tab to review and save.")


# ── Tab 2: Purchase Auto-Log ──────────────────────────────────────────────────

EXPENSE_CATEGORIES = [
    "Food", "Transportation", "Entertainment", "Housing",
    "Personal Care", "Shopping", "Business", "Savings / Investments",
    "Insurance", "Pets", "Loans", "Other"
]

def _render_purchase_tab():
    st.subheader("🛒 Purchase Auto-Log")
    st.caption("Review purchase emails detected in your inbox and log them as expenses with one click.")

    emails = st.session_state.get("pa_inbox_emails", [])
    purchase_emails = [e for e in emails if e.get("is_purchase")]

    if not purchase_emails:
        st.info("No purchase emails loaded yet. Go to the **Inbox** tab and fetch emails first.")
        return

    # Filter out already-logged
    conn = get_conn()
    logged_ids_rows = execute(conn, "SELECT gmail_id FROM pa_emails WHERE expense_logged = 1").fetchall()
    conn.close()
    logged_ids = {r[0] for r in logged_ids_rows}
    pending = [e for e in purchase_emails if e["id"] not in logged_ids]

    st.markdown(f"**{len(pending)} purchase(s) pending review** ({len(purchase_emails) - len(pending)} already logged)")
    if not pending:
        st.success("✅ All detected purchases have been logged!")
        return

    current_month = datetime.now().strftime("%Y-%m")

    for em in pending:
        amt = em.get("extracted_amount") or 0.0
        merchant = em.get("extracted_merchant") or ""
        cat = em.get("suggested_category") or "Shopping"
        with st.expander(f"🛒 {em['date']}  |  {merchant or em['subject'][:50]}  |  ${amt:,.2f}"):
            st.markdown(f"**From:** {em['sender']}")
            st.markdown(f"**Subject:** {em['subject']}")
            st.caption(em.get("snippet", ""))
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            with c1:
                log_merchant = st.text_input("Merchant", value=merchant, key=f"pm_{em['id']}")
                log_amount   = st.number_input("Amount ($)", value=float(amt), min_value=0.0, format="%.2f", key=f"pa_{em['id']}")
            with c2:
                log_cat = st.selectbox("Category", EXPENSE_CATEGORIES,
                                       index=EXPENSE_CATEGORIES.index(cat) if cat in EXPENSE_CATEGORIES else 0,
                                       key=f"pc_{em['id']}")
                log_sub = st.text_input("Subcategory", value=em.get("suggested_subcategory") or merchant, key=f"ps_{em['id']}")
            with c3:
                log_month = st.text_input("Month (YYYY-MM)", value=em["date"][:7] if em["date"] else current_month, key=f"pmo_{em['id']}")
                log_notes = st.text_input("Notes", value=em.get("purchase_description") or "", key=f"pn_{em['id']}")

            col_log, col_skip = st.columns([1, 1])
            with col_log:
                if st.button("✅ Log Expense", type="primary", key=f"log_{em['id']}"):
                    try:
                        conn = get_conn()
                        # Insert into expenses
                        execute(conn,
                            "INSERT INTO expenses (month, category, subcategory, projected, actual, notes) VALUES (?, ?, ?, 0, ?, ?)",
                            (log_month, log_cat, log_sub or log_merchant, log_amount, log_notes)
                        )
                        # Mark email as logged in pa_emails
                        execute(conn,
                            "INSERT INTO pa_emails (gmail_id, thread_id, date, date_iso, subject, sender, snippet, "
                            "email_type, is_purchase, extracted_amount, extracted_merchant, suggested_category, "
                            "expense_logged) VALUES (?,?,?,?,?,?,?,?,1,?,?,?,1) "
                            "ON CONFLICT(gmail_id) DO UPDATE SET expense_logged=1",
                            (em["id"], em.get("thread_id",""), em["date"], em.get("date_iso", em["date"]),
                             em["subject"], em["sender"], em.get("snippet",""), em.get("type","purchase"),
                             log_amount, log_merchant, log_cat)
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Logged ${log_amount:,.2f} at {log_merchant} → {log_cat}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error logging expense: {e}")
            with col_skip:
                if st.button("⏭️ Skip", key=f"skip_{em['id']}"):
                    conn = get_conn()
                    execute(conn,
                        "INSERT INTO pa_emails (gmail_id, thread_id, date, date_iso, subject, sender, snippet, "
                        "email_type, is_purchase, expense_logged) VALUES (?,?,?,?,?,?,?,?,1,1) "
                        "ON CONFLICT(gmail_id) DO UPDATE SET expense_logged=1",
                        (em["id"], em.get("thread_id",""), em["date"], em.get("date_iso", em["date"]),
                         em["subject"], em["sender"], em.get("snippet",""), "purchase")
                    )
                    conn.commit()
                    conn.close()
                    st.rerun()


# ── Tab 3: Task Manager ───────────────────────────────────────────────────────

def _render_tasks_tab():
    st.subheader("✅ Task Manager")

    # Add task form
    with st.expander("➕ Add New Task", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            task_title = st.text_input("Task title", placeholder="Call dentist to reschedule...", key="new_task_title")
            task_notes = st.text_area("Notes", placeholder="Any extra context...", key="new_task_notes", height=80)
        with c2:
            task_due   = st.date_input("Due date (optional)", value=None, key="new_task_due")
            task_prio  = st.selectbox("Priority", ["normal", "high", "low"], key="new_task_prio")
        if st.button("➕ Add Task", type="primary", key="btn_add_task"):
            if task_title.strip():
                conn = get_conn()
                due_str = task_due.strftime("%Y-%m-%d") if task_due else None
                execute(conn,
                    "INSERT INTO pa_tasks (title, due_date, priority, status, source, notes) VALUES (?,?,?,?,?,?)",
                    (task_title.strip(), due_str, task_prio, "open", "manual", task_notes.strip())
                )
                conn.commit()
                conn.close()
                st.success("Task added!")
                st.rerun()
            else:
                st.error("Enter a task title.")

    st.markdown("---")

    # Load tasks
    conn = get_conn()
    try:
        open_tasks = execute(conn,
            "SELECT * FROM pa_tasks WHERE status='open' ORDER BY "
            "CASE priority WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, due_date NULLS LAST"
        ).fetchall()
        done_tasks = execute(conn,
            "SELECT * FROM pa_tasks WHERE status='done' ORDER BY completed_at DESC LIMIT 20"
        ).fetchall()
        cols_info = execute(conn, "SELECT * FROM pa_tasks LIMIT 0").description
    except Exception:
        open_tasks, done_tasks, cols_info = [], [], []
    conn.close()

    def row_to_dict(row, desc):
        if desc:
            return dict(zip([d[0] for d in desc], row))
        try:
            return dict(row)
        except Exception:
            return {}

    today_str = date.today().strftime("%Y-%m-%d")

    # Open tasks
    st.markdown(f"### 📋 Open Tasks ({len(open_tasks)})")
    if not open_tasks:
        st.info("No open tasks. Add one above or fetch emails with action items.")
    else:
        for row in open_tasks:
            t = row_to_dict(row, cols_info)
            prio_emoji = {"high": "🔴", "normal": "🟡", "low": "🟢"}.get(t.get("priority","normal"), "🟡")
            due = t.get("due_date") or ""
            overdue = due and due < today_str
            due_label = f"  ⚠️ **Overdue** ({due})" if overdue else (f"  📅 {due}" if due else "")
            src_label = f"  📧 *{t.get('source_email_subject','')[:40]}*" if t.get("source_email_subject") else ""
            with st.expander(f"{prio_emoji} {t.get('title','')}{due_label}{src_label}"):
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    new_title = st.text_input("Title", value=t.get("title",""), key=f"tt_{t['id']}")
                    new_notes = st.text_area("Notes", value=t.get("notes",""), key=f"tn_{t['id']}", height=60)
                with c2:
                    new_due = st.text_input("Due date", value=due, key=f"td_{t['id']}", placeholder="YYYY-MM-DD")
                    new_prio = st.selectbox("Priority", ["normal","high","low"],
                                            index=["normal","high","low"].index(t.get("priority","normal")),
                                            key=f"tp_{t['id']}")
                with c3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Save", key=f"save_task_{t['id']}"):
                        conn = get_conn()
                        execute(conn,
                            "UPDATE pa_tasks SET title=?, notes=?, due_date=?, priority=? WHERE id=?",
                            (new_title, new_notes, new_due or None, new_prio, t["id"])
                        )
                        conn.commit(); conn.close()
                        st.success("Saved!"); st.rerun()
                    if st.button("✅ Mark Done", type="primary", key=f"done_task_{t['id']}"):
                        conn = get_conn()
                        execute(conn,
                            "UPDATE pa_tasks SET status='done', completed_at=? WHERE id=?",
                            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), t["id"])
                        )
                        conn.commit(); conn.close()
                        st.success("Marked done!"); st.rerun()
                    if st.button("🗑️ Delete", key=f"del_task_{t['id']}"):
                        conn = get_conn()
                        execute(conn, "DELETE FROM pa_tasks WHERE id=?", (t["id"],))
                        conn.commit(); conn.close()
                        st.rerun()

    # Completed tasks
    if done_tasks:
        with st.expander(f"✅ Completed Tasks ({len(done_tasks)} recent)"):
            for row in done_tasks:
                t = row_to_dict(row, cols_info)
                st.markdown(f"- ~~{t.get('title','')}~~ — completed {t.get('completed_at','')[:10]}")


# ── Tab 4: Notification Rules ─────────────────────────────────────────────────

def _render_rules_tab():
    st.subheader("🔔 Notification Rules")
    st.caption("Define rules to auto-classify, label, or flag emails based on sender, subject, or keywords.")

    # Add rule form
    with st.expander("➕ Add New Rule", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            rule_name   = st.text_input("Rule name", placeholder="Amazon orders", key="nr_name")
            match_type  = st.selectbox("Match on", ["sender", "subject", "body_keyword"], key="nr_match_type")
            match_value = st.text_input("Match value", placeholder="amazon.com", key="nr_match_value")
        with c2:
            action       = st.selectbox("Action", ["label", "flag_purchase", "flag_task", "ignore"], key="nr_action")
            action_value = st.text_input("Action value (e.g. label name)", placeholder="Shopping", key="nr_action_value")
        if st.button("➕ Add Rule", type="primary", key="btn_add_rule"):
            if rule_name.strip() and match_value.strip():
                conn = get_conn()
                execute(conn,
                    "INSERT INTO pa_notification_rules (rule_name, match_type, match_value, action, action_value, active) "
                    "VALUES (?,?,?,?,?,1)",
                    (rule_name.strip(), match_type, match_value.strip(), action, action_value.strip())
                )
                conn.commit(); conn.close()
                st.success("Rule added!"); st.rerun()
            else:
                st.error("Rule name and match value are required.")

    st.markdown("---")

    # Load rules
    conn = get_conn()
    try:
        rules = execute(conn, "SELECT * FROM pa_notification_rules ORDER BY id DESC").fetchall()
        cols_info = execute(conn, "SELECT * FROM pa_notification_rules LIMIT 0").description
    except Exception:
        rules, cols_info = [], []
    conn.close()

    def row_to_dict(row, desc):
        if desc:
            return dict(zip([d[0] for d in desc], row))
        try:
            return dict(row)
        except Exception:
            return {}

    if not rules:
        st.info("No rules yet. Add one above to start auto-classifying emails.")
        return

    st.markdown(f"### 📋 Active Rules ({len([r for r in rules if row_to_dict(r, cols_info).get('active',1)])})")

    for row in rules:
        r = row_to_dict(row, cols_info)
        active_icon = "🟢" if r.get("active", 1) else "⚫"
        with st.expander(f"{active_icon} {r.get('rule_name','')}  |  {r.get('match_type','')} contains '{r.get('match_value','')}'  →  {r.get('action','')}"):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                new_name  = st.text_input("Rule name",   value=r.get("rule_name",""),   key=f"rn_{r['id']}")
                new_mtype = st.selectbox("Match on", ["sender","subject","body_keyword"],
                                         index=["sender","subject","body_keyword"].index(r.get("match_type","sender")),
                                         key=f"rmt_{r['id']}")
                new_mval  = st.text_input("Match value", value=r.get("match_value",""), key=f"rmv_{r['id']}")
            with c2:
                new_action = st.selectbox("Action", ["label","flag_purchase","flag_task","ignore"],
                                          index=["label","flag_purchase","flag_task","ignore"].index(r.get("action","label")),
                                          key=f"ra_{r['id']}")
                new_aval   = st.text_input("Action value", value=r.get("action_value",""), key=f"rav_{r['id']}")
                new_active = st.checkbox("Active", value=bool(r.get("active",1)), key=f"ract_{r['id']}")
            with c3:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if st.button("💾 Save", key=f"save_rule_{r['id']}"):
                    conn = get_conn()
                    execute(conn,
                        "UPDATE pa_notification_rules SET rule_name=?, match_type=?, match_value=?, "
                        "action=?, action_value=?, active=? WHERE id=?",
                        (new_name, new_mtype, new_mval, new_action, new_aval, 1 if new_active else 0, r["id"])
                    )
                    conn.commit(); conn.close()
                    st.success("Saved!"); st.rerun()
                if st.button("🗑️ Delete", key=f"del_rule_{r['id']}"):
                    conn = get_conn()
                    execute(conn, "DELETE FROM pa_notification_rules WHERE id=?", (r["id"],))
                    conn.commit(); conn.close()
                    st.rerun()

    # Rule tester
    st.markdown("---")
    st.markdown("### 🧪 Test Rules Against Inbox")
    emails = st.session_state.get("pa_inbox_emails", [])
    if not emails:
        st.info("Fetch emails in the Inbox tab first to test rules.")
        return

    if st.button("▶️ Run Rules Against Loaded Emails"):
        rule_list = [row_to_dict(r, cols_info) for r in rules if row_to_dict(r, cols_info).get("active",1)]
        hits = []
        for em in emails:
            for rl in rule_list:
                mtype = rl.get("match_type","sender")
                mval  = rl.get("match_value","").lower()
                target = ""
                if mtype == "sender":
                    target = em.get("sender","").lower()
                elif mtype == "subject":
                    target = em.get("subject","").lower()
                elif mtype == "body_keyword":
                    target = (em.get("snippet","") + em.get("body","")).lower()
                if mval and mval in target:
                    hits.append({
                        "Rule":    rl.get("rule_name",""),
                        "Email":   em.get("subject","")[:60],
                        "From":    em.get("sender","")[:40],
                        "Action":  rl.get("action",""),
                        "Value":   rl.get("action_value",""),
                    })
        if hits:
            st.success(f"✅ {len(hits)} rule match(es) found:")
            st.dataframe(pd.DataFrame(hits), use_container_width=True, hide_index=True)
        else:
            st.info("No matches found for the current inbox emails.")




# ── AI helpers ────────────────────────────────────────────────────────────────

def _get_api_key():
    """Load Claude API key from session or DB (same as ai_insights.py)."""
    if st.session_state.get("api_key"):
        return st.session_state["api_key"]
    from utils.db import get_setting as _gs
    key = _gs("anthropic_api_key", "")
    if key:
        st.session_state["api_key"] = key
    return key

def _ask_ai(prompt: str, use_ollama: bool = False, ollama_url: str = "") -> str:
    """
    Call Claude or Ollama. Returns response string or raises on error.
    Tries AURA compression first if available.
    """
    if use_ollama and ollama_url:
        import requests as _req
        r = _req.post(
            f"{ollama_url.rstrip('/')}/api/generate",
            json={"model": "llama3.1:8b", "prompt": prompt, "stream": False},
            timeout=60,
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()

    api_key = _get_api_key()
    if not api_key:
        raise ValueError("No Claude API key set. Add it in AI Insights → Settings.")
    import anthropic as _ant
    client = _ant.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()

def _render_ai_settings_sidebar():
    """Render AI model selector in an expander — returns (use_ollama, ollama_url)."""
    with st.expander("⚙️ AI Model Settings", expanded=False):
        use_ollama = st.checkbox(
            "Use Homelab Ollama instead of Claude",
            value=st.session_state.get("pa_use_ollama", False),
            key="pa_use_ollama",
            help="Point to your homelab Ollama server to use Llama 3.1 for free"
        )
        ollama_url = ""
        if use_ollama:
            ollama_url = st.text_input(
                "Ollama URL",
                value=st.session_state.get("pa_ollama_url", "http://100.117.1.19:11434"),
                key="pa_ollama_url",
                help="Your homelab Tailscale IP + Ollama port"
            )
            if st.button("🔍 Test Ollama Connection", key="test_ollama"):
                try:
                    import requests as _req
                    r = _req.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=5)
                    models = [m["name"] for m in r.json().get("models", [])]
                    st.success(f"✅ Connected! Models: {', '.join(models[:5])}")
                except Exception as e:
                    st.error(f"❌ Cannot reach Ollama: {e}")
        else:
            api_key = _get_api_key()
            if not api_key:
                new_key = st.text_input("Claude API Key", type="password",
                                        placeholder="sk-ant-api03-...", key="pa_api_key_input")
                if new_key and new_key.startswith("sk-ant-"):
                    st.session_state["api_key"] = new_key
                    from utils.db import set_setting as _ss
                    _ss("anthropic_api_key", new_key)
                    st.success("API key saved!")
            else:
                st.success(f"✅ Claude API key loaded ({api_key[:12]}...)")
    return use_ollama, ollama_url if use_ollama else ""




# ── Tab 5: AI Assistant ───────────────────────────────────────────────────────

def _render_ai_tab():
    st.subheader("🧠 AI Assistant")
    st.caption("Claude or your homelab Llama model — summarize inbox, parse purchases, extract tasks, and get financial insights.")

    use_ollama, ollama_url = _render_ai_settings_sidebar()

    emails = st.session_state.get("pa_inbox_emails", [])

    ai_tab1, ai_tab2, ai_tab3, ai_tab4 = st.tabs([
        "📋 Inbox Digest",
        "🛒 AI Parse Purchases",
        "✅ AI Extract Tasks",
        "💡 Financial Insights",
    ])

    # ── AI Tab 1: Inbox Digest ────────────────────────────────────────────────
    with ai_tab1:
        st.markdown("#### 📋 Daily Inbox Digest")
        st.caption("Get a concise AI summary of what's in your inbox — key purchases, action items, and anything that needs attention.")

        if not emails:
            st.info("Fetch emails in the **Inbox** tab first, then come back here.")
        else:
            col_gen, col_opts = st.columns([1, 2])
            with col_opts:
                max_emails = st.slider("Emails to summarize", 5, min(50, len(emails)), min(25, len(emails)), key="digest_max")
                focus = st.multiselect("Focus on", ["Purchases", "Action Items", "Newsletters", "All"],
                                       default=["All"], key="digest_focus")
            with col_gen:
                st.markdown("<br>", unsafe_allow_html=True)
                gen_digest = st.button("🧠 Generate Digest", type="primary", use_container_width=True, key="btn_digest")

            if gen_digest:
                subset = emails[:max_emails]
                if "Purchases" in focus and "All" not in focus:
                    subset = [e for e in subset if e.get("is_purchase")]
                elif "Action Items" in focus and "All" not in focus:
                    subset = [e for e in subset if e.get("is_task")]

                email_lines = []
                for i, em in enumerate(subset, 1):
                    amt = f" | ${em['extracted_amount']:,.2f}" if em.get("extracted_amount") else ""
                    tags = []
                    if em.get("is_purchase"): tags.append("PURCHASE")
                    if em.get("is_task"):     tags.append("ACTION")
                    if em.get("is_newsletter"): tags.append("NEWSLETTER")
                    tag_str = f" [{', '.join(tags)}]" if tags else ""
                    email_lines.append(f"{i}. [{em['date']}] {em['subject'][:80]}{amt}{tag_str} — From: {em['sender'][:40]}")
                    if em.get("snippet"):
                        email_lines.append(f"   Preview: {em['snippet'][:120]}")

                prompt = f"""You are a personal assistant. Summarize this email inbox for the user.

Today is {datetime.now().strftime('%A, %B %d, %Y')}.

EMAILS ({len(subset)} total):
{chr(10).join(email_lines)}

Write a concise daily digest with these sections:
1. **🛒 Purchases & Spending** — list any purchases with amounts, flag anything unusual
2. **✅ Action Items** — things that need a response or action, with urgency
3. **📰 FYI / Newsletters** — brief mention of any newsletters or promos worth noting
4. **💡 Key Takeaway** — one sentence summary of the most important thing to do today

Be direct and practical. Skip empty sections. Use bullet points."""

                with st.spinner("Generating digest..."):
                    try:
                        result = _ask_ai(prompt, use_ollama, ollama_url)
                        st.session_state["pa_digest_result"] = result
                    except Exception as e:
                        st.error(f"AI error: {e}")

            if st.session_state.get("pa_digest_result"):
                st.markdown("---")
                st.markdown(st.session_state["pa_digest_result"])
                if st.button("🗑️ Clear Digest", key="clear_digest"):
                    st.session_state.pop("pa_digest_result", None)
                    st.rerun()

    # ── AI Tab 2: AI Parse Purchases ──────────────────────────────────────────
    with ai_tab2:
        st.markdown("#### 🛒 AI-Powered Purchase Parsing")
        st.caption("Use AI to extract merchant, amount, and category from purchase emails more accurately than rule-based detection.")

        purchase_emails = [e for e in emails if e.get("is_purchase")]
        if not purchase_emails:
            st.info("No purchase emails loaded. Fetch emails in the Inbox tab first.")
        else:
            st.markdown(f"**{len(purchase_emails)} purchase email(s) ready to parse**")
            max_parse = st.slider("Max emails to AI-parse (each uses ~1 API call)", 1, min(20, len(purchase_emails)), min(5, len(purchase_emails)), key="parse_max")

            if st.button("🧠 AI Parse All Purchases", type="primary", key="btn_ai_parse"):
                results = []
                progress = st.progress(0)
                status_text = st.empty()
                for i, em in enumerate(purchase_emails[:max_parse]):
                    status_text.text(f"Parsing {i+1}/{max_parse}: {em['subject'][:50]}...")
                    prompt = f"""Extract purchase info from this email. Return ONLY valid JSON, no other text.

Subject: {em['subject']}
From: {em['sender']}
Date: {em['date']}
Preview: {em.get('snippet', '')}
Body (first 1500 chars): {em.get('body', '')[:1500]}

Return exactly this JSON:
{{
  "merchant": "store name",
  "amount": 0.00,
  "date": "YYYY-MM-DD",
  "category": "one of: Food, Transportation, Entertainment, Housing, Personal Care, Shopping, Business, Savings / Investments, Insurance, Pets, Loans, Other",
  "subcategory": "specific subcategory",
  "description": "brief one-line description",
  "is_refund": false,
  "confidence": 0.9
}}
If you cannot find a field, use null. Amount must be a number."""
                    try:
                        import json as _json, re as _re
                        raw = _ask_ai(prompt, use_ollama, ollama_url)
                        raw = _re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
                        m = _re.search(r"\{.*\}", raw, _re.DOTALL)
                        parsed = _json.loads(m.group(0)) if m else {}
                        results.append({"email": em, "parsed": parsed, "error": None})
                    except Exception as e:
                        results.append({"email": em, "parsed": {}, "error": str(e)})
                    progress.progress((i + 1) / max_parse)
                status_text.text("Done!")
                st.session_state["pa_ai_parse_results"] = results

            if st.session_state.get("pa_ai_parse_results"):
                st.markdown("---")
                st.markdown("**Review AI-parsed results — edit and log:**")
                current_month = datetime.now().strftime("%Y-%m")
                for idx, item in enumerate(st.session_state["pa_ai_parse_results"]):
                    em = item["email"]
                    p  = item["parsed"]
                    err = item["error"]
                    conf = p.get("confidence", 0)
                    conf_icon = "🟢" if conf >= 0.8 else ("🟡" if conf >= 0.5 else "🔴")
                    label = f"{conf_icon} {em['date']} | {p.get('merchant') or em['subject'][:40]} | ${p.get('amount') or 0:,.2f}"
                    with st.expander(label):
                        if err:
                            st.error(f"Parse error: {err}")
                            continue
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            ai_merchant = st.text_input("Merchant", value=p.get("merchant") or "", key=f"ai_m_{idx}")
                            ai_amount   = st.number_input("Amount ($)", value=float(p.get("amount") or 0), min_value=0.0, format="%.2f", key=f"ai_a_{idx}")
                        with c2:
                            cats = ["Food","Transportation","Entertainment","Housing","Personal Care","Shopping","Business","Savings / Investments","Insurance","Pets","Loans","Other"]
                            ai_cat = p.get("category") or "Shopping"
                            ai_cat_idx = cats.index(ai_cat) if ai_cat in cats else 0
                            ai_category = st.selectbox("Category", cats, index=ai_cat_idx, key=f"ai_c_{idx}")
                            ai_sub = st.text_input("Subcategory", value=p.get("subcategory") or "", key=f"ai_s_{idx}")
                        with c3:
                            ai_month = st.text_input("Month", value=(p.get("date") or em["date"])[:7] or current_month, key=f"ai_mo_{idx}")
                            ai_notes = st.text_input("Notes", value=p.get("description") or "", key=f"ai_n_{idx}")
                        if st.button("✅ Log Expense", type="primary", key=f"ai_log_{idx}"):
                            try:
                                conn = get_conn()
                                execute(conn,
                                    "INSERT INTO expenses (month, category, subcategory, projected, actual, notes) VALUES (?,?,?,0,?,?)",
                                    (ai_month, ai_category, ai_sub or ai_merchant, ai_amount, ai_notes)
                                )
                                execute(conn,
                                    "INSERT INTO pa_emails (gmail_id, thread_id, date, date_iso, subject, sender, snippet, "
                                    "email_type, is_purchase, extracted_amount, extracted_merchant, suggested_category, "
                                    "expense_logged, llm_parsed) VALUES (?,?,?,?,?,?,?,?,1,?,?,?,1,1) "
                                    "ON CONFLICT(gmail_id) DO UPDATE SET expense_logged=1, llm_parsed=1",
                                    (em["id"], em.get("thread_id",""), em["date"], em.get("date_iso", em["date"]),
                                     em["subject"], em["sender"], em.get("snippet",""), "purchase",
                                     ai_amount, ai_merchant, ai_category)
                                )
                                conn.commit(); conn.close()
                                st.success(f"✅ Logged ${ai_amount:,.2f} at {ai_merchant}!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

    # ── AI Tab 3: Extract Tasks ───────────────────────────────────────────────
    with ai_tab3:
        st.markdown("#### ✅ AI Task Extraction")
        st.caption("Let AI scan your emails and pull out every action item, deadline, and follow-up automatically.")

        task_emails = [e for e in emails if e.get("is_task")]
        all_emails_for_tasks = emails

        col_src, col_max = st.columns(2)
        with col_src:
            task_source = st.radio("Scan which emails?", ["Action-flagged only", "All loaded emails"], key="task_source_radio")
        with col_max:
            scan_emails = task_emails if task_source == "Action-flagged only" else all_emails_for_tasks
            max_scan = st.slider("Max emails to scan", 1, min(30, max(1, len(scan_emails))), min(10, max(1, len(scan_emails))), key="task_scan_max")

        if not scan_emails:
            st.info("No emails loaded. Fetch emails in the Inbox tab first.")
        else:
            if st.button("🧠 Extract Tasks from Emails", type="primary", key="btn_extract_tasks"):
                extracted = []
                progress = st.progress(0)
                for i, em in enumerate(scan_emails[:max_scan]):
                    prompt = f"""Extract any action items or tasks from this email. Return ONLY valid JSON.

Subject: {em['subject']}
From: {em['sender']}
Date: {em['date']}
Preview: {em.get('snippet', '')}
Body (first 1000 chars): {em.get('body', '')[:1000]}

If there IS an action item, return:
{{
  "has_task": true,
  "task_title": "clear actionable task starting with a verb",
  "due_date": "YYYY-MM-DD or null",
  "priority": "high, normal, or low",
  "notes": "relevant context"
}}

If there is NO action item needed, return:
{{"has_task": false}}"""
                    try:
                        import json as _json, re as _re
                        raw = _ask_ai(prompt, use_ollama, ollama_url)
                        raw = _re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
                        m = _re.search(r"\{.*\}", raw, _re.DOTALL)
                        parsed = _json.loads(m.group(0)) if m else {}
                        if parsed.get("has_task"):
                            extracted.append({"email": em, "task": parsed})
                    except Exception:
                        pass
                    progress.progress((i + 1) / max_scan)
                st.session_state["pa_extracted_tasks"] = extracted
                st.success(f"Found {len(extracted)} action item(s) in {min(max_scan, len(scan_emails))} emails.")

            if st.session_state.get("pa_extracted_tasks"):
                st.markdown("---")
                st.markdown("**Review extracted tasks — add to your task list:**")
                for idx, item in enumerate(st.session_state["pa_extracted_tasks"]):
                    em = item["email"]
                    t  = item["task"]
                    prio_icon = {"high": "🔴", "normal": "🟡", "low": "🟢"}.get(t.get("priority","normal"), "🟡")
                    with st.expander(f"{prio_icon} {t.get('task_title','')[:70]}  |  📧 {em['subject'][:50]}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            new_title = st.text_input("Task", value=t.get("task_title",""), key=f"et_t_{idx}")
                            new_notes = st.text_area("Notes", value=t.get("notes",""), key=f"et_n_{idx}", height=60)
                        with c2:
                            new_due  = st.text_input("Due date", value=t.get("due_date") or "", key=f"et_d_{idx}", placeholder="YYYY-MM-DD")
                            new_prio = st.selectbox("Priority", ["normal","high","low"],
                                                    index=["normal","high","low"].index(t.get("priority","normal")),
                                                    key=f"et_p_{idx}")
                        if st.button("➕ Add to Task List", type="primary", key=f"et_add_{idx}"):
                            conn = get_conn()
                            execute(conn,
                                "INSERT INTO pa_tasks (title, due_date, priority, status, source, source_email_id, source_email_subject, notes) "
                                "VALUES (?,?,?,?,?,?,?,?)",
                                (new_title, new_due or None, new_prio, "open", "email",
                                 em["id"], em["subject"][:200], new_notes)
                            )
                            conn.commit(); conn.close()
                            st.success("Task added!"); st.rerun()

    # ── AI Tab 4: Financial Insights ──────────────────────────────────────────
    with ai_tab4:
        st.markdown("#### 💡 AI Financial Insights from Emails")
        st.caption("Ask AI to analyze your spending patterns from email receipts and give personalized advice.")

        if not emails:
            st.info("Fetch emails in the Inbox tab first.")
        else:
            purchase_list = [e for e in emails if e.get("is_purchase")]
            if not purchase_list:
                st.info("No purchase emails detected in the current inbox. Try fetching with query: `subject:receipt newer_than:30d`")
            else:
                # Build spending summary
                total_spend = sum(e.get("extracted_amount") or 0 for e in purchase_list)
                merchants = {}
                for e in purchase_list:
                    m = e.get("extracted_merchant") or "Unknown"
                    merchants[m] = merchants.get(m, 0) + (e.get("extracted_amount") or 0)
                top_merchants = sorted(merchants.items(), key=lambda x: x[1], reverse=True)[:10]

                k1, k2, k3 = st.columns(3)
                k1.metric("🛒 Purchase Emails", len(purchase_list))
                k2.metric("💰 Total Detected Spend", f"${total_spend:,.2f}")
                k3.metric("🏪 Unique Merchants", len(merchants))

                question = st.text_area(
                    "Ask AI about your spending",
                    value="Analyze my recent spending and give me 3 specific ways to save money this month.",
                    key="ai_finance_question",
                    height=80
                )

                if st.button("🧠 Get AI Insights", type="primary", key="btn_finance_insights"):
                    spend_lines = [f"- {m}: ${amt:,.2f}" for m, amt in top_merchants]
                    cat_totals = {}
                    for e in purchase_list:
                        cat = e.get("suggested_category") or "Unknown"
                        cat_totals[cat] = cat_totals.get(cat, 0) + (e.get("extracted_amount") or 0)
                    cat_lines = [f"- {c}: ${a:,.2f}" for c, a in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)]

                    prompt = f"""You are a personal finance advisor analyzing someone's email receipts.

SPENDING SUMMARY (from {len(purchase_list)} purchase emails):
Total detected spend: ${total_spend:,.2f}

Top merchants:
{chr(10).join(spend_lines)}

By category:
{chr(10).join(cat_lines)}

USER QUESTION: {question}

Give specific, actionable advice based on the actual data above. Be direct and practical.
Reference specific merchants or amounts where relevant. Keep response under 400 words."""

                    with st.spinner("Analyzing your spending..."):
                        try:
                            result = _ask_ai(prompt, use_ollama, ollama_url)
                            st.session_state["pa_finance_insight"] = result
                        except Exception as e:
                            st.error(f"AI error: {e}")

                if st.session_state.get("pa_finance_insight"):
                    st.markdown("---")
                    st.markdown(st.session_state["pa_finance_insight"])
                    if st.button("🗑️ Clear", key="clear_finance_insight"):
                        st.session_state.pop("pa_finance_insight", None)
                        st.rerun()


# ── Main layout — tabs ────────────────────────────────────────────────────────

connected = _gmail_is_connected()
status_icon = "🟢" if connected else "🔴"
status_text = "Gmail Connected" if connected else "Gmail Not Connected"

st.markdown(
    f"<div style='display:inline-block; background:#1e2330; border-radius:8px; "
    f"padding:6px 14px; font-size:0.82rem; margin-bottom:12px;'>"
    f"{status_icon} {status_text}</div>",
    unsafe_allow_html=True
)

if connected:
    col_disconnect, _ = st.columns([1, 4])
    with col_disconnect:
        if st.button("🔌 Disconnect Gmail"):
            _save_gmail_token("")
            st.session_state.pop("pa_inbox_emails", None)
            st.success("Gmail disconnected.")
            st.rerun()

tab_setup, tab_inbox, tab_purchases, tab_tasks, tab_rules, tab_ai, tab_jarvis = st.tabs([
    "📧 Gmail Setup",
    "📬 Inbox",
    "🛒 Purchase Log",
    "✅ Tasks",
    "🔔 Rules",
    "🧠 AI Assistant",
    "🎤 Jarvis",
])

with tab_setup:
    if connected:
        st.success("✅ Gmail is connected! Use the other tabs to view your inbox and manage tasks.")
        st.markdown("To re-connect with a different account, click **Disconnect Gmail** above first.")
    else:
        _render_gmail_setup()

with tab_inbox:
    _render_inbox_tab()

with tab_purchases:
    _render_purchase_tab()

with tab_tasks:
    _render_tasks_tab()

with tab_rules:
    _render_rules_tab()

with tab_ai:
    _render_ai_tab()

with tab_jarvis:
    st.subheader("🎤 Talk to Jarvis")
    st.caption("Your personal AI — voice or text. Powered by Claude claude-opus-4-5 with Jarvis personality.")

    # Initialize chat history
    if "jarvis_history" not in st.session_state:
        st.session_state["jarvis_history"] = []

    # ── Voice input ────────────────────────────────────────────────────────────
    st.markdown("**Speak or type below:**")
    voice_text = render_voice_input(
        label="🎤 Hold to speak to Jarvis",
        key="jarvis_voice_input",
    )

    # Text fallback
    typed_text = st.text_input(
        "Or type your message",
        placeholder="Ask Jarvis anything...",
        key="jarvis_text_input",
        label_visibility="collapsed",
    )

    col_send, col_clear = st.columns([3, 1])
    send_pressed  = col_send.button("▶️ Send", type="primary", use_container_width=True, key="jarvis_send")
    clear_pressed = col_clear.button("🗑️ Clear", use_container_width=True, key="jarvis_clear")

    if clear_pressed:
        st.session_state["jarvis_history"] = []
        st.rerun()

    # Determine query (voice takes priority over typed)
    query = voice_text or (typed_text.strip() if send_pressed else "")

    if query:
        with st.spinner("Jarvis is thinking..."):
            response = ask_jarvis(query)

        # Append to history
        st.session_state["jarvis_history"].append(
            {"role": "you", "text": query}
        )
        st.session_state["jarvis_history"].append(
            {"role": "jarvis", "text": response}
        )
        st.rerun()

    # ── Chat history ───────────────────────────────────────────────────────────
    history = st.session_state.get("jarvis_history", [])
    if not history:
        st.markdown(
            "<div style='color:#666;font-size:13px;margin-top:24px;text-align:center'>"
            "🤖 Jarvis is standing by. Speak or type to begin."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.divider()
        for msg in reversed(history):
            if msg["role"] == "jarvis":
                st.markdown(
                    f"<div style='background:#1a2a1a;border-left:3px solid #4caf50;"
                    f"padding:10px 14px;border-radius:6px;margin-bottom:8px'>"
                    f"<span style='color:#4caf50;font-size:11px;font-weight:bold'>JARVIS</span><br>"
                    f"<span style='color:#e0e0e0'>{msg['text']}</span></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='background:#1a1a2a;border-left:3px solid #5c6bc0;"
                    f"padding:10px 14px;border-radius:6px;margin-bottom:8px'>"
                    f"<span style='color:#5c6bc0;font-size:11px;font-weight:bold'>YOU</span><br>"
                    f"<span style='color:#e0e0e0'>{msg['text']}</span></div>",
                    unsafe_allow_html=True,
                )

    # ── Quick prompts ──────────────────────────────────────────────────────────
    st.divider()
    st.markdown("**Quick prompts:**")
    qp_cols = st.columns(3)
    quick_prompts = [
        "What should I focus on today?",
        "Remind me what my cats need",
        "Give me a productivity tip",
        "What's a good money habit to build?",
        "Motivate me to work on my homelab",
        "Give me a content idea for my channel",
    ]
    for i, prompt in enumerate(quick_prompts):
        with qp_cols[i % 3]:
            if st.button(prompt, key=f"qp_{i}", use_container_width=True):
                with st.spinner("Jarvis..."):
                    resp = ask_jarvis(prompt)
                st.session_state["jarvis_history"].append({"role": "you", "text": prompt})
                st.session_state["jarvis_history"].append({"role": "jarvis", "text": resp})
                st.rerun()
