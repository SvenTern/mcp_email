"""
MCP Client Hub — подключение к MCP серверам и управление tools.

Поддерживает:
- Streamable HTTP транспорт (MCP 2025-11-25)
- Сбор tools со всех серверов
- Маршрутизация tool calls
- Конвертация в формат Anthropic API
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional, Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Представление MCP tool."""
    name: str
    description: str
    input_schema: dict
    server_url: str  # Для маршрутизации вызовов


@dataclass
class MCPSession:
    """Сессия с MCP сервером."""
    server_url: str
    session_id: Optional[str] = None
    client: Optional[httpx.AsyncClient] = None
    tools: list[MCPTool] = field(default_factory=list)


class MCPClientHub:
    """
    Управление подключениями к нескольким MCP серверам.

    Пример использования:
        hub = MCPClientHub(timeout=30)
        await hub.connect([
            "https://mcp.example.com/email/mcp",
            "https://mcp.example.com/bitrix/mcp"
        ])

        tools = hub.to_anthropic_format()
        result = await hub.call_tool("email_send", {"to": "...", "body": "..."})

        await hub.close()
    """

    def __init__(self, timeout: int = 30, proxy: Optional[str] = None):
        self.timeout = timeout
        self.proxy = proxy
        self.sessions: dict[str, MCPSession] = {}
        self._tool_to_server: dict[str, str] = {}  # tool_name -> server_url

    async def connect(self, server_urls: list[str]) -> None:
        """Подключиться к списку MCP серверов."""
        tasks = [self._connect_to_server(url) for url in server_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for url, result in zip(server_urls, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to connect to {url}: {result}")
            else:
                logger.info(f"Connected to {url}, tools: {len(self.sessions[url].tools)}")

    def _parse_response(self, response: httpx.Response) -> dict:
        """
        Парсинг ответа с поддержкой JSON и SSE форматов.

        Args:
            response: HTTP ответ от MCP сервера

        Returns:
            Распарсенный JSON-RPC результат
        """
        content_type = response.headers.get("content-type", "")

        if "text/event-stream" in content_type:
            # SSE формат: парсим события
            text = response.text
            result = {}

            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str:
                        try:
                            data = json.loads(data_str)
                            # Если это JSON-RPC ответ с result
                            if "result" in data:
                                result = data
                            elif "error" in data:
                                result = data
                            # Если это просто data без обёртки JSON-RPC
                            elif not result:
                                result = {"result": data}
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse SSE data: {data_str}")

            return result
        else:
            # Обычный JSON формат
            return response.json()

    async def _connect_to_server(self, server_url: str) -> None:
        """Установить соединение с одним MCP сервером."""
        transport_config = {}
        if self.proxy:
            transport_config["proxy"] = self.proxy

        client = httpx.AsyncClient(
            timeout=self.timeout,
            **transport_config
        )

        session = MCPSession(server_url=server_url, client=client)

        try:
            # Initialize request
            init_response = await client.post(
                server_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "ClaudeCron-SubAgent",
                            "version": "1.0.0"
                        }
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            )
            init_response.raise_for_status()

            # Сохраняем session ID
            session.session_id = init_response.headers.get("Mcp-Session-Id")

            # Initialized notification
            await client.post(
                server_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "Mcp-Session-Id": session.session_id or ""
                }
            )

            # Получаем список tools
            tools_response = await client.post(
                server_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "Mcp-Session-Id": session.session_id or ""
                }
            )
            tools_response.raise_for_status()
            tools_data = self._parse_response(tools_response)

            # Парсим tools
            for tool in tools_data.get("result", {}).get("tools", []):
                mcp_tool = MCPTool(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {}),
                    server_url=server_url
                )
                session.tools.append(mcp_tool)
                self._tool_to_server[tool["name"]] = server_url

            self.sessions[server_url] = session

        except Exception as e:
            await client.aclose()
            raise e

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """
        Вызвать tool на соответствующем MCP сервере.

        Args:
            tool_name: Имя tool
            arguments: Аргументы для tool

        Returns:
            Результат выполнения tool
        """
        server_url = self._tool_to_server.get(tool_name)
        if not server_url:
            return {"error": f"Tool not found: {tool_name}"}

        session = self.sessions.get(server_url)
        if not session or not session.client:
            return {"error": f"Not connected to server for tool: {tool_name}"}

        try:
            response = await session.client.post(
                server_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "Mcp-Session-Id": session.session_id or ""
                }
            )
            response.raise_for_status()

            result = self._parse_response(response)
            if "error" in result:
                return {"error": result["error"]}

            return result.get("result", {})

        except Exception as e:
            logger.error(f"Tool call failed {tool_name}: {e}")
            return {"error": str(e)}

    def to_anthropic_format(self, exclude_patterns: Optional[list[str]] = None) -> list[dict]:
        """
        Конвертировать все tools в формат Anthropic API.

        Args:
            exclude_patterns: Паттерны для исключения tools (защита от рекурсии)

        Returns:
            Список tools для Claude API messages.create()
        """
        # Создаём копию списка, чтобы не мутировать входной аргумент
        exclude = list(exclude_patterns) if exclude_patterns else []
        # Всегда блокируем claudecron_ tools для защиты от рекурсии
        exclude.append("claudecron_")

        tools = []
        for session in self.sessions.values():
            for tool in session.tools:
                # Проверяем, не заблокирован ли tool
                if any(pattern in tool.name for pattern in exclude):
                    logger.warning(f"Blocked recursive tool: {tool.name}")
                    continue

                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema
                })
        return tools

    def list_tools(self) -> list[MCPTool]:
        """Получить список всех tools."""
        tools = []
        for session in self.sessions.values():
            tools.extend(session.tools)
        return tools

    def get_tool_names(self) -> list[str]:
        """Получить список имён всех tools."""
        return list(self._tool_to_server.keys())

    async def close(self) -> None:
        """Закрыть все подключения."""
        for session in self.sessions.values():
            if session.client:
                # Terminate session
                try:
                    await session.client.delete(
                        session.server_url,
                        headers={"Mcp-Session-Id": session.session_id or ""}
                    )
                except Exception:
                    pass
                await session.client.aclose()

        self.sessions.clear()
        self._tool_to_server.clear()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
