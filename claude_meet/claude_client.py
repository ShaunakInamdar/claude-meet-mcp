"""
Claude API client with tool calling for calendar operations.

Integrates Claude's natural language understanding with Google Calendar
operations through a tool-calling interface.
"""

import json
from datetime import datetime, timedelta

import anthropic
import pytz
from dateutil import parser

from .scheduler import calculate_end_time, format_slots_as_options

# Claude model configuration
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 2000

# Tool definitions for Claude
TOOLS = [
    {
        "name": "check_calendar_availability",
        "description": "Check the free/busy status of one or more people's calendars for a specific date and time range. Returns when people are busy and when they're free.",
        "input_schema": {
            "type": "object",
            "properties": {
                "emails": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of email addresses to check (e.g., ['alice@example.com', 'bob@example.com'])",
                },
                "date": {
                    "type": "string",
                    "description": "The date to check in YYYY-MM-DD format (e.g., '2026-01-20')",
                },
                "start_time": {
                    "type": "string",
                    "description": "Optional start time in HH:MM 24-hour format (e.g., '09:00'). If not provided, defaults to start of business hours.",
                },
                "end_time": {
                    "type": "string",
                    "description": "Optional end time in HH:MM 24-hour format (e.g., '17:00'). If not provided, defaults to end of business hours.",
                },
            },
            "required": ["emails", "date"],
        },
    },
    {
        "name": "find_meeting_times",
        "description": "Intelligently find available meeting time slots that work for all attendees. Analyzes calendars and returns the best options ranked by preference.",
        "input_schema": {
            "type": "object",
            "properties": {
                "emails": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Email addresses of all meeting attendees",
                },
                "date": {
                    "type": "string",
                    "description": "Target date for the meeting in YYYY-MM-DD format. Can also accept relative dates like 'tomorrow' which will be parsed.",
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "How long the meeting should be in minutes (e.g., 30, 60, 90)",
                },
                "preferences": {
                    "type": "object",
                    "description": "Optional scheduling preferences",
                    "properties": {
                        "prefer_morning": {"type": "boolean"},
                        "prefer_afternoon": {"type": "boolean"},
                        "start_hour": {
                            "type": "integer",
                            "description": "Business hours start (default 9)",
                        },
                        "end_hour": {
                            "type": "integer",
                            "description": "Business hours end (default 17)",
                        },
                    },
                },
            },
            "required": ["emails", "duration_minutes"],
        },
    },
    {
        "name": "create_calendar_event",
        "description": "Create a new calendar event and automatically send email invitations to all attendees. The event will appear on everyone's calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "The title/subject of the meeting (e.g., 'Q1 Planning Meeting')",
                },
                "start_time": {
                    "type": "string",
                    "description": "Meeting start time in ISO 8601 format with timezone (e.g., '2026-01-20T14:00:00-08:00')",
                },
                "end_time": {
                    "type": "string",
                    "description": "Meeting end time in ISO 8601 format with timezone (e.g., '2026-01-20T15:00:00-08:00')",
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of email addresses to invite to the meeting",
                },
                "description": {
                    "type": "string",
                    "description": "Optional detailed description or agenda for the meeting",
                },
                "add_meet_link": {
                    "type": "boolean",
                    "description": "If true, automatically adds a Google Meet video conference link to the event",
                    "default": False,
                },
            },
            "required": ["summary", "start_time", "end_time", "attendees"],
        },
    },
]

# System prompt for Claude
SYSTEM_PROMPT = """You are an intelligent calendar assistant that helps users schedule meetings.
You have access to tools that can:
1. Check people's calendar availability
2. Find suitable meeting times for multiple attendees
3. Create calendar events and send invitations

When helping users schedule meetings:
- Always ask for attendee emails if not provided
- Confirm the meeting details before creating an event
- Suggest the best available time slots based on everyone's schedules
- Be proactive about adding Google Meet links for remote meetings

Today's date is {today}. Use this as reference for relative dates like "tomorrow" or "next week".

Be concise but helpful in your responses."""


