"""
crm/google_auth.py — Centralized Google OAuth manager.
"""

import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CREDENTIALS_PATH = os.path.join(_base_dir, "credentials.json")
_TOKEN_PATH = os.path.join(_base_dir, "token.json")

def get_google_service(api_name: str, api_version: str):
    """
    Dynamically builds scopes based on .env config, gets credentials,
    and returns a built resource. Returns None if credentials.json is missing or features are disabled.
    """
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

    if not os.path.isfile(_CREDENTIALS_PATH):
        print(f"[CRM Auth] credentials.json not found at {_CREDENTIALS_PATH}")
        return None

    creds = None
    if os.path.isfile(_TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(_TOKEN_PATH, scopes)
        except Exception:
            pass

    # Does the saved token actually cover every scope we need RIGHT NOW?
    # This must be checked independently of expiry: a token can be perfectly
    # valid yet under-scoped (e.g. it was minted for Contacts only, and the
    # user has since enabled Gmail/Calendar/Drive). The previous code only
    # tested scope coverage inside the 'expired' branch, so a fresh, valid,
    # under-scoped token slipped straight through and Gmail/Calendar/Drive
    # silently failed. Treat missing scopes as a reason to re-consent.
    have_scopes = set(creds.scopes) if (creds and creds.scopes) else set()
    scopes_covered = set(scopes).issubset(have_scopes)

    def _run_consent():
        flow = InstalledAppFlow.from_client_secrets_file(_CREDENTIALS_PATH, scopes)
        return flow.run_local_server(port=0)

    if creds and creds.valid and scopes_covered:
        pass  # token is good and broad enough — nothing to do
    else:
        if creds and creds.expired and creds.refresh_token and scopes_covered:
            # Only a plain refresh is safe when scopes already match.
            try:
                creds.refresh(Request())
            except Exception:
                creds = _run_consent()
        else:
            # Either no token, an invalid one, or scopes have expanded since
            # the token was issued -> full interactive re-consent for the
            # complete current scope set.
            creds = _run_consent()

        with open(_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    try:
        return build(api_name, api_version, credentials=creds)
    except Exception as e:
        print(f"[CRM Auth] Failed to build service {api_name}: {e}")
        return None

def trigger_auth():
    """Triggers the auth flow if necessary."""
    # We can just request a lightweight service to trigger the OAuth flow
    # calendar is always a safe bet if any service is enabled.
    # But since scopes are dynamic, just getting credentials is enough.
    get_google_service("calendar", "v3") 
