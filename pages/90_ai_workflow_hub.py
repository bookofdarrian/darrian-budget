"""
Page 90 — AI Workflow Hub
Tina Huang's "Hyper-Specific Apps" + AI Model Guide + Vibe Coding Fundamentals
Your command center for building custom AI tools
"""

import streamlit as st
from utils.db import init_db, get_conn, execute as db_exec, get_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="AI Workflow Hub — Peach State Savings",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="auto",
)

init_db()
inject_css()
require_login()

# ─── Sidebar ─────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",          icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="Todo",           icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="Creator",        icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="Notes",          icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="Media Library",  icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant",icon="🤖")
st.sidebar.page_link("pages/89_learning_system.py",     label="🧠 Learning System",icon="🧠")
st.sidebar.page_link("pages/90_ai_workflow_hub.py",     label="⚡ AI Workflow",    icon="⚡")
render_sidebar_user_widget()

# ─── DB Setup ────────────────────────────────────────────────────────────────
USE_POSTGRES = get_setting("use_postgres") == "true"
PH = "%s" if USE_POSTGRES else "?"


def _ensure_tables():
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS hyper_specific_apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            problem_statement TEXT,
            workflow_map TEXT,
            app_scope TEXT,
            prd TEXT,
            ai_tool TEXT,
            hosting TEXT,
            status TEXT DEFAULT 'idea',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def _load_apps():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM hyper_specific_apps ORDER BY created_at DESC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def _create_app(name, category, problem, workflow, scope, prd, ai_tool, hosting, notes):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"""INSERT INTO hyper_specific_apps
        (name, category, problem_statement, workflow_map, app_scope, prd, ai_tool, hosting, notes)
        VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})""",
        (name, category, problem, workflow, scope, prd, ai_tool, hosting, notes)
    )
    conn.commit()
    conn.close()


def _update_app_status(app_id, status):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"UPDATE hyper_specific_apps SET status={PH}, updated_at=CURRENT_TIMESTAMP WHERE id={PH}",
        (status, app_id)
    )
    conn.commit()
    conn.close()


def _delete_app(app_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"DELETE FROM hyper_specific_apps WHERE id={PH}", (app_id,))
    conn.commit()
    conn.close()


def _ai_generate_prd(name, problem, workflow, scope):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ No Anthropic API key set."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompt = f"""Generate a Product Requirements Document (PRD) for a hyper-specific AI app.

App Name: {name}
Problem it solves: {problem}
Workflow it automates: {workflow}
Scope (what parts of the workflow should the app handle): {scope}

The PRD should follow Tina Huang's "Tiny Ferrets Carry Dangerous Code" framework:
- T = Thinking (logical, analytical, computational, procedural thinking about what to build)
- F = Frameworks (what existing libraries/frameworks to use)
- C = Checkpoints (version control milestones)
- D = Debugging (known edge cases to handle)
- C = Context (examples, data, specifics to give the AI coding tool)

Format as:
## Project Overview
## Skills & Tech Stack
## Key Features (Milestone 1 MVP, Milestone 2 enhancements)
## Data Requirements
## Integration Points
## Hosting Recommendation
## Frameworks to Use
## Known Edge Cases

Be specific. This PRD will be pasted directly into Cline/Claude Code/Windsurf to build the app.
Stack: Python + Streamlit (already established in peachstatesavings.com PSS system).
Use the existing utils/db.py get_conn() and utils/auth.py patterns."""

        resp = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text
    except Exception as e:
        return f"❌ AI error: {e}"


def _ai_model_advisor(use_case, requirements):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ No Anthropic API key set."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompt = f"""Darrian needs help picking the right AI model for his use case.

Use case: {use_case}
Requirements: {requirements}

Based on Tina Huang's AI model guide (flagship vs mid-tier vs light vs open source vs specialist):

