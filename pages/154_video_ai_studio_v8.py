import streamlit as st
import json
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import uuid

st.set_page_config(page_title="Video AI Studio", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()


def _ph(count: int = 1) -> str:
    """Return proper placeholder(s) for SQL based on database type."""
    placeholder = "%s" if USE_POSTGRES else "?"
    if count == 1:
        return placeholder
    return ", ".join([placeholder] * count)


def _ensure_tables():
    """Create all required tables for Video AI Studio."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Video Projects table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS video_projects (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            platform TEXT DEFAULT 'youtube',
            aspect_ratio TEXT DEFAULT '16:9',
            status TEXT DEFAULT 'draft',
            target_duration INTEGER DEFAULT 60,
            hook_text TEXT,
            body_text TEXT,
            cta_text TEXT,
            full_script TEXT,
            thumbnail_concept TEXT,
            scheduled_date DATE,
            published_url TEXT,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Video Scenes table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS video_scenes (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            project_id INTEGER NOT NULL,
            scene_number INTEGER NOT NULL,
            scene_title TEXT,
            visual_description TEXT,
            dialogue TEXT,
            duration_seconds INTEGER DEFAULT 5,
            transition_type TEXT DEFAULT 'cut',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES video_projects(id) ON DELETE CASCADE
        )
    """)
    
    # Video Assets table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS video_assets (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            project_id INTEGER NOT NULL,
            scene_id INTEGER,
            asset_type TEXT NOT NULL,
            asset_name TEXT NOT NULL,
            file_path TEXT,
            source_url TEXT,
            duration_seconds REAL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES video_projects(id) ON DELETE CASCADE,
            FOREIGN KEY (scene_id) REFERENCES video_scenes(id) ON DELETE SET NULL
        )
    """)
    
    # Video Exports table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS video_exports (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            project_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            export_preset TEXT NOT NULL,
            resolution TEXT,
            file_path TEXT,
            file_size_mb REAL,
            export_status TEXT DEFAULT 'pending',
            exported_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES video_projects(id) ON DELETE CASCADE
        )
    """)
    
    # Content Calendar table for scheduled releases
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS video_calendar (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            scheduled_date DATE NOT NULL,
            scheduled_time TEXT,
            platform TEXT NOT NULL,
            status TEXT DEFAULT 'scheduled',
            reminder_sent BOOLEAN DEFAULT FALSE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES video_projects(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()


def get_user_id() -> int:
    """Get current user ID from session."""
    return st.session_state.get("user_id", 1)


def get_anthropic_client():
    """Get Anthropic client if API key is available."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return None
    try:
        from anthropic import Anthropic
        return Anthropic(api_key=api_key)
    except Exception:
        return None


def generate_script_with_ai(title: str, platform: str, target_duration: int, topic_details: str) -> Dict[str, str]:
    """Generate video script using Claude AI."""
    client = get_anthropic_client()
    if not client:
        return {
            "hook": f"[Hook for {title}] - Configure Anthropic API key in settings",
            "body": "[Body content will be generated here]",
            "cta": "[Call to action]",
            "full_script": "Please configure your Anthropic API key to generate scripts."
        }
    
    platform_guidance = {
        "youtube": "YouTube video (8-15 minutes ideal, detailed explanations, chapters)",
        "tiktok": "TikTok video (15-60 seconds, fast-paced, trending sounds, hooks in first 3 seconds)",
        "reels": "Instagram Reels (15-90 seconds, visually engaging, trending audio)",
        "shorts": "YouTube Shorts (under 60 seconds, vertical format, quick value)"
    }
    
    prompt = f"""You are a professional video scriptwriter. Create a complete video script for the following:

Title: {title}
Platform: {platform_guidance.get(platform, platform)}
Target Duration: {target_duration} seconds
Topic Details: {topic_details}

Provide the script in three distinct sections:

1. HOOK (first 3-5 seconds): A powerful opening that stops the scroll and grabs attention immediately. Use a question, bold statement, or surprising fact.

2. BODY (main content): The core value delivery. Break into clear beats/points. Include natural pauses and emphasis markers [PAUSE], [EMPHASIS], timing notes (e.g., "5 seconds").

3. CTA (call to action): A clear, compelling call to action that fits the platform (subscribe, follow, comment, link in bio, etc.)

Format your response as JSON:
{{
    "hook": "The hook text with timing markers",
    "body": "The body content with timing markers and visual cues",
    "cta": "The call to action",
    "full_script": "The complete script formatted for reading/teleprompter"
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        # Try to parse as JSON
        try:
            # Find JSON in response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass
        
        # Fallback if not valid JSON
        return {
            "hook": content[:200] if len(content) > 200 else content,
            "body": content[200:800] if len(content) > 800 else content[200:] if len(content) > 200 else "",
            "cta": content[-200:] if len(content) > 200 else "",
            "full_script": content
        }
    except Exception as e:
        return {
            "hook": f"Error generating script: {str(e)}",
            "body": "",
            "cta": "",
            "full_script": f"Error: {str(e)}"
        }


def generate_storyboard_scene(scene_description: str, scene_number: int) -> Dict[str, str]:
    """Generate visual description for a storyboard scene."""
    client = get_anthropic_client()
    if not client:
        return {
            "visual_description": f"Scene {scene_number}: {scene_description}",
            "camera_notes": "Configure API key for AI-generated descriptions",
            "b_roll_suggestions": ""
        }
    
    prompt = f"""You are a professional video storyboard artist. Create a detailed visual description for this scene:

Scene {scene_number}: {scene_description}

Provide:
1. VISUAL DESCRIPTION: Detailed description of what viewers will see (shot type, framing, lighting, colors, movement)
2. CAMERA NOTES: Camera angles, movements (pan, zoom, tracking), transitions
3. B-ROLL SUGGESTIONS: Supporting footage ideas that could enhance this scene

Format as JSON:
{{
    "visual_description": "Detailed visual description",
    "camera_notes": "Camera and movement notes",
    "b_roll_suggestions": "B-roll footage suggestions"
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass
        
        return {
            "visual_description": content,
            "camera_notes": "",
            "b_roll_suggestions": ""
        }
    except Exception as e:
        return {
            "visual_description": f"Error: {str(e)}",
            "camera_notes": "",
            "b_roll_suggestions": ""
        }


def generate_thumbnail_concept(title: str, hook: str, platform: str) -> str:
    """Generate thumbnail concept using Claude."""
    client = get_anthropic_client()
    if not client:
        return "Configure Anthropic API key to generate thumbnail concepts."
    
    prompt = f"""You are a YouTube thumbnail designer expert. Create a compelling thumbnail concept for:

Video Title: {title}
Hook: {hook}
Platform: {platform}

Provide a detailed thumbnail concept including:
1. Main visual element (what's the hero image/subject)
2. Text overlay (3-5 words max, high contrast)
3. Color scheme (2-3 dominant colors)
4. Facial expression if person is shown
5. Composition notes (rule of thirds, focal point)
6. What emotion should it evoke
7. Click-bait level (subtle intrigue vs. obvious)

Be specific enough that a designer or AI image generator could create it."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error generating concept: {str(e)}"


def prepare_voiceover_text(script: str, target_duration: int) -> str:
    """Prepare script for voiceover with timing markers."""
    client = get_anthropic_client()
    if not client:
        return script + "\n\n[Add timing markers manually]"
    
    prompt = f"""You are a professional voiceover director. Prepare this script for voiceover recording:

Script: {script}

Target Duration: {target_duration} seconds

Add:
1. [PAUSE 1s], [PAUSE 2s] markers for natural pauses
2. *emphasis* markers for words to stress
3. (breath) markers for natural breathing points
4. [SLOW] and [FAST] markers for pacing changes
5. Approximate timing for each section in brackets [0:00-0:15]

Return the marked-up script ready for voice recording."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"{script}\n\n[Error adding timing markers: {str(e)}]"


# CRUD Operations
def create_project(user_id: int, title: str, platform: str, description: str = "", 
                   target_duration: int = 60) -> int:
    """Create a new video project."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        INSERT INTO video_projects (user_id, title, description, platform, target_duration, status)
        VALUES ({_ph(6)})
        {'RETURNING id' if USE_POSTGRES else ''}
    """, (user_id, title, description, platform, target_duration, 'draft'))
    
    if USE_POSTGRES:
        project_id = cur.fetchone()[0]
    else:
        project_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return project_id


def get_projects(user_id: int, status: str = None) -> List[Dict]:
    """Get all projects for a user, optionally filtered by status."""
    conn = get_conn()
    cur = conn.cursor()
    
    if status:
        cur.execute(f"""
            SELECT * FROM video_projects 
            WHERE user_id = {_ph()} AND status = {_ph()}
            ORDER BY updated_at DESC
        """, (user_id, status))
    else:
        cur.execute(f"""
            SELECT * FROM video_projects 
            WHERE user_id = {_ph()}
            ORDER BY updated_at DESC
        """, (user_id,))
    
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]


def get_project(project_id: int) -> Optional[Dict]:
    """Get a single project by ID."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"SELECT * FROM video_projects WHERE id = {_ph()}", (project_id,))
    
    row = cur.fetchone()
    if row:
        columns = [desc[0] for desc in cur.description]
        conn.close()
        return dict(zip(columns, row))
    
    conn.close()
    return None


def update_project(project_id: int, **kwargs) -> bool:
    """Update a project with given fields."""
    if not kwargs:
        return False
    
    conn = get_conn()
    cur = conn.cursor()
    
    # Build dynamic update query
    set_clauses = []
    values = []
    for key, value in kwargs.items():
        set_clauses.append(f"{key} = {_ph()}")
        values.append(value)
    
    values.append(project_id)
    
    cur.execute(f"""
        UPDATE video_projects 
        SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
        WHERE id = {_ph()}
    """, tuple(values))
    
    conn.commit()
    conn.close()
    return True


def delete_project(project_id: int) -> bool:
    """Delete a project and all related data."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"DELETE FROM video_projects WHERE id = {_ph()}", (project_id,))
    
    conn.commit()
    conn.close()
    return True


def create_scene(project_id: int, scene_number: int, scene_title: str = "", 
                 visual_description: str = "", dialogue: str = "", 
                 duration_seconds: int = 5) -> int:
    """Create a new scene for a project."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        INSERT INTO video_scenes (project_id, scene_number, scene_title, visual_description, 
                                  dialogue, duration_seconds)
        VALUES ({_ph(6)})
        {'RETURNING id' if USE_POSTGRES else ''}
    """, (project_id, scene_number, scene_title, visual_description, dialogue, duration_seconds))
    
    if USE_POSTGRES:
        scene_id = cur.fetchone()[0]
    else:
        scene_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return scene_id


def get_scenes(project_id: int) -> List[Dict]:
    """Get all scenes for a project."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT * FROM video_scenes 
        WHERE project_id = {_ph()}
        ORDER BY scene_number ASC
    """, (project_id,))
    
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]


def update_scene(scene_id: int, **kwargs) -> bool:
    """Update a scene with given fields."""
    if not kwargs:
        return False
    
    conn = get_conn()
    cur = conn.cursor()
    
    set_clauses = []
    values = []
    for key, value in kwargs.items():
        set_clauses.append(f"{key} = {_ph()}")
        values.append(value)
    
    values.append(scene_id)
    
    cur.execute(f"""
        UPDATE video_scenes 
        SET {', '.join(set_clauses)}
        WHERE id = {_ph()}
    """, tuple(values))
    
    conn.commit()
    conn.close()
    return True


def delete_scene(scene_id: int) -> bool:
    """Delete a scene."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"DELETE FROM video_scenes WHERE id = {_ph()}", (scene_id,))
    
    conn.commit()
    conn.close()
    return True


def create_export(project_id: int, platform: str, export_preset: str, 
                  resolution: str) -> int:
    """Create an export record."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        INSERT INTO video_exports (project_id, platform, export_preset, resolution, export_status)
        VALUES ({_ph(5)})
        {'RETURNING id' if USE_POSTGRES else ''}
    """, (project_id, platform, export_preset, resolution, 'pending'))
    
    if USE_POSTGRES:
        export_id = cur.fetchone()[0]
    else:
        export_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return export_id


def get_exports(project_id: int) -> List[Dict]:
    """Get all exports for a project."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT * FROM video_exports 
        WHERE project_id = {_ph()}
        ORDER BY created_at DESC
    """, (project_id,))
    
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]


def schedule_video(project_id: int, user_id: int, scheduled_date: date, 
                   scheduled_time: str, platform: str, notes: str = "") -> int:
    """Schedule a video for release."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        INSERT INTO video_calendar (project_id, user_id, scheduled_date, scheduled_time, 
                                    platform, notes)
        VALUES ({_ph(6)})
        {'RETURNING id' if USE_POSTGRES else ''}
    """, (project_id, user_id, scheduled_date, scheduled_time, platform, notes))
    
    if USE_POSTGRES:
        cal_id = cur.fetchone()[0]
    else:
        cal_id = cur.lastrowid
    
    # Update project scheduled date
    cur.execute(f"""
        UPDATE video_projects SET scheduled_date = {_ph()} WHERE id = {_ph()}
    """, (scheduled_date, project_id))
    
    conn.commit()
    conn.close()
    return cal_id


