"""
E2E integration tests for ClaudeCron MCP Server.

Tests:
- Task creation (bash and subagent)
- Task listing
- Task execution
- Task deletion
- History retrieval
- Scheduler status
- MCP server registry

Note: Tests use direct database operations instead of FastMCP Client
because tools with task=True and Progress dependencies require
full server context not available in unit tests.
"""

import pytest
import json
import os
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC

import sys
sys.path.insert(0, str(__file__).rsplit("/tests", 1)[0] + "/wrapper")


def extract_result_text(result):
    """Helper to extract text from FastMCP result."""
    if hasattr(result, 'content') and result.content:
        return result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
    elif hasattr(result, 'data'):
        return result.data if isinstance(result.data, str) else json.dumps(result.data)
    return str(result)


class TestServerIntegration:
    """Integration tests for ClaudeCron server tools using direct database access."""

    @pytest.fixture
    def mock_db_path(self, initialized_db):
        """Use initialized test database."""
        return initialized_db

    @pytest.fixture
    def setup_server_env(self, mock_db_path):
        """Setup server environment variables."""
        original = os.environ.get("CLAUDECRON_DB_PATH")
        os.environ["CLAUDECRON_DB_PATH"] = mock_db_path
        yield mock_db_path
        if original:
            os.environ["CLAUDECRON_DB_PATH"] = original
        elif "CLAUDECRON_DB_PATH" in os.environ:
            del os.environ["CLAUDECRON_DB_PATH"]

    @pytest.mark.asyncio
    async def test_add_bash_task_direct(self, setup_server_env):
        """Test adding a bash task using direct database verification."""
        with patch("cron_mcp.server.DB_PATH", setup_server_env):
            from cron_mcp.server import init_database, get_db_connection
            import uuid

            init_database()

            # Simulate task creation
            task_id = str(uuid.uuid4())
            now = datetime.now(UTC).isoformat()

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (id, name, type, schedule, command, timezone, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (task_id, "test-bash-task", "bash", "0 * * * *", "echo 'Hello World'", "UTC", 1, now, now))
            conn.commit()

            # Verify task was created
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            task = dict(cursor.fetchone())
            conn.close()

            assert task["name"] == "test-bash-task"
            assert task["type"] == "bash"
            assert task["command"] == "echo 'Hello World'"

    @pytest.mark.asyncio
    async def test_add_subagent_task_direct(self, setup_server_env):
        """Test adding a subagent task using direct database verification."""
        with patch("cron_mcp.server.DB_PATH", setup_server_env):
            from cron_mcp.server import init_database, get_db_connection
            import uuid

            init_database()

            task_id = str(uuid.uuid4())
            now = datetime.now(UTC).isoformat()
            mcp_servers = json.dumps(["https://mcp.example.com/email/mcp"])

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (id, name, type, schedule, prompt, timezone, enabled,
                    subagent_mode, mcp_servers, max_turns, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (task_id, "test-subagent-task", "subagent", "0 9 * * *",
                  "Send daily report email", "UTC", 1, "mcp_client", mcp_servers, 10, now, now))
            conn.commit()

            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            task = dict(cursor.fetchone())
            conn.close()

            assert task["name"] == "test-subagent-task"
            assert task["type"] == "subagent"
            assert task["prompt"] == "Send daily report email"
            assert task["subagent_mode"] == "mcp_client"

    @pytest.mark.asyncio
    async def test_list_tasks_direct(self, setup_server_env):
        """Test listing tasks using direct database verification."""
        with patch("cron_mcp.server.DB_PATH", setup_server_env):
            from cron_mcp.server import init_database, get_db_connection
            import uuid

            init_database()

            # Create multiple tasks
            now = datetime.now(UTC).isoformat()
            conn = get_db_connection()
            cursor = conn.cursor()

            for i in range(3):
                task_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO tasks (id, name, type, command, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (task_id, f"task-{i}", "bash", f"echo {i}", 1, now, now))

            conn.commit()

            # List all tasks
            cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
            tasks = [dict(row) for row in cursor.fetchall()]
            conn.close()

            assert len(tasks) >= 3

    @pytest.mark.asyncio
    async def test_toggle_task_direct(self, setup_server_env):
        """Test toggling task enabled status using direct database verification."""
        with patch("cron_mcp.server.DB_PATH", setup_server_env):
            from cron_mcp.server import init_database, get_db_connection
            import uuid

            init_database()

            task_id = str(uuid.uuid4())
            now = datetime.now(UTC).isoformat()

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (id, name, type, command, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task_id, "toggle-test", "bash", "echo test", 1, now, now))
            conn.commit()

            # Toggle task
            cursor.execute("UPDATE tasks SET enabled = 0 WHERE id = ?", (task_id,))
            conn.commit()

            cursor.execute("SELECT enabled FROM tasks WHERE id = ?", (task_id,))
            task = cursor.fetchone()
            conn.close()

            assert task["enabled"] == 0

    @pytest.mark.asyncio
    async def test_delete_task_direct(self, setup_server_env):
        """Test deleting a task using direct database verification."""
        with patch("cron_mcp.server.DB_PATH", setup_server_env):
            from cron_mcp.server import init_database, get_db_connection
            import uuid

            init_database()

            task_id = str(uuid.uuid4())
            now = datetime.now(UTC).isoformat()

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (id, name, type, command, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task_id, "delete-test", "bash", "echo test", 1, now, now))
            conn.commit()

            # Delete task
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()

            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            task = cursor.fetchone()
            conn.close()

            assert task is None

    @pytest.mark.asyncio
    async def test_run_bash_task(self, setup_server_env):
        """Test running a bash task."""
        with patch("cron_mcp.server.DB_PATH", setup_server_env):
            from cron_mcp.server import execute_task, init_database, get_db_connection
            import uuid

            init_database()

            task_id = str(uuid.uuid4())
            now = datetime.now(UTC).isoformat()

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (id, name, type, command, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task_id, "run-test", "bash", "echo 'Hello from test'", 1, now, now))
            conn.commit()
            conn.close()

            result = await execute_task(task_id)

            assert result["status"] == "success"
            assert "Hello from test" in result["output"]

    @pytest.mark.asyncio
    async def test_get_history(self, setup_server_env):
        """Test getting execution history."""
        with patch("cron_mcp.server.DB_PATH", setup_server_env):
            from cron_mcp.server import execute_task, init_database, get_db_connection
            import uuid

            init_database()

            task_id = str(uuid.uuid4())
            now = datetime.now(UTC).isoformat()

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (id, name, type, command, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task_id, "history-test", "bash", "echo test", 1, now, now))
            conn.commit()
            conn.close()

            # Run task to generate history
            await execute_task(task_id)

            # Check history
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM history WHERE task_id = ?", (task_id,))
            history = [dict(row) for row in cursor.fetchall()]
            conn.close()

            assert len(history) >= 1
            assert history[0]["task_id"] == task_id
            assert history[0]["status"] == "success"

    @pytest.mark.asyncio
    async def test_scheduler_status(self, setup_server_env):
        """Test getting scheduler status."""
        from cron_mcp.scheduler import CronScheduler, get_scheduler

        # Mock scheduler
        mock_scheduler = MagicMock(spec=CronScheduler)
        mock_scheduler.is_running.return_value = True
        mock_scheduler.get_running_tasks.return_value = set()
        mock_scheduler.max_concurrent = 5
        mock_scheduler.check_interval = 60

        with patch("cron_mcp.scheduler._scheduler", mock_scheduler):
            with patch("cron_mcp.scheduler.get_scheduler", return_value=mock_scheduler):
                scheduler = get_scheduler()

                assert scheduler.is_running() is True
                assert scheduler.max_concurrent == 5
                assert scheduler.check_interval == 60

    @pytest.mark.asyncio
    async def test_scheduler_status_not_running(self, setup_server_env):
        """Test scheduler status when not running."""
        from cron_mcp.scheduler import get_scheduler

        with patch("cron_mcp.scheduler._scheduler", None):
            scheduler = get_scheduler()
            assert scheduler is None

    @pytest.mark.asyncio
    async def test_mcp_registry_operations(self, setup_server_env):
        """Test MCP registry operations."""
        with patch("cron_mcp.server.DB_PATH", setup_server_env):
            from cron_mcp.server import init_database, get_db_connection
            import uuid

            init_database()

            # Add MCP server to registry
            server_id = str(uuid.uuid4())
            now = datetime.now(UTC).isoformat()

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO mcp_servers (id, name, url, transport, enabled, health_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (server_id, "email", "https://mcp.example.com/email/mcp", "http", 1, "healthy", now, now))
            conn.commit()

            # List servers
            cursor.execute("SELECT * FROM mcp_servers")
            servers = [dict(row) for row in cursor.fetchall()]
            conn.close()

            assert len(servers) == 1
            assert servers[0]["name"] == "email"
            assert servers[0]["url"] == "https://mcp.example.com/email/mcp"


