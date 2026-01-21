"""
Command-line interface for Claude Calendar Scheduler.

Provides an interactive terminal interface for natural language
meeting scheduling powered by Claude and Google Calendar.
"""

import os
import sys
from pathlib import Path

# Fix Windows console encoding for Unicode
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click
from dotenv import load_dotenv

from .auth import clear_credentials, get_calendar_service
from .calendar_client import CalendarClient
from .claude_client import ClaudeClient
from .config import (
    CONFIG_KEYS,
    Config,
    detect_system_timezone,
    get_common_timezones,
    get_config_dir,
    get_config_value,
    get_env_file_path,
    get_google_credentials_path,
    save_timezone,
    set_config_value,
)
from .errors import APIKeyNotFoundError


def get_api_key() -> str:
    """
    Get the Anthropic API key from environment or config file.

    Checks in order:
    1. ANTHROPIC_API_KEY environment variable
    2. ~/.claude-meet/anthropic_apikey.txt
    3. config/anthropic_apikey.txt file (project dir)

    Returns:
        str: The API key

    Raises:
        APIKeyNotFoundError: If no API key is found
    """
    # Check environment variable first
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        return api_key.strip()

    # Check user config directory
    user_key_file = get_config_dir() / "anthropic_apikey.txt"
    if user_key_file.exists():
        api_key = user_key_file.read_text().strip()
        if api_key:
            return api_key

    # Check project config file
    config_file = Path(__file__).parent.parent / "config" / "anthropic_apikey.txt"
    if config_file.exists():
        api_key = config_file.read_text().strip()
        if api_key:
            return api_key

    raise APIKeyNotFoundError()


