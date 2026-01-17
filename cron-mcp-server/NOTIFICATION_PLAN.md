# План доработки: Система уведомлений ClaudeCron

## 1. Проблема

### Текущее поведение
При запуске задачи по расписанию (`schedule`):
1. Scheduler вызывает `execute_task(task_id)` в фоне
2. Результат записывается в БД (таблица `history`)
3. **Пользователь НЕ получает уведомление**

### Ограничения Claude API
- Работает по модели request-response
- Нет push-уведомлений, webhooks, server-initiated messages
- Невозможно создать чат со стороны сервера

## 2. Предлагаемое решение: Email-уведомления

### Почему Email?
✅ Готовый Email MCP сервер (`https://mcp.svsfinpro.ru/email/mcp`)
✅ Поддержка HTML-форматирования
✅ Работает на любом устройстве
✅ Можно приложить файлы (логи, отчёты)
✅ Не требует установки дополнительного ПО у пользователя

### Альтернативы (для будущих версий)
- **Telegram бот** — мгновенные уведомления
- **Webhook** — для интеграции с внешними системами
- **Web Dashboard** — для просмотра в браузере

## 3. Архитектура изменений

### 3.1 Изменения в БД (`server.py:init_database`)

```sql
-- Добавить столбец notification в таблицу tasks
ALTER TABLE tasks ADD COLUMN notification TEXT;
-- JSON: {"email": "user@example.com", "on_success": true, "on_failure": true}
```

### 3.2 Новый модуль `notifier.py`

```
cron-mcp-server/wrapper/cron_mcp/
├── notifier.py          # NEW: Отправка уведомлений
├── server.py            # Изменения в execute_task, add_task
├── scheduler.py         # Без изменений
├── mcp_client.py        # Используется для вызова email tool
└── ...
```

### 3.3 Структура конфигурации уведомлений

```json
{
  "notification": {
    "email": "sergey@nortex.ru",
    "on_success": true,
    "on_failure": true,
    "include_output": true,
    "include_tool_calls": false
  }
}
```

## 4. Детальный план реализации

### Этап 1: Миграция БД

**Файл:** `server.py`

```python
# В init_database(), после создания таблицы tasks
# Migration: add notification column
if "notification" not in existing_columns:
    cursor.execute("ALTER TABLE tasks ADD COLUMN notification TEXT")
    logger.info("Added column notification to tasks table")
```

### Этап 2: Создание модуля `notifier.py`

**Файл:** `cron-mcp-server/wrapper/cron_mcp/notifier.py`

```python
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
from datetime import datetime

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
            return False
        if status == "failed" and not config.on_failure:
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
            async with MCPClientHub(timeout=30, proxy=self.proxy) as hub:
                await hub.connect([self.email_server_url])

                # Вызываем imap_send_email
                send_result = await hub.call_tool("imap_send_email", {
                    "account_id": self.default_email_account,
                    "to": config.email,
                    "subject": subject,
                    "html": html
                })

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

        # Время выполнения
        started_at = result.get("started_at", "")
        finished_at = result.get("finished_at", "")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
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
            <div class="status">{"✅ Успешно" if status == "success" else "❌ Ошибка"}</div>
            <div style="font-size: 18px; margin-top: 5px;">{task.get('name', 'Unknown Task')}</div>
        </div>
        <div class="content">
            <div class="meta">
                <strong>Тип:</strong> {task.get('type', 'unknown')}<br>
                <strong>Расписание:</strong> {task.get('schedule', 'manual')}<br>
                <strong>Начало:</strong> {started_at}<br>
                <strong>Завершение:</strong> {finished_at}
            </div>
"""

        # Output
        if config.include_output and result.get("output"):
            html += f"""
            <h3>Результат:</h3>
            <div class="output">{self._escape_html(result.get('output', ''))}</div>
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
                html += f"""
                <div class="tool {tool_class}">
                    {"✓" if tc.get("success") else "✗"} {tc.get('tool', 'unknown')}
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
        return (
            text
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
```

### Этап 3: Интеграция в `server.py`

#### 3.1 Изменения в `execute_task`

**Файл:** `server.py`, функция `execute_task` (после строки 275)

