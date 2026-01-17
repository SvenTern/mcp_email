"""
Unit tests for Subagent Executor (Mode B) - Claude Code CLI.

Tests:
- Successful execution
- Claude CLI not found
- Timeout handling
- JSON output parsing
- Plain text output parsing
- System prompt support
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import json

import sys
sys.path.insert(0, str(__file__).rsplit("/tests", 1)[0] + "/wrapper")

from cron_mcp.subagent_cli import (
    SubagentExecutorCLI,
    CLIConfig,
    CLIResult,
    validate_claude_cli
)


class TestCLIConfig:
    """Tests for CLIConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CLIConfig()
        assert config.cli_path == "claude"
        assert config.timeout == 300
        assert config.allowed_tools is None
        assert config.max_turns == 10
        assert config.model is None

    def test_custom_values(self):
        """Test custom configuration values."""
        config = CLIConfig(
            cli_path="/usr/local/bin/claude",
            timeout=600,
            allowed_tools=["mcp__email__send_email"],
            max_turns=15,
            model="claude-opus-4-20250514"
        )
        assert config.cli_path == "/usr/local/bin/claude"
        assert config.timeout == 600
        assert config.allowed_tools == ["mcp__email__send_email"]
        assert config.max_turns == 15
        assert config.model == "claude-opus-4-20250514"


class TestValidateClaudeCLI:
    """Tests for validate_claude_cli function."""

    def test_cli_not_found(self):
        """Test when CLI is not found."""
        with patch("shutil.which", return_value=None):
            result = validate_claude_cli()

        assert result["available"] is False
        assert result["path"] is None
        assert "not found" in result["error"].lower()

    def test_cli_found_version_success(self):
        """Test when CLI is found and version check succeeds."""
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_run:

            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="claude-code v1.0.0"
            )

            result = validate_claude_cli()

        assert result["available"] is True
        assert result["path"] == "/usr/bin/claude"
        assert result["version"] == "claude-code v1.0.0"

    def test_cli_found_version_fails(self):
        """Test when CLI is found but version check fails."""
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_run:

            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="Error: unknown option"
            )

            result = validate_claude_cli()

        assert result["available"] is False
        assert result["path"] == "/usr/bin/claude"


