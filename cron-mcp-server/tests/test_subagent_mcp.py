"""
Unit tests for Subagent Executor (Mode A) - MCP Client Hub.

Tests:
- Agentic loop with single tool call
- Agentic loop with multiple tool calls
- Max turns exceeded
- Timeout handling
- Tool call errors
- Recursion protection
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

import sys
sys.path.insert(0, str(__file__).rsplit("/tests", 1)[0] + "/wrapper")

from cron_mcp.subagent_mcp import (
    SubagentExecutorMCP,
    SubagentConfig,
    SubagentResult,
    check_recursion_depth,
    reset_recursion_depth,
    RecursionLimitExceeded,
    _subagent_depth,
    MAX_SUBAGENT_DEPTH
)


class TestSubagentConfig:
    """Tests for SubagentConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SubagentConfig()
        assert config.model == "claude-sonnet-4-20250514"
        assert config.max_turns == 10
        assert config.max_tokens == 4096
        assert config.timeout == 300
        assert config.proxy is None

    def test_custom_values(self):
        """Test custom configuration values."""
        config = SubagentConfig(
            model="claude-opus-4-20250514",
            max_turns=5,
            max_tokens=8192,
            timeout=600,
            proxy="http://localhost:7897"
        )
        assert config.model == "claude-opus-4-20250514"
        assert config.max_turns == 5
        assert config.max_tokens == 8192
        assert config.timeout == 600
        assert config.proxy == "http://localhost:7897"


class TestRecursionProtection:
    """Tests for recursion protection mechanism."""

    def setup_method(self):
        """Reset recursion depth before each test."""
        _subagent_depth.set(0)

    def test_check_recursion_depth_success(self):
        """Test incrementing recursion depth."""
        depth = check_recursion_depth()
        assert depth == 1
        depth = check_recursion_depth()
        assert depth == 2

    def test_check_recursion_depth_limit(self):
        """Test recursion limit enforcement."""
        for _ in range(MAX_SUBAGENT_DEPTH):
            check_recursion_depth()

        with pytest.raises(RecursionLimitExceeded):
            check_recursion_depth()

    def test_reset_recursion_depth(self):
        """Test resetting recursion depth."""
        check_recursion_depth()
        check_recursion_depth()
        assert _subagent_depth.get() == 2

        reset_recursion_depth(2)
        assert _subagent_depth.get() == 1

        reset_recursion_depth(1)
        assert _subagent_depth.get() == 0

    def test_reset_recursion_depth_floor(self):
        """Test that reset doesn't go below zero."""
        reset_recursion_depth(0)
        assert _subagent_depth.get() == 0