@click.group(invoke_without_command=True)
@click.version_option(version="1.0.0", prog_name="claude-meet")
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
@click.option("--debug", is_flag=True, help="Enable debug mode with verbose output")
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
    is_first_run = not user_env.exists() and not os.getenv("TIMEZONE")

    click.echo("=" * 60)
    click.echo("  Claude Calendar Scheduler")
    click.echo(f"  Timezone: {click.style(config.default_timezone, fg='yellow')}", nl=False)
    if is_first_run:
        click.echo(click.style(" (auto-detected)", fg="cyan"))
    else:
        click.echo()
    click.echo("  Type 'help' for commands, 'exit' to quit")
    click.echo("=" * 60)

    # First-run prompt
    if is_first_run:
        click.echo()
        click.echo(click.style("First time setup:", fg="cyan", bold=True))
        click.echo(f"  Your timezone was auto-detected as {config.default_timezone}")
        if not click.confirm("  Is this correct?", default=True):
            click.echo("\n  Run 'claude-meet setup' to configure your timezone.")
            click.echo("  Then run 'claude-meet chat' again.\n")
            return
        # Save the detected timezone so we don't ask again
        save_timezone(config.default_timezone)
        click.echo(click.style("  Timezone saved!\n", fg="green"))

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
                click.style("You", fg="green", bold=True), type=str, default="", show_default=False
            )

            # Skip empty input silently
            if not user_input or not user_input.strip():
                continue

            user_input = user_input.strip()

            # Check for exit commands
            if user_input.lower() in ["exit", "quit", "q"]:
                click.echo("\nGoodbye! Have a productive day!")
                break

            # Check for help command
            if user_input.lower() == "help":
                _show_help()
                continue

            # Check for clear command
            if user_input.lower() == "clear":
                conversation_history = []
                click.clear()
                click.echo("Conversation cleared.\n")
                continue

            # Check for config/settings command
            if user_input.lower() in ["config", "settings", "timezone"]:
                click.echo(
                    f"\nCurrent timezone: {click.style(config.default_timezone, fg='yellow')}"
                )
                click.echo("To change: exit and run 'claude-meet setup'\n")
                continue

            # Process the message through Claude
            click.echo()  # Blank line before response

            response, conversation_history = claude_client.process_message(
                user_input, conversation_history
            )

            # Display Claude's response
            click.echo(click.style("Claude: ", fg="blue", bold=True) + response)
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
@click.argument("message", nargs=-1, required=True)
@click.option("--debug", is_flag=True, help="Enable debug mode")
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

    message_text = " ".join(message)

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
        calendar = service.calendars().get(calendarId="primary").execute()
        click.echo("\nSuccessfully authenticated!")
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
@click.option("--timezone", "-tz", help="Set timezone directly (e.g., Europe/Berlin)")
def setup(timezone):
    """
    Configure Claude Calendar Scheduler settings.

    Interactively set your timezone and other preferences.
    Your settings are saved to ~/.claude-meet/.env
    """
    click.echo()
    click.echo(click.style("Claude Calendar Scheduler - Setup", fg="cyan", bold=True))
    click.echo("=" * 45)
    click.echo()

    # Timezone configuration
    if timezone:
        # Validate the provided timezone
        try:
            import pytz

            pytz.timezone(timezone)
            env_path = save_timezone(timezone)
            click.echo(click.style(f"Timezone set to: {timezone}", fg="green"))
            click.echo(f"Saved to: {env_path}")
        except Exception:
            click.echo(click.style(f"Invalid timezone: {timezone}", fg="red"), err=True)
            click.echo("Use 'claude-meet setup' without arguments to see available options.")
            return
    else:
        # Interactive timezone selection
        detected_tz = detect_system_timezone()
        click.echo(f"Detected system timezone: {click.style(detected_tz, fg='yellow')}")
        click.echo()

        # Ask if they want to use detected timezone
        use_detected = click.confirm(f"Use {detected_tz} as your timezone?", default=True)

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
                region = tz.split("/")[0]
                if region not in regions:
                    regions[region] = []
                regions[region].append(tz)

            # Display grouped
            idx = 1
            tz_map = {}
            for region in ["Europe", "America", "Asia", "Australia", "Pacific", "UTC"]:
                if region in regions or region == "UTC":
                    click.echo(click.style(f"\n  {region}:", fg="cyan"))
                    tzs = regions.get(region, ["UTC"])
                    for tz in tzs:
                        city = tz.split("/")[-1].replace("_", " ") if "/" in tz else tz
                        click.echo(f"    {idx:2}. {city:<20} ({tz})")
                        tz_map[idx] = tz
                        idx += 1

            click.echo()
            click.echo(f"    {idx}. Enter custom timezone")
            click.echo()

            choice = click.prompt("Select timezone", type=int, default=1)

            if choice == idx:
                # Custom timezone
                selected_tz = click.prompt("Enter timezone (e.g., Europe/Berlin)")
                try:
                    import pytz

                    pytz.timezone(selected_tz)
                except Exception:
                    click.echo(click.style(f"Invalid timezone: {selected_tz}", fg="red"))
                    return
            elif choice in tz_map:
                selected_tz = tz_map[choice]
            else:
                click.echo(click.style("Invalid selection", fg="red"))
                return

        # Save the timezone
        env_path = save_timezone(selected_tz)
        click.echo()
        click.echo(click.style(f"Timezone set to: {selected_tz}", fg="green", bold=True))
        click.echo(f"Configuration saved to: {env_path}")

    click.echo()
    click.echo("Setup complete! You can now use 'claude-meet chat' to start scheduling.")
    click.echo()
    click.echo("Tip: Run 'claude-meet config' to view your current settings.")


@cli.group(invoke_without_command=True)
@click.pass_context
def config(ctx):
    """
    Manage configuration settings.

    \b
    Subcommands:
      show    Show current configuration (default)
      set     Set a configuration value
      get     Get a specific configuration value
      list    List all available configuration keys
    """
    if ctx.invoked_subcommand is None:
        # Default to showing config
        ctx.invoke(config_show)


