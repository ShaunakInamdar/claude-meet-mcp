"""
Utility functions for date/time parsing and formatting.

Provides helpers for handling natural language dates, timezone conversions,
and datetime formatting.
"""

from datetime import datetime, timedelta

import pytz
from dateutil import parser


def parse_relative_date(date_str: str, timezone: str = "Europe/Berlin") -> str | None:
    """
    Parse relative dates like 'tomorrow', 'next week', 'friday' to YYYY-MM-DD.

    Handles:
    - 'today', 'now'
    - 'tomorrow'
    - 'next week'
    - Day names: 'monday', 'tuesday', etc.
    - 'next monday', 'next friday', etc.
    - ISO format dates
    - Natural date strings (parsed by dateutil)

    Args:
        date_str: The date string to parse
        timezone: Timezone for calculating relative dates

    Returns:
        str: Date in YYYY-MM-DD format, or None if parsing fails
    """
    if not date_str:
        return None

    tz = pytz.timezone(timezone)
    today = datetime.now(tz).date()
    date_str = date_str.lower().strip()

    # Today / now
    if date_str in ["today", "now"]:
        return today.strftime("%Y-%m-%d")

    # Tomorrow
    if date_str == "tomorrow":
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    # Yesterday (for checking past events)
    if date_str == "yesterday":
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # Next week
    if date_str == "next week":
        return (today + timedelta(days=7)).strftime("%Y-%m-%d")

    # This week
    if date_str == "this week":
        return today.strftime("%Y-%m-%d")

    # End of week
    if date_str == "end of week" or date_str == "friday":
        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0 and date_str == "friday":
            days_until_friday = 7  # Next Friday if today is Friday
        return (today + timedelta(days=days_until_friday)).strftime("%Y-%m-%d")

    # Day names (get next occurrence)
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, day in enumerate(weekdays):
        if date_str == day:
            days_ahead = i - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        # "next monday", "next tuesday", etc.
        if date_str == f"next {day}":
            days_ahead = i - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # "in X days"
    if date_str.startswith("in ") and "day" in date_str:
        try:
            parts = date_str.split()
            num_days = int(parts[1])
            return (today + timedelta(days=num_days)).strftime("%Y-%m-%d")
        except (ValueError, IndexError):
            pass

    # "in X weeks"
    if date_str.startswith("in ") and "week" in date_str:
        try:
            parts = date_str.split()
            num_weeks = int(parts[1])
            return (today + timedelta(weeks=num_weeks)).strftime("%Y-%m-%d")
        except (ValueError, IndexError):
            pass

    # Try parsing as actual date with dateutil
    try:
        parsed = parser.parse(date_str, fuzzy=True)
        return parsed.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass

    return None


def format_datetime_for_display(
    dt_str: str, timezone: str = "Europe/Berlin", include_date: bool = True
) -> str:
    """
    Convert ISO datetime string to human-readable format.

    Args:
        dt_str: ISO format datetime string
        timezone: Timezone for display
        include_date: Whether to include the date in output

    Returns:
        str: Formatted datetime string like "Tuesday, January 20 at 2:00 PM PST"

    Examples:
        >>> format_datetime_for_display('2026-01-20T14:00:00-08:00')
        'Tuesday, January 20 at 2:00 PM PST'
    """
    try:
        dt = parser.parse(dt_str)
        tz = pytz.timezone(timezone)
        dt_local = dt.astimezone(tz)

        if include_date:
            return dt_local.strftime("%A, %B %d at %I:%M %p %Z")
        else:
            return dt_local.strftime("%I:%M %p %Z")
    except Exception:
        return dt_str


def create_iso_datetime(date_str: str, time_str: str, timezone: str = "Europe/Berlin") -> str:
    """
    Create ISO format datetime from date and time strings.

    Args:
        date_str: Date in YYYY-MM-DD format
        time_str: Time in HH:MM (24-hour) format
        timezone: Timezone string

    Returns:
        str: ISO format datetime with timezone

    Examples:
        >>> create_iso_datetime('2026-01-20', '14:00')
        '2026-01-20T14:00:00-08:00'
    """
    tz = pytz.timezone(timezone)
    dt_naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    dt_aware = tz.localize(dt_naive)
    return dt_aware.isoformat()


