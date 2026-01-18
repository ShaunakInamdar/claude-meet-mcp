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
from .config import Config, detect_system_timezone, save_timezone, get_common_timezones, get_env_file_path


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


@click.group(invoke_without_command=True)
@click.version_option(version='1.0.0', prog_name='claude-meet')
@click.pass_context
def cli(ctx):
    """
    Claude Calendar Scheduler - Intelligent meeting scheduling from your terminal.

    Use natural language to schedule meetings, check availability,
    and manage your calendar through Claude AI.

    \b
    Quick Start:
      1. claude-meet setup     Configure your timezone
      2. claude-meet auth      Connect to Google Calendar
      3. claude-meet chat      Start scheduling!

    \b
    Examples:
      claude-meet chat
      claude-meet setup --timezone Europe/Berlin
      claude-meet config
    """
    # If no command provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


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

    # Also load from user config directory
    user_env = get_env_file_path()
    if user_env.exists():
        from dotenv import load_dotenv as ld
        ld(user_env, override=True)

    config = Config()

    # Check if this is first run (no user config exists)
    is_first_run = not user_env.exists() and not os.getenv('TIMEZONE')

    click.echo("=" * 60)
    click.echo("  Claude Calendar Scheduler")
    click.echo(f"  Timezone: {click.style(config.default_timezone, fg='yellow')}", nl=False)
    if is_first_run:
        click.echo(click.style(" (auto-detected)", fg='cyan'))
    else:
        click.echo()
    click.echo("  Type 'help' for commands, 'exit' to quit")
    click.echo("=" * 60)

    # First-run prompt
    if is_first_run:
        click.echo()
        click.echo(click.style("First time setup:", fg='cyan', bold=True))
        click.echo(f"  Your timezone was auto-detected as {config.default_timezone}")
        if not click.confirm("  Is this correct?", default=True):
            click.echo("\n  Run 'claude-meet setup' to configure your timezone.")
            click.echo("  Then run 'claude-meet chat' again.\n")
            return
        # Save the detected timezone so we don't ask again
        save_timezone(config.default_timezone)
        click.echo(click.style("  Timezone saved!\n", fg='green'))

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

    calendar_client = CalendarClient(calendar_service, timezone=config.default_timezone)
    claude_client = ClaudeClient(api_key, calendar_client, timezone=config.default_timezone)

    # Main conversation loop
    conversation_history = []

    while True:
        try:
            # Get user input (allow empty with default)
            user_input = click.prompt(
                click.style("You", fg='green', bold=True),
                type=str,
                default='',
                show_default=False
            )

            # Skip empty input silently
            if not user_input or not user_input.strip():
                continue

            user_input = user_input.strip()

            # Check for exit commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                click.echo("\nGoodbye! Have a productive day!")
                break

            # Check for help command
            if user_input.lower() == 'help':
                _show_help()
                continue

            # Check for clear command
            if user_input.lower() == 'clear':
                conversation_history = []
                click.clear()
                click.echo("Conversation cleared.\n")
                continue

            # Check for config/settings command
            if user_input.lower() in ['config', 'settings', 'timezone']:
                click.echo(f"\nCurrent timezone: {click.style(config.default_timezone, fg='yellow')}")
                click.echo("To change: exit and run 'claude-meet setup'\n")
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

    # Also load from user config directory
    user_env = get_env_file_path()
    if user_env.exists():
        from dotenv import load_dotenv as ld
        ld(user_env, override=True)

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
@click.option('--timezone', '-tz', help='Set timezone directly (e.g., Europe/Berlin)')
def setup(timezone):
    """
    Configure Claude Calendar Scheduler settings.

    Interactively set your timezone and other preferences.
    Your settings are saved to ~/.claude-meet/.env
    """
    click.echo()
    click.echo(click.style("Claude Calendar Scheduler - Setup", fg='cyan', bold=True))
    click.echo("=" * 45)
    click.echo()

    # Timezone configuration
    if timezone:
        # Validate the provided timezone
        try:
            import pytz
            pytz.timezone(timezone)
            env_path = save_timezone(timezone)
            click.echo(click.style(f"Timezone set to: {timezone}", fg='green'))
            click.echo(f"Saved to: {env_path}")
        except Exception as e:
            click.echo(click.style(f"Invalid timezone: {timezone}", fg='red'), err=True)
            click.echo("Use 'claude-meet setup' without arguments to see available options.")
            return
    else:
        # Interactive timezone selection
        detected_tz = detect_system_timezone()
        click.echo(f"Detected system timezone: {click.style(detected_tz, fg='yellow')}")
        click.echo()

        # Ask if they want to use detected timezone
        use_detected = click.confirm(
            f"Use {detected_tz} as your timezone?",
            default=True
        )

        if use_detected:
            selected_tz = detected_tz
        else:
            click.echo()
            click.echo("Common timezones:")
            click.echo("-" * 30)

            timezones = get_common_timezones()
            # Group by region
            regions = {}
            for tz in timezones:
                region = tz.split('/')[0]
                if region not in regions:
                    regions[region] = []
                regions[region].append(tz)

            # Display grouped
            idx = 1
            tz_map = {}
            for region in ['Europe', 'America', 'Asia', 'Australia', 'Pacific', 'UTC']:
                if region in regions or region == 'UTC':
                    click.echo(click.style(f"\n  {region}:", fg='cyan'))
                    tzs = regions.get(region, ['UTC'])
                    for tz in tzs:
                        city = tz.split('/')[-1].replace('_', ' ') if '/' in tz else tz
                        click.echo(f"    {idx:2}. {city:<20} ({tz})")
                        tz_map[idx] = tz
                        idx += 1

            click.echo()
            click.echo(f"    {idx}. Enter custom timezone")
            click.echo()

            choice = click.prompt(
                "Select timezone",
                type=int,
                default=1
            )

            if choice == idx:
                # Custom timezone
                selected_tz = click.prompt("Enter timezone (e.g., Europe/Berlin)")
                try:
                    import pytz
                    pytz.timezone(selected_tz)
                except Exception:
                    click.echo(click.style(f"Invalid timezone: {selected_tz}", fg='red'))
                    return
            elif choice in tz_map:
                selected_tz = tz_map[choice]
            else:
                click.echo(click.style("Invalid selection", fg='red'))
                return

        # Save the timezone
        env_path = save_timezone(selected_tz)
        click.echo()
        click.echo(click.style(f"Timezone set to: {selected_tz}", fg='green', bold=True))
        click.echo(f"Configuration saved to: {env_path}")

    click.echo()
    click.echo("Setup complete! You can now use 'claude-meet chat' to start scheduling.")
    click.echo()
    click.echo("Tip: Run 'claude-meet config' to view your current settings.")


