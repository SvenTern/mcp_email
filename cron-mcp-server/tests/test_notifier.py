"""
Tests for notification system.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

# Import the modules to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'wrapper'))

from cron_mcp.notifier import (
    NotificationConfig,
    NotificationService,
    get_notification_service
)


class TestNotificationConfig:
    """Tests for NotificationConfig dataclass."""

    def test_default_values(self):
        """Test default values."""
        config = NotificationConfig()
        assert config.email is None
        assert config.on_success is True
        assert config.on_failure is True
        assert config.include_output is True
        assert config.include_tool_calls is False

    def test_custom_values(self):
        """Test custom values."""
        config = NotificationConfig(
            email="test@example.com",
            on_success=False,
            on_failure=True,
            include_output=False,
            include_tool_calls=True
        )
        assert config.email == "test@example.com"
        assert config.on_success is False
        assert config.on_failure is True
        assert config.include_output is False
        assert config.include_tool_calls is True

    def test_from_json_valid(self):
        """Test parsing valid JSON."""
        json_str = json.dumps({
            "email": "test@example.com",
            "on_success": False,
            "include_tool_calls": True
        })
        config = NotificationConfig.from_json(json_str)
        assert config is not None
        assert config.email == "test@example.com"
        assert config.on_success is False
        assert config.on_failure is True  # default
        assert config.include_tool_calls is True

    def test_from_json_none(self):
        """Test parsing None returns None."""
        config = NotificationConfig.from_json(None)
        assert config is None

    def test_from_json_empty(self):
        """Test parsing empty string returns None."""
        config = NotificationConfig.from_json("")
        assert config is None

    def test_from_json_invalid(self):
        """Test parsing invalid JSON returns None."""
        config = NotificationConfig.from_json("not valid json")
        assert config is None


class TestNotificationService:
    """Tests for NotificationService."""

    def test_init_defaults(self):
        """Test default initialization."""
        service = NotificationService()
        assert service.email_server_url == "https://mcp.svsfinpro.ru/email/mcp"

    def test_init_custom_env(self, monkeypatch):
        """Test custom environment variables."""
        monkeypatch.setenv("NOTIFICATION_EMAIL_SERVER", "https://custom.server/mcp")
        monkeypatch.setenv("NOTIFICATION_EMAIL_ACCOUNT", "custom_account")

        service = NotificationService()
        assert service.email_server_url == "https://custom.server/mcp"
        assert service.default_email_account == "custom_account"

    @pytest.mark.asyncio
    async def test_skip_on_success_disabled(self):
        """Test skipping notification when on_success=False."""
        service = NotificationService()

        task = {"name": "test-task"}
        result = {"status": "success"}
        config = NotificationConfig(email="test@example.com", on_success=False)

        sent = await service.send_task_notification(task, result, config)
        assert sent is False

    @pytest.mark.asyncio
    async def test_skip_on_failure_disabled(self):
        """Test skipping notification when on_failure=False."""
        service = NotificationService()

        task = {"name": "test-task"}
        result = {"status": "failed"}
        config = NotificationConfig(email="test@example.com", on_failure=False)

        sent = await service.send_task_notification(task, result, config)
        assert sent is False

    @pytest.mark.asyncio
    async def test_skip_no_email(self):
        """Test skipping notification when no email configured."""
        service = NotificationService()

        task = {"name": "test-task"}
        result = {"status": "success"}
        config = NotificationConfig(email=None)

        sent = await service.send_task_notification(task, result, config)
        assert sent is False

    def test_escape_html(self):
        """Test HTML escaping."""
        service = NotificationService()

        # Test basic escaping
        assert service._escape_html("<script>alert('xss')</script>") == \
            "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;"

        # Test ampersand
        assert service._escape_html("A & B") == "A &amp; B"

        # Test quotes
        assert service._escape_html('Say "hello"') == "Say &quot;hello&quot;"

        # Test None/empty
        assert service._escape_html(None) == ""
        assert service._escape_html("") == ""

    def test_build_email_html_success(self):
        """Test building HTML for successful task."""
        service = NotificationService()

        task = {
            "id": "task-123",
            "name": "Test Task",
            "type": "subagent",
            "schedule": "0 9 * * *"
        }
        result = {
            "status": "success",
            "output": "Task completed successfully",
            "started_at": "2025-01-15T09:00:00Z",
            "finished_at": "2025-01-15T09:01:00Z"
        }
        config = NotificationConfig(email="test@example.com", include_output=True)

        html = service._build_email_html(task, result, config)

        assert "Test Task" in html
        assert "✅ Успешно" in html
        assert "#28a745" in html  # success color
        assert "Task completed successfully" in html
        assert "task-123" in html

    def test_build_email_html_failure(self):
        """Test building HTML for failed task."""
        service = NotificationService()

        task = {
            "id": "task-456",
            "name": "Failed Task",
            "type": "bash",
            "schedule": None
        }
        result = {
            "status": "failed",
            "output": None,
            "error": "Command not found",
            "started_at": "2025-01-15T10:00:00Z",
            "finished_at": "2025-01-15T10:00:01Z"
        }
        config = NotificationConfig(email="test@example.com")

        html = service._build_email_html(task, result, config)

        assert "Failed Task" in html
        assert "❌ Ошибка" in html
        assert "#dc3545" in html  # error color
        assert "Command not found" in html

    def test_build_email_html_with_tool_calls(self):
        """Test building HTML with tool calls."""
        service = NotificationService()

        task = {
            "id": "task-789",
            "name": "Subagent Task",
            "type": "subagent",
            "schedule": "*/5 * * * *"
        }
        result = {
            "status": "success",
            "output": "Done",
            "tool_calls": [
                {"tool": "email_send", "success": True},
                {"tool": "file_read", "success": False}
            ],
            "mode_used": "mcp_client",
            "turns_used": 3,
            "started_at": "2025-01-15T11:00:00Z",
            "finished_at": "2025-01-15T11:02:00Z"
        }
        config = NotificationConfig(
            email="test@example.com",
            include_tool_calls=True
        )

        html = service._build_email_html(task, result, config)

        assert "email_send" in html
        assert "file_read" in html
        assert "mcp_client" in html
        assert "3" in html  # turns_used

    def test_build_email_html_truncates_output(self):
        """Test that long output is truncated."""
        service = NotificationService()

        task = {"id": "task-1", "name": "Long Output", "type": "bash", "schedule": None}
        result = {
            "status": "success",
            "output": "x" * 10000,  # Very long output
            "started_at": "2025-01-15T12:00:00Z",
            "finished_at": "2025-01-15T12:00:01Z"
        }
        config = NotificationConfig(email="test@example.com", include_output=True)

        html = service._build_email_html(task, result, config)

        # Output should be truncated to ~5000 chars
        assert "обрезано" in html


class TestGlobalNotificationService:
    """Tests for global notification service singleton."""

    def test_get_notification_service(self):
        """Test getting global service."""
        service1 = get_notification_service()
        service2 = get_notification_service()

        assert service1 is service2  # Same instance


@pytest.mark.asyncio
class TestEmailNotificationIntegration:
    """Integration tests for email notification (mocked)."""

    async def test_send_email_notification_success(self):
        """Test successful email sending."""
        service = NotificationService()

        task = {
            "id": "task-int-1",
            "name": "Integration Test",
            "type": "subagent",
            "schedule": "0 0 * * *"
        }
        result = {
            "status": "success",
            "output": "Test output",
            "started_at": "2025-01-15T00:00:00Z",
            "finished_at": "2025-01-15T00:01:00Z"
        }
        config = NotificationConfig(email="test@example.com")

        # Create proper async context manager mock
        mock_hub = MagicMock()  # Use MagicMock for sync methods
        mock_hub.get_tool_names.return_value = ["imap_send_email"]
        mock_hub.call_tool = AsyncMock(return_value={"success": True})
        mock_hub.connect = AsyncMock()

        # Create async context manager
        async_cm = MagicMock()
        async_cm.__aenter__ = AsyncMock(return_value=mock_hub)
        async_cm.__aexit__ = AsyncMock(return_value=None)

        # Mock MCPClientHub constructor to return our async context manager
        with patch('cron_mcp.mcp_client.MCPClientHub', return_value=async_cm):
            sent = await service._send_email_notification(task, result, config)

            assert sent is True
            mock_hub.connect.assert_called_once()
            mock_hub.call_tool.assert_called_once()

            # Check call arguments
            call_args = mock_hub.call_tool.call_args
            assert call_args[0][0] == "imap_send_email"
            assert call_args[0][1]["to"] == "test@example.com"
            assert "Integration Test" in call_args[0][1]["subject"]

    async def test_send_email_notification_tool_not_found(self):
        """Test handling when email tool not available."""
        service = NotificationService()

        task = {"id": "task-1", "name": "Test", "type": "bash", "schedule": None}
        result = {"status": "success", "started_at": "2025-01-15T00:00:00Z", "finished_at": "2025-01-15T00:01:00Z"}
        config = NotificationConfig(email="test@example.com")

        with patch('cron_mcp.mcp_client.MCPClientHub') as MockHub:
            mock_hub = AsyncMock()
            mock_hub.get_tool_names.return_value = []  # No tools
            MockHub.return_value.__aenter__.return_value = mock_hub

            sent = await service._send_email_notification(task, result, config)

            assert sent is False

    async def test_send_email_notification_error(self):
        """Test handling email send error."""
        service = NotificationService()

        task = {"id": "task-1", "name": "Test", "type": "bash", "schedule": None}
        result = {"status": "success", "started_at": "2025-01-15T00:00:00Z", "finished_at": "2025-01-15T00:01:00Z"}
        config = NotificationConfig(email="test@example.com")

        with patch('cron_mcp.mcp_client.MCPClientHub') as MockHub:
            mock_hub = AsyncMock()
            mock_hub.get_tool_names.return_value = ["imap_send_email"]
            mock_hub.call_tool.return_value = {"error": "SMTP connection failed"}
            MockHub.return_value.__aenter__.return_value = mock_hub

            sent = await service._send_email_notification(task, result, config)

            assert sent is False

    async def test_send_email_notification_exception(self):
        """Test handling exception during email send."""
        service = NotificationService()

        task = {"id": "task-1", "name": "Test", "type": "bash", "schedule": None}
        result = {"status": "success", "started_at": "2025-01-15T00:00:00Z", "finished_at": "2025-01-15T00:01:00Z"}
        config = NotificationConfig(email="test@example.com")

        with patch('cron_mcp.mcp_client.MCPClientHub') as MockHub:
            MockHub.return_value.__aenter__.side_effect = Exception("Connection error")

            sent = await service._send_email_notification(task, result, config)

            assert sent is False
