# MCP Server Setup Guide

This guide explains how to use Claude Calendar Scheduler as an MCP (Model Context Protocol) server with Claude Desktop or Claude.ai.

## What is MCP?

MCP (Model Context Protocol) allows Claude to interact with external tools and services. By running claude-meet as an MCP server, Claude can directly schedule meetings, check availability, and manage your calendar.

## Prerequisites

1. Complete the basic setup from [SETUP.md](SETUP.md)
2. Install Claude Desktop (or use Claude.ai with MCP support)
3. Ensure Google Calendar authentication is complete

## Installation

### 1. Install Dependencies

```bash
cd claude-booker
pip install -r requirements.txt
```

### 2. Verify MCP Server Works

Test the server can start:
```bash
python -m claude_meet.mcp_server
```

The server should start without errors (it will wait for input via stdio).

### 3. Run Tests

```bash
python test_mcp.py
```

All tests should pass.

## Claude Desktop Configuration

### Windows

1. Open your Claude Desktop configuration file:
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   ```

2. Add the claude-meet server configuration:
   ```json
   {
     "mcpServers": {
       "claude-meet": {
         "command": "python",
         "args": ["-m", "claude_meet.mcp_server"],
         "cwd": "C:\\Users\\YOUR_USERNAME\\path\\to\\claude-booker",
         "env": {
           "PYTHONPATH": "C:\\Users\\YOUR_USERNAME\\path\\to\\claude-booker"
         }
       }
     }
   }
   ```

3. Replace `YOUR_USERNAME` and path with your actual values.

### macOS / Linux

1. Open your Claude Desktop configuration:
   ```
   ~/Library/Application Support/Claude/claude_desktop_config.json  # macOS
   ~/.config/Claude/claude_desktop_config.json  # Linux
   ```

2. Add the server configuration:
   ```json
   {
     "mcpServers": {
       "claude-meet": {
         "command": "python",
         "args": ["-m", "claude_meet.mcp_server"],
         "cwd": "/path/to/claude-booker",
         "env": {
           "PYTHONPATH": "/path/to/claude-booker"
         }
       }
     }
   }
   ```

### Using Virtual Environment

If you're using a virtual environment:

```json
{
  "mcpServers": {
    "claude-meet": {
      "command": "/path/to/claude-booker/venv/bin/python",
      "args": ["-m", "claude_meet.mcp_server"],
      "cwd": "/path/to/claude-booker"
    }
  }
}
```

## Available Tools

Once configured, Claude will have access to these tools:

### 1. check_calendar_availability

Check when people are free or busy.

**Example prompt:**
> "Check if john@example.com is available tomorrow"

**Parameters:**
- `emails`: List of email addresses to check
- `date`: Date in YYYY-MM-DD format
- `start_time`: Optional start time (HH:MM)
- `end_time`: Optional end time (HH:MM)

### 2. find_meeting_times

Find available meeting slots for multiple attendees.

**Example prompt:**
> "Find a 1-hour slot for a meeting with alice@example.com and bob@example.com next Monday"

**Parameters:**
- `emails`: List of attendee emails
- `date`: Target date
- `duration_minutes`: Meeting duration
- `preferences`: Optional preferences (prefer_morning, prefer_afternoon)

### 3. create_calendar_event

Create a calendar event and send invitations.

**Example prompt:**
> "Schedule a meeting called 'Project Sync' with team@example.com tomorrow at 2pm for 30 minutes"

**Parameters:**
- `summary`: Meeting title
- `start_time`: ISO 8601 datetime
- `end_time`: ISO 8601 datetime
- `attendees`: List of email addresses
- `description`: Optional description
- `add_meet_link`: Add Google Meet link (true/false)

## Example Conversations

### Check Availability
```
You: Is sarah@example.com free tomorrow afternoon?

Claude: [Uses check_calendar_availability tool]
Sarah is free tomorrow afternoon from 1:00 PM to 5:00 PM,
except for a meeting from 2:30 PM to 3:00 PM.
```

### Schedule a Meeting
```
You: Schedule a 1-hour meeting with the marketing team
     (marketing@example.com) next Tuesday at 10am.
     Call it "Marketing Sync" and add a Meet link.

Claude: [Uses create_calendar_event tool]
I've created "Marketing Sync" for next Tuesday at 10:00 AM - 11:00 AM.
A Google Meet link has been added, and an invitation has been sent to
marketing@example.com.

Calendar link: https://calendar.google.com/...
Meet link: https://meet.google.com/...
```

### Find Best Times
```
You: Find a good time for a 2-hour meeting with alice@example.com
     and bob@example.com this week, preferably in the morning.

Claude: [Uses find_meeting_times tool]
Here are the best available slots this week:

1. Wednesday at 9:00 AM - 11:00 AM (Recommended)
2. Thursday at 10:00 AM - 12:00 PM
3. Friday at 9:00 AM - 11:00 AM

Would you like me to schedule one of these?
```

## Troubleshooting

### "Server not found" in Claude Desktop

1. Check the configuration path is correct
2. Verify Python is in your PATH
3. Ensure all dependencies are installed
4. Check Claude Desktop logs for errors

### "Authentication failed"

1. Run `python -m claude_meet.cli auth` to re-authenticate
2. Check that token.json exists in `~/.claude-meet/`

### "Tool execution failed"

1. Run `python test_mcp.py` to diagnose issues
2. Check Google Calendar API quotas
3. Verify email addresses are valid

### Logs

MCP server logs can be found in Claude Desktop's logs directory.

## Security Notes

- OAuth tokens are stored locally in `~/.claude-meet/`
- The MCP server only communicates via stdio (no network exposure)
- Calendar operations require your explicit prompts to Claude
