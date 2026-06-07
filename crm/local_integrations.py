"""
crm/local_integrations.py — Local fallback layer for all Google integrations.

When Google credentials are absent or disabled, every feature that would
normally talk to Gmail / Google Calendar / Contacts / Drive falls through
to this module instead.  The SQLite schema here mirrors what the Google APIs
would return so the rest of the codebase (bridge.py, scheduler.py,
crm_panel.js) sees no difference — only the data source changes.

Tables
------
local_emails        — manually-logged email interactions per organisation
local_calendar      — CRM-managed calendar events (title, start, end, notes)
local_contacts      — organisation contact book (mirrors Google Contacts shape)
local_reminders     — scheduler-generated reminders (follow-ups + seasonal)

Future path
-----------
See GOOGLE_INTEGRATION.md.  When credentials are ready, pass
use_google=True to each public function and the call is forwarded to the
real Google API; local data is kept as a cache / offline fallback.
"""

import os
import sqlite3
from datetime import datetime, date
from typing import Optional, List, Dict, Any

# ---------------------------------------------------------------------------
# DB path
# ---------------------------------------------------------------------------

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_app_data = os.path.join(_base_dir, "memory_data")
os.makedirs(_app_data, exist_ok=True)

LOCAL_DB_PATH = os.path.join(_app_data, "local_integrations.db")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS local_emails (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id      INTEGER,              -- links to crm/db.py organisations.id
    subject     TEXT NOT NULL,
    from_addr   TEXT DEFAULT '',
    to_addr     TEXT DEFAULT '',
    sent_date   TEXT DEFAULT (date('now')),
    body        TEXT DEFAULT '',
    notes       TEXT DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS local_calendar (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    start_dt    TEXT NOT NULL,        -- ISO 8601
    end_dt      TEXT NOT NULL,
    notes       TEXT DEFAULT '',
    source      TEXT DEFAULT 'user',  -- 'user' | 'scheduler'
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS local_contacts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id       INTEGER,
    display_name TEXT NOT NULL,
    email        TEXT DEFAULT '',
    phone        TEXT DEFAULT '',
    organisation TEXT DEFAULT '',
    notes        TEXT DEFAULT '',
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS local_reminders (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    reminder_type TEXT NOT NULL,      -- 'followup' | 'seasonal'
    title        TEXT NOT NULL,
    body         TEXT DEFAULT '',
    triggered_at TEXT DEFAULT (datetime('now')),
    acknowledged INTEGER DEFAULT 0   -- 0 = unread, 1 = dismissed
);
"""


def init_local_db() -> None:
    with _conn() as conn:
        conn.executescript(_SCHEMA)
    print("[LocalDB] Initialised.")


# ---------------------------------------------------------------------------
# Local Email log  (replaces Gmail read view)
# ---------------------------------------------------------------------------

def add_local_email(
    org_id: int,
    subject: str,
    from_addr: str = "",
    to_addr: str = "",
    sent_date: str = "",
    body: str = "",
    notes: str = "",
) -> int:
    """Log an outgoing or incoming email manually."""
    if not sent_date:
        sent_date = date.today().isoformat()
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO local_emails
               (org_id, subject, from_addr, to_addr, sent_date, body, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (org_id, subject, from_addr, to_addr, sent_date, body, notes),
        )
        return cur.lastrowid


def get_local_emails(org_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Return the most recent email interactions for an organisation.
    Shape matches what the Gmail bridge returns so crm_panel.js sees
    the same structure regardless of which source is active.
    """
    with _conn() as conn:
        rows = conn.execute(
            """SELECT id, subject, from_addr AS "from", to_addr AS "to",
                      sent_date AS date, body, notes,
                      '' AS snippet
               FROM local_emails
               WHERE org_id = ?
               ORDER BY sent_date DESC
               LIMIT ?""",
            (org_id, limit),
        ).fetchall()
        emails = []
        for r in rows:
            d = dict(r)
            # Build a snippet from body for display parity with Gmail
            d["snippet"] = (d.get("body") or d.get("notes") or "")[:120]
            emails.append(d)
        return emails


# ---------------------------------------------------------------------------
# Local Calendar  (replaces Google Calendar push)
# ---------------------------------------------------------------------------

def add_local_calendar_event(
    title: str,
    start_dt: str,
    end_dt: str,
    notes: str = "",
    source: str = "user",
) -> int:
    """Store a calendar event locally."""
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO local_calendar (title, start_dt, end_dt, notes, source)
               VALUES (?, ?, ?, ?, ?)""",
            (title, start_dt, end_dt, notes, source),
        )
        return cur.lastrowid


def get_local_calendar_events(
    from_dt: Optional[str] = None,
    to_dt: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return upcoming or all calendar events, optionally filtered by date range."""
    params: list = []
    where = "1=1"
    if from_dt:
        where += " AND start_dt >= ?"
        params.append(from_dt)
    if to_dt:
        where += " AND start_dt <= ?"
        params.append(to_dt)
    params.append(limit)
    with _conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM local_calendar WHERE {where} ORDER BY start_dt LIMIT ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Local Contacts  (replaces Google People API)
# ---------------------------------------------------------------------------

def add_local_contact(
    display_name: str,
    org_id: Optional[int] = None,
    email: str = "",
    phone: str = "",
    organisation: str = "",
    notes: str = "",
) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO local_contacts
               (org_id, display_name, email, phone, organisation, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (org_id, display_name, email, phone, organisation, notes),
        )
        return cur.lastrowid


def get_local_contacts(org_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Return contacts, optionally scoped to an org.
    Shape mirrors Google People API response used by google_tools.py.
    """
    params: list = []
    where = "1=1"
    if org_id is not None:
        where += " AND org_id = ?"
        params.append(org_id)
    params.append(limit)
    with _conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM local_contacts WHERE {where} ORDER BY display_name LIMIT ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Local Reminders  (replaces Google Calendar push from scheduler)
# ---------------------------------------------------------------------------

def log_reminder(reminder_type: str, title: str, body: str = "") -> int:
    """Persist a scheduler-generated reminder so it survives app restarts."""
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO local_reminders (reminder_type, title, body) VALUES (?, ?, ?)",
            (reminder_type, title, body),
        )
        return cur.lastrowid


def get_unread_reminders() -> List[Dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM local_reminders WHERE acknowledged = 0 ORDER BY triggered_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def acknowledge_reminder(reminder_id: int) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE local_reminders SET acknowledged = 1 WHERE id = ?", (reminder_id,)
        )
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

init_local_db()