1. **Recommended Model** — give the specific model name and WHY
2. **Runner-up** — second best option and when to switch to it
3. **Cost estimate** — rough API cost per 1000 queries
4. **Privacy consideration** — should this use an open source local model instead?
5. **Integration path** — how to add this to a Python/Streamlit app

Model options to consider:
- Flagship: Claude Opus 4.5, GPT-4o/5, Gemini 2.5 Pro, Grok
- Mid-tier: Claude Sonnet 4.5, GPT-4o-mini
- Light: Gemini 2.5 Flash, Claude Haiku
- Open Source: Kimi K2, Llama 3.3, Qwen
- Specialist: Perplexity Sonar (research), coding models

For Darrian's stack: Python + Streamlit + SQLite/Postgres + Anthropic API already set up.
Be blunt. Pick ONE primary recommendation."""

        resp = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text
    except Exception as e:
        return f"❌ AI error: {e}"


# ─── Main App ─────────────────────────────────────────────────────────────────
_ensure_tables()

st.title("⚡ AI Workflow Hub")
st.markdown("""
> **Tina Huang's Hyper-Specific App Framework** — Build custom AI tools for your exact problems.  
> *Identify → Map Workflow → Scope → Build with PRD → Host*  
> Average build time: 2–3 hours. Cost: $10–$20 to build, ~$0/month to run (homelab).
""")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🛠️ My Apps",
    "📋 Build a New App",
    "🤖 Model Advisor",
    "📚 Frameworks & Tools",
    "🏠 Hosting Guide"
])

# ── TAB 1: My Apps ────────────────────────────────────────────────────────────
with tab1:
    st.subheader("🛠️ My Hyper-Specific Apps")
    apps = _load_apps()

    STATUS_ICONS = {
        "idea": "💡", "planning": "📋", "building": "🔨",
        "testing": "🧪", "live": "✅", "shelved": "📦"
    }

    if not apps:
        st.info("No apps tracked yet. Use the 'Build a New App' tab to plan your first hyper-specific app.")
    else:
        # Kanban-style status view
        col_idea, col_build, col_live = st.columns(3)
        with col_idea:
            st.markdown("### 💡 Idea / Planning")
            for a in [x for x in apps if x['status'] in ['idea', 'planning']]:
                with st.container(border=True):
                    st.markdown(f"**{a['name']}**")
                    st.caption(f"Category: {a['category']}")
                    if a['problem_statement']:
                        st.markdown(f"_{a['problem_statement'][:100]}..._" if len(a['problem_statement']) > 100 else f"_{a['problem_statement']}_")
                    if st.button("▶ Start Building", key=f"start_{a['id']}"):
                        _update_app_status(a['id'], 'building')
                        st.rerun()

        with col_build:
            st.markdown("### 🔨 Building / Testing")
            for a in [x for x in apps if x['status'] in ['building', 'testing']]:
                with st.container(border=True):
                    st.markdown(f"**{a['name']}**")
                    st.caption(f"Tool: {a['ai_tool']} | Host: {a['hosting']}")
                    col_x, col_y = st.columns(2)
                    with col_x:
                        if st.button("✅ Mark Live", key=f"live_{a['id']}"):
                            _update_app_status(a['id'], 'live')
                            st.rerun()
                    with col_y:
                        if st.button("📦 Shelve", key=f"shelf_{a['id']}"):
                            _update_app_status(a['id'], 'shelved')
                            st.rerun()

        with col_live:
            st.markdown("### ✅ Live")
            for a in [x for x in apps if x['status'] == 'live']:
                with st.container(border=True):
                    st.markdown(f"**{a['name']}**")
                    st.caption(f"Host: {a['hosting']}")
                    if a['notes']:
                        st.markdown(f"_{a['notes'][:80]}_")

    # Full detail table
    if apps:
        st.markdown("---")
        st.subheader("📊 All Apps")
        for a in apps:
            with st.expander(f"{STATUS_ICONS.get(a['status'], '📋')} **{a['name']}** — {a['status'].upper()}", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Problem:** {a['problem_statement']}")
                    st.markdown(f"**Workflow:** {a['workflow_map']}")
                    st.markdown(f"**Scope:** {a['app_scope']}")
                with col2:
                    st.markdown(f"**AI Tool:** {a['ai_tool']}")
                    st.markdown(f"**Hosting:** {a['hosting']}")
                    st.markdown(f"**Category:** {a['category']}")
                if a['prd']:
                    with st.expander("📄 View PRD"):
                        st.markdown(a['prd'])
                if a['notes']:
                    st.markdown(f"**Notes:** {a['notes']}")
                status = st.selectbox(
                    "Status",
                    ["idea", "planning", "building", "testing", "live", "shelved"],
                    index=["idea", "planning", "building", "testing", "live", "shelved"].index(a['status']),
                    key=f"status_{a['id']}"
                )
                col_upd, col_del = st.columns(2)
                with col_upd:
                    if st.button("Update Status", key=f"updst_{a['id']}"):
                        _update_app_status(a['id'], status)
                        st.rerun()
                with col_del:
                    if st.button("🗑️ Delete", key=f"delapp_{a['id']}"):
                        _delete_app(a['id'])
                        st.rerun()

# ── TAB 2: Build a New App ────────────────────────────────────────────────────
with tab2:
    st.subheader("📋 Plan a Hyper-Specific App")
    st.markdown("""
    **Tina's 5-Step Process:**
    1. Identify the workflow to automate
    2. Map out the current process
    3. Identify where the app fits in that workflow
    4. Build with AI-assisted coding (PRD → AI coding tool)
    5. Host it (homelab, VPS, or cloud)
    """)

    # Category selector with examples
    st.markdown("### Step 1: What Category Does This Fall Into?")
    cat_col1, cat_col2, cat_col3 = st.columns(3)
    with cat_col1:
        with st.container(border=True):
            st.markdown("**😤 Bane of Your Existence**")
            st.markdown("Things you HAVE to do but hate:")
            st.markdown("- Accounting / bookkeeping")
            st.markdown("- Filing taxes")
            st.markdown("- Email triage")
            st.markdown("- Expense reporting")
    with cat_col2:
        with st.container(border=True):
            st.markdown("**📋 Procrastinating On**")
            st.markdown("Important but keep pushing off:")
            st.markdown("- Health/sleep tracking")
            st.markdown("- Sneaker inventory updates")
            st.markdown("- Content planning")
            st.markdown("- Financial reviews")
    with cat_col3:
        with st.container(border=True):
            st.markdown("**🚀 Want to Do But Can't**")
            st.markdown("Blocked by skills/time/resources:")
            st.markdown("- Build a trading bot")
            st.markdown("- Create a manga / art")
            st.markdown("- Build a mobile app")
            st.markdown("- Automate any creative workflow")

    st.markdown("---")
    st.markdown("### Step 2–5: Define Your App")

    with st.form("new_app_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            app_name = st.text_input("App Name", placeholder="e.g. Smart Sneaker Pricing Agent")
            app_category = st.selectbox("Category", ["Bane of Existence", "Procrastinating On", "Want But Can't"])
            app_problem = st.text_area(
                "Problem Statement (Step 2: Map the workflow)",
                placeholder="e.g. Every time I list a sneaker on eBay I have to manually check StockX + GOAT + eBay sold listings to price it. Takes 15-20 min per shoe.",
                height=120
            )
        with col_b:
            app_workflow = st.text_area(
                "Current Manual Workflow (list the steps)",
                placeholder="1. Open StockX, search shoe\n2. Open GOAT, search shoe\n3. Check eBay sold listings\n4. Average the prices\n5. Decide on listing price\n6. Write description",
                height=120
            )
            app_scope = st.text_area(
                "App Scope (which steps should the app handle?)",
                placeholder="Steps 1-5: Automate price research. Step 6: AI-generate description draft. I'll do final review and posting.",
                height=80
            )

        col_c, col_d = st.columns(2)
        with col_c:
            app_ai_tool = st.selectbox(
                "AI Coding Tool",
                ["Cline + Claude Opus (complex/full-stack)",
                 "Bolt.new (web app, no-code friendly)",
                 "Replit (beginner, cloud-based)",
                 "Windsurf/Cursor (pro developer)",
                 "Claude Code (CLI, complex projects)"],
                help="Already in your homelab: Use Cline + Claude Opus for PSS pages. For standalone web apps: Bolt.new."
            )
        with col_d:
            app_hosting = st.selectbox(
                "Hosting Plan",
                ["PSS Homelab CT100 (already paid for, free)",
                 "New Streamlit page in PSS (peachstatesavings.com)",
                 "VPS - Hetzner/DigitalOcean (~$6/mo)",
                 "Cloud - Railway/Render (free tier available)",
                 "Local only (laptop/Mac Mini)"],
                help="For PSS-integrated tools: new page in this app. For standalone tools: homelab CT100."
            )

        app_notes = st.text_area("Notes / Additional Context", placeholder="API keys needed, special requirements, deadline...")

        prd_col1, prd_col2 = st.columns(2)
        with prd_col1:
            generate_prd = st.checkbox("🤖 Auto-generate PRD with AI", value=True)
        with prd_col2:
            manual_prd = st.text_area("Or paste your own PRD", height=100)

        if st.form_submit_button("📋 Create App Plan", type="primary"):
            if app_name and app_problem:
                prd_text = manual_prd
                if generate_prd and not manual_prd:
                    with st.spinner("Generating PRD with Claude Opus..."):
                        prd_text = _ai_generate_prd(app_name, app_problem, app_workflow, app_scope)
                _create_app(
                    app_name, app_category, app_problem, app_workflow,
                    app_scope, prd_text, app_ai_tool, app_hosting, app_notes
                )
                st.success(f"✅ '{app_name}' added to your app pipeline!")
                st.rerun()
            else:
                st.error("App name and problem statement are required.")

    # PRD Template
    st.markdown("---")
    st.subheader("📄 PRD Prompt Template (copy into Claude/ChatGPT)")
    st.markdown("Use this to generate a PRD interactively with any AI chatbot:")
    st.code("""Help me build a PRD (Product Requirements Document) for a hyper-specific AI app.

