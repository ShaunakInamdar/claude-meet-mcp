"""
OAuth2 authentication handler for Google Calendar API.

Handles the OAuth flow, token storage, and token refresh for Google Calendar access.
"""

import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


# Google Calendar API scope - full read/write access to calendars
SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_config_dir() -> Path:
    """
    Get the configuration directory path.

    Returns:
        Path: Path to ~/.claude-meet/ directory
    """
    config_dir = Path.home() / '.claude-meet'
    config_dir.mkdir(exist_ok=True)
    return config_dir


def get_credentials_path() -> Path:
    """
    Get the path to the OAuth client credentials file.

    First checks for credentials.json in the config directory,
    then falls back to looking for client_secret*.json files.

    Returns:
        Path: Path to the credentials file

    Raises:
        FileNotFoundError: If no credentials file is found
    """
    config_dir = get_config_dir()

    # Check standard location first
    standard_path = config_dir / 'credentials.json'
    if standard_path.exists():
        return standard_path

    # Check project config directory for client_secret files
    project_config = Path(__file__).parent.parent / 'config'
    if project_config.exists():
        client_secrets = list(project_config.glob('client_secret*.json'))
        if client_secrets:
            return client_secrets[0]

    raise FileNotFoundError(
        f"Google OAuth credentials not found. "
        f"Please download OAuth credentials from Google Cloud Console and save to:\n"
        f"  {standard_path}\n"
        f"Or place client_secret*.json in the config/ directory."
    )


def get_token_path() -> Path:
    """
    Get the path to the stored OAuth token.

    Returns:
        Path: Path to token.json file
    """
    return get_config_dir() / 'token.json'


def get_calendar_credentials() -> Credentials:
    """
    Get valid Google Calendar credentials.

    Handles the full OAuth flow:
    1. Load existing token if available
    2. Refresh expired tokens automatically
    3. Run OAuth consent flow for new users
    4. Save tokens for future use

    Returns:
        Credentials: Valid Google OAuth2 credentials

    Raises:
        FileNotFoundError: If OAuth client credentials are not configured
    """
    creds = None
    token_path = get_token_path()

    # Load existing token if available
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception:
            # Token file corrupted, will re-authenticate
            pass

    # Check if credentials need refresh or new auth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired token
            try:
                creds.refresh(Request())
            except Exception:
                # Refresh failed, need to re-authenticate
                creds = None

        if not creds:
            # Run OAuth consent flow
            credentials_path = get_credentials_path()
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path),
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the credentials for future use
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())

    return creds


def get_calendar_service():
    """
    Build and return an authenticated Google Calendar service.

    This is the main entry point for getting a Calendar API client.

    Returns:
        Resource: Authenticated Google Calendar API service

    Example:
        service = get_calendar_service()
        events = service.events().list(calendarId='primary').execute()
    """
    creds = get_calendar_credentials()
    return build('calendar', 'v3', credentials=creds)


def clear_credentials():
    """
    Clear stored OAuth credentials.

    Useful for forcing re-authentication or switching accounts.
    """
    token_path = get_token_path()
    if token_path.exists():
        token_path.unlink()
