"""
Intelligent scheduling logic for finding optimal meeting times.

Provides algorithms for analyzing availability, scoring time slots,
and finding mutual free times for multiple attendees.
"""

from datetime import timedelta

import pytz
from dateutil import parser


def find_mutual_availability(
    busy_periods: dict, start_time: str, end_time: str, duration_minutes: int
) -> list:
    """
    Find time slots where ALL attendees are free.

    Analyzes busy periods from multiple calendars to find common
    availability windows.

    Args:
        busy_periods: Dictionary mapping email to list of busy slots
                     {email: [{'start': str, 'end': str}, ...]}
        start_time: Search range start (ISO format)
        end_time: Search range end (ISO format)
        duration_minutes: Required meeting duration

    Returns:
        list: Available slots [{'start': str, 'end': str, 'score': int}, ...]
              Sorted by score (best options first)
    """
    # Collect all busy periods into a single list
    all_busy = []
    for email, periods in busy_periods.items():
        for period in periods:
            all_busy.append({"start": period["start"], "end": period["end"], "email": email})

    # Sort by start time
    all_busy.sort(key=lambda x: x["start"])

    # Merge overlapping periods
    merged = merge_busy_periods(all_busy)

    # Find gaps between busy periods
    free_slots = find_free_gaps(merged, start_time, end_time, duration_minutes)

    # Score each slot
    scored_slots = []
    for slot in free_slots:
        score = score_time_slot(slot["start"])
        scored_slots.append(
            {
                "start": slot["start"],
                "end": slot["end"],
                "duration_minutes": slot.get("duration_minutes", duration_minutes),
                "score": score,
            }
        )

    # Sort by score (highest first)
    scored_slots.sort(key=lambda x: x["score"], reverse=True)

    return scored_slots


def merge_busy_periods(busy_periods: list) -> list:
    """
    Merge overlapping or adjacent busy periods.

    Args:
        busy_periods: List of busy period dicts with 'start' and 'end'

    Returns:
        list: Merged busy periods
    """
    if not busy_periods:
        return []

    # Sort by start time
    sorted_periods = sorted(busy_periods, key=lambda x: x["start"])

    merged = [{"start": sorted_periods[0]["start"], "end": sorted_periods[0]["end"]}]

    for period in sorted_periods[1:]:
        last = merged[-1]

        # Check for overlap or adjacency (within 1 minute)
        last_end = parser.parse(last["end"])
        period_start = parser.parse(period["start"])

        if (period_start - last_end).total_seconds() <= 60:
            # Extend the last period
            period_end = parser.parse(period["end"])
            if period_end > last_end:
                last["end"] = period["end"]
        else:
            merged.append({"start": period["start"], "end": period["end"]})

    return merged


def find_free_gaps(busy_periods: list, range_start: str, range_end: str, min_duration: int) -> list:
    """
    Find free time gaps between busy periods.

    Args:
        busy_periods: Merged list of busy periods
        range_start: Start of search range (ISO format)
        range_end: End of search range (ISO format)
        min_duration: Minimum required gap duration in minutes

    Returns:
        list: List of free slots with duration >= min_duration
    """
    gaps = []
    current = range_start

    for busy in busy_periods:
        # Calculate gap before this busy period
        gap_minutes = time_diff_minutes(current, busy["start"])

        if gap_minutes >= min_duration:
            gaps.append({"start": current, "end": busy["start"], "duration_minutes": gap_minutes})

        # Move current pointer past the busy period
        if busy["end"] > current:
            current = busy["end"]

    # Check for gap after the last busy period
    final_gap = time_diff_minutes(current, range_end)
    if final_gap >= min_duration:
        gaps.append({"start": current, "end": range_end, "duration_minutes": final_gap})

    return gaps


def time_diff_minutes(start: str, end: str) -> int:
    """
    Calculate difference in minutes between two ISO timestamps.

    Args:
        start: Start time (ISO format)
        end: End time (ISO format)

    Returns:
        int: Difference in minutes (0 if end <= start)
    """
    try:
        start_dt = parser.parse(start)
        end_dt = parser.parse(end)
        diff = end_dt - start_dt
        minutes = int(diff.total_seconds() / 60)
        return max(0, minutes)
    except Exception:
        return 0


