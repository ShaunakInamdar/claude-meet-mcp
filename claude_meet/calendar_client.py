"""
Google Calendar API client wrapper.

Provides high-level methods for calendar operations including event creation,
availability checking, and finding free time slots.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

import pytz
from dateutil import parser
from googleapiclient.errors import HttpError


class CalendarClient:
    """
    Wrapper for Google Calendar API operations.

    Provides methods to:
    - Create calendar events with attendees
    - Check free/busy status for multiple calendars
    - Find available meeting time slots
    """

    def __init__(self, service, timezone: str = "Europe/Berlin"):
        """
        Initialize the calendar client.

        Args:
            service: Authenticated Google Calendar API service
            timezone: Default timezone for operations
        """
        self.service = service
        self.timezone = timezone
        self.tz = pytz.timezone(timezone)

    def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        attendees: list,
        description: Optional[str] = None,
        add_meet_link: bool = False,
    ) -> dict:
        """
        Create a calendar event and send invitations to attendees.

        Args:
            summary: Event title/subject
            start_time: Start time in ISO format with timezone
            end_time: End time in ISO format with timezone
            attendees: List of email addresses to invite
            description: Optional event description/agenda
            add_meet_link: Whether to add a Google Meet video link

        Returns:
            dict: Created event details including:
                - event_id: Unique event identifier
                - html_link: Link to view event in Google Calendar
                - summary: Event title
                - start: Start time
                - end: End time
                - attendees: List of invited emails
                - meet_link: Google Meet link (if requested)

        Raises:
            HttpError: If the Calendar API request fails
        """
        event = {
            "summary": summary,
            "description": description or "",
            "start": {
                "dateTime": start_time,
                "timeZone": self.timezone,
            },
            "end": {
                "dateTime": end_time,
                "timeZone": self.timezone,
            },
            "attendees": [{"email": email} for email in attendees],
            "reminders": {
                "useDefault": True,
            },
        }

        # Add Google Meet link if requested
        if add_meet_link:
            event["conferenceData"] = {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }

        try:
            created_event = (
                self.service.events()
                .insert(
                    calendarId="primary",
                    body=event,
                    conferenceDataVersion=1 if add_meet_link else 0,
                    sendUpdates="all",  # Send email invitations to all attendees
                )
                .execute()
            )

            return {
                "event_id": created_event["id"],
                "html_link": created_event["htmlLink"],
                "summary": created_event["summary"],
                "start": created_event["start"].get("dateTime", created_event["start"].get("date")),
                "end": created_event["end"].get("dateTime", created_event["end"].get("date")),
                "attendees": [a["email"] for a in created_event.get("attendees", [])],
                "meet_link": created_event.get("hangoutLink"),
            }

        except HttpError as e:
            raise Exception(self._handle_calendar_error(e))

    def check_availability(self, emails: list, start_time: str, end_time: str) -> dict:
        """
        Check free/busy status for multiple calendars.

        Args:
            emails: List of email addresses to check
            start_time: Start of time range (ISO format)
            end_time: End of time range (ISO format)

        Returns:
            dict: Mapping of email to list of busy periods
                  {email: [{'start': str, 'end': str}, ...]}

        Raises:
            HttpError: If the Calendar API request fails
        """
        body = {
            "timeMin": start_time,
            "timeMax": end_time,
            "items": [{"id": email} for email in emails],
        }

        try:
            result = self.service.freebusy().query(body=body).execute()

            availability = {}
            for email in emails:
                calendar_data = result["calendars"].get(email, {})
                availability[email] = calendar_data.get("busy", [])

            return availability

        except HttpError as e:
            raise Exception(self._handle_calendar_error(e))

    def find_free_slots(
        self,
        emails: list,
        date: str,
        duration_minutes: int,
        start_hour: int = 9,
        end_hour: int = 17,
        preferences: Optional[dict] = None,
    ) -> list:
        """
        Find available meeting time slots for all attendees.

        Analyzes calendars to find times when everyone is free,
        then scores and ranks the slots by preference.

        Args:
            emails: List of attendee email addresses
            date: Date to search (YYYY-MM-DD format)
            duration_minutes: Required meeting duration
            start_hour: Business hours start (default 9am)
            end_hour: Business hours end (default 5pm)
            preferences: Optional dict with prefer_morning, prefer_afternoon

        Returns:
            list: Ranked list of available time slots, each containing:
                - start: ISO format start time
                - end: ISO format end time
                - duration_minutes: Slot duration
                - score: Preference score (higher is better)
                - display: Human-readable time string
        """
        # Build time range for the day
        tz_offset = self._get_tz_offset(date)
        start_time = f"{date}T{start_hour:02d}:00:00{tz_offset}"
        end_time = f"{date}T{end_hour:02d}:00:00{tz_offset}"

        # Get busy periods for all attendees
        availability = self.check_availability(emails, start_time, end_time)

        # Collect and merge all busy periods
        all_busy = []
        for busy_periods in availability.values():
            all_busy.extend(busy_periods)

        # Sort busy periods by start time
        all_busy.sort(key=lambda x: x["start"])

        # Merge overlapping busy periods
        merged_busy = self._merge_busy_periods(all_busy)

        # Find free slots between busy periods
        free_slots = self._find_gaps(merged_busy, start_time, end_time, duration_minutes)

        # Score and rank slots
        scored_slots = []
        for slot in free_slots:
            score = self._score_time_slot(slot["start"], preferences)
            display = self._format_slot_for_display(slot["start"], slot["end"])

            scored_slots.append(
                {
                    "start": slot["start"],
                    "end": slot["end"],
                    "duration_minutes": slot["duration_minutes"],
                    "score": score,
                    "display": display,
                }
            )

        # Sort by score (highest first) and return top results
        scored_slots.sort(key=lambda x: x["score"], reverse=True)
        return scored_slots[:10]

    def get_upcoming_events(self, max_results: int = 10) -> list:
        """
        Get upcoming events from the primary calendar.

        Args:
            max_results: Maximum number of events to return

        Returns:
            list: List of upcoming events
        """
        now = datetime.utcnow().isoformat() + "Z"

        try:
            events_result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            return events_result.get("items", [])

        except HttpError as e:
            raise Exception(self._handle_calendar_error(e))

    def _get_tz_offset(self, date: str) -> str:
        """Get timezone offset string for a given date."""
        dt = datetime.strptime(date, "%Y-%m-%d")
        localized = self.tz.localize(dt)
        offset = localized.strftime("%z")
        # Format as -08:00 instead of -0800
        return f"{offset[:3]}:{offset[3:]}"

    def _merge_busy_periods(self, busy_periods: list) -> list:
        """Merge overlapping busy periods into continuous blocks."""
        if not busy_periods:
            return []

        merged = [busy_periods[0].copy()]

        for period in busy_periods[1:]:
            last = merged[-1]
            if period["start"] <= last["end"]:
                # Overlapping or adjacent - extend the last period
                last["end"] = max(last["end"], period["end"])
            else:
                merged.append(period.copy())

        return merged

    def _find_gaps(
        self, busy_periods: list, range_start: str, range_end: str, min_duration: int
    ) -> list:
        """Find free time gaps between busy periods."""
        gaps = []
        current = range_start

        for busy in busy_periods:
            gap_minutes = self._time_diff_minutes(current, busy["start"])

            if gap_minutes >= min_duration:
                # Calculate end time for the required duration
                gap_start = parser.parse(current)
                gap_end = gap_start + timedelta(minutes=min_duration)

                gaps.append(
                    {"start": current, "end": gap_end.isoformat(), "duration_minutes": gap_minutes}
                )

            # Move past the busy period
            if busy["end"] > current:
                current = busy["end"]

        # Check for gap after last busy period
        final_gap = self._time_diff_minutes(current, range_end)
        if final_gap >= min_duration:
            gap_start = parser.parse(current)
            gap_end = gap_start + timedelta(minutes=min_duration)

            gaps.append(
                {"start": current, "end": gap_end.isoformat(), "duration_minutes": final_gap}
            )

        return gaps

    def _time_diff_minutes(self, start: str, end: str) -> int:
        """Calculate the difference in minutes between two ISO timestamps."""
        try:
            start_dt = parser.parse(start)
            end_dt = parser.parse(end)
            diff = end_dt - start_dt
            return int(diff.total_seconds() / 60)
        except Exception:
            return 0

    def _score_time_slot(self, start_time_iso: str, preferences: Optional[dict] = None) -> int:
        """
        Score a time slot based on scheduling preferences.

        Scoring system:
        - Early morning (9-11am): +10 points (prime productivity time)
        - Mid-day (11am-1pm): -5 points (lunch conflict)
        - Early afternoon (1-3pm): +5 points (post-lunch alertness)
        - Late afternoon (3-5pm): 0 points (acceptable)
        - Very early (<9am): -15 points (too early)
        - After hours (>5pm): -20 points (outside business hours)

        Args:
            start_time_iso: ISO format start time
            preferences: Optional dict with prefer_morning, prefer_afternoon

        Returns:
            int: Score (higher is better)
        """
        dt = parser.parse(start_time_iso)
        hour = dt.hour
        score = 50  # Base score

        if hour < 9:
            score -= 15
        elif 9 <= hour < 11:
            score += 10
        elif 11 <= hour < 13:
            score -= 5
        elif 13 <= hour < 15:
            score += 5
        elif 15 <= hour < 17:
            score += 0
        else:
            score -= 20

        # Apply user preferences
        if preferences:
            if preferences.get("prefer_morning") and 9 <= hour < 12:
                score += 10
            if preferences.get("prefer_afternoon") and 13 <= hour < 17:
                score += 10

        return score

    def _format_slot_for_display(self, start: str, end: str) -> str:
        """Format a time slot for human-readable display."""
        start_dt = parser.parse(start)
        end_dt = parser.parse(end)

        start_local = start_dt.astimezone(self.tz)
        end_local = end_dt.astimezone(self.tz)

        return f"{start_local.strftime('%I:%M %p')} - {end_local.strftime('%I:%M %p')}"

    def _handle_calendar_error(self, error: HttpError) -> str:
        """Convert Google Calendar API errors to user-friendly messages."""
        status = error.resp.status

        if status == 401:
            return "Authentication failed. Please re-authorize the application."
        elif status == 403:
            return "Permission denied. Check calendar access permissions."
        elif status == 404:
            return "Calendar or event not found."
        elif status == 429:
            return "Rate limit exceeded. Please try again in a moment."
        else:
            return f"Calendar API error ({status}): {str(error)}"
