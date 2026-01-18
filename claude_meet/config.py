"""
Configuration management for Claude Calendar Scheduler.

Handles application settings, paths, and user preferences.
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """
    Application configuration container.

    Manages paths, settings, and preferences for the scheduler.
    Settings can be overridden via environment variables.
    """

    def __init__(self):
        """Initialize configuration with defaults and environment overrides."""
        # Configuration directory
        self.config_dir = Path.home() / '.claude-meet'
        self.config_dir.mkdir(exist_ok=True)

        # Credential paths
        self.token_path = self.config_dir / 'token.json'
        self.credentials_path = self.config_dir / 'credentials.json'

        # Timezone
        self.default_timezone = os.getenv('TIMEZONE', 'Europe/Berlin')

        # Business hours
        self.business_hours_start = int(os.getenv('BUSINESS_HOURS_START', '9'))
        self.business_hours_end = int(os.getenv('BUSINESS_HOURS_END', '17'))

        # Meeting defaults
        self.default_duration = int(os.getenv('DEFAULT_DURATION', '60'))
        self.max_suggestions = int(os.getenv('MAX_SUGGESTIONS', '5'))

        # Preferences
        self.prefer_morning = os.getenv('PREFER_MORNING', 'true').lower() == 'true'
        self.avoid_lunch = os.getenv('AVOID_LUNCH', 'true').lower() == 'true'

        # API settings
        self.claude_model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
        self.claude_max_tokens = int(os.getenv('CLAUDE_MAX_TOKENS', '2000'))

        # Debug settings
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')

    def get_token_path(self) -> Path:
        """Get the path to the OAuth token file."""
        return self.token_path

    def get_credentials_path(self) -> Path:
        """Get the path to the OAuth credentials file."""
        return self.credentials_path

    def get_user_timezone(self) -> str:
        """Get the user's configured timezone."""
        return self.default_timezone

    def get_business_hours(self) -> tuple:
        """Get business hours as (start, end) tuple."""
        return (self.business_hours_start, self.business_hours_end)

    def get_scheduling_preferences(self) -> dict:
        """Get scheduling preferences as a dictionary."""
        return {
            'prefer_morning': self.prefer_morning,
            'avoid_lunch': self.avoid_lunch,
            'start_hour': self.business_hours_start,
            'end_hour': self.business_hours_end,
        }

    def to_dict(self) -> dict:
        """Export configuration as a dictionary."""
        return {
            'timezone': self.default_timezone,
            'business_hours': {
                'start': self.business_hours_start,
                'end': self.business_hours_end,
            },
            'defaults': {
                'duration': self.default_duration,
                'max_suggestions': self.max_suggestions,
            },
            'preferences': {
                'prefer_morning': self.prefer_morning,
                'avoid_lunch': self.avoid_lunch,
            },
            'api': {
                'model': self.claude_model,
                'max_tokens': self.claude_max_tokens,
            },
            'debug': self.debug,
        }


def get_project_config_dir() -> Path:
    """
    Get the project's config directory path.

    Returns:
        Path: Path to the config/ directory in the project
    """
    return Path(__file__).parent.parent / 'config'


def load_api_key_from_file(filename: str = 'anthropic_apikey.txt') -> Optional[str]:
    """
    Load API key from a file in the config directory.

    Args:
        filename: Name of the file containing the API key

    Returns:
        str: The API key, or None if not found
    """
    config_dir = get_project_config_dir()
    key_file = config_dir / filename

    if key_file.exists():
        return key_file.read_text().strip()

    return None


def get_google_credentials_path() -> Optional[Path]:
    """
    Find the Google OAuth credentials file.

    Searches for:
    1. credentials.json in ~/.claude-meet/
    2. client_secret*.json in project config/

    Returns:
        Path: Path to credentials file, or None if not found
    """
    # Check user config directory
    user_creds = Path.home() / '.claude-meet' / 'credentials.json'
    if user_creds.exists():
        return user_creds

    # Check project config directory
    project_config = get_project_config_dir()
    if project_config.exists():
        client_secrets = list(project_config.glob('client_secret*.json'))
        if client_secrets:
            return client_secrets[0]

    return None