def score_time_slot(slot_start: str, preferences: dict | None = None) -> int:
    """
    Score a time slot based on scheduling preferences.

    Higher scores indicate more desirable meeting times.

    Scoring criteria (default):
    - Early morning (9-11am): +10 points (prime focus time)
    - Late morning (11am-12pm): +5 points
    - Lunch time (12-1pm): -10 points (avoid lunch conflicts)
    - Early afternoon (1-3pm): +5 points (post-lunch productivity)
    - Late afternoon (3-5pm): 0 points (acceptable)
    - Before 9am: -15 points (too early for most)
    - After 5pm: -20 points (outside business hours)

    Args:
        slot_start: Slot start time (ISO format)
        preferences: Optional dict with:
            - prefer_morning: bool
            - prefer_afternoon: bool
            - avoid_lunch: bool (default True)

    Returns:
        int: Score for the time slot
    """
    try:
        dt = parser.parse(slot_start)
        hour = dt.hour
        minute = dt.minute
    except Exception:
        return 0

    # Base score
    score = 50

    # Time-based scoring
    if hour < 9:
        score -= 15  # Too early
    elif 9 <= hour < 11:
        score += 10  # Prime morning time
    elif 11 <= hour < 12:
        score += 5  # Late morning
    elif 12 <= hour < 13:
        score -= 10  # Lunch time
    elif 13 <= hour < 15:
        score += 5  # Early afternoon
    elif 15 <= hour < 17:
        score += 0  # Late afternoon (neutral)
    else:
        score -= 20  # After hours

    # Apply preferences if provided
    if preferences:
        if preferences.get("prefer_morning") and 9 <= hour < 12:
            score += 10
        if preferences.get("prefer_afternoon") and 13 <= hour < 17:
            score += 10
        if preferences.get("avoid_lunch", True) and 12 <= hour < 13:
            score -= 5  # Extra penalty for lunch

    # Slight preference for "on the hour" meetings
    if minute == 0:
        score += 2
    elif minute == 30:
        score += 1

    return score


def format_time_slot(slot: dict, timezone: str = "Europe/Berlin") -> str:
    """
    Format a time slot for human-readable display.

    Args:
        slot: Dict with 'start' and 'end' (ISO format)
        timezone: Timezone for display

    Returns:
        str: Formatted string like "Tuesday, January 20 at 2:00 PM - 3:00 PM PST"
    """
    try:
        tz = pytz.timezone(timezone)
        start_dt = parser.parse(slot["start"]).astimezone(tz)
        end_dt = parser.parse(slot["end"]).astimezone(tz)

        date_str = start_dt.strftime("%A, %B %d")
        start_time = start_dt.strftime("%I:%M %p").lstrip("0")
        end_time = end_dt.strftime("%I:%M %p %Z").lstrip("0")

        return f"{date_str} at {start_time} - {end_time}"
    except Exception:
        return f"{slot['start']} - {slot['end']}"


def format_slots_as_options(
    slots: list, timezone: str = "Europe/Berlin", max_options: int = 5
) -> str:
    """
    Format multiple slots as numbered options for display.

    Args:
        slots: List of slot dicts with 'start', 'end', 'score'
        timezone: Timezone for display
        max_options: Maximum number of options to show

    Returns:
        str: Formatted string with numbered options
    """
    if not slots:
        return "No available time slots found."

    lines = []
    for i, slot in enumerate(slots[:max_options], 1):
        formatted = format_time_slot(slot, timezone)
        score_indicator = ""
        if slot.get("score", 0) >= 60:
            score_indicator = " (Recommended)"
        elif slot.get("score", 0) >= 50:
            score_indicator = " (Good option)"

        lines.append(f"{i}. {formatted}{score_indicator}")

    return "\n".join(lines)


def calculate_end_time(start_time: str, duration_minutes: int) -> str:
    """
    Calculate end time given start time and duration.

    Args:
        start_time: Start time (ISO format)
        duration_minutes: Duration in minutes

    Returns:
        str: End time (ISO format)
    """
    start_dt = parser.parse(start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    return end_dt.isoformat()
