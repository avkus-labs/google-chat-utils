"""
Google Drive OAuth2 Authentication Module.

Handles credentials loading from environment variables or local token files,
and manages token refresh and interactive OAuth flow.
"""

import os
from typing import Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Scopes required for searching and reading files from Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def get_drive_credentials(token_path: str = ".gdrive_token.json") -> Credentials:
    """
    Retrieves or refreshes Google Drive OAuth2 credentials.

    Priority:
    1. GDRIVE_REFRESH_TOKEN env var + GDRIVE_CLIENT_ID / GDRIVE_CLIENT_SECRET
    2. Local token file (.gdrive_token.json)
    3. Error instructing user to run 'auth-drive' command or set environment variables.
    """
    creds: Optional[Credentials] = None

    client_id = os.environ.get("GDRIVE_CLIENT_ID")
    client_secret = os.environ.get("GDRIVE_CLIENT_SECRET")
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN")

    # 1. Try env var refresh token
    if refresh_token and client_id and client_secret:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )

    # 2. Try loading from token_path if creds not initialized or invalid
    if (not creds or not creds.valid) and os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            print(f"Warning: Failed to load token from {token_path}: {e}")

    # Refresh token if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            raise RuntimeError(
                f"OAuth refresh token invalid or expired: {e}. "
                "Please check GDRIVE_REFRESH_TOKEN or run 'python utils/cli_v3.py auth-drive'."
            )

    if not creds or not creds.valid:
        raise RuntimeError(
            "Google Drive OAuth credentials not configured.\n"
            "Please set environment variables (GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN)\n"
            f"or run 'python utils/cli_v3.py auth-drive' to generate {token_path}."
        )

    return creds


def run_interactive_auth(client_secrets_file: str = "client_secret.json", token_path: str = ".gdrive_token.json"):
    """Interactive CLI authorization helper for user consent screen."""
    if not os.path.exists(client_secrets_file):
        client_id = os.environ.get("GDRIVE_CLIENT_ID")
        client_secret = os.environ.get("GDRIVE_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise FileNotFoundError(
                f"Client secrets file '{client_secrets_file}' not found, "
                "and GDRIVE_CLIENT_ID / GDRIVE_CLIENT_SECRET environment variables are missing."
            )
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)

    creds = flow.run_local_server(port=8080)

    # Save credentials locally
    with open(token_path, "w", encoding="utf-8") as token_file:
        token_file.write(creds.to_json())

    print(f"✅ Authorization successful! Token saved to {token_path}.")
    print(f"Key refresh token for env var: GDRIVE_REFRESH_TOKEN='{creds.refresh_token}'")
    return creds
