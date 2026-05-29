"""
crm/google_tools.py — Agno tools for Gmail, Google Contacts, and Google Drive.
"""
from typing import Optional, List, Dict, Any
from agno.tools import tool
import os

def _get_service(api_name: str, api_version: str):
    from crm.google_auth import get_google_service
    return get_google_service(api_name, api_version)

@tool(name="tool_get_google_contacts", description="Fetch Google Contacts (People API). Helpful to list names and emails.")
def tool_get_google_contacts(limit: int = 50) -> str:
    service = _get_service('people', 'v1')
    if not service:
        return "Google Contacts API is not enabled or credentials are missing."
    
    try:
        results = service.people().connections().list(
            resourceName='people/me',
            pageSize=limit,
            personFields='names,emailAddresses,organizations'
        ).execute()
        connections = results.get('connections', [])
        if not connections:
            return "No contacts found."
        
        output = []
        for person in connections:
            names = person.get('names', [])
            name = names[0].get('displayName') if names else "Unknown"
            emails = person.get('emailAddresses', [])
            email = emails[0].get('value') if emails else "No email"
            orgs = person.get('organizations', [])
            org = orgs[0].get('name') if orgs else "No org"
            output.append(f"- {name} | {email} | {org}")
        return "\n".join(output)
    except Exception as e:
        return f"Error fetching contacts: {str(e)}"

@tool(name="tool_read_recent_emails", description="Search and read recent emails from Gmail. Provide a query (e.g. 'subject:hello' or 'from:boss@example.com').")
def tool_read_recent_emails(query: str = "", limit: int = 5) -> str:
    service = _get_service('gmail', 'v1')
    if not service:
        return "Gmail API is not enabled or credentials are missing."
    
    try:
        results = service.users().messages().list(userId='me', q=query, maxResults=limit).execute()
        messages = results.get('messages', [])
        if not messages:
            return "No emails found matching query."
        
        output = []
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute()
            headers = msg_data.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
            snippet = msg_data.get('snippet', '')
            output.append(f"From: {sender}\nDate: {date}\nSubject: {subject}\nSnippet: {snippet}\n---")
        return "\n".join(output)
    except Exception as e:
        return f"Error fetching emails: {str(e)}"

@tool(name="tool_search_drive", description="Search for documents in Google Drive. Provide a query string.")
def tool_search_drive(query: str = "", limit: int = 5) -> str:
    service = _get_service('drive', 'v3')
    if not service:
        return "Google Drive API is not enabled or credentials are missing."
    
    try:
        results = service.files().list(
            q=query, pageSize=limit, fields="nextPageToken, files(id, name, mimeType, modifiedTime)"
        ).execute()
        items = results.get('files', [])
        if not items:
            return "No files found."
        
        output = []
        for item in items:
            output.append(f"- {item['name']} (ID: {item['id']}, Type: {item['mimeType']}, Modified: {item['modifiedTime']})")
        return "\n".join(output)
    except Exception as e:
        return f"Error searching drive: {str(e)}"

ALL_GOOGLE_TOOLS = [tool_get_google_contacts, tool_read_recent_emails, tool_search_drive]
