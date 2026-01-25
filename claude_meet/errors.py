"""
Custom exceptions and error handling for Claude Calendar Scheduler.

Provides actionable error messages with fix suggestions to guide users
through common setup and configuration issues.
"""


class ClaudeMeetError(Exception):
    """Base exception for Claude Calendar Scheduler."""

    def __init__(self, message: str, fix_suggestion: str | None = None):
        self.message = message
        self.fix_suggestion = fix_suggestion
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format the error with fix suggestion if available."""
        if self.fix_suggestion:
            return f"{self.message}\n\n{self.fix_suggestion}"
        return self.message


class APIKeyNotFoundError(ClaudeMeetError):
    """Raised when the Anthropic API key is not found."""

    def __init__(self):
        super().__init__(
            message="Anthropic API key not found.",
            fix_suggestion="""To fix this:
  1. Get your API key from: https://console.anthropic.com/settings/keys
  2. Set it using one of these methods:

     Option A - Environment variable:
       export ANTHROPIC_API_KEY=sk-ant-...

     Option B - Config command:
       claude-meet config set ANTHROPIC_API_KEY=sk-ant-...

     Option C - Config file:
       echo "sk-ant-..." > ~/.claude-meet/anthropic_apikey.txt""",
        )


class CredentialsNotFoundError(ClaudeMeetError):
    """Raised when Google OAuth credentials are not found."""

    def __init__(self):
        super().__init__(
            message="Google OAuth credentials file not found.",
            fix_suggestion="""To fix this:
  1. Go to Google Cloud Console: https://console.cloud.google.com
  2. Create a project (or select existing)
  3. Enable the Google Calendar API
  4. Create OAuth 2.0 credentials (Desktop app type)
  5. Download the credentials JSON file
  6. Place it at: ~/.claude-meet/credentials.json

  Or run 'claude-meet init' for step-by-step guidance.""",
        )


class AuthenticationError(ClaudeMeetError):
    """Raised when Google Calendar authentication fails."""

    def __init__(self, details: str = ""):
        detail_msg = f" ({details})" if details else ""
        super().__init__(
            message=f"Google Calendar authentication failed{detail_msg}.",
            fix_suggestion="""To fix this:
  1. Run 'claude-meet logout' to clear existing credentials
  2. Run 'claude-meet auth' to re-authenticate

  If the issue persists:
  - Check that your credentials.json file is valid
  - Ensure you've enabled the Google Calendar API
  - Try regenerating your OAuth credentials""",
        )


class TokenExpiredError(ClaudeMeetError):
    """Raised when the OAuth token has expired and can't be refreshed."""

    def __init__(self):
        super().__init__(
            message="Google Calendar authentication token expired.",
            fix_suggestion="""To fix this:
  Run 'claude-meet auth' to re-authenticate with Google Calendar.""",
        )


class CalendarAPIError(ClaudeMeetError):
    """Raised when a Google Calendar API call fails."""

    def __init__(self, status_code: int, details: str = ""):
        messages = {
            401: "Authentication required",
            403: "Permission denied - check calendar sharing settings",
            404: "Calendar or event not found",
            429: "Rate limit exceeded - please wait and try again",
        }
        message = messages.get(status_code, f"API error (HTTP {status_code})")
        if details:
            message = f"{message}: {details}"

        fix_map = {
            401: "Run 'claude-meet auth' to re-authenticate.",
            403: "Ensure you have access to the calendar. Check sharing settings.",
            404: "Verify the calendar ID or event ID is correct.",
            429: "Wait a few minutes before trying again.",
        }
        fix = fix_map.get(status_code, "Check your internet connection and try again.")

        super().__init__(message=message, fix_suggestion=fix)


class TimezoneError(ClaudeMeetError):
    """Raised when an invalid timezone is provided."""

    def __init__(self, timezone: str):
        super().__init__(
            message=f"Invalid timezone: {timezone}",
            fix_suggestion="""To fix this:
  Run 'claude-meet setup' to select from a list of valid timezones.

  Common timezone examples:
    - Europe/Berlin
    - America/New_York
    - Asia/Tokyo
    - UTC""",
        )


class ConfigurationError(ClaudeMeetError):
    """Raised when there's a configuration problem."""

    def __init__(self, key: str, issue: str):
        super().__init__(
            message=f"Configuration error for {key}: {issue}",
            fix_suggestion=f"""To fix this:
  Run 'claude-meet config set {key}=<value>' to set the correct value.
  Run 'claude-meet config list' to see current configuration.""",
        )


class SetupIncompleteError(ClaudeMeetError):
    """Raised when setup is incomplete."""

    def __init__(self, missing_items: list):
        items_str = "\n  - ".join(missing_items)
        super().__init__(
            message=f"Setup incomplete. Missing:\n  - {items_str}",
            fix_suggestion="""To fix this:
  Run 'claude-meet init' for guided setup, or manually:

  1. Set up Google Cloud credentials (see docs/SETUP.md)
  2. Run 'claude-meet auth' to authenticate
  3. Run 'claude-meet setup' to configure timezone""",
        )


def print_error(error: Exception, debug: bool = False) -> None:
    """
    Print an error message in a user-friendly format.

    Args:
        error: The exception to print
        debug: If True, also print the full traceback
    """
    import click

    click.echo()
    if isinstance(error, ClaudeMeetError):
        click.echo(click.style("Error: ", fg="red", bold=True) + error.message)
        if error.fix_suggestion:
            click.echo()
            click.echo(click.style("How to fix:", fg="yellow"))
            click.echo(error.fix_suggestion)
    else:
        click.echo(click.style(f"Error: {str(error)}", fg="red"))

    if debug:
        click.echo()
        click.echo(click.style("Debug traceback:", fg="cyan"))
        import traceback

        traceback.print_exc()

    click.echo()
