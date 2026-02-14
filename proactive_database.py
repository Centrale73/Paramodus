import aiosqlite
import asyncio
import json
import uuid
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

DB_FILE = "proactive.db"

async def init_proactive_database():
    """Initialize the proactive database tables."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS proactive_tasks (
                task_id TEXT PRIMARY KEY,
                session_id TEXT,
                task_type TEXT,
                task_config TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_execution TIMESTAMP,
                next_execution TIMESTAMP,
                execution_count INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS proactive_alerts (
                alert_id TEXT PRIMARY KEY,
                task_id TEXT,
                session_id TEXT,
                alert_type TEXT,
                message TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged BOOLEAN DEFAULT 0
            )
        """)
        await db.commit()
    logger.info("Proactive database initialized")

def init_proactive_database_sync():
    """Sync wrapper for database initialization."""
    asyncio.run(init_proactive_database())

async def create_proactive_task(session_id, task_type, task_config, interval_seconds=3600):
    """Create a new proactive task."""
    task_id = str(uuid.uuid4())
    config_str = json.dumps(task_config)
    
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            INSERT INTO proactive_tasks 
            (task_id, session_id, task_type, task_config, status)
            VALUES (?, ?, ?, ?, 'active')
        """, (task_id, session_id, task_type, config_str))
        await db.commit()
    return task_id

async def get_active_tasks():
    """Get all active tasks."""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM proactive_tasks WHERE status='active'") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_task_from_db(task_id):
    """Get a specific task."""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM proactive_tasks WHERE task_id=?", (task_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_task_execution(task_id, last_execution, execution_count):
    """Update task execution metadata."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            UPDATE proactive_tasks 
            SET last_execution=?, execution_count=?
            WHERE task_id=?
        """, (last_execution, execution_count, task_id))
        await db.commit()

async def update_next_execution(task_id, next_execution):
    """Update next scheduled execution time."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE proactive_tasks SET next_execution=? WHERE task_id=?", 
                        (next_execution, task_id))
        await db.commit()

async def update_task_status(task_id, status):
    """Update task status (active/paused)."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE proactive_tasks SET status=? WHERE task_id=?", 
                        (status, task_id))
        await db.commit()

async def create_alert(task_id, session_id, alert_type, message, data):
    """Create a new alert."""
    alert_id = str(uuid.uuid4())
    data_str = json.dumps(data)
    
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            INSERT INTO proactive_alerts 
            (alert_id, task_id, session_id, alert_type, message, data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (alert_id, task_id, session_id, alert_type, message, data_str))
        await db.commit()
    return alert_id

def get_session_tasks_sync(session_id):
    """Get tasks for a session (sync wrapper)."""
    async def _get():
        async with aiosqlite.connect(DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM proactive_tasks WHERE session_id=?", (session_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    return asyncio.run(_get())

def get_session_alerts_sync(session_id, limit=50):
    """Get alerts for a session (sync wrapper)."""
    async def _get():
        async with aiosqlite.connect(DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM proactive_alerts 
                WHERE session_id=? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (session_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    return asyncio.run(_get())

async def get_task_stats(task_id):
    """Get statistics for a specific task."""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("""
            SELECT count(*) FROM proactive_alerts WHERE task_id=?
        """, (task_id,)) as cursor:
            alert_count = (await cursor.fetchone())[0]
            
        task = await get_task_from_db(task_id)
        if not task:
            return None
            
        return {
            "execution_count": task.get("execution_count", 0),
            "alert_count": alert_count,
            "last_execution": task.get("last_execution")
        }

async def get_session_stats(session_id):
    """Get statistics for a session."""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT count(*) FROM proactive_tasks WHERE session_id=?", (session_id,)) as c1:
            task_count = (await c1.fetchone())[0]
        async with db.execute("SELECT count(*) FROM proactive_alerts WHERE session_id=?", (session_id,)) as c2:
            alert_count = (await c2.fetchone())[0]
            
        return {
            "active_tasks": task_count,
            "total_alerts": alert_count
        }

async def get_unacknowledged_count(session_id):
    """Get count of unacknowledged alerts."""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("""
            SELECT count(*) FROM proactive_alerts 
            WHERE session_id=? AND acknowledged=0
        """, (session_id,)) as cursor:
            return (await cursor.fetchone())[0]
