"""
Notification System — отправка уведомлений о выполнении задач.

Поддерживаемые каналы:
- Email (через Email MCP Server)
- Telegram (будущее)
- Webhook (будущее)
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Конфигурация уведомлений."""
    email: Optional[str] = None
    on_success: bool = True
    on_failure: bool = True
    include_output: bool = True
    include_tool_calls: bool = False

    @classmethod
    def from_json(cls, json_str: Optional[str]) -> Optional["NotificationConfig"]:
        """Создать из JSON строки."""
        if not json_str:
            return None
        try:
            data = json.loads(json_str)
            return cls(**data)
        except Exception as e:
            logger.error(f"Failed to parse notification config: {e}")
            return None


class NotificationService:
    """
    Сервис отправки уведомлений.

    Использует Email MCP Server для отправки email уведомлений.
    """

    def __init__(self):
        self.email_server_url = os.environ.get(
            "NOTIFICATION_EMAIL_SERVER",
            "https://mcp.svsfinpro.ru/email/mcp"
        )
        self.proxy = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
        self.default_email_account = os.environ.get("NOTIFICATION_EMAIL_ACCOUNT")

    async def send_task_notification(
        self,
        task: dict,
        result: dict,
        config: NotificationConfig
    ) -> bool:
        """
        Отправить уведомление о выполнении задачи.

        Args:
            task: Словарь с данными задачи
            result: Словарь с результатом выполнения
            config: Конфигурация уведомлений

        Returns:
            True если уведомление отправлено успешно
        """
        # Проверяем, нужно ли отправлять
        status = result.get("status", "unknown")
        if status == "success" and not config.on_success:
            logger.debug(f"Skipping notification for {task.get('name')}: on_success=False")
            return False
        if status == "failed" and not config.on_failure:
            logger.debug(f"Skipping notification for {task.get('name')}: on_failure=False")
            return False

        # Отправляем email если настроен
        if config.email:
            return await self._send_email_notification(task, result, config)

        return False

    async def _send_email_notification(
        self,
        task: dict,
        result: dict,
        config: NotificationConfig
    ) -> bool:
        """Отправить email уведомление через Email MCP Server."""
        from .mcp_client import MCPClientHub

        try:
            # Формируем HTML контент
            html = self._build_email_html(task, result, config)

            # Определяем тему
            status = result.get("status", "unknown")
            status_emoji = "✅" if status == "success" else "❌"
            subject = f"[ClaudeCron] {status_emoji} {task.get('name', 'Unknown')} - {status}"

            # Подключаемся к Email MCP Server
            async with MCPClientHub(timeout=60, proxy=self.proxy) as hub:
                await hub.connect([self.email_server_url])

                # Проверяем наличие tool imap_send_email
                tool_names = hub.get_tool_names()
                if "imap_send_email" not in tool_names:
                    logger.error(f"Tool imap_send_email not found. Available: {tool_names}")
                    return False

                # Вызываем imap_send_email
                send_args = {
                    "to": config.email,
                    "subject": subject,
                    "html": html
                }

                # Добавляем account_id если указан
                if self.default_email_account:
                    send_args["account_id"] = self.default_email_account

                send_result = await hub.call_tool("imap_send_email", send_args)

                if "error" in send_result:
                    logger.error(f"Failed to send email: {send_result['error']}")
                    return False

                logger.info(f"Notification sent to {config.email} for task {task.get('name')}")
                return True

        except Exception as e:
            logger.error(f"Email notification error: {e}")
            return False

    def _build_email_html(
        self,
        task: dict,
        result: dict,
        config: NotificationConfig
    ) -> str:
        """Сформировать HTML контент письма."""
        status = result.get("status", "unknown")
        status_color = "#28a745" if status == "success" else "#dc3545"
        status_text = "✅ Успешно" if status == "success" else "❌ Ошибка"

        # Время выполнения
        started_at = result.get("started_at", "N/A")
        finished_at = result.get("finished_at", "N/A")

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: {status_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; }}
        .status {{ font-size: 24px; font-weight: bold; }}
        .meta {{ color: #666; font-size: 14px; margin: 10px 0; }}
        .output {{ background: #fff; border: 1px solid #ddd; border-radius: 4px; padding: 15px; margin: 15px 0; white-space: pre-wrap; font-family: monospace; font-size: 13px; max-height: 400px; overflow-y: auto; }}
        .error {{ background: #fff5f5; border-color: #dc3545; color: #dc3545; }}
        .tool-calls {{ margin: 15px 0; }}
        .tool {{ padding: 8px 12px; background: #e9ecef; border-radius: 4px; margin: 5px 0; font-size: 13px; }}
        .tool-success {{ border-left: 3px solid #28a745; }}
        .tool-failed {{ border-left: 3px solid #dc3545; }}
        .footer {{ margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="status">{status_text}</div>
            <div style="font-size: 18px; margin-top: 5px;">{self._escape_html(task.get('name', 'Unknown Task'))}</div>
        </div>
        <div class="content">
            <div class="meta">
                <strong>Тип:</strong> {task.get('type', 'unknown')}<br>
                <strong>Расписание:</strong> {task.get('schedule') or 'manual'}<br>
                <strong>Начало:</strong> {started_at}<br>
                <strong>Завершение:</strong> {finished_at}
            </div>
"""

        # Output
        if config.include_output and result.get("output"):
            output_text = self._escape_html(result.get("output", ""))
            # Ограничиваем длину output
            if len(output_text) > 5000:
                output_text = output_text[:5000] + "\n\n... (обрезано)"
            html += f"""
            <h3>Результат:</h3>
            <div class="output">{output_text}</div>
"""

        # Error
        if result.get("error"):
            html += f"""
            <h3>Ошибка:</h3>
            <div class="output error">{self._escape_html(result.get('error', ''))}</div>
"""

        # Tool calls
        if config.include_tool_calls and result.get("tool_calls"):
            html += """
            <h3>Вызовы инструментов:</h3>
            <div class="tool-calls">
"""
            for tc in result.get("tool_calls", []):
                tool_class = "tool-success" if tc.get("success") else "tool-failed"
                tool_icon = "✓" if tc.get("success") else "✗"
                html += f"""
                <div class="tool {tool_class}">
                    {tool_icon} {self._escape_html(tc.get('tool', 'unknown'))}
                </div>
"""
            html += """
            </div>
"""

        # Mode info for subagent tasks
        if result.get("mode_used"):
            html += f"""
            <div class="meta" style="margin-top: 15px;">
                <strong>Режим:</strong> {result.get('mode_used')}<br>
                <strong>Итераций:</strong> {result.get('turns_used', 0)}
            </div>
"""

        html += f"""
            <div class="footer">
                Отправлено автоматически системой ClaudeCron<br>
                Task ID: {task.get('id', 'unknown')}
            </div>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _escape_html(self, text: str) -> str:
        """Экранировать HTML символы."""
        if not text:
            return ""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )


# Глобальный экземпляр сервиса
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Получить глобальный сервис уведомлений."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
