# Claude Calendar Scheduler

Intelligent meeting scheduling from your terminal using Claude AI and Google Calendar.

## Features

- **Natural Language Scheduling**: Schedule meetings using plain English
- **Smart Time Finding**: Automatically finds times when all attendees are free
- **Intelligent Ranking**: Suggests optimal meeting times based on preferences
- **Google Calendar Integration**: Creates events and sends invitations automatically
- **Google Meet Support**: Optionally adds video conferencing links
- **Interactive CLI**: Conversational interface for complex scheduling tasks
- **MCP Server**: Integrates with Claude Desktop and Claude.ai as an MCP tool

## Quick Start (3 Steps)

### Step 1: Install

```bash
# Clone and run the installer
git clone https://github.com/ShaunakInamdar/claude-meet-mcp.git
cd claude-meet-mcp

# macOS/Linux:
./scripts/install.sh

# Windows PowerShell:
.\scripts\install.ps1

# Windows CMD:
scripts\install.bat
```

Or install manually:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### Step 2: Setup

Run the interactive setup wizard:
```bash
claude-meet init
```

This guides you through:
- Setting your Anthropic API key
- Creating Google Cloud credentials (with step-by-step instructions)
- Authenticating with Google Calendar
- Configuring your timezone

### Step 3: Use

```bash
claude-meet chat
```

That's it! You can verify everything is working with:
```bash
claude-meet check
```

---

## Detailed Setup (Manual)

### Prerequisites

- Python 3.9 or higher
- Google Cloud project with Calendar API enabled
- Anthropic API key

### Configuration

1. **Set up Google Calendar API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select an existing one
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials JSON file
   - Save it to `~/.claude-meet/credentials.json`

2. **Set up Anthropic API**:
   - Get your API key from [Anthropic Console](https://console.anthropic.com)
   - Set it using the config command:
     ```bash
     claude-meet config set ANTHROPIC_API_KEY=sk-ant-...
     ```

3. **Authenticate with Google**:
   ```bash
   claude-meet auth
   ```

---

## Usage

**Interactive Mode:**
```bash
claude-meet chat
```

**Single Command:**
```bash
claude-meet schedule "Schedule a meeting with alice@example.com tomorrow at 2pm"
```

**View Upcoming Events:**
```bash
claude-meet upcoming
```

## Example Conversations

```
You: Schedule a 1-hour meeting with alice@example.com and bob@example.com tomorrow

Claude: I'll find a time that works for everyone. Let me check their availability...

I found these available slots for tomorrow:
1. 9:00 AM - 10:00 AM (Recommended)
2. 2:00 PM - 3:00 PM (Good option)
3. 3:00 PM - 4:00 PM

Which time would you prefer? Also, what should I call this meeting?

You: Let's do 2pm, call it "Project Sync"

Claude: I've created the meeting "Project Sync" for tomorrow at 2:00 PM - 3:00 PM.
Invitations have been sent to alice@example.com and bob@example.com.

Calendar link: https://calendar.google.com/calendar/event?...
```

## Commands

| Command | Description |
|---------|-------------|
| `claude-meet init` | Interactive setup wizard (start here!) |
| `claude-meet check` | Verify your setup is complete |
| `claude-meet chat` | Start interactive scheduling session |
| `claude-meet schedule "..."` | Send a single scheduling request |
| `claude-meet auth` | Authenticate with Google Calendar |
| `claude-meet logout` | Clear stored credentials |
| `claude-meet setup` | Configure timezone and preferences |
| `claude-meet config` | View/manage configuration |
| `claude-meet config set KEY=value` | Set a configuration value |
| `claude-meet config get KEY` | Get a configuration value |
| `claude-meet mcp-setup` | Generate MCP config for Claude Desktop |
| `claude-meet upcoming` | Show upcoming calendar events |

## MCP Server (Claude Desktop Integration)

Claude Calendar Scheduler can run as an MCP server, allowing Claude Desktop to directly access your calendar.

### Quick Setup

Run the setup helper to get your configuration:
```bash
claude-meet mcp-setup
```

This will show you the exact JSON to add to your Claude Desktop config file.

Alternatively, add this to your Claude Desktop config manually:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "calendar-scheduler": {
      "command": "python",
      "args": ["-m", "claude_meet.mcp_server"]
    }
  }
}
```

After adding the config, restart Claude Desktop. Claude can now schedule meetings directly:
> "Schedule a meeting with alice@example.com tomorrow at 2pm"

### MCP Tools Available

| Tool | Description |
|------|-------------|
| `check_calendar_availability` | Check when people are free/busy |
| `find_meeting_times` | Find optimal meeting slots for multiple attendees |
| `create_calendar_event` | Create events and send invitations |

See [docs/MCP_SETUP.md](docs/MCP_SETUP.md) for detailed configuration.

## Configuration Options

Set via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | - | Your Anthropic API key |
| `TIMEZONE` | America/Los_Angeles | Default timezone |
| `BUSINESS_HOURS_START` | 9 | Business hours start (24h) |
| `BUSINESS_HOURS_END` | 17 | Business hours end (24h) |
| `DEFAULT_DURATION` | 60 | Default meeting duration (minutes) |
| `DEBUG` | false | Enable debug output |

## Project Structure

```
claude-booker/
├── claude_meet/
│   ├── __init__.py
│   ├── cli.py           # Command-line interface
│   ├── mcp_server.py    # MCP server for Claude Desktop
│   ├── claude_client.py # Claude API integration
│   ├── calendar_client.py # Google Calendar wrapper
│   ├── scheduler.py     # Scheduling algorithms
│   ├── auth.py          # OAuth handling
│   ├── config.py        # Configuration management
│   ├── errors.py        # Custom exceptions
│   └── utils.py         # Utility functions
├── scripts/
│   ├── install.sh       # Unix/macOS installer
│   ├── install.ps1      # Windows PowerShell installer
│   └── install.bat      # Windows CMD installer
├── tests/
├── docs/
├── config/              # Credentials (gitignored)
├── requirements.txt
├── setup.py
└── README.md
```

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/

# Run with debug output
claude-meet chat --debug
```

## Troubleshooting

First, run `claude-meet check` to see what's configured and what's missing.

**"Anthropic API key not found"**
- Run `claude-meet config set ANTHROPIC_API_KEY=sk-ant-...`
- Or set the `ANTHROPIC_API_KEY` environment variable

**"Google credentials not found"**
- Run `claude-meet init` for step-by-step setup instructions
- Download OAuth credentials from Google Cloud Console
- Save to `~/.claude-meet/credentials.json`

**"Authentication failed"**
- Run `claude-meet logout` then `claude-meet auth` to re-authenticate
- Check that your credentials.json file is valid

**"Rate limit exceeded"**
- Wait a moment and try again
- Check your API quotas in Google Cloud Console

**Need help with setup?**
- Run `claude-meet init` for guided setup
- Run `claude-meet check` to verify your configuration

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request
