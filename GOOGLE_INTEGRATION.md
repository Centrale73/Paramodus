# Google Integration — Future Implementation Plan

Paramodus currently runs in **local mode** for all Google features.
Every function that would call Gmail, Google Calendar, Contacts, or Drive
falls back to a local SQLite database (`memory_data/local_integrations.db`)
and the UI displays a yellow badge to indicate this.

No functionality is lost in local mode — emails can be logged manually, calendar
events are stored locally, reminders fire via the scheduler and persist to SQLite.

---

## What local mode replaces

| Feature | Google (full) | Local (current) |
|---|---|---|
| Email history per org | Gmail API — reads real inbox | Manual log via UI prompt |
| Calendar events | Google Calendar — syncs to your calendar app | Local SQLite, visible in Paramodus only |
| Contact sync | Google People API | Manually entered contacts in local DB |
| Scheduler reminders | Push to Google Calendar | Stored in `local_reminders` table, shown in app on next launch |
| Drive search | Google Drive API | Not applicable (no local equivalent) |

---

## How to enable Google integrations

### Step 1 — Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. "Paramodus CRM")
3. Enable the APIs you need:
   - **Gmail API** (for email history)
   - **Google Calendar API** (for reminder sync)
   - **People API** (for contact sync)
   - **Google Drive API** (optional, for Drive search)

### Step 2 — OAuth 2.0 credentials

1. In the Cloud Console → **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Download the JSON file
5. Rename it to `credentials.json` and place it in the **project root** (same folder as `app.py`)

### Step 3 — .env configuration

Add to your `.env` (or set as environment variables):

```env
# Enable only the services you want — leave others unset or false
GOOGLE_CALENDAR_ENABLED=true
GOOGLE_GMAIL_ENABLED=true
GOOGLE_CONTACTS_ENABLED=false
GOOGLE_DRIVE_ENABLED=false
```

### Step 4 — First launch consent

On the next app start, a browser tab will open for Google OAuth consent.
Sign in with the Google account whose Gmail/Calendar you want to use.
A `token.json` file will be saved to the project root — **do not commit this file**.

`.gitignore` already excludes both files:
```
credentials.json
token.json
```

### Step 5 — Scopes granted

| Service | Scope | Access level |
|---|---|---|
| Gmail | `gmail.readonly` | Read-only — Paramodus never sends or deletes emails |
| Calendar | `calendar.events` | Read + write events only |
| Contacts | `contacts.readonly` | Read-only |
| Drive | `drive.readonly` | Read-only |

---

## Architecture notes

The integration is **additive** — enabling Google does not remove local data.

- `crm/google_auth.py` — OAuth token manager; returns `None` silently when credentials are absent
- `crm/google_tools.py` — Agno tool wrappers for Gmail, Contacts, Drive
- `crm/local_integrations.py` — SQLite fallback (always active, used as cache)
- `crm/scheduler.py` — Background reminder engine; tries Google Calendar, falls back to local
- `api/bridge.py` — Each method tries Google first, falls back to local on any failure

The fallback chain in `get_org_emails`:

```
Gmail enabled + credentials.json present?
  └─ Yes → call Gmail API
       └─ Success → return emails (source: "gmail")
       └─ Fails   → fall through ↓
  └─ No  → read local_integrations.local_emails (source: "local")
```

Same pattern for `add_calendar_event`, `get_local_reminders`, etc.

---

## Migrating local data to Google

When you connect Google, your manually-logged emails and local calendar events
stay in `local_integrations.db` — they are not automatically uploaded to Google.
This is intentional: local data is private and may contain notes not suitable
for your Google account.

If you want to migrate specific events, use the Google Calendar app directly or
build a one-time migration script using `crm/local_integrations.get_local_calendar_events()`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Browser doesn't open for consent | Check that `credentials.json` is in the project root and `GOOGLE_*_ENABLED=true` |
| `token.json` exists but Gmail still shows local | The token may be under-scoped. Delete `token.json` and restart to re-consent |
| `google-api-python-client` import error | Run `pip install google-api-python-client google-auth-oauthlib` |
| Yellow badge still showing after setup | Restart the app — env vars are read at startup |