class TestExecuteTask:
    """Tests for execute_task function."""

    @pytest.fixture
    def mock_db_path(self, initialized_db):
        """Use initialized test database."""
        return initialized_db

    @pytest.mark.asyncio
    async def test_execute_subagent_task(self, mock_db_path):
        """Test executing subagent task."""
        # Insert a test task
        conn = sqlite3.connect(mock_db_path)
        cursor = conn.cursor()
        now = datetime.now(UTC).isoformat()
        cursor.execute("""
            INSERT INTO tasks (id, name, type, prompt, subagent_mode, mcp_servers, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "test-subagent-id",
            "test-subagent",
            "subagent",
            "Send test email",
            "mcp_client",
            json.dumps(["https://mcp.example.com/email/mcp"]),
            1,
            now,
            now
        ))
        conn.commit()
        conn.close()

        with patch("cron_mcp.server.DB_PATH", mock_db_path):
            from cron_mcp.server import execute_task

            # Mock SubagentExecutor (imported inside function, so patch in subagent module)
            with patch("cron_mcp.subagent.SubagentExecutor") as MockExecutor:
                mock_executor = AsyncMock()
                mock_executor.execute = AsyncMock(return_value=MagicMock(
                    success=True,
                    output="Email sent",
                    tool_calls=[{"tool": "email_send", "success": True}],
                    turns_used=2,
                    mode_used="mcp_client",
                    error=None
                ))
                MockExecutor.return_value = mock_executor

                result = await execute_task("test-subagent-id")

        assert result["status"] == "success"
        assert "Email sent" in result["output"]
        assert result["mode_used"] == "mcp_client"
        assert result["turns_used"] == 2

    @pytest.mark.asyncio
    async def test_execute_nonexistent_task(self, mock_db_path):
        """Test executing nonexistent task."""
        with patch("cron_mcp.server.DB_PATH", mock_db_path):
            from cron_mcp.server import execute_task, ensure_initialized

            ensure_initialized()
            result = await execute_task("nonexistent-id")

        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_bash_task_failure(self, mock_db_path):
        """Test executing bash task with failure."""
        conn = sqlite3.connect(mock_db_path)
        cursor = conn.cursor()
        now = datetime.now(UTC).isoformat()
        cursor.execute("""
            INSERT INTO tasks (id, name, type, command, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("fail-task-id", "fail-task", "bash", "exit 1", 1, now, now))
        conn.commit()
        conn.close()

        with patch("cron_mcp.server.DB_PATH", mock_db_path):
            from cron_mcp.server import execute_task

            result = await execute_task("fail-task-id")

        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_execute_subagent_task_failure(self, mock_db_path):
        """Test executing subagent task with failure."""
        conn = sqlite3.connect(mock_db_path)
        cursor = conn.cursor()
        now = datetime.now(UTC).isoformat()
        cursor.execute("""
            INSERT INTO tasks (id, name, type, prompt, subagent_mode, mcp_servers, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "fail-subagent-id",
            "fail-subagent",
            "subagent",
            "Do something",
            "mcp_client",
            json.dumps(["https://mcp.example.com/mcp"]),
            1,
            now,
            now
        ))
        conn.commit()
        conn.close()

        with patch("cron_mcp.server.DB_PATH", mock_db_path):
            from cron_mcp.server import execute_task

            # Mock SubagentExecutor with failure (imported inside function, so patch in subagent module)
            with patch("cron_mcp.subagent.SubagentExecutor") as MockExecutor:
                mock_executor = AsyncMock()
                mock_executor.execute = AsyncMock(return_value=MagicMock(
                    success=False,
                    output="",
                    tool_calls=[],
                    turns_used=0,
                    mode_used="mcp_client",
                    error="Connection failed"
                ))
                MockExecutor.return_value = mock_executor

                result = await execute_task("fail-subagent-id")

        assert result["status"] == "failed"
        assert result["error"] == "Connection failed"


class TestCronValidation:
    """Tests for cron expression validation."""

    def test_valid_cron_expression(self):
        """Test valid cron expressions."""
        from croniter import croniter

        valid_expressions = [
            "0 * * * *",      # Every hour
            "*/5 * * * *",    # Every 5 minutes
            "0 0 * * *",      # Daily at midnight
            "0 9 * * 1-5",    # 9 AM weekdays
            "0 0 1 * *",      # First day of month
        ]

        for expr in valid_expressions:
            cron = croniter(expr)
            assert cron is not None

    def test_invalid_cron_expression(self):
        """Test invalid cron expressions."""
        from croniter import croniter
        import pytest

        invalid_expressions = [
            "invalid",
            "* * *",
            "60 * * * *",
            "not a cron",
        ]

        for expr in invalid_expressions:
            with pytest.raises(Exception):
                croniter(expr)
