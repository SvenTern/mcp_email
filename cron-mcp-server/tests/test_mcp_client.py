"""
Unit tests for MCP Client Hub.

Tests:
- Connection to MCP server
- Getting tools list
- Tool calls
- Connection error handling
- Conversion to Anthropic format
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

import sys
sys.path.insert(0, str(__file__).rsplit("/tests", 1)[0] + "/wrapper")

from cron_mcp.mcp_client import MCPClientHub, MCPTool, MCPSession


class TestMCPClientHub:
    """Tests for MCPClientHub class."""

    @pytest_asyncio.fixture
    async def hub(self):
        """Create MCPClientHub instance."""
        hub = MCPClientHub(timeout=30)
        yield hub
        await hub.close()

    @pytest.mark.asyncio
    async def test_init(self, hub):
        """Test MCPClientHub initialization."""
        assert hub.timeout == 30
        assert hub.proxy is None
        assert hub.sessions == {}
        assert hub._tool_to_server == {}

    @pytest.mark.asyncio
    async def test_init_with_proxy(self):
        """Test MCPClientHub initialization with proxy."""
        hub = MCPClientHub(timeout=30, proxy="http://localhost:7897")
        assert hub.proxy == "http://localhost:7897"
        await hub.close()

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_mcp_response):
        """Test successful connection to MCP server."""
        hub = MCPClientHub(timeout=30)

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.headers = {"Mcp-Session-Id": "test-session-123"}
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = mock_mcp_response["tools_list"]
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            await hub.connect(["https://mcp.example.com/email/mcp"])

        assert "https://mcp.example.com/email/mcp" in hub.sessions
        session = hub.sessions["https://mcp.example.com/email/mcp"]
        assert session.session_id == "test-session-123"
        assert len(session.tools) == 2
        assert hub._tool_to_server["test_tool"] == "https://mcp.example.com/email/mcp"
        assert hub._tool_to_server["email_send"] == "https://mcp.example.com/email/mcp"

        await hub.close()

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure handling."""
        hub = MCPClientHub(timeout=30)

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            await hub.connect(["https://mcp.example.com/invalid/mcp"])

        # Connection failed, but no exception raised
        assert "https://mcp.example.com/invalid/mcp" not in hub.sessions

        await hub.close()

    @pytest.mark.asyncio
    async def test_call_tool_success(self, mock_mcp_response):
        """Test successful tool call."""
        hub = MCPClientHub(timeout=30)

        # Create separate mock responses for different calls
        init_response = MagicMock()
        init_response.headers = {"Mcp-Session-Id": "test-session"}
        init_response.raise_for_status = MagicMock()
        init_response.json.return_value = mock_mcp_response["initialize"]

        notif_response = MagicMock()
        notif_response.headers = {"Mcp-Session-Id": "test-session"}
        notif_response.raise_for_status = MagicMock()

        tools_list_response = MagicMock()
        tools_list_response.headers = {"Mcp-Session-Id": "test-session"}
        tools_list_response.raise_for_status = MagicMock()
        tools_list_response.json.return_value = mock_mcp_response["tools_list"]

        tool_call_response = MagicMock()
        tool_call_response.headers = {"Mcp-Session-Id": "test-session"}
        tool_call_response.raise_for_status = MagicMock()
        tool_call_response.json.return_value = mock_mcp_response["tool_call"]

        mock_client = AsyncMock()
        # Return different responses for each POST call
        mock_client.post.side_effect = [
            init_response,      # initialize
            notif_response,     # notifications/initialized
            tools_list_response, # tools/list
            tool_call_response  # tools/call
        ]
        mock_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            await hub.connect(["https://mcp.example.com/email/mcp"])
            result = await hub.call_tool("test_tool", {"message": "Hello"})

        assert "content" in result
        assert result["content"][0]["text"] == "Tool executed successfully"

        await hub.close()

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, hub):
        """Test tool call when tool not found."""
        result = await hub.call_tool("nonexistent_tool", {})
        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_to_anthropic_format(self, mock_mcp_response):
        """Test conversion to Anthropic API format."""
        hub = MCPClientHub(timeout=30)

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.headers = {"Mcp-Session-Id": "test-session"}
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = mock_mcp_response["tools_list"]
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            await hub.connect(["https://mcp.example.com/email/mcp"])

        tools = hub.to_anthropic_format()

        assert len(tools) == 2
        assert tools[0]["name"] == "test_tool"
        assert tools[0]["description"] == "A test tool"
        assert "input_schema" in tools[0]

        await hub.close()

    @pytest.mark.asyncio
    async def test_to_anthropic_format_excludes_claudecron(self, mock_mcp_response):
        """Test that claudecron_ tools are excluded for recursion protection."""
        hub = MCPClientHub(timeout=30)

        # Add claudecron tool to response
        tools_with_claudecron = mock_mcp_response["tools_list"].copy()
        tools_with_claudecron["result"]["tools"].append({
            "name": "claudecron_add_task",
            "description": "Add a task",
            "inputSchema": {"type": "object"}
        })

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.headers = {"Mcp-Session-Id": "test-session"}
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = tools_with_claudecron
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            await hub.connect(["https://mcp.example.com/cron/mcp"])

        tools = hub.to_anthropic_format()

        # claudecron_ tools should be excluded
        tool_names = [t["name"] for t in tools]
        assert "claudecron_add_task" not in tool_names
        assert "test_tool" in tool_names

        await hub.close()

    @pytest.mark.asyncio
    async def test_to_anthropic_format_no_mutation(self, mock_mcp_response):
        """Test that exclude_patterns list is not mutated."""
        hub = MCPClientHub(timeout=30)

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.headers = {"Mcp-Session-Id": "test-session"}
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = mock_mcp_response["tools_list"]
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            await hub.connect(["https://mcp.example.com/email/mcp"])

        original_patterns = ["custom_pattern"]
        hub.to_anthropic_format(exclude_patterns=original_patterns)

        # Original list should not be mutated
        assert original_patterns == ["custom_pattern"]

        await hub.close()

    @pytest.mark.asyncio
    async def test_list_tools(self, mock_mcp_response):
        """Test listing all tools."""
        hub = MCPClientHub(timeout=30)

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.headers = {"Mcp-Session-Id": "test-session"}
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = mock_mcp_response["tools_list"]
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            await hub.connect(["https://mcp.example.com/email/mcp"])

        tools = hub.list_tools()

        assert len(tools) == 2
        assert all(isinstance(t, MCPTool) for t in tools)

        await hub.close()

    @pytest.mark.asyncio
    async def test_get_tool_names(self, mock_mcp_response):
        """Test getting tool names."""
        hub = MCPClientHub(timeout=30)

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.headers = {"Mcp-Session-Id": "test-session"}
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = mock_mcp_response["tools_list"]
        mock_client.post.return_value = mock_response
        mock_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            await hub.connect(["https://mcp.example.com/email/mcp"])

        names = hub.get_tool_names()

        assert "test_tool" in names
        assert "email_send" in names

        await hub.close()

    @pytest.mark.asyncio
    async def test_close(self, mock_mcp_response):
        """Test closing connections."""
        hub = MCPClientHub(timeout=30)

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.headers = {"Mcp-Session-Id": "test-session"}
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = mock_mcp_response["tools_list"]
        mock_client.post.return_value = mock_response
        mock_client.delete = AsyncMock()
        mock_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            await hub.connect(["https://mcp.example.com/email/mcp"])

        await hub.close()

        assert hub.sessions == {}
        assert hub._tool_to_server == {}
        mock_client.aclose.assert_called()

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_mcp_response):
        """Test async context manager."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.headers = {"Mcp-Session-Id": "test-session"}
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = mock_mcp_response["tools_list"]
        mock_client.post.return_value = mock_response
        mock_client.delete = AsyncMock()
        mock_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            async with MCPClientHub(timeout=30) as hub:
                await hub.connect(["https://mcp.example.com/email/mcp"])
                assert len(hub.sessions) == 1

        # After context manager exit, connections should be closed
        mock_client.aclose.assert_called()