class TestSubagentExecutorCLI:
    """Tests for SubagentExecutorCLI class."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return CLIConfig(
            cli_path="claude",
            timeout=30,
            max_turns=5
        )

    @pytest.fixture
    def executor(self, config):
        """Create executor instance."""
        with patch("shutil.which", return_value="/usr/bin/claude"):
            return SubagentExecutorCLI(config)

    @pytest.mark.asyncio
    async def test_execute_success_json_output(self, config):
        """Test successful execution with JSON output."""
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_subprocess_run:

            # Mock version check
            mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="v1.0.0")

            executor = SubagentExecutorCLI(config)

            # Mock async subprocess
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                json.dumps({"result": "Email sent successfully"}).encode(),
                b""
            ))

            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await executor.execute(
                    prompt="Send email to test@example.com"
                )

        assert result.success is True
        assert result.output == "Email sent successfully"
        assert result.exit_code == 0
        assert result.error is None

    @pytest.mark.asyncio
    async def test_execute_success_plain_text_output(self, config):
        """Test successful execution with plain text output."""
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_subprocess_run:

            mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="v1.0.0")

            executor = SubagentExecutorCLI(config)

            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                b"Task completed successfully",
                b""
            ))

            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await executor.execute(
                    prompt="Do something"
                )

        assert result.success is True
        assert result.output == "Task completed successfully"

    @pytest.mark.asyncio
    async def test_execute_cli_not_available(self, config):
        """Test execution when CLI is not available."""
        with patch("shutil.which", return_value=None), \
             patch("subprocess.run") as mock_subprocess_run:

            # Version check will fail
            mock_subprocess_run.return_value = MagicMock(returncode=1, stderr="not found")

            executor = SubagentExecutorCLI(config)
            result = await executor.execute(
                prompt="Do something"
            )

        assert result.success is False
        assert "not available" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_timeout(self, config):
        """Test timeout handling."""
        config.timeout = 1

        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_subprocess_run:

            mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="v1.0.0")

            executor = SubagentExecutorCLI(config)

            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(
                side_effect=asyncio.TimeoutError()
            )
            mock_process.kill = MagicMock()
            mock_process.wait = AsyncMock()

            with patch("asyncio.create_subprocess_exec", return_value=mock_process), \
                 patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
                result = await executor.execute(
                    prompt="Long running task"
                )

        assert result.success is False
        assert "timed out" in result.error.lower() or "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_non_zero_exit_code(self, config):
        """Test handling of non-zero exit code."""
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_subprocess_run:

            mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="v1.0.0")

            executor = SubagentExecutorCLI(config)

            # Use MagicMock for process with AsyncMock only for async methods
            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(
                b"",
                b"Error: Authentication failed"
            ))

            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await executor.execute(
                    prompt="Do something"
                )

        assert result.success is False
        assert result.exit_code == 1
        assert "authentication failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_with_allowed_tools(self, config):
        """Test execution with allowed tools parameter."""
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_subprocess_run:

            mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="v1.0.0")

            executor = SubagentExecutorCLI(config)

            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"Done", b""))

            with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
                await executor.execute(
                    prompt="Send email",
                    allowed_tools=["mcp__email__send_email", "mcp__email__list_emails"]
                )

            # Verify --allowedTools was passed
            call_args = mock_exec.call_args[0]
            assert "--allowedTools" in call_args
            tools_index = call_args.index("--allowedTools")
            assert call_args[tools_index + 1] == "mcp__email__send_email,mcp__email__list_emails"

    @pytest.mark.asyncio
    async def test_execute_with_system_prompt(self, config):
        """Test execution with system prompt parameter."""
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_subprocess_run:

            mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="v1.0.0")

            executor = SubagentExecutorCLI(config)

            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"Done", b""))

            with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
                await executor.execute(
                    prompt="Do task",
                    system_prompt="You are a helpful email assistant"
                )

            # Verify --system-prompt was passed
            call_args = mock_exec.call_args[0]
            assert "--system-prompt" in call_args
            sys_prompt_index = call_args.index("--system-prompt")
            assert call_args[sys_prompt_index + 1] == "You are a helpful email assistant"

    @pytest.mark.asyncio
    async def test_execute_with_model(self):
        """Test execution with custom model."""
        config = CLIConfig(
            cli_path="claude",
            timeout=30,
            model="claude-opus-4-20250514"
        )

        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_subprocess_run:

            mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="v1.0.0")

            executor = SubagentExecutorCLI(config)

            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"Done", b""))

            with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
                await executor.execute(prompt="Do task")

            # Verify --model was passed
            call_args = mock_exec.call_args[0]
            assert "--model" in call_args
            model_index = call_args.index("--model")
            assert call_args[model_index + 1] == "claude-opus-4-20250514"

    def test_build_command_basic(self, config):
        """Test building basic command."""
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_subprocess_run:

            mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="v1.0.0")

            executor = SubagentExecutorCLI(config)
            cmd = executor._build_command("Test prompt")

        assert cmd[0] == "claude"
        assert "-p" in cmd
        assert "Test prompt" in cmd
        assert "--max-turns" in cmd
        assert "5" in cmd
        assert "--output-format" in cmd
        assert "json" in cmd

    def test_build_command_with_all_options(self):
        """Test building command with all options."""
        config = CLIConfig(
            cli_path="/custom/claude",
            timeout=60,
            allowed_tools=["tool1", "tool2"],
            max_turns=20,
            model="claude-opus-4-20250514"
        )

        with patch("shutil.which", return_value="/custom/claude"), \
             patch("subprocess.run") as mock_subprocess_run:

            mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="v1.0.0")

            executor = SubagentExecutorCLI(config)
            cmd = executor._build_command(
                "Test prompt",
                allowed_tools=["override_tool"],
                system_prompt="Custom system prompt"
            )

        assert cmd[0] == "/custom/claude"
        assert "--allowedTools" in cmd
        assert "override_tool" in cmd
        assert "--max-turns" in cmd
        assert "20" in cmd
        assert "--model" in cmd
        assert "claude-opus-4-20250514" in cmd
        assert "--system-prompt" in cmd
        assert "Custom system prompt" in cmd

    def test_get_default_allowed_tools(self):
        """Test getting default allowed tools."""
        tools = SubagentExecutorCLI.get_default_allowed_tools()

        assert "mcp__email__send_email" in tools
        assert "mcp__email__list_emails" in tools
        assert "mcp__bitrix__create_lead" in tools