```python
# После записи результата в history, добавить отправку уведомления:

    # Send notification if configured
    notification_json = task.get('notification')
    if notification_json:
        from .notifier import NotificationConfig, get_notification_service

        config = NotificationConfig.from_json(notification_json)
        if config:
            notification_service = get_notification_service()
            try:
                await notification_service.send_task_notification(
                    task=task,
                    result={
                        "status": status,
                        "output": output,
                        "error": error,
                        "tool_calls": tool_calls,
                        "turns_used": turns_used,
                        "mode_used": mode_used,
                        "started_at": started_at,
                        "finished_at": finished_at
                    },
                    config=config
                )
            except Exception as e:
                logger.error(f"Notification error for task {task['name']}: {e}")
```

#### 3.2 Изменения в `claudecron_add_task`

**Файл:** `server.py`, функция `claudecron_add_task`

Добавить параметр:
```python
async def claudecron_add_task(
    # ... существующие параметры ...
    notification: Optional[dict] = None,  # NEW
    # ...
) -> str:
```

Добавить в docstring:
```python
        notification: Notification settings:
            - email: Email address to send notifications
            - on_success: Send on successful completion (default: True)
            - on_failure: Send on failure (default: True)
            - include_output: Include task output in email (default: True)
            - include_tool_calls: Include tool calls list (default: False)
```

Добавить в INSERT:
```python
notification_json = json.dumps(notification) if notification else None

cursor.execute("""
    INSERT INTO tasks (
        id, name, type, schedule, command, prompt, timezone, enabled,
        trigger_type, trigger_path, subagent_mode, mcp_servers,
        allowed_tools, system_prompt, max_turns, notification,  # ADD notification
        created_at, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)  # ADD one more ?
""", (
    task_id, name, type, schedule, command, prompt, timezone,
    1 if enabled else 0, trigger_type, trigger_path,
    subagent_mode, mcp_servers_json, allowed_tools_json,
    system_prompt, max_turns, notification_json,  # ADD
    now, now
))
```

### Этап 4: Настройка окружения

#### 4.1 Переменные окружения

**Файл:** `.env.example`

```bash
# =============================================================================
# Notification Settings
# =============================================================================
# Email MCP server for notifications
NOTIFICATION_EMAIL_SERVER=https://mcp.svsfinpro.ru/email/mcp

# Default email account ID for sending (from imap_list_accounts)
NOTIFICATION_EMAIL_ACCOUNT=your-account-id
```

#### 4.2 Docker Compose

**Файл:** `docker-compose.yml`

```yaml
environment:
  # ... existing vars ...

  # Notification settings
  - NOTIFICATION_EMAIL_SERVER=${NOTIFICATION_EMAIL_SERVER:-https://mcp.svsfinpro.ru/email/mcp}
  - NOTIFICATION_EMAIL_ACCOUNT=${NOTIFICATION_EMAIL_ACCOUNT:-}
```

## 5. Пример использования

### Создание задачи с уведомлениями

```json
{
  "name": "daily-bitrix-report",
  "type": "subagent",
  "schedule": "0 9 * * *",
  "subagent_mode": "mcp_client",
  "mcp_servers": ["bitrix"],
  "prompt": "Получи список задач со статусом 'в работе' за последние 24 часа и сформируй краткий отчёт",
  "notification": {
    "email": "sergey@nortex.ru",
    "on_success": true,
    "on_failure": true,
    "include_output": true,
    "include_tool_calls": false
  }
}
```

### MCP Tool Call

```
claudecron_add_task(
    name="daily-bitrix-report",
    type="subagent",
    schedule="0 9 * * *",
    subagent_mode="mcp_client",
    mcp_servers=["bitrix"],
    prompt="Получи список задач со статусом 'в работе'...",
    notification={
        "email": "sergey@nortex.ru",
        "on_success": true,
        "on_failure": true
    }
)
```

## 6. Тестирование

### Unit тесты (`tests/test_notifier.py`)

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from cron_mcp.notifier import (
    NotificationConfig,
    NotificationService,
    get_notification_service
)


class TestNotificationConfig:
    def test_from_json_valid(self):
        json_str = '{"email": "test@example.com", "on_success": true}'
        config = NotificationConfig.from_json(json_str)
        assert config is not None
        assert config.email == "test@example.com"
        assert config.on_success is True

    def test_from_json_invalid(self):
        config = NotificationConfig.from_json("invalid json")
        assert config is None

    def test_from_json_none(self):
        config = NotificationConfig.from_json(None)
        assert config is None