def parse_time_string(time_str: str) -> str | None:
    """
    Parse various time formats to HH:MM (24-hour).

    Handles:
    - "2pm", "2:30pm", "14:00"
    - "2 PM", "2:30 PM"
    - "morning", "afternoon", "evening"

    Args:
        time_str: Time string to parse

    Returns:
        str: Time in HH:MM format, or None if parsing fails
    """
    if not time_str:
        return None

    time_str = time_str.lower().strip()

    # Handle special keywords
    if time_str == "morning":
        return "09:00"
    if time_str == "noon":
        return "12:00"
    if time_str == "afternoon":
        return "14:00"
    if time_str == "evening":
        return "18:00"

    try:
        # Use dateutil to parse
        parsed = parser.parse(time_str)
        return parsed.strftime("%H:%M")
    except (ValueError, TypeError):
        pass

    return None


def get_timezone_offset(date_str: str, timezone: str = "Europe/Berlin") -> str:
    """
    Get the timezone offset for a specific date.

    Handles DST transitions correctly.

    Args:
        date_str: Date in YYYY-MM-DD format
        timezone: Timezone string

    Returns:
        str: Offset like '-08:00' or '-07:00'
    """
    tz = pytz.timezone(timezone)
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    localized = tz.localize(dt)
    offset = localized.strftime("%z")
    # Format as -08:00 instead of -0800
    return f"{offset[:3]}:{offset[3:]}"


def duration_to_minutes(duration_str: str) -> int | None:
    """
    Parse duration strings to minutes.

    Handles:
    - "30 minutes", "30min", "30m"
    - "1 hour", "1hr", "1h"
    - "1.5 hours", "90 minutes"

    Args:
        duration_str: Duration string to parse

    Returns:
        int: Duration in minutes, or None if parsing fails
    """
    if not duration_str:
        return None

    duration_str = duration_str.lower().strip()

    # Remove common words
    duration_str = duration_str.replace("about", "").replace("around", "").strip()

    try:
        # Pure number - assume minutes
        if duration_str.isdigit():
            return int(duration_str)

        # Hours
        if "hour" in duration_str or "hr" in duration_str or duration_str.endswith("h"):
            # Extract number
            num_str = "".join(c for c in duration_str if c.isdigit() or c == ".")
            if num_str:
                hours = float(num_str)
                return int(hours * 60)

        # Minutes
        if "min" in duration_str or duration_str.endswith("m"):
            num_str = "".join(c for c in duration_str if c.isdigit())
            if num_str:
                return int(num_str)

    except (ValueError, TypeError):
        pass

    return None


def validate_email(email: str) -> bool:
    """
    Basic email validation.

    Args:
        email: Email address to validate

    Returns:
        bool: True if email appears valid
    """
    if not email or "@" not in email:
        return False

    parts = email.split("@")
    if len(parts) != 2:
        return False

    local, domain = parts
    if not local or not domain:
        return False

    if "." not in domain:
        return False

    return True


def sanitize_email(email: str) -> str:
    """
    Sanitize and normalize an email address.

    Args:
        email: Email address to sanitize

    Returns:
        str: Lowercase, trimmed email address
    """
    return email.lower().strip()


def format_attendee_list(attendees: list) -> str:
    """
    Format a list of attendees for display.

    Args:
        attendees: List of email addresses

    Returns:
        str: Formatted string like "alice@example.com and bob@example.com"
    """
    if not attendees:
        return "no attendees"

    if len(attendees) == 1:
        return attendees[0]

    if len(attendees) == 2:
        return f"{attendees[0]} and {attendees[1]}"

    return f"{', '.join(attendees[:-1])}, and {attendees[-1]}"
