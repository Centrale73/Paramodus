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
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Check if current token has all required scopes
            if set(scopes).issubset(set(creds.scopes)):
                try:
                    creds.refresh(Request())
                except Exception:
                    flow = InstalledAppFlow.from_client_secrets_file(_CREDENTIALS_PATH, scopes)
                    creds = flow.run_local_server(port=0)
            else:
                # Scopes have expanded, need to re-auth
                flow = InstalledAppFlow.from_client_secrets_file(_CREDENTIALS_PATH, scopes)
                creds = flow.run_local_server(port=0)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(_CREDENTIALS_PATH, scopes)
            creds = flow.run_local_server(port=0)
        
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