@config.command("show")
def config_show():
    """Show current configuration settings."""
    load_dotenv()

    # Also load from user config directory
    user_env = get_env_file_path()
    if user_env.exists():
        from dotenv import load_dotenv as ld

        ld(user_env)

    cfg = Config()

    click.echo()
    click.echo(click.style("Current Configuration", fg="cyan", bold=True))
    click.echo("=" * 40)
    click.echo()
    click.echo(f"  Timezone:        {click.style(cfg.default_timezone, fg='yellow')}")
    click.echo(f"  Business hours:  {cfg.business_hours_start}:00 - {cfg.business_hours_end}:00")
    click.echo(f"  Default meeting: {cfg.default_duration} minutes")
    click.echo(f"  Prefer morning:  {cfg.prefer_morning}")
    click.echo()

    # Show API key status
    api_key_status = click.style("Not set", fg="red")
    try:
        key = get_api_key()
        api_key_status = click.style(f"{key[:8]}...{key[-4:]}", fg="green")
    except Exception:
        pass
    click.echo(f"  Anthropic API:   {api_key_status}")

    # Show credentials status
    creds_path = get_google_credentials_path()
    if creds_path:
        creds_status = click.style("Found", fg="green")
    else:
        creds_status = click.style("Not found", fg="red")
    click.echo(f"  Google creds:    {creds_status}")

    click.echo()
    click.echo(f"  Config file:     {get_env_file_path()}")
    click.echo()
    click.echo("Commands:")
    click.echo("  claude-meet config set KEY=value   Set a config value")
    click.echo("  claude-meet config get KEY         Get a config value")
    click.echo("  claude-meet config list            List all config keys")
    click.echo()


@config.command("set")
@click.argument("key_value")
def config_set(key_value):
    """
    Set a configuration value.

    \b
    Usage:
      claude-meet config set TIMEZONE=Europe/Berlin
      claude-meet config set ANTHROPIC_API_KEY=sk-ant-...
    """
    if "=" not in key_value:
        click.echo(click.style("Error: ", fg="red") + "Use format: KEY=value")
        click.echo("Example: claude-meet config set TIMEZONE=Europe/Berlin")
        sys.exit(1)

    key, value = key_value.split("=", 1)
    key = key.upper().strip()
    value = value.strip()

    if not value:
        click.echo(click.style("Error: ", fg="red") + "Value cannot be empty")
        sys.exit(1)

    # Validate timezone if setting TIMEZONE
    if key == "TIMEZONE":
        try:
            import pytz

            pytz.timezone(value)
        except Exception:
            click.echo(click.style(f"Error: Invalid timezone: {value}", fg="red"))
            click.echo("Run 'claude-meet setup' to see valid timezones.")
            sys.exit(1)

    env_path = set_config_value(key, value)
    click.echo(click.style(f"Set {key}", fg="green"))
    click.echo(f"Saved to: {env_path}")


@config.command("get")
@click.argument("key")
def config_get(key):
    """
    Get a configuration value.

    \b
    Usage:
      claude-meet config get TIMEZONE
      claude-meet config get ANTHROPIC_API_KEY
    """
    load_dotenv()
    user_env = get_env_file_path()
    if user_env.exists():
        from dotenv import load_dotenv as ld

        ld(user_env, override=True)

    key = key.upper().strip()
    value = get_config_value(key)

    if value:
        # Mask sensitive values
        display_value = value
        if "KEY" in key or "SECRET" in key:
            if len(value) > 10:
                display_value = value[:8] + "..." + value[-4:]
        click.echo(f"{key}={display_value}")
    else:
        click.echo(f"{key} is not set")


@config.command("list")
def config_list():
    """
    List all available configuration keys.
    """
    click.echo()
    click.echo(click.style("Available Configuration Keys", fg="cyan", bold=True))
    click.echo("=" * 50)
    click.echo()

    for key, description in CONFIG_KEYS.items():
        click.echo(f"  {click.style(key, fg='yellow')}")
        click.echo(f"    {description}")
        click.echo()

    click.echo("Set values with: claude-meet config set KEY=value")