Ask me these questions one by one:
1. What problem does this app solve? (be specific about the pain)
2. What is the current manual workflow? (list every step)
3. Which parts of the workflow should the app automate?
4. Who are the users? (just me, small team, public)
5. What data does it need? (inputs/outputs)
6. What integrations does it need? (APIs, databases, services)
7. What does "done" look like? (how do I know it works)
8. What are the nice-to-haves vs. must-haves?

After my answers, generate a PRD with:
- Project Overview
- Skills & Tech Stack (Python + Streamlit for peachstatesavings.com)
- Key Features (MVP first)
- Data Requirements
- Integration Points
- Hosting: CT100 homelab (100.95.125.112)
- Edge Cases & Known Challenges""", language="text")

# ── TAB 3: Model Advisor ──────────────────────────────────────────────────────
with tab3:
    st.subheader("🤖 AI Model Advisor")
    st.markdown("Tell me what you're building and I'll tell you which model to use.")

    col1, col2 = st.columns([2, 1])
    with col1:
        use_case_input = st.text_area(
            "What do you need the AI to do?",
            placeholder="e.g. Analyze my sneaker sales data, identify trends, and generate a weekly report with recommendations",
            height=100
        )
        requirements_input = st.text_area(
            "Any specific requirements?",
            placeholder="e.g. Needs to be fast (runs every morning), handle financial data (privacy important), integrate with my existing Streamlit app",
            height=80
        )
        if st.button("🎯 Recommend a Model", type="primary"):
            if use_case_input:
                with st.spinner("Analyzing your use case..."):
                    advice = _ai_model_advisor(use_case_input, requirements_input)
                st.markdown(advice)

    with col2:
        st.markdown("### Quick Reference")
        with st.container(border=True):
            st.markdown("**🏆 Flagship (Best Capability)**")
            st.markdown("- Claude Opus 4.5 → Writing & code")
            st.markdown("- GPT-4o / GPT-5 → Well-rounded")
            st.markdown("- Gemini 2.5 Pro → Multimodal/video")
            st.markdown("- Grok 4 → Highest EQ, fast")

        with st.container(border=True):
            st.markdown("**⚡ Mid-Tier (Best Balance)**")
            st.markdown("- Claude Sonnet 4.5 → Your daily driver")
            st.markdown("- GPT-4o-mini → Budget OpenAI")
            st.markdown("- Gemini 2.0 Flash → Speed + quality")

        with st.container(border=True):
            st.markdown("**🚀 Light (Speed Priority)**")
            st.markdown("- Gemini 2.5 Flash → Fastest quality")
            st.markdown("- Claude Haiku → Cheapest Claude")

        with st.container(border=True):
            st.markdown("**🔒 Open Source (Privacy)**")
            st.markdown("- Kimi K2 → Flagship quality, free")
            st.markdown("- Llama 3.3 → Run locally")
            st.markdown("- Use for: financial data, emails")

        with st.container(border=True):
            st.markdown("**🔬 Specialist**")
            st.markdown("- Perplexity Sonar → Research + citations")

    # Model comparison table
    st.markdown("---")
    st.subheader("📊 Model Comparison Table (2026)")
    st.markdown("""
    | Model | Type | Best For | Privacy | Cost | Speed |
    |-------|------|----------|---------|------|-------|
    | Claude Opus 4.5 | Flagship | Code, writing | Medium | $$$$ | Slow |
    | Claude Sonnet 4.5 | Mid-tier | Most tasks | Medium | $$ | Fast |
    | Claude Haiku | Light | Simple tasks | Medium | $ | Very Fast |
    | GPT-4o | Flagship | Well-rounded, multimodal | Low | $$$ | Medium |
    | Gemini 2.5 Pro | Flagship | Video, images, 2M context | Low | $$$ | Medium |
    | Gemini 2.5 Flash | Light | Speed-critical | Low | $ | Very Fast |
    | Grok 4 | Flagship | EQ, conversation, speed | Low | $$ | Fast |
    | Kimi K2 | Open Source | Privacy, free local run | **High** | Free | Varies |
    | Llama 3.3 | Open Source | Local/offline, privacy | **High** | Free | Varies |
    | Perplexity Sonar | Specialist | Research with citations | Medium | $$ | Medium |

    **Darrian's Default Stack:**
    - Page AI features → Claude Opus 4.5 (set in `get_setting("anthropic_api_key")`)
    - Financial analysis → Kimi/Llama locally (privacy)
    - Quick summaries → Claude Haiku
    - Research → Perplexity via web
    """)

    # Decision tree
    st.markdown("---")
    st.subheader("🌳 Quick Decision Tree")
    st.markdown("""
    ```
    Is the data PRIVATE (financial, health, emails)?
    ├─ YES → Use Open Source (Kimi K2 / Llama) running on homelab
    └─ NO → Continue...
           Is SPEED the #1 priority?
           ├─ YES → Gemini 2.5 Flash or Claude Haiku
           └─ NO → Continue...
                  Is this CODING or WRITING?
                  ├─ YES → Claude Opus 4.5 or Sonnet 4.5
                  └─ NO → Continue...
                         Is this MULTIMODAL (images/video)?
                         ├─ YES → Gemini 2.5 Pro
                         └─ NO → Use Claude Sonnet 4.5 (your daily driver)
    ```
    """)

# ── TAB 4: Frameworks & Tools ─────────────────────────────────────────────────
with tab4:
    st.subheader("📚 Vibe Coding Frameworks & Tools")
    st.markdown("The TFCDC framework from Tina's Vibe Coding Fundamentals video.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🐱 TFCDC Framework")
        st.markdown("*'The Friendly Cat Dances Constantly'*")

        with st.container(border=True):
            st.markdown("**T — Thinking** (4 levels)")
            st.markdown("1. **Logical:** What is the thing?")
            st.markdown("2. **Analytical:** How does it work?")
            st.markdown("3. **Computational:** How do I implement it?")
            st.markdown("4. **Procedural:** How do I make it excellent?")
            st.markdown("*→ This feeds into your PRD*")

        with st.container(border=True):
            st.markdown("**F — Frameworks**")
            st.markdown("Don't reinvent the wheel.")
            st.markdown("- Python + Streamlit → PSS pages")
            st.markdown("- React + Tailwind → web apps (Bolt)")
            st.markdown("- FastAPI + Postgres → APIs")
            st.markdown("- LangChain/Agno → AI agents")
            st.markdown("Ask AI: 'What frameworks exist for X?'")

        with st.container(border=True):
            st.markdown("**C — Checkpoints (Git)**")
            st.markdown("```bash")
            st.markdown("git init")
            st.markdown("git add .")
            st.markdown("git commit -m 'feat: initial MVP'")
            st.markdown("git push origin feature/my-app")
            st.markdown("```")
            st.markdown("*PSS SDLC: feature → dev → qa → staging → main*")

        with st.container(border=True):
            st.markdown("**D — Debugging**")
            st.markdown("1. Identify WHERE the problem is")
            st.markdown("2. Copy-paste exact error message to AI")
            st.markdown("3. Provide screenshot of what's wrong")
            st.markdown("4. Let AI propose fix → accept → test")
            st.markdown("5. If stuck in loop → roll back with `git reset`")

        with st.container(border=True):
            st.markdown("**C — Context**")
            st.markdown("More context = better AI output:")
            st.markdown("- Include mock-ups / wireframes")
            st.markdown("- Include example data")
            st.markdown("- Reference existing files in the codebase")
            st.markdown("- Paste full error messages, not summaries")
            st.markdown("- Screenshot the UI issue")

    with col2:
        st.markdown("### 🛠️ Tool Decision Guide")

        with st.container(border=True):
            st.markdown("**When to use Cline (VS Code) + Claude:**")
            st.markdown("✅ Adding features to existing PSS app")
            st.markdown("✅ Complex multi-file projects")
            st.markdown("✅ Full SDLC with git/testing")
            st.markdown("✅ Projects you'll maintain long-term")
            st.markdown("❌ Not great for: completely new from-scratch apps")

        with st.container(border=True):
            st.markdown("**When to use Bolt.new:**")
            st.markdown("✅ Standalone web apps (not PSS)")
            st.markdown("✅ No-code/low-code approach")
            st.markdown("✅ Quick prototypes in hours")
            st.markdown("✅ Client-facing tools")
            st.markdown("✅ Has GitHub/Notion/Linear connectors")
            st.markdown("❌ Not great for: PSS integration")

        with st.container(border=True):
            st.markdown("**When to use Replit:**")
            st.markdown("✅ Complete beginner starting out")
            st.markdown("✅ Cloud-based, no setup needed")
            st.markdown("✅ Quick experiments")
            st.markdown("❌ Not great for: complex production apps")

        with st.container(border=True):
            st.markdown("**When to use Windsurf/Cursor:**")
            st.markdown("✅ Pro developer workflows")
            st.markdown("✅ Large complex codebases")
            st.markdown("✅ Multi-developer projects")
            st.markdown("✅ Fine-tuned control over AI output")
            st.markdown("❌ Higher learning curve")

        with st.container(border=True):
            st.markdown("**When to use Claude Code (CLI):**")
            st.markdown("✅ Building large systems")
            st.markdown("✅ Multiple parallel coding agents")
            st.markdown("✅ Accounting/accounting-style workflows")
            st.markdown("✅ Advanced, experienced developers")

        st.markdown("---")
        st.markdown("### 🔄 Two Modes of Vibe Coding")
        with st.container(border=True):
            st.markdown("**Mode 1: Implementing New Feature**")
            st.markdown("→ Provide full context, frameworks, PRD")
            st.markdown("→ Make incremental changes")
            st.markdown("→ Commit after each working feature")
            st.markdown("→ Test before moving on")

        with st.container(border=True):
            st.markdown("**Mode 2: Debugging Errors**")
            st.markdown("→ Understand the project structure first")
            st.markdown("→ Copy exact error message")
            st.markdown("→ Screenshot what's wrong")
            st.markdown("→ Point to the specific file/line")
            st.markdown("→ Let AI propose fix, accept, test")
            st.markdown("→ If broken >3 cycles: `git reset`")

    st.markdown("---")
    st.markdown("### ⚡ Darrian's Hyper-Specific App Backlog (Ideas)")
    st.markdown("""
    Based on Tina's framework categories, here are apps that would upgrade your systems:

    **🤬 Bane of Existence:**
    - eBay/Mercari listing auto-generator (describe shoe → full listing)
    - Visa expense report auto-filler (receipts → corporate template)
    - Tax document organizer (upload docs → categorized summary)

    **📋 Procrastinating On:**
    - Sleep + energy tracker that feeds into learning schedule
    - Weekly financial email auto-sender (already built at page 36!)
    - Sneaker inventory photo manager (AI tags condition + notes)

    **🚀 Want But Can't:**
    - AI manga/comic generator from text (Tina's exact use case!)
    - Custom slide deck maker in your PSS brand colors
    - Voice memo → structured notes → BACKLOG.md items
    """)

# ── TAB 5: Hosting Guide ──────────────────────────────────────────────────────
with tab5:
    st.subheader("🏠 Hosting Guide — Where Should Your App Live?")
    st.markdown("Tina's 3 categories: Cloud, VPS, Own Hardware. Here's how they apply to YOUR setup.")

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("### 🏠 Own Hardware (Your Setup)")
            st.markdown("**CT100 @ 100.95.125.112**")
            st.markdown("*Like owning a home*")
            st.markdown("")
            st.markdown("**✅ Pros:**")
            st.markdown("- Already paid for")
            st.markdown("- Full privacy")
            st.markdown("- Free to run (electricity only)")
            st.markdown("- Already running PSS app")
            st.markdown("- Tailscale VPN access")
            st.markdown("")
            st.markdown("**❌ Cons:**")
            st.markdown("- You maintain everything")
            st.markdown("- Home internet = bottleneck")
            st.markdown("- If Proxmox crashes, you fix it")
            st.markdown("")
            st.markdown("**Best for:**")
            st.markdown("- New PSS pages (just add a page file)")
            st.markdown("- Personal tools (just you + Tailscale)")
            st.markdown("- Private data (finances, health, emails)")
            st.markdown("")
            st.markdown("**Deploy command:**")
            st.code("# Just add pages/XX_pagename.py\n# Streamlit auto-discovers it\ngit push origin main")

    with col2:
        with st.container(border=True):
            st.markdown("### 🏢 VPS (Hetzner/DigitalOcean)")
            st.markdown("*Like renting an apartment*")
            st.markdown("")
            st.markdown("**✅ Pros:**")
            st.markdown("- ~$4-6/month flat fee")
            st.markdown("- More reliable than home")
            st.markdown("- Public internet access")
            st.markdown("- Good for client-facing tools")
            st.markdown("")
            st.markdown("**❌ Cons:**")
            st.markdown("- Monthly cost")
            st.markdown("- You manage it")
            st.markdown("- Not fully private")
            st.markdown("")
            st.markdown("**Best for:**")
            st.markdown("- College Confused (if public-facing)")
            st.markdown("- SoleOps tools for clients")
            st.markdown("- Apps that need uptime SLA")
            st.markdown("")
            st.markdown("**Recommended:**")
            st.markdown("- Hetzner CAX11: €3.79/mo (ARM)")
            st.markdown("- DigitalOcean Droplet: $4/mo")
            st.markdown("- Coolify on VPS = app deployment GUI")

    with col3:
        with st.container(border=True):
            st.markdown("### ☁️ Cloud (Streamlit Community)")
            st.markdown("*Like a hotel room*")
            st.markdown("")
            st.markdown("**✅ Pros:**")
            st.markdown("- Free tier available")
            st.markdown("- Managed, no maintenance")
            st.markdown("- Public URL instantly")
            st.markdown("")
            st.markdown("**❌ Cons:**")
            st.markdown("- Cold starts (sleeps after inactivity)")
            st.markdown("- Not for sensitive data")
            st.markdown("- Limited compute on free tier")
            st.markdown("")
            st.markdown("**Best for:**")
            st.markdown("- Demos / prototypes")
            st.markdown("- Open source projects")
            st.markdown("- Public-facing non-sensitive apps")
            st.markdown("")
            st.markdown("**Other options:**")
            st.markdown("- Railway.app (free tier, easy deploy)")
            st.markdown("- Render.com (free tier)")
            st.markdown("- Fly.io (great free tier)")
            st.markdown("- Vercel (Next.js/frontend)")

    # College Confused specific hosting assessment
    st.markdown("---")
    st.subheader("📚 College Confused Hosting Assessment")
    st.markdown("""
    > **Blunt answer: College Confused should STAY in Streamlit/PSS for now.**

    **Why Streamlit is the right choice for CC (for now):**
    - ✅ Already built and working (pages 80-88)
    - ✅ Integrated with PSS auth/DB system
    - ✅ Running on your homelab for free
    - ✅ AI features (essay station, test prep) use existing Anthropic key
    - ✅ SDLC pipeline already set up

    **When to consider moving CC to its own platform:**
    - When you have >100 active users (Streamlit performance degrades)
    - When you want a mobile app experience
    - When you need public registration (without PSS account)
    - When you need payments/monetization

    **If/when you do move CC:**
    - Frontend: Next.js + Tailwind (build with Bolt.new)
    - Backend: FastAPI on Hetzner VPS
    - DB: Postgres (already have migrate_to_postgres.py)
    - Auth: Clerk or Supabase Auth
    - Host: Hetzner VPS + Coolify (~$6/month)

    **Current recommendation:** Keep CC in PSS. Add the Learning System (page 89) to CC pages as it directly applies to college prep. Update CC sidebar to include it.
    """)

    # Deployment cheatsheet
    st.markdown("---")
    st.subheader("🚀 Quick Deploy Cheatsheet")
    st.code("""# Deploy new PSS page to homelab
# 1. Build and test locally
python3 -m py_compile pages/XX_page.py && echo "OK"

# 2. Run tests
source venv/bin/activate && pytest tests/ -v

# 3. Commit and push
git add pages/XX_page.py tests/unit/test_XX.py
git commit -m "feat: add XX page"
git push origin feature/XX

# 4. Promote to dev → qa → staging → main
git checkout dev && git merge feature/XX && git push origin dev
# (test on dev.peachstatesavings.com)
git checkout main && git merge dev && git push origin main

# 5. Deploy to CT100 (if not auto-deploy)
ssh root@100.95.125.112
cd /opt/darrian-budget && git pull && systemctl restart streamlit""", language="bash")
