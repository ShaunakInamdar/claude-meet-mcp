# Usage Guide

How to use Claude Calendar Scheduler effectively.

## Basic Commands

### Interactive Chat Mode

Start a conversation with Claude for complex scheduling:

```bash
claude-meet chat
```

This opens an interactive session where you can have a back-and-forth conversation about scheduling.

### Single Command Mode

For quick one-off scheduling requests:

```bash
claude-meet schedule "Schedule a meeting with alice@example.com tomorrow at 2pm"
```

### View Upcoming Events

See what's on your calendar:

```bash
claude-meet upcoming
claude-meet upcoming -n 20  # Show 20 events
```

### Manage Authentication

```bash
claude-meet auth    # Authenticate with Google
claude-meet logout  # Clear credentials
```

## Chat Commands

In interactive mode, these commands are available:

| Command | Action |
|---------|--------|
| `help` | Show help and examples |
| `clear` | Clear conversation history |
| `exit` / `quit` / `q` | Exit the application |

## Example Conversations

### Schedule a Simple Meeting

```
You: Schedule a meeting with bob@example.com tomorrow at 3pm for 1 hour

Claude: I'll create that meeting for you. What would you like to call it?

You: Weekly Sync

Claude: I've created "Weekly Sync" for tomorrow at 3:00 PM - 4:00 PM.
An invitation has been sent to bob@example.com.
```

### Find Available Times

```
You: Find a time for a 2-hour meeting with alice@example.com and bob@example.com next week

Claude: Let me check everyone's availability for next week...

I found these available slots:
1. Monday, January 20 at 9:00 AM - 11:00 AM (Recommended)
2. Tuesday, January 21 at 2:00 PM - 4:00 PM (Good option)
3. Wednesday, January 22 at 10:00 AM - 12:00 PM

Which time works best for you?
```

### Check Availability

```
You: Is alice@example.com free tomorrow afternoon?

Claude: Let me check alice@example.com's calendar for tomorrow afternoon...

Tomorrow afternoon availability for alice@example.com:
- 1:00 PM - 2:30 PM: Busy
- 2:30 PM - 5:00 PM: Free

Alice is free from 2:30 PM onwards tomorrow.
```

### Schedule with Video Conferencing

```
You: Schedule a video call with the team at team@example.com on Friday at 10am

Claude: I'll create a video meeting for Friday at 10:00 AM. How long should it be?

You: 30 minutes

Claude: I've created "Video Call" for Friday at 10:00 AM - 10:30 AM with a Google Meet link.
Invitation sent to team@example.com.

Google Meet link: https://meet.google.com/abc-defg-hij
```

## Natural Language Examples

The scheduler understands various ways to express dates and times:

### Dates
- "tomorrow"
- "next week"
- "Monday"
- "next Friday"
- "January 20"
- "in 3 days"

### Times
- "2pm"
- "14:00"
- "morning" (defaults to 9am)
- "afternoon" (defaults to 2pm)

### Durations
- "30 minutes"
- "1 hour"
- "90 minutes"
- "2 hours"

## Tips for Best Results

### Be Specific with Attendees
Always use full email addresses:
```
Good: "Schedule with alice@example.com"
Bad: "Schedule with Alice"
```

### Confirm Before Creating
Claude will confirm meeting details before creating. Review carefully:
```
Claude: I'll create "Project Planning" for tomorrow at 2:00 PM - 3:00 PM
        with alice@example.com and bob@example.com. Should I proceed?
```

### Use Context
In chat mode, Claude remembers the conversation:
```
You: Find a time for a meeting with alice@example.com tomorrow
Claude: [shows available times]
You: Let's do the 2pm slot
Claude: [creates meeting at 2pm]
```

### Provide Meeting Details
Include the purpose for better organization:
```
You: Schedule a meeting with bob@example.com tomorrow at 3pm
     to discuss the Q1 roadmap
```

## Troubleshooting

### "No available time slots found"
- Try a different date
- Expand the time range (early morning or late afternoon)
- Check if attendees have blocked calendars

### "Permission denied"
- The attendee's calendar may not be accessible
- You can still create the meeting; they'll receive an invitation

### Meeting not appearing in calendar
- Wait a few seconds and refresh Google Calendar
- Check the calendar link provided in the response

## Advanced Usage

### Environment Variables

Fine-tune behavior with environment variables:

```bash
# Set timezone
export TIMEZONE=Europe/London

# Adjust business hours
export BUSINESS_HOURS_START=8
export BUSINESS_HOURS_END=18

# Default meeting duration
export DEFAULT_DURATION=45
```

### Debug Mode

For troubleshooting, enable debug output:

```bash
claude-meet chat --debug
```

This shows detailed information about API calls and responses.
