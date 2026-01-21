"""Tests for the errors module."""

from claude_meet.errors import (
    APIKeyNotFoundError,
    AuthenticationError,
    CalendarAPIError,
    ClaudeMeetError,
    ConfigurationError,
    CredentialsNotFoundError,
    SetupIncompleteError,
    TimezoneError,
    TokenExpiredError,
)


class TestClaudeMeetError:
    """Tests for base ClaudeMeetError."""

    def test_message_only(self):
        """Error with message only."""
        error = ClaudeMeetError("Something went wrong")
        assert "Something went wrong" in str(error)

    def test_with_fix_suggestion(self):
        """Error with fix suggestion."""
        error = ClaudeMeetError("Error occurred", fix_suggestion="Try this fix")
        assert "Error occurred" in str(error)
        assert "Try this fix" in str(error)


class TestAPIKeyNotFoundError:
    """Tests for APIKeyNotFoundError."""

    def test_has_helpful_message(self):
        """Error includes helpful fix suggestions."""
        error = APIKeyNotFoundError()
        error_str = str(error)
        assert "API key not found" in error_str
        assert "console.anthropic.com" in error_str
        assert "ANTHROPIC_API_KEY" in error_str


class TestCredentialsNotFoundError:
    """Tests for CredentialsNotFoundError."""

    def test_has_helpful_message(self):
        """Error includes helpful fix suggestions."""
        error = CredentialsNotFoundError()
        error_str = str(error)
        assert "credentials" in error_str.lower()
        assert "Google Cloud Console" in error_str
        assert "claude-meet init" in error_str


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_basic_message(self):
        """Error without details."""
        error = AuthenticationError()
        assert "authentication failed" in str(error).lower()

    def test_with_details(self):
        """Error with details."""
        error = AuthenticationError("token expired")
        error_str = str(error)
        assert "token expired" in error_str
        assert "claude-meet auth" in error_str


class TestTokenExpiredError:
    """Tests for TokenExpiredError."""

    def test_has_helpful_message(self):
        """Error includes helpful fix suggestions."""
        error = TokenExpiredError()
        error_str = str(error)
        assert "expired" in error_str.lower()
        assert "claude-meet auth" in error_str


class TestCalendarAPIError:
    """Tests for CalendarAPIError."""

    def test_401_error(self):
        """401 error shows auth message."""
        error = CalendarAPIError(401)
        assert "Authentication" in str(error) or "auth" in str(error).lower()

    def test_403_error(self):
        """403 error shows permission message."""
        error = CalendarAPIError(403)
        assert "Permission" in str(error) or "denied" in str(error).lower()

    def test_404_error(self):
        """404 error shows not found message."""
        error = CalendarAPIError(404)
        assert "not found" in str(error).lower()

    def test_429_error(self):
        """429 error shows rate limit message."""
        error = CalendarAPIError(429)
        assert "rate" in str(error).lower() or "limit" in str(error).lower()

    def test_with_details(self):
        """Error includes details when provided."""
        error = CalendarAPIError(500, "Server error details")
        assert "Server error details" in str(error)


class TestTimezoneError:
    """Tests for TimezoneError."""

    def test_includes_invalid_timezone(self):
        """Error includes the invalid timezone."""
        error = TimezoneError("Invalid/Zone")
        error_str = str(error)
        assert "Invalid/Zone" in error_str
        assert "Europe/Berlin" in error_str or "UTC" in error_str


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_includes_key_and_issue(self):
        """Error includes the key and issue."""
        error = ConfigurationError("TIMEZONE", "invalid value")
        error_str = str(error)
        assert "TIMEZONE" in error_str
        assert "invalid value" in error_str


class TestSetupIncompleteError:
    """Tests for SetupIncompleteError."""

    def test_lists_missing_items(self):
        """Error lists all missing items."""
        missing = ["API key", "Google credentials"]
        error = SetupIncompleteError(missing)
        error_str = str(error)
        assert "API key" in error_str
        assert "Google credentials" in error_str
        assert "claude-meet init" in error_str
