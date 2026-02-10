"""
OAuth2 authentication handler for Google Calendar API.

Handles the OAuth flow, token storage, and token refresh for Google Calendar access.
"""

import json
from importlib.resources import files as _resource_files
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Google Calendar API scope - full read/write access to calendars
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_config_dir() -> Path:
    """
    Get the configuration directory path.

    Returns:
        Path: Path to ~/.claude-meet/ directory
    """
    config_dir = Path.home() / ".claude-meet"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def _load_bundled_credentials() -> dict | None:
    """Load OAuth client credentials bundled with the package.

    Returns None if the bundled file is missing or still contains placeholder values.
    """
    try:
        content = _resource_files("claude_meet").joinpath("_bundled_credentials.json").read_text()
        config = json.loads(content)
        client_id = config.get("installed", {}).get("client_id", "")
        if client_id and "YOUR_CLIENT_ID" not in client_id:
            return config
    except Exception:
        pass
    return None


def has_bundled_credentials() -> bool:
    """Check whether valid credentials are bundled with the package."""
    return _load_bundled_credentials() is not None


def _get_client_config() -> dict:
    """Get OAuth client configuration.

    Priority:
        1. User-provided credentials in ~/.claude-meet/credentials.json (allows override)
        2. Credentials bundled with the package

    Raises:
        FileNotFoundError: If no valid credentials are available from either source.
    """
    user_creds = get_config_dir() / "credentials.json"
    if user_creds.exists():
        with open(user_creds) as f:
            return json.load(f)

    bundled = _load_bundled_credentials()
    if bundled:
        return bundled

    raise FileNotFoundError(
        "Google OAuth credentials not found. "
        "Run 'claude-meet init' for setup help, or place a credentials.json in "
        f"{get_config_dir()}/"
    )


def get_token_path() -> Path:
    """
    Get the path to the stored OAuth token.

    Returns:
        Path: Path to token.json file
    """
    return get_config_dir() / "token.json"


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
            client_config = _get_client_config()
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for future use
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w") as token_file:
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
    return build("calendar", "v3", credentials=creds)


def clear_credentials():
    """
    Clear stored OAuth credentials.

    Useful for forcing re-authentication or switching accounts.
    """
    token_path = get_token_path()
    if token_path.exists():
        token_path.unlink()
