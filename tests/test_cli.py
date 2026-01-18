"""Tests for the CLI module."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from claude_meet.cli import cli, get_api_key


class TestGetApiKey:
    """Tests for get_api_key function."""

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key-123'})
    def test_from_environment(self):
        """Gets API key from environment variable."""
        result = get_api_key()
        assert result == 'test-key-123'

    @patch.dict('os.environ', {}, clear=True)
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    def test_from_config_file(self, mock_read, mock_exists):
        """Gets API key from config file when env var not set."""
        mock_exists.return_value = True
        mock_read.return_value = 'file-key-456'

        result = get_api_key()
        assert result == 'file-key-456'


class TestCLI:
    """Tests for CLI commands."""

    def test_version(self):
        """Version command works."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert '1.0.0' in result.output

    def test_help(self):
        """Help command works."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Claude Calendar Scheduler' in result.output

    def test_chat_help(self):
        """Chat command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ['chat', '--help'])
        assert result.exit_code == 0
        assert 'interactive' in result.output.lower()

    def test_schedule_help(self):
        """Schedule command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ['schedule', '--help'])
        assert result.exit_code == 0

    def test_auth_help(self):
        """Auth command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ['auth', '--help'])
        assert result.exit_code == 0
        assert 'Google' in result.output

    def test_logout_help(self):
        """Logout command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ['logout', '--help'])
        assert result.exit_code == 0

    def test_upcoming_help(self):
        """Upcoming command help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ['upcoming', '--help'])
        assert result.exit_code == 0


class TestScheduleCommand:
    """Tests for the schedule command."""

    @patch('claude_meet.cli.get_calendar_service')
    @patch('claude_meet.cli.get_api_key')
    @patch('claude_meet.cli.ClaudeClient')
    def test_schedule_processes_message(self, mock_claude, mock_key, mock_calendar):
        """Schedule command processes the message."""
        mock_key.return_value = 'test-key'
        mock_calendar.return_value = MagicMock()

        mock_client = MagicMock()
        mock_client.process_message.return_value = ('Meeting scheduled!', [])
        mock_claude.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ['schedule', 'Test meeting'])

        assert result.exit_code == 0
        assert 'Meeting scheduled!' in result.output


class TestLogoutCommand:
    """Tests for the logout command."""

    @patch('claude_meet.cli.clear_credentials')
    def test_logout_clears_credentials(self, mock_clear):
        """Logout command clears credentials."""
        runner = CliRunner()
        result = runner.invoke(cli, ['logout'])

        assert result.exit_code == 0
        assert 'Credentials cleared' in result.output
        mock_clear.assert_called_once()
