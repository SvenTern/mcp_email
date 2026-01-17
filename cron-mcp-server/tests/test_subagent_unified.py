"""
Integration tests for Unified Subagent Interface.

Tests:
- Auto mode selection
- Explicit MCP_CLIENT mode
- Explicit CLAUDE_CLI mode
- Fallback when CLI unavailable
- Environment variable configuration
"""

import pytest
import pytest_asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, str(__file__).rsplit("/tests", 1)[0] + "/wrapper")

from cron_mcp.subagent import (
    SubagentExecutor,
    SubagentMode,
    UnifiedResult
)


class TestSubagentMode:
    """Tests for SubagentMode enum."""

    def test_mode_values(self):
        """Test enum values."""
        assert SubagentMode.MCP_CLIENT.value == "mcp_client"
        assert SubagentMode.CLAUDE_CLI.value == "claude_cli"
        assert SubagentMode.AUTO.value == "auto"


class TestUnifiedResult:
    """Tests for UnifiedResult dataclass."""

    def test_create_success_result(self):
        """Test creating successful result."""
        result = UnifiedResult(
            success=True,
            output="Task completed",
            mode_used="mcp_client",
            tool_calls=[{"tool": "test", "success": True}],
            turns_used=2
        )

        assert result.success is True
        assert result.output == "Task completed"
        assert result.mode_used == "mcp_client"
        assert len(result.tool_calls) == 1
        assert result.turns_used == 2
        assert result.error is None

    def test_create_failure_result(self):
        """Test creating failure result."""
        result = UnifiedResult(
            success=False,
            output="",
            mode_used="claude_cli",
            tool_calls=[],
            turns_used=0,
            error="Timeout"
        )

        assert result.success is False
        assert result.error == "Timeout"