@cli.command()
def check():
    """
    Verify your setup is complete and working.

    Checks all prerequisites and shows what's configured correctly
    and what still needs attention.
    """
    load_dotenv()
    user_env = get_env_file_path()
    if user_env.exists():
        from dotenv import load_dotenv as ld

        ld(user_env, override=True)

    click.echo()
    click.echo(click.style("Claude Calendar Scheduler - Setup Check", fg="cyan", bold=True))
    click.echo("=" * 50)
    click.echo()

    all_ok = True
    issues = []

    # Check 1: Python version
    py_version = sys.version_info
    if py_version >= (3, 9):
        click.echo(
            click.style("  [OK] ", fg="green") + f"Python {py_version.major}.{py_version.minor}"
        )
    else:
        click.echo(
            click.style("  [!]  ", fg="yellow")
            + f"Python {py_version.major}.{py_version.minor} (3.9+ recommended)"
        )

    # Check 2: Config directory
    config_dir = get_config_dir()
    if config_dir.exists():
        click.echo(click.style("  [OK] ", fg="green") + f"Config directory: {config_dir}")
    else:
        click.echo(click.style("  [X]  ", fg="red") + "Config directory not found")
        all_ok = False
        issues.append("Config directory missing")

    # Check 3: Anthropic API key
    try:
        api_key = get_api_key()
        masked = f"{api_key[:8]}...{api_key[-4:]}"
        click.echo(click.style("  [OK] ", fg="green") + f"Anthropic API key: {masked}")
    except APIKeyNotFoundError:
        click.echo(click.style("  [X]  ", fg="red") + "Anthropic API key: Not found")
        all_ok = False
        issues.append("Set ANTHROPIC_API_KEY (claude-meet config set ANTHROPIC_API_KEY=...)")

    # Check 4: Google credentials file
    creds_path = get_google_credentials_path()
    if creds_path:
        click.echo(click.style("  [OK] ", fg="green") + f"Google credentials: {creds_path}")

        # Validate JSON
        try:
            import json

            with open(creds_path) as f:
                creds_data = json.load(f)
            if "installed" in creds_data or "web" in creds_data:
                click.echo(click.style("  [OK] ", fg="green") + "Credentials file format: Valid")
            else:
                click.echo(
                    click.style("  [!]  ", fg="yellow")
                    + "Credentials file format: Unusual structure"
                )
        except json.JSONDecodeError:
            click.echo(click.style("  [X]  ", fg="red") + "Credentials file format: Invalid JSON")
            all_ok = False
            issues.append("credentials.json is not valid JSON")
    else:
        click.echo(click.style("  [X]  ", fg="red") + "Google credentials: Not found")
        all_ok = False
        issues.append("Add Google OAuth credentials (see 'claude-meet init' for help)")

    # Check 5: OAuth token (authentication status)
    token_path = get_config_dir() / "token.json"
    if token_path.exists():
        click.echo(click.style("  [OK] ", fg="green") + "Google authentication: Authenticated")

        # Try to verify token is valid
        try:
            service = get_calendar_service()
            calendar = service.calendars().get(calendarId="primary").execute()
            cal_name = calendar.get("summary", "Primary")
            click.echo(click.style("  [OK] ", fg="green") + f"Calendar connection: {cal_name}")
        except Exception:
            click.echo(
                click.style("  [!]  ", fg="yellow") + "Calendar connection: Token may be expired"
            )
            issues.append("Run 'claude-meet auth' to re-authenticate")
    else:
        click.echo(click.style("  [X]  ", fg="red") + "Google authentication: Not authenticated")
        all_ok = False
        issues.append("Run 'claude-meet auth' to authenticate")

    # Check 6: Timezone
    cfg = Config()
    click.echo(click.style("  [OK] ", fg="green") + f"Timezone: {cfg.default_timezone}")

    click.echo()

    if all_ok and not issues:
        click.echo(click.style("All checks passed!", fg="green", bold=True))
        click.echo("You're ready to use: claude-meet chat")
    else:
        click.echo(click.style("Setup incomplete. To fix:", fg="yellow", bold=True))
        for issue in issues:
            click.echo(f"  - {issue}")
        click.echo()
        click.echo("Or run 'claude-meet init' for guided setup.")

    click.echo()