class ClaudeClient:
    """
    Claude API client with tool calling for calendar operations.

    Handles the conversation loop with Claude, including:
    - Sending messages with tool definitions
    - Processing tool calls from Claude
    - Returning tool results back to Claude
    - Extracting final responses
    """

    def __init__(self, api_key: str, calendar_client, timezone: str = "Europe/Berlin"):
        """
        Initialize the Claude client.

        Args:
            api_key: Anthropic API key
            calendar_client: Initialized CalendarClient instance
            timezone: Default timezone for operations
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.calendar_client = calendar_client
        self.timezone = timezone
        self.tz = pytz.timezone(timezone)

    def process_message(self, user_message: str, conversation_history: list | None = None) -> tuple:
        """
        Process a user message through Claude with tool calling support.

        Handles the full conversation loop including:
        1. Sending user message to Claude
        2. Processing any tool calls
        3. Returning tool results to Claude
        4. Repeating until Claude provides a final response

        Args:
            user_message: The user's input text
            conversation_history: Previous messages in the conversation

        Returns:
            tuple: (response_text, updated_conversation_history)
        """
        if conversation_history is None:
            conversation_history = []

        # Build messages list
        messages = conversation_history + [{"role": "user", "content": user_message}]

        # Get today's date for the system prompt
        today = datetime.now(self.tz).strftime("%A, %B %d, %Y")
        system = SYSTEM_PROMPT.format(today=today)

        # Initial API call
        try:
            response = self.client.messages.create(
                model=MODEL, max_tokens=MAX_TOKENS, system=system, tools=TOOLS, messages=messages
            )
        except anthropic.APIError as e:
            return self._handle_claude_error(e), messages

        # Tool calling loop - continue until Claude provides a final response
        while response.stop_reason == "tool_use":
            # Extract all tool use blocks from the response
            tool_uses = [block for block in response.content if block.type == "tool_use"]

            # Execute each tool and collect results
            tool_results = []
            for tool_use in tool_uses:
                try:
                    result = self.execute_tool(tool_use.name, tool_use.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(result, default=str),
                        }
                    )
                except Exception as e:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps({"error": str(e)}),
                            "is_error": True,
                        }
                    )

            # Add assistant response and tool results to conversation
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            # Get next response from Claude
            try:
                response = self.client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=system,
                    tools=TOOLS,
                    messages=messages,
                )
            except anthropic.APIError as e:
                return self._handle_claude_error(e), messages

        # Extract final text response
        final_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_text += block.text

        # Add final assistant message to history
        messages.append({"role": "assistant", "content": response.content})

        return final_text, messages

    def execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """
        Execute a tool call and return the result.

        Dispatches to the appropriate calendar client method based on tool name.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            dict: Tool execution result
        """
        if tool_name == "check_calendar_availability":
            return self._execute_check_availability(tool_input)
        elif tool_name == "find_meeting_times":
            return self._execute_find_meeting_times(tool_input)
        elif tool_name == "create_calendar_event":
            return self._execute_create_event(tool_input)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _execute_check_availability(self, tool_input: dict) -> dict:
        """Execute the check_calendar_availability tool."""
        emails = tool_input["emails"]
        date = self._parse_date(tool_input.get("date"))

        if not date:
            return {"error": "Could not parse the date. Please use YYYY-MM-DD format."}

        # Build time range
        start_hour = int(tool_input.get("start_time", "09:00").split(":")[0])
        end_hour = int(tool_input.get("end_time", "17:00").split(":")[0])

        tz_offset = self._get_tz_offset(date)
        start_time = f"{date}T{start_hour:02d}:00:00{tz_offset}"
        end_time = f"{date}T{end_hour:02d}:00:00{tz_offset}"

        availability = self.calendar_client.check_availability(emails, start_time, end_time)

        # Format results for readability
        formatted = {}
        for email, busy_periods in availability.items():
            if busy_periods:
                formatted[email] = [
                    f"{self._format_time(p['start'])} - {self._format_time(p['end'])}"
                    for p in busy_periods
                ]
            else:
                formatted[email] = ["Free all day"]

        return {"date": date, "availability": formatted}

    def _execute_find_meeting_times(self, tool_input: dict) -> dict:
        """Execute the find_meeting_times tool."""
        emails = tool_input["emails"]
        duration = tool_input["duration_minutes"]
        date = self._parse_date(tool_input.get("date"))

        if not date:
            # Default to tomorrow if no date provided
            tomorrow = datetime.now(self.tz) + timedelta(days=1)
            date = tomorrow.strftime("%Y-%m-%d")

        preferences = tool_input.get("preferences", {})
        start_hour = preferences.get("start_hour", 9)
        end_hour = preferences.get("end_hour", 17)

        slots = self.calendar_client.find_free_slots(
            emails=emails,
            date=date,
            duration_minutes=duration,
            start_hour=start_hour,
            end_hour=end_hour,
            preferences=preferences,
        )

        if not slots:
            return {
                "date": date,
                "available_slots": [],
                "message": "No available time slots found for this date. Try another day.",
            }

        # Format the results
        formatted_slots = []
        for slot in slots[:5]:  # Return top 5 options
            formatted_slots.append(
                {
                    "start": slot["start"],
                    "end": slot["end"],
                    "display": slot["display"],
                    "score": slot["score"],
                    "recommended": slot["score"] >= 55,
                }
            )

        return {
            "date": date,
            "duration_minutes": duration,
            "available_slots": formatted_slots,
            "options_text": format_slots_as_options(slots, self.timezone),
        }

    def _execute_create_event(self, tool_input: dict) -> dict:
        """Execute the create_calendar_event tool."""
        summary = tool_input["summary"]
        start_time = tool_input["start_time"]
        end_time = tool_input.get("end_time")
        attendees = tool_input["attendees"]
        description = tool_input.get("description")
        add_meet_link = tool_input.get("add_meet_link", False)

        # Calculate end time if not provided but duration is available
        if not end_time and "duration_minutes" in tool_input:
            end_time = calculate_end_time(start_time, tool_input["duration_minutes"])

        result = self.calendar_client.create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
            description=description,
            add_meet_link=add_meet_link,
        )

        return {
            "success": True,
            "event_id": result["event_id"],
            "summary": result["summary"],
            "start": result["start"],
            "end": result["end"],
            "attendees": result["attendees"],
            "calendar_link": result["html_link"],
            "meet_link": result.get("meet_link"),
            "message": f"Meeting '{summary}' created successfully! Invitations sent to {len(attendees)} attendee(s).",
        }

    def _parse_date(self, date_str: str | None) -> str | None:
        """
        Parse a date string to YYYY-MM-DD format.

        Handles relative dates like 'tomorrow', 'next week', etc.
        """
        if not date_str:
            return None

        date_str = date_str.lower().strip()
        today = datetime.now(self.tz).date()

        # Handle relative dates
        if date_str in ["today", "now"]:
            return today.strftime("%Y-%m-%d")
        elif date_str == "tomorrow":
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        elif date_str == "next week":
            return (today + timedelta(days=7)).strftime("%Y-%m-%d")
        elif date_str in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            return self._next_weekday(today, date_str)

        # Try parsing as actual date
        try:
            parsed = parser.parse(date_str)
            return parsed.strftime("%Y-%m-%d")
        except Exception:
            return None

    def _next_weekday(self, from_date, weekday_name: str) -> str:
        """Get the next occurrence of a weekday."""
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        target_day = weekdays.index(weekday_name.lower())
        days_ahead = target_day - from_date.weekday()

        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7

        next_date = from_date + timedelta(days=days_ahead)
        return next_date.strftime("%Y-%m-%d")

    def _get_tz_offset(self, date: str) -> str:
        """Get timezone offset string for a given date."""
        dt = datetime.strptime(date, "%Y-%m-%d")
        localized = self.tz.localize(dt)
        offset = localized.strftime("%z")
        return f"{offset[:3]}:{offset[3:]}"

    def _format_time(self, iso_time: str) -> str:
        """Format ISO time to readable format."""
        try:
            dt = parser.parse(iso_time).astimezone(self.tz)
            return dt.strftime("%I:%M %p")
        except Exception:
            return iso_time

    def _handle_claude_error(self, error: anthropic.APIError) -> str:
        """Handle Claude API errors with user-friendly messages."""
        error_str = str(error).lower()

        if "rate_limit" in error_str:
            return "Claude API rate limit reached. Please wait a moment and try again."
        elif "authentication" in error_str or "api_key" in error_str:
            return "Claude API authentication failed. Please check your API key."
        elif "overloaded" in error_str:
            return "Claude is currently overloaded. Please try again in a moment."
        else:
            return f"Claude API error: {str(error)}"
