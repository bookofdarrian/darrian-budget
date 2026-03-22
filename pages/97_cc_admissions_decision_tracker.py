import streamlit as st
import json
from datetime import datetime, date, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="CC: Admissions Decision Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ph(n=1):
    return ", ".join(["%s"] * n) if USE_POSTGRES else ", ".join(["?"] * n)

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS cc_admissions_decisions (
            id {"SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"},
            user_id INTEGER NOT NULL,
            school_name TEXT NOT NULL,
            decision_type TEXT NOT NULL,
            decision_date DATE,
            financial_aid_offered REAL DEFAULT 0,
            merit_scholarship REAL DEFAULT 0,
            need_based_aid REAL DEFAULT 0,
            total_cost REAL DEFAULT 0,
            deposit_deadline DATE,
            deposit_amount REAL DEFAULT 0,
            deposit_paid BOOLEAN DEFAULT FALSE,
            enrolled BOOLEAN DEFAULT FALSE,
            waitlist_response TEXT,
            waitlist_appeal_status TEXT,
            appeal_submitted BOOLEAN DEFAULT FALSE,
            appeal_date DATE,
            notes TEXT,
            pros TEXT,
            cons TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

_ensure_tables()

def get_decisions(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, school_name, decision_type, decision_date, financial_aid_offered,
               merit_scholarship, need_based_aid, total_cost, deposit_deadline,
               deposit_amount, deposit_paid, enrolled, waitlist_response,
               waitlist_appeal_status, appeal_submitted, appeal_date, notes, pros, cons
        FROM cc_admissions_decisions
        WHERE user_id = {_ph()}
        ORDER BY decision_date DESC NULLS LAST, school_name
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def add_decision(user_id, school_name, decision_type, decision_date, financial_aid_offered,
                 merit_scholarship, need_based_aid, total_cost, deposit_deadline,
                 deposit_amount, notes):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO cc_admissions_decisions
        (user_id, school_name, decision_type, decision_date, financial_aid_offered,
         merit_scholarship, need_based_aid, total_cost, deposit_deadline, deposit_amount, notes)
        VALUES ({_ph(11)})
    """, (user_id, school_name, decision_type, decision_date, financial_aid_offered,
          merit_scholarship, need_based_aid, total_cost, deposit_deadline, deposit_amount, notes))
    conn.commit()
    cur.close()
    conn.close()

def update_decision(dec_id, **kwargs):
    conn = get_conn()
    cur = conn.cursor()
    set_clauses = []
    values = []
    for k, v in kwargs.items():
        set_clauses.append(f"{k} = {_ph()}")
        values.append(v)
    values.append(dec_id)
    cur.execute(f"""
        UPDATE cc_admissions_decisions
        SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
        WHERE id = {_ph()}
    """, tuple(values))
    conn.commit()
    cur.close()
    conn.close()

def delete_decision(dec_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM cc_admissions_decisions WHERE id = {_ph()}", (dec_id,))
    conn.commit()
    cur.close()
    conn.close()

def analyze_decisions_with_claude(decisions, api_key):
    if not api_key:
        return "⚠️ Please configure your Anthropic API key in settings."
    
    if not decisions:
        return "No decisions to analyze yet. Add some admissions decisions first!"
    
    accepted = [d for d in decisions if d[2] == "Accepted"]
    rejected = [d for d in decisions if d[2] == "Rejected"]
    waitlisted = [d for d in decisions if d[2] == "Waitlisted"]
    deferred = [d for d in decisions if d[2] == "Deferred"]
    
    summary = f"""
Student Admissions Decision Summary:
- Total Applications: {len(decisions)}
- Accepted: {len(accepted)}
- Rejected: {len(rejected)}
- Waitlisted: {len(waitlisted)}
- Deferred: {len(deferred)}
- Acceptance Rate: {(len(accepted)/len(decisions)*100):.1f}% (personal)

Accepted Schools Details:
"""
    for d in accepted:
        aid = d[4] or 0
        cost = d[7] or 0
        net_cost = cost - aid
        summary += f"- {d[1]}: Total Aid ${aid:,.0f}, Net Cost ${net_cost:,.0f}, Deposit Deadline: {d[8] or 'Not set'}\n"
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": f"""You are a college admissions counselor analyzing a student's decision results.

{summary}

Please provide:
1. **Decision Pattern Analysis**: What patterns do you see in acceptances vs rejections?
2. **Financial Aid Assessment**: Compare the aid packages and identify the best value options
3. **Enrollment Recommendation**: Based on the data, which school(s) should the student seriously consider?
4. **Waitlist Strategy**: If waitlisted anywhere, what actions should they take?
5. **Key Deadlines**: Highlight any urgent deposit deadlines

Be specific, encouraging, and actionable. Use the actual school names and numbers provided."""
            }]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error calling Claude API: {str(e)}"

def generate_pros_cons(school_name, decision_data, api_key):
    if not api_key:
        return "Configure API key", "Configure API key"
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{
                "role": "user",
                "content": f"""Generate a brief pros and cons list for attending {school_name}.

Financial context:
- Total financial aid offered: ${decision_data.get('aid', 0):,.0f}
- Net cost after aid: ${decision_data.get('net_cost', 0):,.0f}
- Notes from student: {decision_data.get('notes', 'None provided')}

Provide exactly 3-4 bullet points for PROS and 3-4 bullet points for CONS.
Format as two sections clearly labeled PROS: and CONS:
Be specific to this school if possible, otherwise give general college selection criteria."""
            }]
        )
        
        text = response.content[0].text
        pros = ""
        cons = ""
        
        if "PROS:" in text and "CONS:" in text:
            parts = text.split("CONS:")
            pros = parts[0].replace("PROS:", "").strip()
            cons = parts[1].strip() if len(parts) > 1 else ""
        else:
            pros = text
            cons = "Unable to parse cons"
        
        return pros, cons
    except Exception as e:
        return f"Error: {str(e)}", f"Error: {str(e)}"

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎓 College Confused")
st.sidebar.page_link("pages/80_cc_home.py", label="CC Home", icon="🏠")
st.sidebar.page_link("pages/87_cc_college_list.py", label="College List", icon="📋")
st.sidebar.page_link("pages/93_cc_application_tracker.py", label="Applications", icon="📝")
st.sidebar.page_link("pages/97_cc_admissions_decision_tracker.py", label="Decisions", icon="📬")

st.title("📬 Admissions Decision Tracker")
st.markdown("Track your admissions decisions, manage waitlists, compare financial aid, and make your enrollment choice.")

user_id = st.session_state.get("user_id", 1)
api_key = get_setting("anthropic_api_key")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Dashboard", "➕ Log Decision", "⏳ Waitlist Manager",
    "📅 Deposit Deadlines", "💰 Financial Comparison", "🤖 AI Analysis"
])

decisions = get_decisions(user_id)

with tab1:
    st.subheader("📊 Decision Statistics Dashboard")
    
    if not decisions:
        st.info("No decisions logged yet. Start by adding your first admissions decision!")
    else:
        accepted = [d for d in decisions if d[2] == "Accepted"]
        rejected = [d for d in decisions if d[2] == "Rejected"]
        waitlisted = [d for d in decisions if d[2] == "Waitlisted"]
        deferred = [d for d in decisions if d[2] == "Deferred"]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Decisions", len(decisions))
        with col2:
            st.metric("✅ Accepted", len(accepted), 
                     f"{len(accepted)/len(decisions)*100:.0f}%" if decisions else "0%")
        with col3:
            st.metric("❌ Rejected", len(rejected))
        with col4:
            st.metric("⏳ Waitlisted", len(waitlisted))
        
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            st.metric("🔄 Deferred", len(deferred))
        with col6:
            enrolled = [d for d in decisions if d[11]]
            st.metric("🎓 Enrolled", len(enrolled))
        with col7:
            total_aid = sum(d[4] or 0 for d in accepted)
            st.metric("💰 Total Aid Offered", f"${total_aid:,.0f}")
        with col8:
            deposits_due = [d for d in accepted if d[8] and not d[10] and 
                          datetime.strptime(str(d[8]), "%Y-%m-%d").date() >= date.today()]
            st.metric("📅 Pending Deposits", len(deposits_due))
        
        st.markdown("---")
        st.subheader("📋 All Decisions")
        
        for dec in decisions:
            dec_id, school, dec_type, dec_date, aid, merit, need, cost, deadline, dep_amt, dep_paid, enrolled_status, wl_resp, wl_appeal, appeal_sub, appeal_dt, notes, pros, cons = dec
            
            if dec_type == "Accepted":
                icon = "✅"
                color = "green"
            elif dec_type == "Rejected":
                icon = "❌"
                color = "red"
            elif dec_type == "Waitlisted":
                icon = "⏳"
                color = "orange"
            else:
                icon = "🔄"
                color = "blue"
            
            with st.expander(f"{icon} {school} - {dec_type} ({dec_date or 'Date TBD'})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Decision Date:** {dec_date or 'Not recorded'}")
                    st.write(f"**Financial Aid:** ${aid or 0:,.0f}")
                    st.write(f"**Merit Scholarship:** ${merit or 0:,.0f}")
                    st.write(f"**Need-Based Aid:** ${need or 0:,.0f}")
                
                with col2:
                    st.write(f"**Total Cost:** ${cost or 0:,.0f}")
                    net_cost = (cost or 0) - (aid or 0)
                    st.write(f"**Net Cost:** ${net_cost:,.0f}")
                    if deadline:
                        st.write(f"**Deposit Deadline:** {deadline}")
                        st.write(f"**Deposit Amount:** ${dep_amt or 0:,.0f}")
                        st.write(f"**Deposit Paid:** {'✅ Yes' if dep_paid else '❌ No'}")
                
                if notes:
                    st.write(f"**Notes:** {notes}")
                
                if enrolled_status:
                    st.success("🎓 You are enrolled at this school!")
                
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    if dec_type == "Accepted" and not enrolled_status:
                        if st.button(f"🎓 Mark Enrolled", key=f"enroll_{dec_id}"):
                            update_decision(dec_id, enrolled=True)
                            st.success(f"Enrolled at {school}!")
                            st.rerun()
                
                with col_b:
                    if dec_type == "Accepted" and not dep_paid:
                        if st.button(f"💳 Mark Deposit Paid", key=f"deposit_{dec_id}"):
                            update_decision(dec_id, deposit_paid=True)
                            st.success("Deposit marked as paid!")
                            st.rerun()
                
                with col_c:
                    if st.button(f"🗑️ Delete", key=f"del_{dec_id}"):
                        delete_decision(dec_id)
                        st.success("Decision deleted!")
                        st.rerun()

with tab2:
    st.subheader("➕ Log New Decision")
    
    with st.form("add_decision_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            school_name = st.text_input("School Name *", placeholder="e.g., Georgia Tech")
            decision_type = st.selectbox("Decision Type *", 
                                        ["Accepted", "Rejected", "Waitlisted", "Deferred"])
            decision_date = st.date_input("Decision Date", value=date.today())
        
        with col2:
            total_cost = st.number_input("Total Cost of Attendance ($/year)", min_value=0.0, value=0.0, step=1000.0)
            financial_aid = st.number_input("Total Financial Aid ($/year)", min_value=0.0, value=0.0, step=500.0)
        
        st.markdown("**Aid Breakdown (Optional)**")
        col3, col4 = st.columns(2)
        
        with col3:
            merit_scholarship = st.number_input("Merit Scholarship ($/year)", min_value=0.0, value=0.0, step=500.0)
        
        with col4:
            need_based_aid = st.number_input("Need-Based Aid ($/year)", min_value=0.0, value=0.0, step=500.0)
        
        if decision_type == "Accepted":
            st.markdown("**Deposit Information**")
            col5, col6 = st.columns(2)
            
            with col5:
                deposit_deadline = st.date_input("Deposit Deadline", 
                                                value=date.today() + timedelta(days=30))
            with col6:
                deposit_amount = st.number_input("Deposit Amount ($)", min_value=0.0, value=500.0, step=50.0)
        else:
            deposit_deadline = None
            deposit_amount = 0.0
        
        notes = st.text_area("Notes", placeholder="Any additional thoughts about this school...")
        
        submitted = st.form_submit_button("📬 Log Decision", use_container_width=True)
        
        if submitted:
            if not school_name:
                st.error("Please enter a school name.")
            else:
                add_decision(
                    user_id=user_id,
                    school_name=school_name,
                    decision_type=decision_type,
                    decision_date=decision_date,
                    financial_aid_offered=financial_aid,
                    merit_scholarship=merit_scholarship,
                    need_based_aid=need_based_aid,
                    total_cost=total_cost,
                    deposit_deadline=deposit_deadline,
                    deposit_amount=deposit_amount,
                    notes=notes
                )
                st.success(f"✅ Logged {decision_type.lower()} from {school_name}!")
                st.rerun()

with tab3:
    st.subheader("⏳ Waitlist Manager")
    
    waitlisted = [d for d in decisions if d[2] == "Waitlisted"]
    
    if not waitlisted:
        st.info("No waitlisted schools. If you get waitlisted, you can track your response and appeal status here.")
    else:
        for dec in waitlisted:
            dec_id, school, dec_type, dec_date, aid, merit, need, cost, deadline, dep_amt, dep_paid, enrolled_status, wl_resp, wl_appeal, appeal_sub, appeal_dt, notes, pros, cons = dec
            
            with st.expander(f"⏳ {school}", expanded=True):
                st.write(f"**Waitlisted on:** {dec_date or 'Not recorded'}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Your Response**")
                    response_options = ["Pending", "Accepted Spot on Waitlist", "Declined Waitlist Spot", "Removed Self"]
                    current_resp = wl_resp if wl_resp else "Pending"
                    new_response = st.selectbox(f"Response Status", response_options, 
                                               index=response_options.index(current_resp) if current_resp in response_options else 0,
                                               key=f"wl_resp_{dec_id}")
                    
                    if new_response != current_resp:
                        if st.button(f"Update Response", key=f"update_resp_{dec_id}"):
                            update_decision(dec_id, waitlist_response=new_response)
                            st.success("Response updated!")
                            st.rerun()
                
                with col2:
                    st.markdown("**Appeal Status**")
                    appeal_options = ["Not Started", "Drafted", "Submitted", "Under Review", "Accepted", "Denied"]
                    current_appeal = wl_appeal if wl_appeal else "Not Started"
                    new_appeal = st.selectbox(f"Appeal Status", appeal_options,
                                             index=appeal_options.index(current_appeal) if current_appeal in appeal_options else 0,
                                             key=f"wl_appeal_{dec_id}")
                    
                    if new_appeal != current_appeal:
                        if st.button(f"Update Appeal", key=f"update_appeal_{dec_id}"):
                            update_decision(dec_id, waitlist_appeal_status=new_appeal)
                            st.success("Appeal status updated!")
                            st.rerun()
                
                st.markdown("---")
                st.markdown("**💡 Waitlist Tips:**")
                st.markdown("""
                1. **Respond promptly** - Let them know you want to stay on the list
                2. **Send a LOCI** - Letter of Continued Interest reaffirming your commitment
                3. **Update achievements** - Share new grades, awards, or accomplishments
                4. **Visit if possible** - Demonstrate continued interest
                5. **Have a backup plan** - Deposit at another school by May 1st
                """)

with tab4:
    st.subheader("📅 Deposit Deadline Calendar")
    
    accepted_with_deadlines = [d for d in decisions if d[2] == "Accepted" and d[8]]
    
    if not accepted_with_deadlines:
        st.info("No accepted schools with deposit deadlines. Add deposit deadlines when logging acceptances!")
    else:
        st.markdown("### ⏰ Upcoming Deadlines")
        
        today = date.today()
        
        sorted_deadlines = sorted(accepted_with_deadlines, 
                                  key=lambda x: datetime.strptime(str(x[8]), "%Y-%m-%d").date())
        
        for dec in sorted_deadlines:
            dec_id, school, dec_type, dec_date, aid, merit, need, cost, deadline, dep_amt, dep_paid, enrolled_status, wl_resp, wl_appeal, appeal_sub, appeal_dt, notes, pros, cons = dec
            
            deadline_date = datetime.strptime(str(deadline), "%Y-%m-%d").date()
            days_until = (deadline_date - today).days
            
            if dep_paid:
                status_icon = "✅"
                status_text = "PAID"
                status_color = "green"
            elif days_until < 0:
                status_icon = "🚨"
                status_text = f"OVERDUE by {abs(days_until)} days"
                status_color = "red"
            elif days_until <= 7:
                status_icon = "⚠️"
                status_text = f"{days_until} days left"
                status_color = "orange"
            elif days_until <= 14:
                status_icon = "📅"
                status_text = f"{days_until} days left"
                status_color = "yellow"
            else:
                status_icon = "📅"
                status_text = f"{days_until} days left"
                status_color = "gray"
            
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            
            with col1:
                st.write(f"**{school}**")
            with col2:
                st.write(f"📅 {deadline}")
            with col3:
                st.write(f"💵 ${dep_amt or 0:,.0f}")
            with col4:
                if dep_paid:
                    st.success(f"{status_icon} {status_text}")
                elif days_until < 0:
                    st.error(f"{status_icon} {status_text}")
                elif days_until <= 7:
                    st.warning(f"{status_icon} {status_text}")
                else:
                    st.info(f"{status_icon} {status_text}")
            
            if not dep_paid and not enrolled_status:
                if st.button(f"💳 Mark Deposit Paid for {school}", key=f"pay_dep_{dec_id}"):
                    update_decision(dec_id, deposit_paid=True)
                    st.success(f"Deposit for {school} marked as paid!")
                    st.rerun()
            
            st.markdown("---")
        
        national_deadline = date(today.year, 5, 1)
        if today < national_deadline:
            days_to_may1 = (national_deadline - today).days
            st.info(f"📌 **National Candidate Reply Date (May 1):** {days_to_may1} days away")

with tab5:
    st.subheader("💰 Financial Aid Comparison")
    
    accepted = [d for d in decisions if d[2] == "Accepted"]
    
    if not accepted:
        st.info("No accepted schools to compare. Get those acceptances! 🎉")
    else:
        comparison_data = []
        for dec in accepted:
            dec_id, school, dec_type, dec_date, aid, merit, need, cost, deadline, dep_amt, dep_paid, enrolled_status, wl_resp, wl_appeal, appeal_sub, appeal_dt, notes, pros, cons = dec
            
            net_cost = (cost or 0) - (aid or 0)
            four_year_cost = net_cost * 4
            
            comparison_data.append({
                "School": school,
                "Total COA": f"${cost or 0:,.0f}",
                "Merit Aid": f"${merit or 0:,.0f}",
                "Need Aid": f"${need or 0:,.0f}",
                "Total Aid": f"${aid or 0:,.0f}",
                "Net Cost/Year": f"${net_cost:,.0f}",
                "4-Year Cost": f"${four_year_cost:,.0f}",
                "Aid %": f"{((aid or 0)/(cost or 1)*100):.0f}%" if cost else "N/A"
            })
        
        comparison_data = sorted(comparison_data, key=lambda x: float(x["Net Cost/Year"].replace("$", "").replace(",", "")))
        
        st.dataframe(comparison_data, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("📊 Visual Comparison")
        
        import pandas as pd
        
        chart_data = []
        for dec in accepted:
            dec_id, school, dec_type, dec_date, aid, merit, need, cost, deadline, dep_amt, dep_paid, enrolled_status, wl_resp, wl_appeal, appeal_sub, appeal_dt, notes, pros, cons = dec
            net_cost = (cost or 0) - (aid or 0)
            chart_data.append({"School": school[:20], "Net Cost": net_cost, "Aid": aid or 0})
        
        df = pd.DataFrame(chart_data)
        
        if len(df) > 0:
            st.bar_chart(df.set_index("School")[["Net Cost", "Aid"]])
        
        st.markdown("---")
        st.subheader("🏆 Best Value Rankings")
        
        if comparison_data:
            st.write("**Lowest Net Cost:**")
            st.success(f"🥇 {comparison_data[0]['School']} at {comparison_data[0]['Net Cost/Year']}/year")
            
            if len(comparison_data) > 1:
                st.write(f"🥈 {comparison_data[1]['School']} at {comparison_data[1]['Net Cost/Year']}/year")
            
            if len(comparison_data) > 2:
                st.write(f"🥉 {comparison_data[2]['School']} at {comparison_data[2]['Net Cost/Year']}/year")

with tab6:
    st.subheader("🤖 AI Decision Analysis")
    
    if not api_key:
        st.warning("⚠️ Please configure your Anthropic API key in settings to use AI analysis.")
    elif not decisions:
        st.info("Add some decisions first to get AI-powered analysis!")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if st.button("🔍 Analyze My Decisions", use_container_width=True):
                with st.spinner("Claude is analyzing your admissions results..."):
                    analysis = analyze_decisions_with_claude(decisions, api_key)
                    st.session_state["decision_analysis"] = analysis
            
            if "decision_analysis" in st.session_state:
                st.markdown("### 📋 Claude's Analysis")
                st.markdown(st.session_state["decision_analysis"])
        
        with col2:
            st.markdown("### Quick Stats")
            total = len(decisions)
            accepted_count = len([d for d in decisions if d[2] == "Accepted"])
            
            if total > 0:
                st.metric("Your Acceptance Rate", f"{accepted_count/total*100:.0f}%")
                
                avg_aid = sum(d[4] or 0 for d in decisions if d[2] == "Accepted") / max(accepted_count, 1)
                st.metric("Avg Aid (Accepted)", f"${avg_aid:,.0f}")
        
        st.markdown("---")
        st.subheader("📝 Pros & Cons Generator")
        
        accepted_schools = [d for d in decisions if d[2] == "Accepted"]
        
        if not accepted_schools:
            st.info("Get accepted to some schools first!")
        else:
            selected_school = st.selectbox("Select a school for pros/cons analysis",
                                          [d[1] for d in accepted_schools])
            
            if st.button("Generate Pros & Cons", use_container_width=True):
                school_dec = next((d for d in accepted_schools if d[1] == selected_school), None)
                
                if school_dec:
                    with st.spinner(f"Generating pros & cons for {selected_school}..."):
                        dec_data = {
                            "aid": school_dec[4] or 0,
                            "net_cost": (school_dec[7] or 0) - (school_dec[4] or 0),
                            "notes": school_dec[16] or ""
                        }
                        pros, cons = generate_pros_cons(selected_school, dec_data, api_key)
                        
                        update_decision