class TestSubagentExecutor:
    """Tests for SubagentExecutor unified interface."""

    def setup_method(self):
        """Reset environment variables."""
        self._original_env = {}
        for key in ["SUBAGENT_DEFAULT_MODE", "SUBAGENT_TIMEOUT", "SUBAGENT_MAX_TURNS", "CLAUDE_MODEL"]:
            self._original_env[key] = os.environ.get(key)

    def teardown_method(self):
        """Restore environment variables."""
        for key, value in self._original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_default_mode_from_env_mcp_client(self):
        """Test getting default mode from environment - mcp_client."""
        os.environ["SUBAGENT_DEFAULT_MODE"] = "mcp_client"
        executor = SubagentExecutor()
        assert executor.default_mode == SubagentMode.MCP_CLIENT

    def test_default_mode_from_env_claude_cli(self):
        """Test getting default mode from environment - claude_cli."""
        os.environ["SUBAGENT_DEFAULT_MODE"] = "claude_cli"
        executor = SubagentExecutor()
        assert executor.default_mode == SubagentMode.CLAUDE_CLI

    def test_default_mode_from_env_auto(self):
        """Test getting default mode from environment - auto."""
        os.environ["SUBAGENT_DEFAULT_MODE"] = "auto"
        executor = SubagentExecutor()
        assert executor.default_mode == SubagentMode.AUTO

    def test_default_mode_unknown_value(self):
        """Test that unknown value defaults to AUTO."""
        os.environ["SUBAGENT_DEFAULT_MODE"] = "unknown"
        executor = SubagentExecutor()
        assert executor.default_mode == SubagentMode.AUTO

    def test_auto_select_mode_with_mcp_servers(self):
        """Test auto mode selection when mcp_servers provided."""
        executor = SubagentExecutor()
        mode = executor._auto_select_mode(
            mcp_servers=["https://mcp.example.com/email/mcp"],
            allowed_tools=None
        )
        assert mode == SubagentMode.MCP_CLIENT

    def test_auto_select_mode_with_allowed_tools_cli_available(self):
        """Test auto mode selection when allowed_tools provided and CLI available."""
        with patch("shutil.which", return_value="/usr/bin/claude"):
            executor = SubagentExecutor()
            mode = executor._auto_select_mode(
                mcp_servers=None,
                allowed_tools=["mcp__email__send_email"]
            )
        assert mode == SubagentMode.CLAUDE_CLI

    def test_auto_select_mode_with_allowed_tools_cli_unavailable(self):
        """Test auto mode selection when allowed_tools provided but CLI unavailable."""
        with patch("shutil.which", return_value=None):
            executor = SubagentExecutor()
            mode = executor._auto_select_mode(
                mcp_servers=None,
                allowed_tools=["mcp__email__send_email"]
            )
        # Falls back to MCP_CLIENT
        assert mode == SubagentMode.MCP_CLIENT

    def test_auto_select_mode_no_params(self):
        """Test auto mode selection with no params."""
        with patch("shutil.which", return_value=None):
            executor = SubagentExecutor()
            mode = executor._auto_select_mode(
                mcp_servers=None,
                allowed_tools=None
            )
        # Default to MCP_CLIENT
        assert mode == SubagentMode.MCP_CLIENT

    @pytest.mark.asyncio
    async def test_get_default_mcp_servers_from_registry(self):
        """Test getting default MCP servers from Registry."""
        from cron_mcp.mcp_registry import MCPServerConfig

        # Mock the registry
        mock_registry = MagicMock()
        mock_registry.list_servers = AsyncMock(return_value=[
            MCPServerConfig(
                id="test-email",
                name="email",
                url="https://mcp.example.com/email/mcp"
            ),
            MCPServerConfig(
                id="test-bitrix",
                name="bitrix",
                url="https://mcp.example.com/bitrix/mcp"
            ),
        ])

        with patch("cron_mcp.mcp_registry.get_registry", return_value=mock_registry):
            executor = SubagentExecutor()
            servers = await executor._get_default_mcp_servers()

        assert "https://mcp.example.com/email/mcp" in servers
        assert "https://mcp.example.com/bitrix/mcp" in servers

    @pytest.mark.asyncio
    async def test_get_default_mcp_servers_no_registry(self):
        """Test getting default MCP servers when Registry not initialized."""
        with patch("cron_mcp.mcp_registry.get_registry", return_value=None):
            executor = SubagentExecutor()
            servers = await executor._get_default_mcp_servers()

        assert servers == []

    @pytest.mark.asyncio
    async def test_execute_explicit_mcp_client_mode(self):
        """Test execution with explicit MCP_CLIENT mode."""
        with patch("cron_mcp.subagent.SubagentExecutorMCP") as MockMCPExecutor:
            mock_executor = AsyncMock()
            mock_executor.execute = AsyncMock(return_value=MagicMock(
                success=True,
                output="Done via MCP",
                tool_calls=[],
                turns_used=1,
                error=None
            ))
            MockMCPExecutor.return_value = mock_executor

            executor = SubagentExecutor()
            result = await executor.execute(
                prompt="Test task",
                mode=SubagentMode.MCP_CLIENT,
                mcp_servers=["https://mcp.example.com/test/mcp"]
            )

        assert result.success is True
        assert result.mode_used == "mcp_client"
        assert result.output == "Done via MCP"

    @pytest.mark.asyncio
    async def test_execute_explicit_claude_cli_mode(self):
        """Test execution with explicit CLAUDE_CLI mode."""
        with patch("cron_mcp.subagent.SubagentExecutorCLI") as MockCLIExecutor:
            mock_executor = AsyncMock()
            mock_executor.execute = AsyncMock(return_value=MagicMock(
                success=True,
                output="Done via CLI",
                exit_code=0,
                error=None
            ))
            MockCLIExecutor.return_value = mock_executor

            executor = SubagentExecutor()
            result = await executor.execute(
                prompt="Test task",
                mode=SubagentMode.CLAUDE_CLI,
                allowed_tools=["mcp__email__send_email"]
            )

        assert result.success is True
        assert result.mode_used == "claude_cli"
        assert result.output == "Done via CLI"

    @pytest.mark.asyncio
    async def test_execute_auto_mode_selects_mcp(self):
        """Test that AUTO mode selects MCP_CLIENT when servers provided."""
        with patch("cron_mcp.subagent.SubagentExecutorMCP") as MockMCPExecutor:
            mock_executor = AsyncMock()
            mock_executor.execute = AsyncMock(return_value=MagicMock(
                success=True,
                output="Auto selected MCP",
                tool_calls=[],
                turns_used=1,
                error=None
            ))
            MockMCPExecutor.return_value = mock_executor

            executor = SubagentExecutor()
            result = await executor.execute(
                prompt="Test task",
                mode=SubagentMode.AUTO,
                mcp_servers=["https://mcp.example.com/test/mcp"]
            )

        assert result.mode_used == "mcp_client"

    @pytest.mark.asyncio
    async def test_execute_auto_mode_selects_cli(self):
        """Test that AUTO mode selects CLAUDE_CLI when CLI available and tools specified."""
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("cron_mcp.subagent.SubagentExecutorCLI") as MockCLIExecutor:

            mock_executor = AsyncMock()
            mock_executor.execute = AsyncMock(return_value=MagicMock(
                success=True,
                output="Auto selected CLI",
                exit_code=0,
                error=None
            ))
            MockCLIExecutor.return_value = mock_executor

            executor = SubagentExecutor()
            result = await executor.execute(
                prompt="Test task",
                mode=SubagentMode.AUTO,
                allowed_tools=["mcp__email__send_email"]
            )

        assert result.mode_used == "claude_cli"

    @pytest.mark.asyncio
    async def test_execute_with_custom_parameters(self):
        """Test execution with custom parameters."""
        os.environ["SUBAGENT_TIMEOUT"] = "60"
        os.environ["SUBAGENT_MAX_TURNS"] = "3"
        os.environ["CLAUDE_MODEL"] = "claude-sonnet-4-20250514"

        with patch("cron_mcp.subagent.SubagentExecutorMCP") as MockMCPExecutor:
            mock_executor = AsyncMock()
            mock_executor.execute = AsyncMock(return_value=MagicMock(
                success=True,
                output="Done",
                tool_calls=[],
                turns_used=1,
                error=None
            ))
            MockMCPExecutor.return_value = mock_executor

            executor = SubagentExecutor()
            await executor.execute(
                prompt="Test task",
                mode=SubagentMode.MCP_CLIENT,
                mcp_servers=["https://mcp.example.com/test/mcp"],
                max_turns=10,  # Override env
                timeout=120,   # Override env
                model="claude-opus-4-20250514"  # Override env
            )

        # Verify SubagentConfig was created with overridden values
        call_args = MockMCPExecutor.call_args
        config = call_args[0][0]  # First positional arg is config
        assert config.max_turns == 10
        assert config.timeout == 120
        assert config.model == "claude-opus-4-20250514"

    @pytest.mark.asyncio
    async def test_execute_with_system_prompt(self):
        """Test that system_prompt is passed through."""
        with patch("cron_mcp.subagent.SubagentExecutorMCP") as MockMCPExecutor:
            mock_executor = AsyncMock()
            mock_executor.execute = AsyncMock(return_value=MagicMock(
                success=True,
                output="Done",
                tool_calls=[],
                turns_used=1,
                error=None
            ))
            MockMCPExecutor.return_value = mock_executor

            executor = SubagentExecutor()
            await executor.execute(
                prompt="Test task",
                mode=SubagentMode.MCP_CLIENT,
                mcp_servers=["https://mcp.example.com/test/mcp"],
                system_prompt="You are a helpful assistant"
            )

        # Verify execute was called with system_prompt
        mock_executor.execute.assert_called_once()
        call_kwargs = mock_executor.execute.call_args[1]
        assert call_kwargs["system_prompt"] == "You are a helpful assistant"

    @pytest.mark.asyncio
    async def test_execute_mcp_failure(self):
        """Test handling of MCP execution failure."""
        with patch("cron_mcp.subagent.SubagentExecutorMCP") as MockMCPExecutor:
            mock_executor = AsyncMock()
            mock_executor.execute = AsyncMock(return_value=MagicMock(
                success=False,
                output="",
                tool_calls=[],
                turns_used=2,
                error="Connection failed"
            ))
            MockMCPExecutor.return_value = mock_executor

            executor = SubagentExecutor()
            result = await executor.execute(
                prompt="Test task",
                mode=SubagentMode.MCP_CLIENT,
                mcp_servers=["https://mcp.example.com/test/mcp"]
            )

        assert result.success is False
        assert result.error == "Connection failed"
        assert result.turns_used == 2

    @pytest.mark.asyncio
    async def test_execute_cli_failure(self):
        """Test handling of CLI execution failure."""
        with patch("cron_mcp.subagent.SubagentExecutorCLI") as MockCLIExecutor:
            mock_executor = AsyncMock()
            mock_executor.execute = AsyncMock(return_value=MagicMock(
                success=False,
                output="",
                exit_code=1,
                error="CLI not found"
            ))
            MockCLIExecutor.return_value = mock_executor

            executor = SubagentExecutor()
            result = await executor.execute(
                prompt="Test task",
                mode=SubagentMode.CLAUDE_CLI,
                allowed_tools=["mcp__email__send_email"]
            )

        assert result.success is False
        assert result.error == "CLI not found"
        assert result.mode_used == "claude_cli"
        # CLI mode doesn't return detailed tool_calls or turns_used
        assert result.tool_calls == []
        assert result.turns_used == 0
