"""
Pytest fixtures for ClaudeCron MCP Server tests.
"""

import asyncio
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Set test environment variables before imports
os.environ["ANTHROPIC_API_KEY"] = "test-api-key"
os.environ["SUBAGENT_DEFAULT_MODE"] = "mcp_client"
os.environ["SUBAGENT_TIMEOUT"] = "30"
os.environ["SUBAGENT_MAX_TURNS"] = "5"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path(tmp_path: Path) -> str:
    """Create temporary database path."""
    return str(tmp_path / "test_tasks.db")


@pytest.fixture
def initialized_db(temp_db_path: str) -> str:
    """Create and initialize test database."""
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    # Tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            schedule TEXT,
            command TEXT,
            prompt TEXT,
            timezone TEXT DEFAULT 'UTC',
            enabled INTEGER DEFAULT 1,
            trigger_type TEXT,
            trigger_path TEXT,
            subagent_mode TEXT,
            mcp_servers TEXT,
            allowed_tools TEXT,
            system_prompt TEXT,
            max_turns INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # History table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            output TEXT,
            error TEXT,
            tool_calls TEXT,
            turns_used INTEGER,
            mode_used TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)

    # MCP servers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mcp_servers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            url TEXT NOT NULL,
            transport TEXT DEFAULT 'http',
            auth_type TEXT,
            auth_token TEXT,
            description TEXT,
            enabled INTEGER DEFAULT 1,
            health_status TEXT DEFAULT 'unknown',
            last_health_check TEXT,
            tools_cache TEXT,
            tools_updated_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

    return temp_db_path


@pytest.fixture
def mock_mcp_response():
    """Mock MCP server response data."""
    return {
        "initialize": {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2025-11-25",
                "serverInfo": {"name": "test-server", "version": "1.0.0"},
                "capabilities": {}
            }
        },
        "tools_list": {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string"}
                            },
                            "required": ["message"]
                        }
                    },
                    {
                        "name": "email_send",
                        "description": "Send an email",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "to": {"type": "string"},
                                "subject": {"type": "string"},
                                "body": {"type": "string"}
                            },
                            "required": ["to", "subject", "body"]
                        }
                    }
                ]
            }
        },
        "tool_call": {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "content": [
                    {"type": "text", "text": "Tool executed successfully"}
                ]
            }
        }
    }


@pytest.fixture
def mock_claude_response():
    """Mock Claude API response."""
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [
        MagicMock(type="text", text="Task completed successfully")
    ]
    return response


@pytest.fixture
def mock_claude_response_with_tool_use():
    """Mock Claude API response with tool use."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "I will send an email"

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = "tool_123"
    tool_block.name = "email_send"
    tool_block.input = {
        "to": "test@example.com",
        "subject": "Test",
        "body": "Test body"
    }

    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [text_block, tool_block]
    return response


@pytest.fixture
def sample_task_bash():
    """Sample bash task data."""
    return {
        "name": "test-bash-task",
        "type": "bash",
        "schedule": "0 * * * *",
        "command": "echo 'Hello World'",
        "timezone": "UTC",
        "enabled": True
    }


@pytest.fixture
def sample_task_subagent():
    """Sample subagent task data."""
    return {
        "name": "test-subagent-task",
        "type": "subagent",
        "schedule": "0 9 * * *",
        "prompt": "Send a test email to test@example.com",
        "timezone": "UTC",
        "enabled": True,
        "subagent_mode": "mcp_client",
        "mcp_servers": ["https://mcp.example.com/email/mcp"],
        "max_turns": 10
    }


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient."""
    with patch("httpx.AsyncClient") as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic AsyncAnthropic client."""
    with patch("anthropic.AsyncAnthropic") as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client
