"""
crm/google_auth.py — Google OAuth manager with graceful local fallback.

When credentials.json is absent OR all GOOGLE_*_ENABLED env vars are
false/unset, every function in this module returns None immediately —
no exception, no browser pop-up, no crash.  The rest of the codebase
checks the return value and falls through to crm/local_integrations.py.

To enable Google services:
  1. Create a Google Cloud project, enable the required APIs.
  2. Download OAuth 2.0 credentials → save as  <project_root>/credentials.json
  3. Set GOOGLE_CALENDAR_ENABLED=true (and/or GMAIL/CONTACTS/DRIVE) in .env
  4. On first launch Paramodus will open a browser tab for consent.
  See GOOGLE_INTEGRATION.md for the full step-by-step guide.
"""

import os

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CREDENTIALS_PATH = os.path.join(_base_dir, "credentials.json")
_TOKEN_PATH = os.path.join(_base_dir, "token.json")


def _google_enabled() -> bool:
    """Return True only when at least one Google feature flag is set AND
    credentials.json actually exists on disk."""
    any_flag = any(
        os.environ.get(k, "").lower() in ("1", "true", "yes")
        for k in (
            "GOOGLE_CALENDAR_ENABLED",
            "GOOGLE_GMAIL_ENABLED",
            "GOOGLE_CONTACTS_ENABLED",
            "GOOGLE_DRIVE_ENABLED",
        )
    )
    creds_exist = os.path.isfile(_CREDENTIALS_PATH)
    return any_flag and creds_exist


def get_google_service(api_name: str, api_version: str):
    """
    Build and return a Google API service client, or None if Google is
    not configured.  Handles token refresh and re-consent automatically.
    """
    if not _google_enabled():
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("[CRM Auth] google-api-python-client not installed. "
              "Run: pip install google-api-python-client google-auth-oauthlib")
        return None

    scopes = []
    if os.environ.get("GOOGLE_CALENDAR_ENABLED", "").lower() in ("1", "true", "yes"):
        scopes.append("https://www.googleapis.com/auth/calendar.events")
    if os.environ.get("GOOGLE_GMAIL_ENABLED", "").lower() in ("1", "true", "yes"):
        scopes.append("https://www.googleapis.com/auth/gmail.readonly")
    if os.environ.get("GOOGLE_CONTACTS_ENABLED", "").lower() in ("1", "true", "yes"):
        scopes.append("https://www.googleapis.com/auth/contacts.readonly")
    if os.environ.get("GOOGLE_DRIVE_ENABLED", "").lower() in ("1", "true", "yes"):
        scopes.append("https://www.googleapis.com/auth/drive.readonly")

    if not scopes:
        return None

    creds = None
    if os.path.isfile(_TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(_TOKEN_PATH, scopes)
        except Exception:
            pass

    have_scopes = set(creds.scopes) if (creds and creds.scopes) else set()
    scopes_covered = set(scopes).issubset(have_scopes)

    def _run_consent():
        flow = InstalledAppFlow.from_client_secrets_file(_CREDENTIALS_PATH, scopes)
        return flow.run_local_server(port=0)

    try:
        if creds and creds.valid and scopes_covered:
            pass
        elif creds and creds.expired and creds.refresh_token and scopes_covered:
            try:
                creds.refresh(Request())
            except Exception:
                creds = _run_consent()
        else:
            creds = _run_consent()

        with open(_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

        return build(api_name, api_version, credentials=creds)

    except Exception as e:
        print(f"[CRM Auth] Google auth failed for {api_name}: {e}")
        return None


def trigger_auth():
    """
    Trigger the OAuth flow proactively (called from bridge.py when the user
    enables a Google toggle in the UI).  No-op if Google is not configured.
    """
    if not _google_enabled():
        print("[CRM Auth] Google not configured — skipping auth trigger.")
        return
    get_google_service("calendar", "v3")