@cli.command()
def init():
    """
    Interactive setup wizard for first-time configuration.

    Guides you through:
    - Setting up your Anthropic API key
    - Creating Google Cloud credentials
    - Authenticating with Google Calendar
    - Configuring your timezone
    """
    click.echo()
    click.echo(click.style("=" * 60, fg="cyan"))
    click.echo(click.style("  Claude Calendar Scheduler - Setup Wizard", fg="cyan", bold=True))
    click.echo(click.style("=" * 60, fg="cyan"))
    click.echo()
    click.echo("This wizard will help you set up everything you need.")
    click.echo("Press Ctrl+C at any time to exit.\n")

    load_dotenv()
    user_env = get_env_file_path()
    if user_env.exists():
        from dotenv import load_dotenv as ld

        ld(user_env, override=True)

    # Step 1: Anthropic API Key
    click.echo(click.style("Step 1/4: Anthropic API Key", fg="cyan", bold=True))
    click.echo("-" * 40)

    try:
        existing_key = get_api_key()
        masked = f"{existing_key[:8]}...{existing_key[-4:]}"
        click.echo(f"  Current key: {click.style(masked, fg='green')}")
        if not click.confirm("  Keep this key?", default=True):
            existing_key = None
    except APIKeyNotFoundError:
        existing_key = None
        click.echo("  No API key found.")

    if not existing_key:
        click.echo()
        click.echo("  Get your API key from: https://console.anthropic.com/settings/keys")
        click.echo()
        api_key = click.prompt("  Enter your Anthropic API key", hide_input=False)
        if api_key.strip():
            set_config_value("ANTHROPIC_API_KEY", api_key.strip())
            click.echo(click.style("  API key saved!", fg="green"))
    click.echo()

    # Step 2: Google Cloud Credentials
    click.echo(click.style("Step 2/4: Google Cloud Credentials", fg="cyan", bold=True))
    click.echo("-" * 40)

    creds_path = get_google_credentials_path()
    if creds_path:
        click.echo(f"  Credentials found: {click.style(str(creds_path), fg='green')}")
    else:
        click.echo("  No Google credentials found.")
        click.echo()
        click.echo(click.style("  Follow these steps to create credentials:", fg="yellow"))
        click.echo()
        click.echo("  1. Go to: https://console.cloud.google.com")
        click.echo("  2. Create a new project (or select existing)")
        click.echo("  3. Search for 'Google Calendar API' and enable it")
        click.echo("  4. Go to 'APIs & Services' > 'Credentials'")
        click.echo("  5. Click 'Create Credentials' > 'OAuth client ID'")
        click.echo("  6. Select 'Desktop app' as application type")
        click.echo("  7. Download the JSON file")
        click.echo(
            f"  8. Save it as: {click.style(str(get_config_dir() / 'credentials.json'), fg='yellow')}"
        )
        click.echo()

        click.pause("  Press Enter once you've saved the credentials file...")

        # Check again
        creds_path = get_google_credentials_path()
        if creds_path:
            click.echo(click.style("  Credentials found!", fg="green"))
        else:
            click.echo(click.style("  Credentials not found yet.", fg="yellow"))
            click.echo("  You can continue and add them later.")

    click.echo()

    # Step 3: Google Calendar Authentication
    click.echo(click.style("Step 3/4: Google Calendar Authentication", fg="cyan", bold=True))
    click.echo("-" * 40)

    token_path = get_config_dir() / "token.json"
    if token_path.exists():
        click.echo("  Already authenticated with Google Calendar.")
        if click.confirm("  Re-authenticate?", default=False):
            token_path.unlink()
        else:
            click.echo()
            # Skip to step 4
            pass

    if not token_path.exists() and creds_path:
        click.echo("  Opening browser for Google sign-in...")
        click.echo()
        try:
            service = get_calendar_service()
            calendar = service.calendars().get(calendarId="primary").execute()
            click.echo(
                click.style(f"  Connected to: {calendar.get('summary', 'Primary')}", fg="green")
            )
        except Exception as e:
            click.echo(click.style(f"  Authentication failed: {str(e)}", fg="red"))
            click.echo("  You can try again later with 'claude-meet auth'")
    elif not creds_path:
        click.echo("  Skipping - credentials file needed first.")

    click.echo()

    # Step 4: Timezone
    click.echo(click.style("Step 4/4: Timezone Configuration", fg="cyan", bold=True))
    click.echo("-" * 40)

    detected_tz = detect_system_timezone()
    current_tz = os.getenv("TIMEZONE") or detected_tz

    click.echo(f"  Detected timezone: {click.style(current_tz, fg='yellow')}")

    if click.confirm("  Is this correct?", default=True):
        save_timezone(current_tz)
        click.echo(click.style("  Timezone saved!", fg="green"))
    else:
        click.echo()
        click.echo("  Run 'claude-meet setup' to choose a different timezone.")

    # Summary
    click.echo()
    click.echo(click.style("=" * 60, fg="cyan"))
    click.echo(click.style("  Setup Complete!", fg="green", bold=True))
    click.echo(click.style("=" * 60, fg="cyan"))
    click.echo()
    click.echo("  Next steps:")
    click.echo("    1. Run 'claude-meet check' to verify everything")
    click.echo("    2. Run 'claude-meet chat' to start scheduling!")
    click.echo()
    click.echo("  For MCP integration with Claude Desktop:")
    click.echo("    Run 'claude-meet mcp-setup' to get configuration")
    click.echo()


