"""Tests for the CLI module."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from claude_meet.cli import cli, get_api_key
from claude_meet.errors import APIKeyNotFoundError


class TestGetApiKey:
    """Tests for get_api_key function."""

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key-123"})
    def test_from_environment(self):
        """Gets API key from environment variable."""
        result = get_api_key()
        assert result == "test-key-123"

    @patch("claude_meet.cli.get_config_dir")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    def test_from_config_file(self, mock_read, mock_exists, mock_config_dir):
        """Gets API key from config file when env var not set."""
        # Clear the API key env var but keep HOME
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False):
            mock_config_dir.return_value = MagicMock()
            mock_config_dir.return_value.__truediv__ = MagicMock(return_value=MagicMock())
            mock_config_dir.return_value.__truediv__.return_value.exists.return_value = True
            mock_config_dir.return_value.__truediv__.return_value.read_text.return_value = (
                "file-key-456"
            )
            mock_exists.return_value = True
            mock_read.return_value = "file-key-456"

            result = get_api_key()
            assert result == "file-key-456"


class TestCLI:
    """Tests for CLI commands."""

    def test_version(self):
        """Version command works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_help(self):
        """Help command works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Claude Calendar Scheduler" in result.output

    def test_chat_help(self):
        """Chat command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["chat", "--help"])
        assert result.exit_code == 0
        assert "interactive" in result.output.lower()

    def test_schedule_help(self):
        """Schedule command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["schedule", "--help"])
        assert result.exit_code == 0

    def test_auth_help(self):
        """Auth command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["auth", "--help"])
        assert result.exit_code == 0
        assert "Google" in result.output

    def test_logout_help(self):
        """Logout command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["logout", "--help"])
        assert result.exit_code == 0

    def test_upcoming_help(self):
        """Upcoming command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["upcoming", "--help"])
        assert result.exit_code == 0


class TestScheduleCommand:
    """Tests for the schedule command."""

    @patch("claude_meet.cli.get_calendar_service")
    @patch("claude_meet.cli.get_api_key")
    @patch("claude_meet.cli.ClaudeClient")
    def test_schedule_processes_message(self, mock_claude, mock_key, mock_calendar):
        """Schedule command processes the message."""
        mock_key.return_value = "test-key"
        mock_calendar.return_value = MagicMock()

        mock_client = MagicMock()
        mock_client.process_message.return_value = ("Meeting scheduled!", [])
        mock_claude.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["schedule", "Test meeting"])

        assert result.exit_code == 0
        assert "Meeting scheduled!" in result.output


class TestLogoutCommand:
    """Tests for the logout command."""

    @patch("claude_meet.cli.clear_credentials")
    def test_logout_clears_credentials(self, mock_clear):
        """Logout command clears credentials."""
        runner = CliRunner()
        result = runner.invoke(cli, ["logout"])

        assert result.exit_code == 0
        assert "Credentials cleared" in result.output
        mock_clear.assert_called_once()


class TestCheckCommand:
    """Tests for the check command."""

    def test_check_help(self):
        """Check command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["check", "--help"])
        assert result.exit_code == 0
        assert "Verify" in result.output

    @patch("claude_meet.cli.get_api_key")
    @patch("claude_meet.cli.get_google_credentials_path")
    @patch("claude_meet.cli.get_config_dir")
    def test_check_shows_status(self, mock_config_dir, mock_creds, mock_key):
        """Check command shows configuration status."""
        mock_config_dir.return_value = MagicMock(exists=lambda: True)
        mock_creds.return_value = None
        mock_key.side_effect = APIKeyNotFoundError()

        runner = CliRunner()
        result = runner.invoke(cli, ["check"])

        assert "Setup Check" in result.output
        assert "Python" in result.output


class TestConfigCommand:
    """Tests for the config command group."""

    def test_config_help(self):
        """Config command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "Manage configuration" in result.output

    def test_config_show_help(self):
        """Config show subcommand help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "show", "--help"])
        assert result.exit_code == 0

    def test_config_set_help(self):
        """Config set subcommand help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "--help"])
        assert result.exit_code == 0
        assert "TIMEZONE=" in result.output or "KEY_VALUE" in result.output

    def test_config_get_help(self):
        """Config get subcommand help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "get", "--help"])
        assert result.exit_code == 0

    def test_config_list_help(self):
        """Config list subcommand help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "list", "--help"])
        assert result.exit_code == 0

    def test_config_list_shows_keys(self):
        """Config list shows available configuration keys."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "list"])
        assert result.exit_code == 0
        assert "TIMEZONE" in result.output
        assert "ANTHROPIC_API_KEY" in result.output

    def test_config_set_invalid_format(self):
        """Config set rejects invalid format."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "INVALID"])
        assert result.exit_code != 0
        assert "KEY=value" in result.output

    def test_config_set_invalid_timezone(self):
        """Config set rejects invalid timezone."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "TIMEZONE=InvalidZone"])
        assert result.exit_code != 0
        assert "Invalid timezone" in result.output


class TestInitCommand:
    """Tests for the init command."""

    def test_init_help(self):
        """Init command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "setup wizard" in result.output.lower()


class TestMcpSetupCommand:
    """Tests for the mcp-setup command."""

    def test_mcp_setup_help(self):
        """MCP setup command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["mcp-setup", "--help"])
        assert result.exit_code == 0
        assert "Claude Desktop" in result.output

    def test_mcp_setup_generates_json(self):
        """MCP setup generates valid JSON config."""
        runner = CliRunner()
        result = runner.invoke(cli, ["mcp-setup"])
        assert result.exit_code == 0
        assert "mcpServers" in result.output
        assert "calendar-scheduler" in result.output
        assert "claude_meet.mcp_server" in result.output


class TestSetupCommand:
    """Tests for the setup command."""

    def test_setup_help(self):
        """Setup command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["setup", "--help"])
        assert result.exit_code == 0
        assert "timezone" in result.output.lower()

    def test_setup_invalid_timezone(self):
        """Setup rejects invalid timezone."""
        runner = CliRunner()
        result = runner.invoke(cli, ["setup", "--timezone", "Invalid/Zone"])
        assert "Invalid timezone" in result.output
