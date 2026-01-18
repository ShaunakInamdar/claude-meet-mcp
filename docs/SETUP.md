# Setup Guide

Complete setup instructions for Claude Calendar Scheduler.

## Prerequisites

- Python 3.9 or higher
- A Google account
- An Anthropic account

## Step 1: Google Cloud Setup

### Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click "Select a project" in the top navigation
3. Click "New Project"
4. Enter a project name (e.g., "Claude Calendar Scheduler")
5. Click "Create"

### Enable Google Calendar API

1. In your project, go to "APIs & Services" > "Library"
2. Search for "Google Calendar API"
3. Click on it and then click "Enable"

### Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - User Type: External
   - App name: Claude Calendar Scheduler
   - User support email: Your email
   - Developer contact: Your email
   - Click "Save and Continue" through the remaining steps
4. Back to credentials, select "Desktop app" as application type
5. Name it (e.g., "Claude Meet Desktop")
6. Click "Create"
7. Download the JSON file

### Save Credentials

Save the downloaded JSON file to one of these locations:
- `~/.claude-meet/credentials.json` (recommended)
- `config/` directory in the project (already gitignored)

## Step 2: Anthropic API Setup

### Get API Key

1. Go to [Anthropic Console](https://console.anthropic.com)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key (starts with `sk-ant-`)

### Save API Key

Option A - Environment variable (recommended):
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Option B - File:
Save to `config/anthropic_apikey.txt`

Option C - .env file:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## Step 3: Install the Application

```bash
# Navigate to project directory
cd claude-booker

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Step 4: Authenticate with Google

Run the authentication command:
```bash
claude-meet auth
```

This will:
1. Open your default browser
2. Ask you to sign in to Google
3. Request permission to access your calendar
4. Save the authentication token locally

## Step 5: Verify Setup

```bash
# Check upcoming events
claude-meet upcoming

# Start interactive mode
claude-meet chat
```

## Configuration (Optional)

Create a `.env` file in the project root:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional
TIMEZONE=America/Los_Angeles
BUSINESS_HOURS_START=9
BUSINESS_HOURS_END=17
DEFAULT_DURATION=60
DEBUG=false
```

## File Locations

| File | Location | Purpose |
|------|----------|---------|
| Google credentials | `~/.claude-meet/credentials.json` | OAuth client config |
| OAuth token | `~/.claude-meet/token.json` | Stored auth token |
| API key | `config/anthropic_apikey.txt` | Anthropic API key |

## Troubleshooting

### "The OAuth client was not found"
- Verify the credentials.json file is in the correct location
- Check that the file contains valid JSON

### "Access blocked: This app's request is invalid"
- Make sure the OAuth consent screen is configured
- Add yourself as a test user if the app is in testing mode

### "Invalid API key"
- Verify the Anthropic API key is correct
- Check that there are no extra spaces or newlines

### "Module not found" errors
- Make sure the virtual environment is activated
- Run `pip install -r requirements.txt` again

## Security Notes

- Never commit credentials to version control
- The `config/` directory is gitignored by default
- Tokens are stored in your home directory (`~/.claude-meet/`)
- API keys should be kept secret

## Next Steps

See [USAGE.md](USAGE.md) for how to use the scheduler.
