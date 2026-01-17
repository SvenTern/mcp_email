"""
MCP Registry — централизованное управление MCP серверами.

Источники конфигурации (в порядке приоритета):
1. База данных (динамически добавленные)
2. Переменные окружения MCP_SERVER_*
3. Конфиг файл mcp_servers.yaml
"""

import json
import logging
import os
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from pathlib import Path
from urllib.parse import urlparse

import httpx
import yaml

logger = logging.getLogger(__name__)


def validate_url(url: Optional[str]) -> bool:
    """Validate MCP server URL."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        # Must have scheme (http/https) and netloc (host)
        if parsed.scheme not in ('http', 'https'):
            return False
        if not parsed.netloc:
            return False
        return True
    except Exception:
        return False


@dataclass
class MCPServerConfig:
    """Конфигурация MCP сервера."""
    id: str
    name: str
    url: str
    transport: str = "http"
    auth_type: Optional[str] = None      # 'none', 'bearer', 'api_key'
    auth_token: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    health_status: str = "unknown"
    tools: list[dict] = field(default_factory=list)


class MCPRegistry:
    """
    Централизованный реестр MCP серверов.

    Пример:
        registry = MCPRegistry(db_path="/app/data/tasks.db")
        await registry.initialize()

        # Получить все серверы
        servers = await registry.list_servers()

        # Добавить сервер
        await registry.add_server(MCPServerConfig(
            id="email-1",
            name="email",
            url="https://mcp.example.com/email/mcp"
        ))

        # Получить серверы для задачи
        servers = await registry.get_servers_by_names(["email", "bitrix"])

        # Получить URLs для серверов
        urls = await registry.get_server_urls(["email", "bitrix"])
    """

    def __init__(
        self,
        db_path: str = "/app/data/tasks.db",
        config_path: Optional[str] = None
    ):
        self.db_path = db_path
        self.config_path = config_path or os.environ.get(
            "MCP_REGISTRY_CONFIG",
            "/app/config/mcp-servers.yaml"
        )
        self._initialized = False

    async def initialize(self) -> None:
        """Инициализация registry."""
        if self._initialized:
            return

        self._init_database()
        await self._load_from_env()
        await self._load_from_config()

        self._initialized = True
        logger.info("MCP Registry initialized")

    def _init_database(self) -> None:
        """Создать таблицы если не существуют."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mcp_server_groups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                server_ids TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    async def _load_from_env(self) -> None:
        """Загрузить серверы из переменных окружения."""
        for key, value in os.environ.items():
            if key.startswith("MCP_SERVER_") and value:
                name = key.replace("MCP_SERVER_", "").lower()
                server_id = f"env-{name}"

                # Проверяем, есть ли уже такой сервер
                existing = await self.get_server_by_name(name)
                if not existing:
                    await self.add_server(MCPServerConfig(
                        id=server_id,
                        name=name,
                        url=value,
                        description=f"From environment: {key}"
                    ))
                    logger.info(f"Added MCP server from env: {name} -> {value}")

    async def _load_from_config(self) -> None:
        """Загрузить серверы из YAML конфига."""
        if not Path(self.config_path).exists():
            return

        try:
            with open(self.config_path) as f:
                config = yaml.safe_load(f)

            if not config:
                return

            for server_data in config.get("servers", []):
                name = server_data.get("name")
                url = server_data.get("url")

                if not name:
                    logger.warning("Skipping server with missing name in config")
                    continue

                if not validate_url(url):
                    logger.warning(f"Skipping server '{name}' with invalid URL: {url}")
                    continue

                existing = await self.get_server_by_name(name)
                if not existing:
                    try:
                        await self.add_server(MCPServerConfig(
                            id=f"config-{name}",
                            name=name,
                            url=url,
                            transport=server_data.get("transport", "http"),
                            auth_type=server_data.get("auth_type"),
                            auth_token=server_data.get("auth_token"),
                            description=server_data.get("description")
                        ))
                        logger.info(f"Added MCP server from config: {name}")
                    except ValueError as e:
                        logger.warning(f"Failed to add server '{name}': {e}")

        except Exception as e:
            logger.error(f"Failed to load config: {e}")

    async def list_servers(self, enabled_only: bool = True) -> list[MCPServerConfig]:
        """Получить список всех серверов."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if enabled_only:
            cursor.execute("SELECT * FROM mcp_servers WHERE enabled = 1")
        else:
            cursor.execute("SELECT * FROM mcp_servers")

        rows = cursor.fetchall()
        conn.close()

        servers = []
        for row in rows:
            tools = json.loads(row["tools_cache"]) if row["tools_cache"] else []
            servers.append(MCPServerConfig(
                id=row["id"],
                name=row["name"],
                url=row["url"],
                transport=row["transport"],
                auth_type=row["auth_type"],
                auth_token=row["auth_token"],
                description=row["description"],
                enabled=bool(row["enabled"]),
                health_status=row["health_status"],
                tools=tools
            ))

        return servers

    async def get_server_by_name(self, name: str) -> Optional[MCPServerConfig]:
        """Получить сервер по имени."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM mcp_servers WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        tools = json.loads(row["tools_cache"]) if row["tools_cache"] else []
        return MCPServerConfig(
            id=row["id"],
            name=row["name"],
            url=row["url"],
            transport=row["transport"],
            auth_type=row["auth_type"],
            auth_token=row["auth_token"],
            description=row["description"],
            enabled=bool(row["enabled"]),
            health_status=row["health_status"],
            tools=tools
        )

    async def get_servers_by_names(self, names: list[str]) -> list[MCPServerConfig]:
        """Получить серверы по списку имён."""
        servers = []
        for name in names:
            server = await self.get_server_by_name(name)
            if server and server.enabled:
                servers.append(server)
        return servers

    async def get_server_urls(self, names: list[str]) -> list[str]:
        """Получить URLs серверов по именам."""
        servers = await self.get_servers_by_names(names)
        return [s.url for s in servers]

    async def add_server(self, server: MCPServerConfig) -> None:
        """Добавить или обновить сервер."""
        # Validate URL before adding
        if not validate_url(server.url):
            logger.warning(f"Invalid URL for server '{server.name}': {server.url}")
            raise ValueError(f"Invalid URL for server '{server.name}': URL must be a valid HTTP/HTTPS URL")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now(UTC).isoformat()

        cursor.execute("""
            INSERT INTO mcp_servers (
                id, name, url, transport, auth_type, auth_token,
                description, enabled, health_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                url = excluded.url,
                transport = excluded.transport,
                auth_type = excluded.auth_type,
                auth_token = excluded.auth_token,
                description = excluded.description,
                updated_at = excluded.updated_at
        """, (
            server.id, server.name, server.url, server.transport,
            server.auth_type, server.auth_token, server.description,
            1 if server.enabled else 0, server.health_status, now, now
        ))

        conn.commit()
        conn.close()

    async def remove_server(self, name: str) -> bool:
        """Удалить сервер."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM mcp_servers WHERE name = ?", (name,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    async def update_health_status(self, name: str, status: str) -> None:
        """Обновить статус здоровья сервера."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now(UTC).isoformat()

        cursor.execute("""
            UPDATE mcp_servers
            SET health_status = ?, last_health_check = ?, updated_at = ?
            WHERE name = ?
        """, (status, now, now, name))

        conn.commit()
        conn.close()

    async def health_check(self, name: str, timeout: int = 10) -> str:
        """Проверить здоровье MCP сервера."""
        server = await self.get_server_by_name(name)
        if not server:
            return "unknown"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Пробуем GET на /health или корневой эндпоинт
                health_url = server.url.rsplit("/mcp", 1)[0] + "/health"
                response = await client.get(health_url)

                if response.status_code == 200:
                    status = "healthy"
                else:
                    status = "unhealthy"

        except Exception as e:
            logger.warning(f"Health check failed for {name}: {e}")
            status = "unhealthy"

        await self.update_health_status(name, status)
        return status

    async def update_tools_cache(self, name: str, tools: list[dict]) -> None:
        """Обновить кэш tools для сервера."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now(UTC).isoformat()
        tools_json = json.dumps(tools)

        cursor.execute("""
            UPDATE mcp_servers
            SET tools_cache = ?, tools_updated_at = ?, updated_at = ?
            WHERE name = ?
        """, (tools_json, now, now, name))

        conn.commit()
        conn.close()


# Глобальный экземпляр registry
_registry: Optional[MCPRegistry] = None


def get_registry() -> Optional[MCPRegistry]:
    """Получить глобальный registry."""
    return _registry


async def init_registry(db_path: str) -> MCPRegistry:
    """Инициализировать глобальный registry."""
    global _registry
    if _registry is None:
        _registry = MCPRegistry(db_path=db_path)
        await _registry.initialize()
    return _registry
