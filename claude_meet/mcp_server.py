"""
MCP Server for Claude Calendar Scheduler.

Exposes calendar operations as MCP tools for integration with
Claude Desktop and Claude.ai.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any

# Fix Windows console encoding
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .auth import get_calendar_service
from .calendar_client import CalendarClient
from .config import Config, get_env_file_path

# Load environment variables (project .env first, then user config)
load_dotenv()

# Load user config (overrides project .env)
user_env = get_env_file_path()
if user_env.exists():
    load_dotenv(user_env, override=True)

# Create the MCP server
server = Server("claude-meet")

# Global calendar client (initialized lazily)
_calendar_client = None


def get_calendar_client() -> CalendarClient:
    """Get or create the calendar client."""
    global _calendar_client
    if _calendar_client is None:
        config = Config()
        service = get_calendar_service()
        _calendar_client = CalendarClient(service, timezone=config.default_timezone)
    return _calendar_client


# Get configured timezone for tool descriptions
def _get_configured_timezone() -> str:
    """Get the configured timezone from environment or auto-detect."""
    from .config import detect_system_timezone

    return os.getenv("TIMEZONE") or detect_system_timezone()


def get_tools() -> list[Tool]:
    """Generate tool definitions with current timezone context."""
    tz = _get_configured_timezone()

    return [
        Tool(
            name="check_calendar_availability",
            description=f"Check the free/busy status of one or more people's calendars for a specific date and time range. Returns when people are busy and when they're free. All times are in {tz} timezone.",
            inputSchema={
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
                        "description": "Optional start time in HH:MM 24-hour format (e.g., '09:00'). Defaults to 09:00.",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Optional end time in HH:MM 24-hour format (e.g., '17:00'). Defaults to 17:00.",
                    },
                },
                "required": ["emails", "date"],
            },
        ),
        Tool(
            name="find_meeting_times",
            description=f"Find available meeting time slots that work for all attendees. Analyzes calendars and returns the best options ranked by preference. Returns ISO timestamps with correct {tz} timezone offset - use these exact values when creating events.",
            inputSchema={
                "type": "object",
                "properties": {
                    "emails": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Email addresses of all meeting attendees",
                    },
                    "date": {"type": "string", "description": "Target date in YYYY-MM-DD format"},
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
        ),
        Tool(
            name="create_calendar_event",
            description=f"Create a new calendar event and send email invitations to all attendees. The event will appear on everyone's calendar. Calendar is configured for {tz} timezone.",
            inputSchema={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "The title/subject of the meeting (e.g., 'Q1 Planning Meeting')",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Meeting start time in ISO 8601 format with timezone. IMPORTANT: Use the exact 'start' value from find_meeting_times results - do not construct your own time string.",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Meeting end time in ISO 8601 format with timezone. IMPORTANT: Use the exact 'end' value from find_meeting_times results - do not construct your own time string.",
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
                        "description": "If true, adds a Google Meet video conference link",
                        "default": False,
                    },
                },
                "required": ["summary", "start_time", "end_time", "attendees"],
            },
        ),
    ]


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return the list of available tools."""
    return get_tools()


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool and return the result."""
    try:
        if name == "check_calendar_availability":
            result = await execute_check_availability(arguments)
        elif name == "find_meeting_times":
            result = await execute_find_meeting_times(arguments)
        elif name == "create_calendar_event":
            result = await execute_create_event(arguments)
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    except Exception as e:
        error_result = {"error": str(e)}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


async def execute_check_availability(args: dict) -> dict:
    """Execute the check_calendar_availability tool."""
    client = get_calendar_client()
    config = Config()

    emails = args["emails"]
    date = args["date"]
    start_hour = int(args.get("start_time", "09:00").split(":")[0])
    end_hour = int(args.get("end_time", "17:00").split(":")[0])

    # Build time range
    tz_offset = _get_tz_offset(date, config.default_timezone)
    start_time = f"{date}T{start_hour:02d}:00:00{tz_offset}"
    end_time = f"{date}T{end_hour:02d}:00:00{tz_offset}"

    # Run synchronous code in executor
    loop = asyncio.get_event_loop()
    availability = await loop.run_in_executor(
        None, lambda: client.check_availability(emails, start_time, end_time)
    )

    # Format results
    formatted = {}
    for email, busy_periods in availability.items():
        if busy_periods:
            formatted[email] = {
                "status": "has_meetings",
                "busy_periods": [{"start": p["start"], "end": p["end"]} for p in busy_periods],
            }
        else:
            formatted[email] = {"status": "free", "busy_periods": []}

    return {
        "date": date,
        "time_range": f"{start_hour:02d}:00 - {end_hour:02d}:00",
        "availability": formatted,
    }


async def execute_find_meeting_times(args: dict) -> dict:
    """Execute the find_meeting_times tool."""
    client = get_calendar_client()
    config = Config()

    emails = args["emails"]
    duration = args["duration_minutes"]
    date = args.get("date")

    # Default to tomorrow if no date provided
    if not date:
        import pytz

        tz = pytz.timezone(config.default_timezone)
        tomorrow = datetime.now(tz) + timedelta(days=1)
        date = tomorrow.strftime("%Y-%m-%d")

    preferences = args.get("preferences", {})
    start_hour = preferences.get("start_hour", 9)
    end_hour = preferences.get("end_hour", 17)

    # Run synchronous code in executor
    loop = asyncio.get_event_loop()
    slots = await loop.run_in_executor(
        None,
        lambda: client.find_free_slots(
            emails=emails,
            date=date,
            duration_minutes=duration,
            start_hour=start_hour,
            end_hour=end_hour,
            preferences=preferences,
        ),
    )

    if not slots:
        return {
            "date": date,
            "duration_minutes": duration,
            "available_slots": [],
            "message": "No available time slots found for this date. Try another day.",
        }

    # Format results
    formatted_slots = []
    for i, slot in enumerate(slots[:5], 1):
        formatted_slots.append(
            {
                "rank": i,
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
        "attendees": emails,
        "available_slots": formatted_slots,
    }


async def execute_create_event(args: dict) -> dict:
    """Execute the create_calendar_event tool."""
    client = get_calendar_client()

    summary = args["summary"]
    start_time = args["start_time"]
    end_time = args["end_time"]
    attendees = args["attendees"]
    description = args.get("description")
    add_meet_link = args.get("add_meet_link", False)

    # Run synchronous code in executor
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: client.create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
            description=description,
            add_meet_link=add_meet_link,
        ),
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


def _get_tz_offset(date: str, timezone: str) -> str:
    """Get timezone offset string for a given date."""
    import pytz

    tz = pytz.timezone(timezone)
    dt = datetime.strptime(date, "%Y-%m-%d")
    localized = tz.localize(dt)
    offset = localized.strftime("%z")
    return f"{offset[:3]}:{offset[3:]}"


async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Main entry point for the MCP server."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
