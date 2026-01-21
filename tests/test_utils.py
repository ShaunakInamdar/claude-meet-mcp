"""Tests for the utils module."""

from datetime import date, datetime

from claude_meet.utils import (
    create_iso_datetime,
    duration_to_minutes,
    format_attendee_list,
    format_datetime_for_display,
    parse_relative_date,
    parse_time_string,
    sanitize_email,
    validate_email,
)


class TestParseRelativeDate:
    """Tests for parse_relative_date function."""

    def test_today(self):
        """'today' returns today's date."""
        result = parse_relative_date("today")
        today = date.today().strftime("%Y-%m-%d")
        assert result == today

    def test_tomorrow(self):
        """'tomorrow' returns tomorrow's date."""
        result = parse_relative_date("tomorrow")
        assert result is not None
        # Should be different from today
        today = date.today().strftime("%Y-%m-%d")
        assert result != today

    def test_next_week(self):
        """'next week' returns date 7 days from now."""
        result = parse_relative_date("next week")
        assert result is not None

    def test_iso_format_passthrough(self):
        """ISO format dates are parsed correctly."""
        result = parse_relative_date("2026-01-20")
        assert result == "2026-01-20"

    def test_day_name(self):
        """Day names return next occurrence."""
        result = parse_relative_date("monday")
        assert result is not None
        # Result should be a valid date
        datetime.strptime(result, "%Y-%m-%d")

    def test_invalid_returns_none(self):
        """Invalid input returns None."""
        result = parse_relative_date("invalid date string xyz")
        assert result is None

    def test_empty_returns_none(self):
        """Empty string returns None."""
        result = parse_relative_date("")
        assert result is None


class TestFormatDatetimeForDisplay:
    """Tests for format_datetime_for_display function."""

    def test_formats_correctly(self):
        """Formats ISO datetime to readable string."""
        result = format_datetime_for_display("2026-01-20T14:00:00-08:00")
        assert "January 20" in result
        assert "PM" in result

    def test_without_date(self):
        """Can format time only."""
        result = format_datetime_for_display("2026-01-20T14:00:00-08:00", include_date=False)
        assert "January" not in result
        assert "PM" in result


class TestCreateIsoDatetime:
    """Tests for create_iso_datetime function."""

    def test_creates_valid_iso(self):
        """Creates valid ISO datetime string."""
        result = create_iso_datetime("2026-01-20", "14:00")
        assert "2026-01-20" in result
        assert "14:00:00" in result

    def test_includes_timezone(self):
        """Result includes timezone offset."""
        result = create_iso_datetime("2026-01-20", "14:00")
        # Should have offset like -08:00 or -07:00
        assert "-0" in result or "+0" in result


class TestParseTimeString:
    """Tests for parse_time_string function."""

    def test_12_hour_format(self):
        """Parses 12-hour format."""
        result = parse_time_string("2pm")
        assert result == "14:00"

    def test_12_hour_with_minutes(self):
        """Parses 12-hour format with minutes."""
        result = parse_time_string("2:30pm")
        assert result == "14:30"

    def test_24_hour_format(self):
        """Parses 24-hour format."""
        result = parse_time_string("14:00")
        assert result == "14:00"

    def test_keywords(self):
        """Parses time keywords."""
        assert parse_time_string("morning") == "09:00"
        assert parse_time_string("noon") == "12:00"
        assert parse_time_string("afternoon") == "14:00"
        assert parse_time_string("evening") == "18:00"


class TestDurationToMinutes:
    """Tests for duration_to_minutes function."""

    def test_minutes(self):
        """Parses minute durations."""
        assert duration_to_minutes("30 minutes") == 30
        assert duration_to_minutes("30min") == 30
        assert duration_to_minutes("45m") == 45

    def test_hours(self):
        """Parses hour durations."""
        assert duration_to_minutes("1 hour") == 60
        assert duration_to_minutes("2 hours") == 120
        assert duration_to_minutes("1.5 hours") == 90

    def test_plain_number(self):
        """Plain number defaults to minutes."""
        assert duration_to_minutes("30") == 30

    def test_invalid(self):
        """Invalid input returns None."""
        assert duration_to_minutes("invalid") is None
        assert duration_to_minutes("") is None


class TestValidateEmail:
    """Tests for validate_email function."""

    def test_valid_emails(self):
        """Valid emails return True."""
        assert validate_email("user@example.com") is True
        assert validate_email("user.name@example.co.uk") is True
        assert validate_email("user+tag@example.com") is True

    def test_invalid_emails(self):
        """Invalid emails return False."""
        assert validate_email("not-an-email") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
        assert validate_email("") is False
        assert validate_email("user@nodomain") is False


class TestSanitizeEmail:
    """Tests for sanitize_email function."""

    def test_lowercase(self):
        """Converts to lowercase."""
        assert sanitize_email("User@Example.COM") == "user@example.com"

    def test_strips_whitespace(self):
        """Strips whitespace."""
        assert sanitize_email("  user@example.com  ") == "user@example.com"


class TestFormatAttendeeList:
    """Tests for format_attendee_list function."""

    def test_empty(self):
        """Empty list returns 'no attendees'."""
        assert format_attendee_list([]) == "no attendees"

    def test_single(self):
        """Single attendee returns just the email."""
        assert format_attendee_list(["alice@example.com"]) == "alice@example.com"

    def test_two(self):
        """Two attendees joined with 'and'."""
        result = format_attendee_list(["alice@example.com", "bob@example.com"])
        assert result == "alice@example.com and bob@example.com"

    def test_multiple(self):
        """Multiple attendees use Oxford comma."""
        result = format_attendee_list(["a@x.com", "b@x.com", "c@x.com"])
        assert result == "a@x.com, b@x.com, and c@x.com"