def get_calendar_events(user_id: int, start_date: date = None, end_date: date = None) -> List[Dict]:
    """Get calendar events for a user within date range."""
    conn = get_conn()
    cur = conn.cursor()
    
    if start_date and end_date:
        cur.execute(f"""
            SELECT vc.*, vp.title as project_title 
            FROM video_calendar vc
            JOIN video_projects vp ON vc.project_id = vp.id
            WHERE vc.user_id = {_ph()} 
            AND vc.scheduled_date >= {_ph()} 
            AND vc.scheduled_date <= {_ph()}
            ORDER BY vc.scheduled_date ASC, vc.scheduled_time ASC
        """, (user_id, start_date, end_date))
    else:
        cur.execute(f"""
            SELECT vc.*, vp.title as project_title 
            FROM video_calendar vc
            JOIN video_projects vp ON vc.project_id = vp.id
            WHERE vc.user_id = {_ph()}
            ORDER BY vc.scheduled_date ASC, vc.scheduled_time ASC
        """, (user_id,))
    
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]


# Export Presets
EXPORT_PRESETS = {
    "youtube": {
        "name": "YouTube (16:9)",
        "aspect_ratio": "16:9",
        "resolutions": ["1920x1080", "2560x1440", "3840x2160"],
        "recommended": "1920x1080",
        "max_duration": None,
        "notes": "Landscape format, best for tutorials, vlogs, reviews"
    },
    "tiktok": {
        "name": "TikTok (9:16)",
        "aspect_ratio": "9:16",
        "resolutions": ["1080x1920"],
        "recommended": "1080x1920",
        "max_duration": 600,
        "notes": "Vertical format, 15s-10min, trending sounds important"
    },
    "reels": {
        "name": "Instagram Reels (9:16)",
        "aspect_ratio": "9:16",
        "resolutions": ["1080x1920"],
        "recommended": "1080x1920",
        "max_duration": 90,
        "notes": "Vertical format, 15-90 seconds, use trending audio"
    },
    "shorts": {
        "name": "YouTube Shorts (9:16)",
        "aspect_ratio": "9:16",
        "resolutions": ["1080x1920"],
        "recommended": "1080x1920",
        "max_duration": 60,
        "notes": "Vertical format, under 60 seconds, fast-paced"
    }
}