@cli.command()
def config():
    """
    Show current configuration settings.
    """
    load_dotenv()

    # Also load from user config directory
    user_env = get_env_file_path()
    if user_env.exists():
        from dotenv import load_dotenv as ld
        ld(user_env)

    cfg = Config()

    click.echo()
    click.echo(click.style("Current Configuration", fg='cyan', bold=True))
    click.echo("=" * 40)
    click.echo()
    click.echo(f"  Timezone:        {click.style(cfg.default_timezone, fg='yellow')}")
    click.echo(f"  Business hours:  {cfg.business_hours_start}:00 - {cfg.business_hours_end}:00")
    click.echo(f"  Default meeting: {cfg.default_duration} minutes")
    click.echo(f"  Prefer morning:  {cfg.prefer_morning}")
    click.echo()
    click.echo(f"  Config file:     {get_env_file_path()}")
    click.echo()
    click.echo("To change timezone: claude-meet setup")
    click.echo("To change timezone directly: claude-meet setup --timezone Europe/London")
    click.echo()


@cli.command()
@click.option('--count', '-n', default=10, help='Number of events to show')
def upcoming(count):
    """
    Show upcoming calendar events.
    """
    load_dotenv()

    # Also load from user config directory
    user_env = get_env_file_path()
    if user_env.exists():
        from dotenv import load_dotenv as ld
        ld(user_env, override=True)

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
║    help     - Show this help message                         ║
║    clear    - Clear conversation history                     ║
║    timezone - Show current timezone                          ║
║    exit     - Exit the application (or 'quit', 'q')          ║
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