class TestNotificationService:
    @pytest.mark.asyncio
    async def test_send_task_notification_success(self):
        service = NotificationService()

        task = {"name": "test-task", "type": "bash", "id": "123"}
        result = {"status": "success", "output": "Done"}
        config = NotificationConfig(email="test@example.com")

        with patch.object(service, "_send_email_notification", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            sent = await service.send_task_notification(task, result, config)

            assert sent is True
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_notification_on_success_disabled(self):
        service = NotificationService()

        task = {"name": "test-task", "type": "bash"}
        result = {"status": "success", "output": "Done"}
        config = NotificationConfig(email="test@example.com", on_success=False)

        sent = await service.send_task_notification(task, result, config)

        assert sent is False

    @pytest.mark.asyncio
    async def test_skip_notification_on_failure_disabled(self):
        service = NotificationService()

        task = {"name": "test-task", "type": "bash"}
        result = {"status": "failed", "error": "Error"}
        config = NotificationConfig(email="test@example.com", on_failure=False)

        sent = await service.send_task_notification(task, result, config)

        assert sent is False

    def test_build_email_html(self):
        service = NotificationService()

        task = {"name": "test", "type": "subagent", "schedule": "0 9 * * *", "id": "123"}
        result = {
            "status": "success",
            "output": "Task completed",
            "started_at": "2024-01-01T09:00:00Z",
            "finished_at": "2024-01-01T09:01:00Z"
        }
        config = NotificationConfig(include_output=True)

        html = service._build_email_html(task, result, config)

        assert "test" in html
        assert "Task completed" in html
        assert "Успешно" in html
```

### Интеграционный тест

```bash
# 1. Создать задачу с уведомлением
curl -X POST "https://mcp.svsfinpro.ru/cron/mcp" \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: YOUR_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "claudecron_add_task",
      "arguments": {
        "name": "notification-test",
        "type": "bash",
        "command": "echo Hello from notification test",
        "notification": {
          "email": "sergey@nortex.ru",
          "on_success": true,
          "on_failure": true
        }
      }
    },
    "id": 3
  }'

# 2. Запустить задачу
curl -X POST "https://mcp.svsfinpro.ru/cron/mcp" \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: YOUR_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "claudecron_run_task",
      "arguments": {
        "task_id": "TASK_ID_FROM_STEP_1"
      }
    },
    "id": 4
  }'

# 3. Проверить email
```

## 7. Порядок внедрения

### Phase 1: Core Implementation
1. ✅ Создать файл `notifier.py`
2. ✅ Добавить миграцию БД (столбец `notification`)
3. ✅ Обновить `claudecron_add_task` — добавить параметр `notification`
4. ✅ Интегрировать отправку уведомлений в `execute_task`

### Phase 2: Configuration
5. ✅ Обновить `.env.example`
6. ✅ Обновить `docker-compose.yml`

### Phase 3: Testing & Documentation
7. ✅ Написать unit тесты для `notifier.py`
8. ✅ Провести интеграционное тестирование
9. ✅ Обновить документацию (`servers.md`)

### Phase 4: Deployment
10. ✅ Деплой на продакшен
11. ✅ Мониторинг логов

## 8. Риски и ограничения

### Риски
- **Email MCP Server недоступен** — уведомление не отправится, но задача выполнится
- **Неправильный email** — письма будут уходить "в никуда"
- **Spam-фильтры** — письма могут попасть в спам

### Митигация
- Логирование ошибок отправки
- Валидация email при создании задачи
- Настройка SPF/DKIM на почтовом сервере
- Retry механизм (опционально)

## 9. Будущие улучшения

### v2.1: Telegram уведомления
```json
{
  "notification": {
    "telegram": {
      "chat_id": "123456789",
      "on_success": true
    }
  }
}
```

### v2.2: Webhook
```json
{
  "notification": {
    "webhook": {
      "url": "https://api.example.com/webhook",
      "method": "POST",
      "headers": {"Authorization": "Bearer ..."}
    }
  }
}
```

### v2.3: Агрегация уведомлений
- Группировка нескольких задач в одно письмо
- Дайджест по расписанию (ежедневный отчёт)
