"""
crm/scheduler.py — Background scheduler for the Cirkanime CRM.

Fires daily follow-up checks and monthly seasonal contact briefings.

Google Calendar integration is OPTIONAL.  When credentials are absent or
GOOGLE_CALENDAR_ENABLED is not set, reminders are persisted to the local
SQLite store (local_integrations.local_reminders) instead.  The UI polls
bridge.get_local_reminders() on startup to surface any missed reminders.
"""

import os
import json
import threading
import time
from datetime import datetime, date, timedelta
from typing import Optional, Callable, Dict, Any

from crm import db as crm_db

GOOGLE_CALENDAR_ENABLED = os.environ.get("GOOGLE_CALENDAR_ENABLED", "").lower() in ("1", "true", "yes")
CHECK_INTERVAL_SECONDS  = 3600
DAILY_CHECK_HOUR        = 9
MONTHLY_CHECK_DAY       = 1

_calendar_service = None


# ---------------------------------------------------------------------------
# Google Calendar (optional)
# ---------------------------------------------------------------------------

def _init_google_calendar():
    global _calendar_service
    if not GOOGLE_CALENDAR_ENABLED:
        return
    try:
        from crm.google_auth import get_google_service
        _calendar_service = get_google_service("calendar", "v3")
        if _calendar_service:
            print("[CRM Scheduler] Google Calendar connected.")
        else:
            print("[CRM Scheduler] Google Calendar unavailable — using local fallback.")
    except Exception as e:
        print(f"[CRM Scheduler] Google Calendar init error: {e} — using local fallback.")
        _calendar_service = None


def _push_calendar_event(title: str, description: str, event_date: str = "", duration_hours: int = 1) -> bool:
    """
    Try Google Calendar first.  If unavailable, fall through to local store.
    Returns True if either path succeeded.
    """
    if not event_date:
        event_date = date.today().isoformat()

    # ── Google path ──────────────────────────────────────────────────────────
    if _calendar_service:
        try:
            start_dt = datetime.fromisoformat(f"{event_date}T{DAILY_CHECK_HOUR:02d}:00:00")
            end_dt   = start_dt + timedelta(hours=duration_hours)
            body = {
                "summary":     title,
                "description": description,
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "America/Montreal"},
                "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "America/Montreal"},
                "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 30}]},
            }
            created = _calendar_service.events().insert(calendarId="primary", body=body).execute()
            print(f"[CRM Scheduler] Calendar event: {created.get('htmlLink')}")
            return True
        except Exception as e:
            print(f"[CRM Scheduler] Google Calendar push failed: {e} — falling back to local.")

    # ── Local fallback ────────────────────────────────────────────────────────
    try:
        from crm.local_integrations import log_reminder
        log_reminder("scheduler", title, description)
        print(f"[CRM Scheduler] Reminder saved locally: {title}")
        return True
    except Exception as e:
        print(f"[CRM Scheduler] Local reminder log failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Reminder builders
# ---------------------------------------------------------------------------

def _build_followup_reminder(followups: list) -> Dict[str, Any]:
    lines = []
    for f in followups:
        org_name = f.get("org_name", f"Org #{f['org_id']}")
        lines.append(f"  - {org_name} ({f.get('status','?')}) — relance {f.get('follow_up_date','?')}")
    body = "\n".join(lines) if lines else "Aucun suivi en retard."
    return {
        "type":  "followup_reminder",
        "title": f"[CRM] {len(followups)} suivi(s) en retard",
        "body":  body,
        "count": len(followups),
        "data":  followups,
    }


def _build_seasonal_reminder(targets: list, month: int) -> Dict[str, Any]:
    names = {
        1: "Janvier", 2: "Février",  3: "Mars",     4: "Avril",
        5: "Mai",     6: "Juin",     7: "Juillet",   8: "Août",
        9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre",
    }
    mn = names.get(month, str(month))
    by_type: Dict[str, list] = {}
    for t in targets:
        by_type.setdefault(t.get("org_type", "Autre"), []).append(t)

    lines = [f"Contacts saisonniers pour {mn}:"]
    for otype, orgs in by_type.items():
        lines.append(f"\n  {otype} ({len(orgs)}):")
        for o in orgs[:5]:
            lines.append(f"    - {o['name']} ({o.get('city', '?')})")
        if len(orgs) > 5:
            lines.append(f"    ... et {len(orgs) - 5} autres")

    return {
        "type":  "seasonal_reminder",
        "title": f"[CRM] Briefing saisonnier — {mn}",
        "body":  "\n".join(lines),
        "count": len(targets),
        "data":  targets,
    }


# ---------------------------------------------------------------------------
# Scheduler loop
# ---------------------------------------------------------------------------

_scheduler_thread: Optional[threading.Thread] = None
_stop_event  = threading.Event()
_last_daily_check   = None
_last_monthly_check = None


def _scheduler_loop(on_reminder_callback: Optional[Callable] = None):
    global _last_daily_check, _last_monthly_check

    if GOOGLE_CALENDAR_ENABLED:
        _init_google_calendar()

    print("[CRM Scheduler] Started.")

    while not _stop_event.is_set():
        now      = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # ── Daily follow-up check ────────────────────────────────────────────
        if now.hour >= DAILY_CHECK_HOUR and _last_daily_check != today_str:
            _last_daily_check = today_str
            try:
                followups = crm_db.get_followups_due()
                if followups:
                    payload = _build_followup_reminder(followups)
                    if on_reminder_callback:
                        on_reminder_callback(payload)
                    _push_calendar_event(payload["title"], payload["body"])
                    print(f"[CRM Scheduler] {len(followups)} follow-up(s) due.")
            except Exception as e:
                print(f"[CRM Scheduler] Daily check error: {e}")

        # ── Monthly seasonal briefing ────────────────────────────────────────
        if now.day == MONTHLY_CHECK_DAY and now.hour >= DAILY_CHECK_HOUR and _last_monthly_check != today_str:
            _last_monthly_check = today_str
            try:
                targets = crm_db.get_seasonal_targets(month=now.month)
                if targets:
                    payload = _build_seasonal_reminder(targets, now.month)
                    if on_reminder_callback:
                        on_reminder_callback(payload)
                    _push_calendar_event(payload["title"], payload["body"], duration_hours=2)
                    print(f"[CRM Scheduler] {len(targets)} seasonal target(s).")
            except Exception as e:
                print(f"[CRM Scheduler] Monthly check error: {e}")

        _stop_event.wait(CHECK_INTERVAL_SECONDS)

    print("[CRM Scheduler] Stopped.")


def start_scheduler(on_reminder_callback: Optional[Callable] = None):
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        args=(on_reminder_callback,),
        daemon=True,
        name="crm-scheduler",
    )
    _scheduler_thread.start()


def stop_scheduler():
    _stop_event.set()


if __name__ == "__main__":
    print("=== CRM Scheduler Demo ===")
    crm_db.init_db()
    followups = crm_db.get_followups_due()
    if followups:
        print(json.dumps(_build_followup_reminder(followups), indent=2, ensure_ascii=False))
    targets = crm_db.get_seasonal_targets()
    if targets:
        print(json.dumps(_build_seasonal_reminder(targets, date.today().month), indent=2, ensure_ascii=False))

    def demo_cb(p):
        print(f"\n--- {p['title']} ---\n{p['body']}\n---")

    start_scheduler(on_reminder_callback=demo_cb)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_scheduler()
