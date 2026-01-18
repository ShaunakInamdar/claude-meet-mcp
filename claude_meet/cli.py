"""
Command-line interface for Claude Calendar Scheduler.

Provides an interactive terminal interface for natural language
meeting scheduling powered by Claude and Google Calendar.
"""

import os
import sys
from pathlib import Path

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import click
from dotenv import load_dotenv

from .auth import get_calendar_service, clear_credentials
from .calendar_client import CalendarClient
from .claude_client import ClaudeClient
from .config import Config


def get_api_key() -> str:
    """
    Get the Anthropic API key from environment or config file.

    Checks in order:
    1. ANTHROPIC_API_KEY environment variable
    2. config/anthropic_apikey.txt file

    Returns:
        str: The API key

    Raises:
        SystemExit: If no API key is found
    """
    # Check environment variable first
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        return api_key.strip()

    # Check config file
    config_file = Path(__file__).parent.parent / 'config' / 'anthropic_apikey.txt'
    if config_file.exists():
        api_key = config_file.read_text().strip()
        if api_key:
            return api_key

    click.echo("Error: Anthropic API key not found.", err=True)
    click.echo("Please set ANTHROPIC_API_KEY environment variable or create config/anthropic_apikey.txt", err=True)
    sys.exit(1)


@click.group()
@click.version_option(version='1.0.0', prog_name='claude-meet')
def cli():
    """
    Claude Calendar Scheduler - Intelligent meeting scheduling from your terminal.

    Use natural language to schedule meetings, check availability,
    and manage your calendar through Claude AI.
    """
    pass


@cli.command()
@click.option('--debug', is_flag=True, help='Enable debug mode with verbose output')
def chat(debug):
    """
    Start an interactive chat session for scheduling meetings.

    Use natural language to:
    - Schedule meetings with attendees
    - Check calendar availability
    - Find suitable meeting times
    - Create events with Google Meet links

    Examples:
        "Schedule a meeting with alice@example.com tomorrow at 2pm"
        "Find a time for a 1-hour meeting with bob@example.com next week"
        "What's on my calendar today?"
    """
    load_dotenv()

    click.echo("=" * 60)
    click.echo("  Claude Calendar Scheduler")
    click.echo("  Type 'exit', 'quit', or 'q' to end the session")
    click.echo("  Type 'help' for usage examples")
    click.echo("=" * 60)
    click.echo()

    # Initialize services
    try:
        click.echo("Connecting to Google Calendar...")
        calendar_service = get_calendar_service()
        click.echo("Connected!\n")
    except FileNotFoundError as e:
        click.echo(f"\nSetup required: {str(e)}", err=True)
        click.echo("\nPlease follow the setup instructions in docs/SETUP.md", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\nError connecting to Google Calendar: {str(e)}", err=True)
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Get API key and initialize clients
    api_key = get_api_key()
    config = Config()

    calendar_client = CalendarClient(calendar_service, timezone=config.default_timezone)
    claude_client = ClaudeClient(api_key, calendar_client, timezone=config.default_timezone)

    # Main conversation loop
    conversation_history = []

    while True:
        try:
            # Get user input
            user_input = click.prompt(click.style("You", fg='green', bold=True), type=str)

            # Check for exit commands
            if user_input.lower().strip() in ['exit', 'quit', 'q']:
                click.echo("\nGoodbye! Have a productive day!")
                break

            # Check for help command
            if user_input.lower().strip() == 'help':
                _show_help()
                continue

            # Check for clear command
            if user_input.lower().strip() == 'clear':
                conversation_history = []
                click.clear()
                click.echo("Conversation cleared.\n")
                continue

            # Skip empty input
            if not user_input.strip():
                continue

            # Process the message through Claude
            click.echo()  # Blank line before response

            response, conversation_history = claude_client.process_message(
                user_input,
                conversation_history
            )

            # Display Claude's response
            click.echo(click.style("Claude: ", fg='blue', bold=True) + response)
            click.echo()

        except KeyboardInterrupt:
            click.echo("\n\nGoodbye!")
            break
        except Exception as e:
            click.echo(f"\nError: {str(e)}", err=True)
            if debug:
                import traceback
                traceback.print_exc()
            click.echo()  # Continue the conversation


@cli.command()
@click.argument('message', nargs=-1, required=True)
@click.option('--debug', is_flag=True, help='Enable debug mode')
def schedule(message, debug):
    """
    Send a single scheduling request without interactive mode.

    Usage:
        claude-meet schedule "Schedule a meeting with alice@example.com tomorrow at 3pm"
    """
    load_dotenv()

    message_text = ' '.join(message)

    try:
        # Initialize services
        calendar_service = get_calendar_service()
        api_key = get_api_key()
        config = Config()

        calendar_client = CalendarClient(calendar_service, timezone=config.default_timezone)
        claude_client = ClaudeClient(api_key, calendar_client, timezone=config.default_timezone)

        # Process the message
        response, _ = claude_client.process_message(message_text)

        click.echo(response)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
def auth():
    """
    Authenticate with Google Calendar.

    Opens a browser window for Google OAuth consent.
    Tokens are stored locally for future use.
    """
    click.echo("Starting Google Calendar authentication...")

    try:
        service = get_calendar_service()

        # Test the connection by getting calendar info
        calendar = service.calendars().get(calendarId='primary').execute()
        click.echo(f"\nSuccessfully authenticated!")
        click.echo(f"Connected to calendar: {calendar.get('summary', 'Primary')}")

    except Exception as e:
        click.echo(f"\nAuthentication failed: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
def logout():
    """
    Clear stored Google Calendar credentials.

    Use this to switch accounts or re-authenticate.
    """
    clear_credentials()
    click.echo("Credentials cleared. Run 'claude-meet auth' to re-authenticate.")


@cli.command()
@click.option('--count', '-n', default=10, help='Number of events to show')
def upcoming(count):
    """
    Show upcoming calendar events.
    """
    load_dotenv()

    try:
        calendar_service = get_calendar_service()
        config = Config()
        calendar_client = CalendarClient(calendar_service, timezone=config.default_timezone)

        events = calendar_client.get_upcoming_events(max_results=count)

        if not events:
            click.echo("No upcoming events found.")
            return

        click.echo(f"\nUpcoming {len(events)} events:\n")

        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            click.echo(f"  - {summary}")
            click.echo(f"    {start}")
            click.echo()

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


def _show_help():
    """Display help and usage examples."""
    help_text = """
╔══════════════════════════════════════════════════════════════╗
║                    Claude Calendar Scheduler                  ║
╠══════════════════════════════════════════════════════════════╣
║  Commands:                                                    ║
║    help  - Show this help message                            ║
║    clear - Clear conversation history                        ║
║    exit  - Exit the application                              ║
╠══════════════════════════════════════════════════════════════╣
║  Example Requests:                                            ║
║                                                               ║
║  Schedule a meeting:                                          ║
║    "Schedule a meeting with alice@example.com tomorrow at 2pm"║
║    "Set up a 1-hour sync with bob@example.com on Friday"     ║
║                                                               ║
║  Find available times:                                        ║
║    "Find a time for a meeting with team@example.com next week"║
║    "When is alice@example.com free tomorrow?"                ║
║                                                               ║
║  Add video conferencing:                                      ║
║    "Schedule a video call with client@example.com at 3pm"    ║
║    "Create a meeting with Google Meet link"                  ║
║                                                               ║
║  Check availability:                                          ║
║    "Is bob@example.com available tomorrow afternoon?"        ║
║    "Check availability for alice@example.com on Monday"      ║
╚══════════════════════════════════════════════════════════════╝
"""
    click.echo(help_text)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