@cli.command("mcp-setup")
def mcp_setup():
    """
    Generate MCP server configuration for Claude Desktop.

    Shows the JSON configuration needed to add this tool
    to Claude Desktop's MCP servers.
    """
    import json

    click.echo()
    click.echo(click.style("MCP Server Configuration for Claude Desktop", fg="cyan", bold=True))
    click.echo("=" * 55)
    click.echo()

    # Get Python path
    python_path = sys.executable

    # Build the config
    mcp_config = {
        "mcpServers": {
            "calendar-scheduler": {"command": python_path, "args": ["-m", "claude_meet.mcp_server"]}
        }
    }

    click.echo("Add this to your Claude Desktop configuration file:")
    click.echo()

    # Platform-specific path hints
    if sys.platform == "win32":
        config_path = r"%APPDATA%\Claude\claude_desktop_config.json"
    elif sys.platform == "darwin":
        config_path = "~/Library/Application Support/Claude/claude_desktop_config.json"
    else:
        config_path = "~/.config/Claude/claude_desktop_config.json"

    click.echo(f"  Config file location: {click.style(config_path, fg='yellow')}")
    click.echo()
    click.echo(click.style("Configuration to add:", fg="cyan"))
    click.echo()

    # Pretty print the JSON
    json_str = json.dumps(mcp_config, indent=2)
    for line in json_str.split("\n"):
        click.echo(f"  {line}")

    click.echo()
    click.echo(click.style("Instructions:", fg="yellow"))
    click.echo("  1. Open or create the config file at the location above")
    click.echo("  2. If file exists, merge the 'mcpServers' section")
    click.echo("  3. If file is empty, paste the entire configuration")
    click.echo("  4. Save and restart Claude Desktop")
    click.echo()
    click.echo("  For detailed instructions, see: docs/MCP_SETUP.md")
    click.echo()


@cli.command()
@click.option("--count", "-n", default=10, help="Number of events to show")
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
            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event.get("summary", "No title")
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


if __name__ == "__main__":
    main()