class TestSubagentExecutorMCP:
    """Tests for SubagentExecutorMCP class."""

    def setup_method(self):
        """Reset recursion depth before each test."""
        _subagent_depth.set(0)

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return SubagentConfig(
            model="claude-sonnet-4-20250514",
            max_turns=5,
            max_tokens=4096,
            timeout=30
        )

    @pytest.fixture
    def mock_mcp_hub(self, mock_mcp_response):
        """Create mock MCP Client Hub."""
        hub = AsyncMock()
        hub.connect = AsyncMock()
        hub.close = AsyncMock()
        hub.to_anthropic_format.return_value = [
            {
                "name": "email_send",
                "description": "Send an email",
                "input_schema": {"type": "object"}
            }
        ]
        hub.call_tool = AsyncMock(return_value=mock_mcp_response["tool_call"]["result"])
        return hub

    def _create_mock_hub(self, tools=None, tool_result=None):
        """Create a mock MCP Client Hub with proper async methods."""
        hub = MagicMock()
        hub.connect = AsyncMock()
        hub.close = AsyncMock()
        hub.to_anthropic_format = MagicMock(return_value=tools or [
            {"name": "test_tool", "description": "Test", "input_schema": {}}
        ])
        hub.call_tool = AsyncMock(return_value=tool_result or {
            "content": [{"type": "text", "text": "Success"}]
        })
        return hub

    @pytest.mark.asyncio
    async def test_execute_simple_response(self, config, mock_claude_response):
        """Test execution with simple text response (no tool calls)."""
        mock_hub = self._create_mock_hub()

        with patch("cron_mcp.subagent_mcp.MCPClientHub", return_value=mock_hub), \
             patch("anthropic.AsyncAnthropic") as MockAnthropic:

            # Setup Claude API mock
            client = AsyncMock()
            client.messages.create = AsyncMock(return_value=mock_claude_response)
            MockAnthropic.return_value = client

            executor = SubagentExecutorMCP(config)
            result = await executor.execute(
                prompt="Say hello",
                mcp_servers=["https://mcp.example.com/test/mcp"]
            )

        assert result.success is True
        assert result.output == "Task completed successfully"
        assert result.turns_used == 1
        assert result.tool_calls == []
        assert result.error is None

    @pytest.mark.asyncio
    async def test_execute_with_tool_call(self, config, mock_claude_response_with_tool_use, mock_claude_response, mock_mcp_response):
        """Test execution with tool call."""
        mock_hub = self._create_mock_hub(
            tools=[{"name": "email_send", "description": "Send email", "input_schema": {}}],
            tool_result=mock_mcp_response["tool_call"]["result"]
        )

        with patch("cron_mcp.subagent_mcp.MCPClientHub", return_value=mock_hub), \
             patch("anthropic.AsyncAnthropic") as MockAnthropic:

            # Setup Claude API mock - first call returns tool_use, second returns end_turn
            # Use MagicMock for client, AsyncMock only for async methods
            client = MagicMock()
            client.messages = MagicMock()
            client.messages.create = AsyncMock(
                side_effect=[mock_claude_response_with_tool_use, mock_claude_response]
            )
            MockAnthropic.return_value = client

            executor = SubagentExecutorMCP(config)
            result = await executor.execute(
                prompt="Send an email to test@example.com",
                mcp_servers=["https://mcp.example.com/email/mcp"]
            )

        assert result.success is True
        assert result.turns_used == 2
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["tool"] == "email_send"

    @pytest.mark.asyncio
    async def test_execute_max_turns_exceeded(self, config, mock_claude_response_with_tool_use, mock_mcp_response):
        """Test that max turns limit is enforced."""
        config.max_turns = 2

        mock_hub = self._create_mock_hub(
            tools=[{"name": "email_send", "description": "Send email", "input_schema": {}}],
            tool_result=mock_mcp_response["tool_call"]["result"]
        )

        with patch("cron_mcp.subagent_mcp.MCPClientHub", return_value=mock_hub), \
             patch("anthropic.AsyncAnthropic") as MockAnthropic:

            # Setup Claude API mock - always returns tool_use
            client = AsyncMock()
            client.messages.create = AsyncMock(return_value=mock_claude_response_with_tool_use)
            MockAnthropic.return_value = client

            executor = SubagentExecutorMCP(config)
            result = await executor.execute(
                prompt="Keep calling tools",
                mcp_servers=["https://mcp.example.com/email/mcp"]
            )

        assert result.success is False
        assert "max turns" in result.error.lower()
        assert result.turns_used == 2

    @pytest.mark.asyncio
    async def test_execute_no_tools_available(self, config):
        """Test handling when no tools are available."""
        # Create mock hub that returns empty tools list
        mock_hub = AsyncMock()
        mock_hub.connect = AsyncMock()
        mock_hub.close = AsyncMock()
        mock_hub.to_anthropic_format = MagicMock(return_value=[])  # Empty tools!

        with patch("cron_mcp.subagent_mcp.MCPClientHub", return_value=mock_hub), \
             patch("anthropic.AsyncAnthropic"):

            executor = SubagentExecutorMCP(config)
            result = await executor.execute(
                prompt="Do something",
                mcp_servers=["https://mcp.example.com/empty/mcp"]
            )

        assert result.success is False
        assert "no tools" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_tool_call_error(self, config, mock_claude_response_with_tool_use, mock_claude_response):
        """Test handling of tool call errors."""
        mock_hub = self._create_mock_hub(
            tools=[{"name": "email_send", "description": "Send email", "input_schema": {}}],
            tool_result={"error": "Connection failed"}
        )

        with patch("cron_mcp.subagent_mcp.MCPClientHub", return_value=mock_hub), \
             patch("anthropic.AsyncAnthropic") as MockAnthropic:

            # Setup Claude API mock
            client = AsyncMock()
            client.messages.create = AsyncMock(
                side_effect=[mock_claude_response_with_tool_use, mock_claude_response]
            )
            MockAnthropic.return_value = client

            executor = SubagentExecutorMCP(config)
            result = await executor.execute(
                prompt="Send email",
                mcp_servers=["https://mcp.example.com/email/mcp"]
            )

        # Should still succeed overall (Claude handles the error)
        assert result.success is True
        assert len(result.tool_calls) == 1
        # Tool call should be marked as failed
        assert result.tool_calls[0]["success"] is False

    @pytest.mark.asyncio
    async def test_execute_recursion_limit(self, config):
        """Test recursion limit protection."""
        # Set depth to max
        for _ in range(MAX_SUBAGENT_DEPTH):
            check_recursion_depth()

        mock_hub = self._create_mock_hub()

        with patch("cron_mcp.subagent_mcp.MCPClientHub", return_value=mock_hub), \
             patch("anthropic.AsyncAnthropic"):

            executor = SubagentExecutorMCP(config)
            result = await executor.execute(
                prompt="Recursive call",
                mcp_servers=["https://mcp.example.com/mcp"]
            )

        assert result.success is False
        assert "recursion" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_with_system_prompt(self, config, mock_claude_response):
        """Test execution with custom system prompt."""
        mock_hub = self._create_mock_hub()

        with patch("cron_mcp.subagent_mcp.MCPClientHub", return_value=mock_hub), \
             patch("anthropic.AsyncAnthropic") as MockAnthropic:

            # Setup Claude API mock
            client = AsyncMock()
            client.messages.create = AsyncMock(return_value=mock_claude_response)
            MockAnthropic.return_value = client

            executor = SubagentExecutorMCP(config)
            await executor.execute(
                prompt="Do task",
                mcp_servers=["https://mcp.example.com/mcp"],
                system_prompt="You are a helpful assistant for email tasks."
            )

        # Verify system prompt was passed
        call_args = client.messages.create.call_args
        assert call_args.kwargs["system"] == "You are a helpful assistant for email tasks."

    @pytest.mark.asyncio
    async def test_execute_api_error(self, config):
        """Test handling of Anthropic API errors."""
        import anthropic

        mock_hub = self._create_mock_hub()

        with patch("cron_mcp.subagent_mcp.MCPClientHub", return_value=mock_hub), \
             patch("anthropic.AsyncAnthropic") as MockAnthropic:

            # Setup Claude API mock to raise error
            client = AsyncMock()
            client.messages.create = AsyncMock(
                side_effect=anthropic.APIError(
                    message="Rate limit exceeded",
                    request=MagicMock(),
                    body=None
                )
            )
            MockAnthropic.return_value = client

            executor = SubagentExecutorMCP(config)
            result = await executor.execute(
                prompt="Do task",
                mcp_servers=["https://mcp.example.com/mcp"]
            )

        assert result.success is False
        assert "api error" in result.error.lower() or "rate limit" in result.error.lower()

    @pytest.mark.asyncio
    async def test_mcp_hub_closed_on_success(self, config, mock_claude_response):
        """Test that MCP Hub is closed after successful execution."""
        mock_hub = self._create_mock_hub()

        with patch("cron_mcp.subagent_mcp.MCPClientHub", return_value=mock_hub), \
             patch("anthropic.AsyncAnthropic") as MockAnthropic:

            client = AsyncMock()
            client.messages.create = AsyncMock(return_value=mock_claude_response)
            MockAnthropic.return_value = client

            executor = SubagentExecutorMCP(config)
            await executor.execute(
                prompt="Do task",
                mcp_servers=["https://mcp.example.com/mcp"]
            )

        mock_hub.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_hub_closed_on_error(self, config):
        """Test that MCP Hub is closed even after error."""
        mock_hub = self._create_mock_hub()

        with patch("cron_mcp.subagent_mcp.MCPClientHub", return_value=mock_hub), \
             patch("anthropic.AsyncAnthropic") as MockAnthropic:

            client = AsyncMock()
            client.messages.create = AsyncMock(side_effect=Exception("Unexpected error"))
            MockAnthropic.return_value = client

            executor = SubagentExecutorMCP(config)
            await executor.execute(
                prompt="Do task",
                mcp_servers=["https://mcp.example.com/mcp"]
            )

        mock_hub.close.assert_called_once()
