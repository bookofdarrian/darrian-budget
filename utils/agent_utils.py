"""
Agent lifecycle management utilities for the Agent Dashboard.
Handles: agent runs, logs, scheduling, task tracking, and Telegram notifications.
"""

from datetime import datetime, UTC
from utils.db import get_conn, execute as db_exec, USE_POSTGRES, get_setting, get_auth_conn


def _ensure_agent_tables(conn):
    """
    Create agent_runs, agent_scheduled_tasks, agent_log tables if not exist.
    Always call this at the start of any function that touches agent tables.
    """
    ph = "%s" if USE_POSTGRES else "?"
    
    # agent_runs: tracks every agent execution
    db_exec(conn, f"""
    CREATE TABLE IF NOT EXISTS agent_runs (
        id {('SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT')},
        agent_name TEXT NOT NULL,
        task_description TEXT DEFAULT '',
        display_name TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        exit_code INTEGER DEFAULT NULL,
        error_message TEXT DEFAULT '',
        logs_text TEXT DEFAULT '',
        log_entry_count INTEGER DEFAULT 0,
        started_at TEXT DEFAULT CURRENT_TIMESTAMP,
        ended_at TEXT DEFAULT NULL,
        duration_seconds REAL DEFAULT NULL,
        result_data TEXT DEFAULT NULL,
        result_file_path TEXT DEFAULT NULL,
        run_trigger TEXT DEFAULT 'cron',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Backward-compatible migrations for older agent_runs schema
    if USE_POSTGRES:
        c = db_exec(conn, """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'agent_runs'
        """)
        run_cols = {row[0] for row in c.fetchall()}
    else:
        c = db_exec(conn, "PRAGMA table_info(agent_runs)")
        run_cols = {row[1] for row in c.fetchall()}

    run_col_defs = {
        "agent_name": "TEXT DEFAULT ''",
        "task_description": "TEXT DEFAULT ''",
        "exit_code": "INTEGER DEFAULT NULL",
        "error_message": "TEXT DEFAULT ''",
        "logs_text": "TEXT DEFAULT ''",
        "log_entry_count": "INTEGER DEFAULT 0",
        "duration_seconds": "REAL DEFAULT NULL",
        "result_data": "TEXT DEFAULT NULL",
        "result_file_path": "TEXT DEFAULT NULL",
        "run_trigger": "TEXT DEFAULT 'cron'",
        "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
    }
    for col, ddl in run_col_defs.items():
        if col not in run_cols:
            db_exec(conn, f"ALTER TABLE agent_runs ADD COLUMN {col} {ddl}")

    # Seed agent_name from legacy feature_name where possible
    if "feature_name" in run_cols:
        db_exec(conn, """
            UPDATE agent_runs
            SET agent_name = COALESCE(NULLIF(agent_name, ''), feature_name)
            WHERE COALESCE(agent_name, '') = ''
        """)
    
    # agent_scheduled_tasks: schedule config
    db_exec(conn, f"""
    CREATE TABLE IF NOT EXISTS agent_scheduled_tasks (
        id {('SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT')},
        agent_name TEXT NOT NULL UNIQUE,
        display_name TEXT NOT NULL,
        description TEXT DEFAULT '',
        schedule_type TEXT DEFAULT 'daily',
        schedule_day INTEGER DEFAULT 0,
        schedule_hour INTEGER DEFAULT 7,
        schedule_minute INTEGER DEFAULT 0,
        enabled INTEGER DEFAULT 1,
        last_run TEXT DEFAULT NULL,
        next_run TEXT DEFAULT NULL,
        run_count INTEGER DEFAULT 0,
        failure_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Backward-compatible migration for older agent_scheduled_tasks schema
    if USE_POSTGRES:
        c = db_exec(conn, """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'agent_scheduled_tasks'
        """)
        sched_cols = {row[0] for row in c.fetchall()}
    else:
        c = db_exec(conn, "PRAGMA table_info(agent_scheduled_tasks)")
        sched_cols = {row[1] for row in c.fetchall()}

    sched_col_defs = {
        "agent_name": "TEXT DEFAULT ''",
        "display_name": "TEXT DEFAULT ''",
        "description": "TEXT DEFAULT ''",
        "schedule_minute": "INTEGER DEFAULT 0",
        "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
        "failure_count": "INTEGER DEFAULT 0",
    }
    for col, ddl in sched_col_defs.items():
        if col not in sched_cols:
            db_exec(conn, f"ALTER TABLE agent_scheduled_tasks ADD COLUMN {col} {ddl}")

    # Seed names from legacy columns
    if "task_name" in sched_cols:
        db_exec(conn, """
            UPDATE agent_scheduled_tasks
            SET agent_name = COALESCE(NULLIF(agent_name, ''), task_name)
            WHERE COALESCE(agent_name, '') = ''
        """)
    db_exec(conn, """
        UPDATE agent_scheduled_tasks
        SET display_name = COALESCE(NULLIF(display_name, ''), agent_name)
        WHERE COALESCE(display_name, '') = ''
    """)
    
    # agent_log: detailed log entries per run
    db_exec(conn, f"""
    CREATE TABLE IF NOT EXISTS agent_log (
        id {('SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT')},
        run_id INTEGER NOT NULL,
        level TEXT DEFAULT 'INFO',
        message TEXT NOT NULL,
        source TEXT DEFAULT 'stdout',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (run_id) REFERENCES agent_runs(id) ON DELETE CASCADE
    )
    """)

    # Backward-compatible migration for older agent_log schema
    if USE_POSTGRES:
        c = db_exec(conn, """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'agent_log'
        """)
        log_cols = {row[0] for row in c.fetchall()}
    else:
        c = db_exec(conn, "PRAGMA table_info(agent_log)")
        log_cols = {row[1] for row in c.fetchall()}

    if "source" not in log_cols:
        db_exec(conn, "ALTER TABLE agent_log ADD COLUMN source TEXT DEFAULT 'stdout'")
    
    conn.commit()


def start_agent_run(agent_name: str, task_description: str, display_name: str = None) -> int:
    """
    Start a new agent run. Returns run_id.
    Called at the beginning of agent execution.
    
    Args:
        agent_name (str): Name of the agent (e.g., 'morning-briefing')
        task_description (str): Human-readable description of what was triggered
        display_name (str, optional): Pretty display name. Auto-generated if None.
    
    Returns:
        int: The newly created run_id for tracking this execution.
    """
    conn = get_auth_conn()
    try:
        _ensure_agent_tables(conn)
        
        if display_name is None:
            display_name = agent_name.replace('-', ' ').title()
        
        ph = "%s" if USE_POSTGRES else "?"
        now = datetime.now(UTC).isoformat()
        
        db_exec(conn, f"""
        INSERT INTO agent_runs 
        (agent_name, task_description, display_name, status, started_at, created_at)
        VALUES ({ph}, {ph}, {ph}, 'running', {ph}, {ph})
        """, (agent_name, task_description, display_name, now, now))
        
        conn.commit()
        
        # Fetch the inserted row ID
        if USE_POSTGRES:
            c = db_exec(conn, "SELECT CURRVAL('agent_runs_id_seq') as id", ())
        else:
            c = db_exec(conn, "SELECT last_insert_rowid() as id", ())
        
        row = c.fetchone()
        run_id = row[0] if row else None
        
        return run_id
    finally:
        conn.close()


def log_agent_step(run_id: int, level: str, message: str, source: str = 'stdout'):
    """
    Log a single line/step during agent execution.
    
    Args:
        run_id (int): The run_id from start_agent_run()
        level (str): 'DEBUG', 'INFO', 'WARN', 'ERROR'
        message (str): The log message
        source (str): Where this came from ('stdout', 'stderr', 'agent', etc.)
    """
    conn = get_auth_conn()
    try:
        _ensure_agent_tables(conn)
        
        ph = "%s" if USE_POSTGRES else "?"
        now = datetime.now(UTC).isoformat()
        
        db_exec(conn, f"""
        INSERT INTO agent_log (run_id, level, message, source, created_at)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
        """, (run_id, level, message, source, now))
        
        conn.commit()
    finally:
        conn.close()


def end_agent_run(run_id: int, status: str, exit_code: int = 0, error_msg: str = "", result_data: str = None):
    """
    Finalize an agent run.
    
    Args:
        run_id (int): The run_id from start_agent_run()
        status (str): 'success', 'failed', 'timeout', 'pending'
        exit_code (int): 0=success, 1=error, 124=timeout
        error_msg (str): Error message if status is 'failed' or 'timeout'
        result_data (str): Optional JSON or text result to store
    """
    conn = get_auth_conn()
    try:
        _ensure_agent_tables(conn)
        
        ph = "%s" if USE_POSTGRES else "?"
        now = datetime.now(UTC).isoformat()
        
        # Fetch started_at to calculate duration
        c = db_exec(conn, f"SELECT started_at FROM agent_runs WHERE id = {ph}", (run_id,))
        row = c.fetchone()
        
        duration = None
        if row and row[0]:
            try:
                started = datetime.fromisoformat(row[0])
                ended = datetime.now(UTC)
                duration = (ended - started).total_seconds()
            except (ValueError, TypeError):
                duration = None
        
        db_exec(conn, f"""
        UPDATE agent_runs 
        SET status = {ph}, exit_code = {ph}, error_message = {ph}, 
            ended_at = {ph}, duration_seconds = {ph}, result_data = {ph}
        WHERE id = {ph}
        """, (status, exit_code, error_msg, now, duration, result_data, run_id))
        
        conn.commit()
    finally:
        conn.close()


def get_recent_runs(agent_name: str = None, limit: int = 7) -> list:
    """
    Fetch recent agent runs for display in dashboard.
    
    Args:
        agent_name (str, optional): Filter to a specific agent. If None, all agents.
        limit (int): Max rows to return (default 7)
    
    Returns:
        list of dicts: Each dict is a row from agent_runs table.
    """
    conn = get_auth_conn()
    try:
        _ensure_agent_tables(conn)
        
        ph = "%s" if USE_POSTGRES else "?"
        
        if agent_name:
            c = db_exec(conn, f"""
            SELECT id, agent_name, display_name, status, duration_seconds, 
                   error_message, started_at, exit_code
            FROM agent_runs
            WHERE agent_name = {ph}
            ORDER BY started_at DESC
            LIMIT {ph}
            """, (agent_name, limit))
        else:
            c = db_exec(conn, f"""
            SELECT id, agent_name, display_name, status, duration_seconds, 
                   error_message, started_at, exit_code
            FROM agent_runs
            ORDER BY started_at DESC
            LIMIT {ph}
            """, (limit,))
        
        rows = c.fetchall()
        
        # Convert rows to dicts for Streamlit rendering
        result = []
        if USE_POSTGRES:
            # psycopg2.extras.RealDictCursor makes rows dict-like
            for row in rows:
                result.append(dict(row))
        else:
            # sqlite3.Row is dict-like
            for row in rows:
                result.append(dict(row))
        
        return result
    finally:
        conn.close()


def get_agent_logs(run_id: int) -> list:
    """
    Fetch all log entries for a specific agent run.
    
    Args:
        run_id (int): The run_id to fetch logs for
    
    Returns:
        list of dicts: Each dict is a log entry {id, level, message, source, created_at}
    """
    conn = get_auth_conn()
    try:
        _ensure_agent_tables(conn)
        
        ph = "%s" if USE_POSTGRES else "?"
        
        c = db_exec(conn, f"""
        SELECT id, level, message, source, created_at
        FROM agent_log
        WHERE run_id = {ph}
        ORDER BY created_at ASC
        """, (run_id,))
        
        rows = c.fetchall()
        
        result = []
        for row in rows:
            result.append(dict(row))
        
        return result
    finally:
        conn.close()


def send_agent_notification(status: str, agent_name: str, run_id: int, error: str = None):
    """
    Send Telegram notification for agent status (success, failed, timeout).
    Delegates to the existing phone push notification system.
    
    Args:
        status (str): 'success', 'failed', 'timeout'
        agent_name (str): Name of the agent
        run_id (int): The run_id
        error (str, optional): Error message if status is 'failed' or 'timeout'
    """
    def _send_phone_push_fallback(message: str):
        """Best-effort Telegram notifier without hard dependency on utils.auth."""
        try:
            import requests
            token = get_setting("telegram_bot_token")
            chat_id = get_setting("telegram_chat_id")
            if not token or not chat_id:
                return
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception:
            return

    if status == 'success':
        msg = f"✅ <b>{agent_name}</b> ran successfully (run #{run_id})"
    elif status in ['failed', 'timeout']:
        error_text = error or 'Unknown error'
        msg = f"🚨 <b>{agent_name}</b> failed: {error_text} (run #{run_id})"
    else:
        return

    try:
        try:
            from utils.auth import send_phone_push  # optional in this repo state
            send_phone_push(msg)
        except Exception:
            _send_phone_push_fallback(msg)
    except Exception as e:
        # Silently fail — don't let notification errors crash the agent
        print(f"Warning: Failed to send Telegram notification: {e}")
