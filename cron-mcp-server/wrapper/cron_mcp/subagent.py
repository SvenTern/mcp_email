"""
Unified Subagent Interface — выбор между Mode A и Mode B.

Автоматический выбор режима на основе:
1. Явного указания в задаче (subagent_mode)
2. Переменной окружения SUBAGENT_DEFAULT_MODE
3. Автоопределения (наличие Claude CLI)
"""

import logging
import os
import shutil
from dataclasses import dataclass
from typing import Optional
from enum import Enum

from .subagent_mcp import SubagentExecutorMCP, SubagentConfig, SubagentResult
from .subagent_cli import SubagentExecutorCLI, CLIConfig, CLIResult

logger = logging.getLogger(__name__)


class SubagentMode(Enum):
    """Режим выполнения subagent."""
    MCP_CLIENT = "mcp_client"  # Mode A: MCP Client Hub
    CLAUDE_CLI = "claude_cli"  # Mode B: Claude Code CLI
    AUTO = "auto"              # Автовыбор


@dataclass
class UnifiedResult:
    """Унифицированный результат subagent."""
    success: bool
    output: str
    mode_used: str
    tool_calls: list[dict]
    turns_used: int
    error: Optional[str] = None


class SubagentExecutor:
    """
    Unified Subagent Executor.

    Пример:
        executor = SubagentExecutor()

        # Автоматический выбор режима
        result = await executor.execute(
            prompt="Отправь email...",
            mcp_servers=["https://..."],
            mode=SubagentMode.AUTO
        )

        # Явное указание режима
        result = await executor.execute(
            prompt="Отправь email...",
            allowed_tools=["mcp__email__send_email"],
            mode=SubagentMode.CLAUDE_CLI
        )
    """

    def __init__(self):
        self.default_mode = self._get_default_mode()

    def _get_default_mode(self) -> SubagentMode:
        """Получить режим по умолчанию."""
        env_mode = os.environ.get("SUBAGENT_DEFAULT_MODE", "auto").lower()

        if env_mode == "mcp_client":
            return SubagentMode.MCP_CLIENT
        elif env_mode == "claude_cli":
            return SubagentMode.CLAUDE_CLI
        else:
            return SubagentMode.AUTO

    def _auto_select_mode(
        self,
        mcp_servers: Optional[list[str]],
        allowed_tools: Optional[list[str]]
    ) -> SubagentMode:
        """
        Автоматический выбор режима.

        Логика:
        1. Если указаны mcp_servers -> MCP_CLIENT
        2. Если указаны allowed_tools и есть Claude CLI -> CLAUDE_CLI
        3. Fallback на MCP_CLIENT
        """
        if mcp_servers:
            return SubagentMode.MCP_CLIENT

        if allowed_tools and shutil.which("claude"):
            return SubagentMode.CLAUDE_CLI

        # Default: MCP Client (требует явного указания серверов)
        return SubagentMode.MCP_CLIENT

    async def execute(
        self,
        prompt: str,
        mode: SubagentMode = SubagentMode.AUTO,
        mcp_servers: Optional[list[str]] = None,
        allowed_tools: Optional[list[str]] = None,
        system_prompt: Optional[str] = None,
        max_turns: Optional[int] = None,
        timeout: Optional[int] = None,
        model: Optional[str] = None
    ) -> UnifiedResult:
        """
        Выполнить subagent задачу.

        Args:
            prompt: Промпт задачи
            mode: Режим выполнения (AUTO, MCP_CLIENT, CLAUDE_CLI)
            mcp_servers: URL MCP серверов (для MCP_CLIENT mode)
            allowed_tools: Разрешённые tools (для CLAUDE_CLI mode)
            system_prompt: Системный промпт
            max_turns: Макс. итераций
            timeout: Таймаут в секундах
            model: Модель Claude

        Returns:
            UnifiedResult
        """
        # Определяем режим
        if mode == SubagentMode.AUTO:
            selected_mode = self._auto_select_mode(mcp_servers, allowed_tools)
        else:
            selected_mode = mode

        logger.info(f"Subagent mode: {selected_mode.value}")

        # Параметры из окружения
        default_timeout = int(os.environ.get("SUBAGENT_TIMEOUT", 300))
        default_max_turns = int(os.environ.get("SUBAGENT_MAX_TURNS", 10))
        default_model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

        timeout = timeout or default_timeout
        max_turns = max_turns or default_max_turns
        model = model or default_model

        if selected_mode == SubagentMode.MCP_CLIENT:
            # Получаем серверы из Registry если не указаны явно
            servers_to_use = mcp_servers or await self._get_default_mcp_servers()
            return await self._execute_mcp(
                prompt=prompt,
                mcp_servers=servers_to_use,
                system_prompt=system_prompt,
                max_turns=max_turns,
                timeout=timeout,
                model=model
            )
        else:
            return await self._execute_cli(
                prompt=prompt,
                allowed_tools=allowed_tools,
                system_prompt=system_prompt,
                max_turns=max_turns,
                timeout=timeout,
                model=model
            )

    async def _execute_mcp(
        self,
        prompt: str,
        mcp_servers: list[str],
        system_prompt: Optional[str],
        max_turns: int,
        timeout: int,
        model: str
    ) -> UnifiedResult:
        """Выполнение через MCP Client Hub (Mode A)."""
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")

        config = SubagentConfig(
            model=model,
            max_turns=max_turns,
            timeout=timeout,
            proxy=proxy
        )

        executor = SubagentExecutorMCP(config)
        result = await executor.execute(
            prompt=prompt,
            mcp_servers=mcp_servers,
            system_prompt=system_prompt
        )

        return UnifiedResult(
            success=result.success,
            output=result.output,
            mode_used="mcp_client",
            tool_calls=result.tool_calls,
            turns_used=result.turns_used,
            error=result.error
        )

    async def _execute_cli(
        self,
        prompt: str,
        allowed_tools: Optional[list[str]],
        system_prompt: Optional[str],
        max_turns: int,
        timeout: int,
        model: str
    ) -> UnifiedResult:
        """Выполнение через Claude CLI (Mode B)."""
        cli_path = os.environ.get("CLAUDE_CLI_PATH", "claude")

        config = CLIConfig(
            cli_path=cli_path,
            timeout=timeout,
            allowed_tools=allowed_tools,
            max_turns=max_turns,
            model=model
        )

        executor = SubagentExecutorCLI(config)
        result = await executor.execute(
            prompt=prompt,
            allowed_tools=allowed_tools,
            system_prompt=system_prompt
        )

        return UnifiedResult(
            success=result.success,
            output=result.output,
            mode_used="claude_cli",
            tool_calls=[],  # CLI не возвращает детальные tool calls
            turns_used=0,   # Неизвестно для CLI
            error=result.error
        )

    async def _get_default_mcp_servers(self) -> list[str]:
        """Получить MCP серверы по умолчанию из Registry (загружаются из YAML)."""
        from .mcp_registry import get_registry

        registry = get_registry()
        if registry:
            servers = await registry.list_servers(enabled_only=True)
            return [s.url for s in servers]

        logger.warning("MCP Registry not initialized, no default servers available")
        return []