# Initialize tables
_ensure_tables()


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


# Main content
st.title("🎬 Video AI Studio V8")
st.caption("AI-powered video creation platform for YouTube, TikTok, Reels & Shorts")

user_id = get_user_id()

# Check for API key
api_key = get_setting("anthropic_api_key")
if not api_key:
    st.warning("⚠️ Configure your Anthropic API key in Settings to enable AI features.")

# Main tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📁 Projects", "✍️ Script Studio", "🎨 Storyboard", 
    "🎤 Voiceover", "📤 Export", "📅 Calendar"
])

# Project selection in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎬 Current Project")

projects = get_projects(user_id)
project_options = {p["id"]: p["title"] for p in projects}

if project_options:
    selected_project_id = st.sidebar.selectbox(
        "Select Project",
        options=list(project_options.keys()),
        format_func=lambda x: project_options[x],
        key="selected_project"
    )
    current_project = get_project(selected_project_id)
else:
    selected_project_id = None
    current_project = None
    st.sidebar.info("No projects yet. Create one in the Projects tab.")


# Tab 1: Projects Management
with tab1:
    st.header("📁 Project Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Create new project
        with st.expander("➕ Create New Project", expanded=not bool(projects)):
            with st.form("new_project_form"):
                title = st.text_input("Project Title", placeholder="My Awesome Video")
                description = st.text_area("Description", placeholder="What's this video about?")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    platform = st.selectbox(
                        "Primary Platform",
                        options=list(EXPORT_PRESETS.keys()),
                        format_func=lambda x: EXPORT_PRESETS[x]["name"]
                    )
                with col_b:
                    target_duration = st.number_input(
                        "Target Duration (seconds)",
                        min_value=15,
                        max_value=3600,
                        value=60
                    )
                
                if st.form_submit_button("Create Project", type="primary"):
                    if title:
                        project_id = create_project(user_id, title, platform, description, target_duration)
                        st.success(f"✅ Created project: {title}")
                        st.rerun()
                    else:
                        st.error("Please enter a project title.")
    
    with col2:
        # Project stats
        st.metric("Total Projects", len(projects))
        draft_count = len([p for p in projects if p["status"] == "draft"])
        in_progress_count = len([p for p in projects if p["status"] == "in_progress"])
        complete_count = len([p for p in projects if p["status"] == "complete"])
        
        st.metric("Drafts", draft_count)
        st.metric("In Progress", in_progress_count)
        st.metric("Complete", complete_count)
    
    st.markdown("---")
    
    # Project list
    st.subheader("Your Projects")
    
    status_filter = st.selectbox(
        "Filter by Status",
        options=["All", "draft", "in_progress", "complete", "published"],
        format_func=lambda x: x.replace("_", " ").title() if x != "All" else "All Projects"
    )
    
    filtered_projects = projects if status_filter == "All" else [p for p in projects if p["status"] == status_filter]
    
    if not filtered_projects:
        st.info("No projects found. Create your first project above!")
    else:
        for project in filtered_projects:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    status_emoji = {
                        "draft": "📝",
                        "in_progress": "🔄",
                        "complete": "✅",
                        "published": "🚀"
                    }
                    st.markdown(f"**{status_emoji.get(project['status'], '📄')} {project['title']}**")
                    st.caption(f"Platform: {project['platform'].upper()} | Duration: {project['target_duration']}s")
                
                with col2:
                    new_status = st.selectbox(
                        "Status",
                        options=["draft", "in_progress", "complete", "published"],
                        index=["draft", "in_progress", "complete", "published"].index(project["status"]),
                        key=f"status_{project['id']}",
                        label_visibility="collapsed"
                    )
                    if new_status != project["status"]:
                        update_project(project["id"], status=new_status)
                        st.rerun()
                
                with col3:
                    if st.button("📋", key=f"view_{project['id']}", help="View Details"):
                        st.session_state.selected_project = project["id"]
                        st.rerun()
                
                with col4:
                    if st.button("🗑️", key=f"delete_{project['id']}", help="Delete"):
                        delete_project(project["id"])
                        st.success("Project deleted")
                        st.rerun()
                
                st.markdown("---")


# Tab 2: Script Studio
with tab2:
    st.header("✍️ Script Studio")
    
    if not current_project:
        st.info("👈 Select or create a project first.")
    else:
        st.markdown(f"**Working on:** {current_project['title']}")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("🤖 AI Script Generator")
            
            topic_details = st.text_area(
                "Describe your video content",
                placeholder="What specific points do you want to cover? Who is your target audience? What's the main takeaway?",
                height=150
            )