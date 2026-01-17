"""
Subagent Executor (Mode A) — выполнение AI задач через MCP Client Hub.

Реализует agentic loop:
1. Подключение к MCP серверам
2. Сбор tools
3. Claude API с tool calling
4. Обработка tool results через MCP
5. Возврат финального ответа
"""

import asyncio
import contextvars
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional, Any

import anthropic
import httpx

from .mcp_client import MCPClientHub

logger = logging.getLogger(__name__)

# Контекстная переменная для отслеживания глубины вложенности (защита от рекурсии)
_subagent_depth: contextvars.ContextVar[int] = contextvars.ContextVar(
    'subagent_depth', default=0
)

MAX_SUBAGENT_DEPTH = 3  # Максимальная глубина вложенности


class RecursionLimitExceeded(Exception):
    """Превышен лимит рекурсии subagent."""
    pass


def check_recursion_depth() -> int:
    """Проверить и увеличить глубину рекурсии."""
    current = _subagent_depth.get()
    if current >= MAX_SUBAGENT_DEPTH:
        raise RecursionLimitExceeded(
            f"Subagent recursion limit exceeded (max: {MAX_SUBAGENT_DEPTH})"
        )
    _subagent_depth.set(current + 1)
    return current + 1


def reset_recursion_depth(depth: int) -> None:
    """Сбросить глубину рекурсии."""
    _subagent_depth.set(max(0, depth - 1))


@dataclass
class SubagentConfig:
    """Конфигурация subagent."""
    model: str = "claude-sonnet-4-20250514"
    max_turns: int = 10
    max_tokens: int = 4096
    timeout: int = 300
    proxy: Optional[str] = None


@dataclass
class ToolCallLog:
    """Лог вызова tool."""
    tool: str
    arguments: dict
    result: Any
    success: bool
    error: Optional[str] = None


@dataclass
class SubagentResult:
    """Результат выполнения subagent."""
    success: bool
    output: str
    tool_calls: list[dict]
    turns_used: int
    error: Optional[str] = None


class SubagentExecutorMCP:
    """
    Выполнение subagent задач через MCP Client Hub.

    Пример:
        config = SubagentConfig(model="claude-sonnet-4-20250514", max_turns=10)
        executor = SubagentExecutorMCP(config)

        result = await executor.execute(
            prompt="Отправь email на test@example.com с темой 'Тест'",
            mcp_servers=["https://mcp.example.com/email/mcp"]
        )

        print(result.output)
    """

    def __init__(self, config: SubagentConfig):
        self.config = config

        # Настройка proxy для Anthropic client
        http_client = None
        if config.proxy:
            http_client = httpx.AsyncClient(proxy=config.proxy)

        self.client = anthropic.AsyncAnthropic(
            http_client=http_client
        )
        self.mcp_hub: Optional[MCPClientHub] = None

    async def execute(
        self,
        prompt: str,
        mcp_servers: list[str],
        system_prompt: Optional[str] = None
    ) -> SubagentResult:
        """
        Выполнить subagent задачу.

        Args:
            prompt: Промпт пользователя
            mcp_servers: Список URL MCP серверов
            system_prompt: Опциональный системный промпт

        Returns:
            SubagentResult с результатом выполнения
        """
        tool_calls_log: list[dict] = []
        depth = 0

        try:
            # Проверка рекурсии
            depth = check_recursion_depth()
            logger.info(f"Subagent depth: {depth}")

            # 1. Подключаемся к MCP серверам
            self.mcp_hub = MCPClientHub(
                timeout=self.config.timeout,
                proxy=self.config.proxy
            )
            await self.mcp_hub.connect(mcp_servers)

            # 2. Получаем tools в формате Anthropic
            tools = self.mcp_hub.to_anthropic_format()

            if not tools:
                return SubagentResult(
                    success=False,
                    output="",
                    tool_calls=[],
                    turns_used=0,
                    error="No tools available from MCP servers"
                )

            logger.info(f"Available tools: {[t['name'] for t in tools]}")

            # 3. Начинаем agentic loop
            messages = [{"role": "user", "content": prompt}]
            turns_used = 0

            default_system = """You are a helpful assistant with access to external tools.
Use the available tools to complete the user's request.
Always explain what you're doing and report results clearly."""

            system = system_prompt or default_system

            while turns_used < self.config.max_turns:
                turns_used += 1
                logger.info(f"Agentic loop turn {turns_used}/{self.config.max_turns}")

                # 4. Вызов Claude API
                response = await self.client.messages.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    system=system,
                    tools=tools,
                    messages=messages
                )

                logger.debug(f"Claude response stop_reason: {response.stop_reason}")

                # 5. Обработка ответа
                assistant_content = []
                tool_use_blocks = []

                for block in response.content:
                    if block.type == "text":
                        assistant_content.append({
                            "type": "text",
                            "text": block.text
                        })
                    elif block.type == "tool_use":
                        assistant_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input
                        })
                        tool_use_blocks.append(block)

                # Добавляем ответ ассистента в историю
                messages.append({
                    "role": "assistant",
                    "content": assistant_content
                })

                # 6. Если нет tool calls — завершаем
                if response.stop_reason == "end_turn" or not tool_use_blocks:
                    # Собираем финальный текст
                    final_text = ""
                    for block in response.content:
                        if block.type == "text":
                            final_text += block.text

                    return SubagentResult(
                        success=True,
                        output=final_text,
                        tool_calls=tool_calls_log,
                        turns_used=turns_used
                    )

                # 7. Выполняем tool calls через MCP Hub
                tool_results = []
                for tool_block in tool_use_blocks:
                    tool_name = tool_block.name
                    tool_input = tool_block.input

                    logger.info(f"Calling tool: {tool_name}")

                    try:
                        result = await self.mcp_hub.call_tool(tool_name, tool_input)

                        # Логируем успешный вызов
                        tool_calls_log.append({
                            "tool": tool_name,
                            "arguments": tool_input,
                            "result": result,
                            "success": "error" not in result
                        })

                        # Формируем результат для Claude
                        if "error" in result:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_block.id,
                                "is_error": True,
                                "content": json.dumps(result["error"])
                            })
                        else:
                            # Извлекаем content из MCP результата
                            content_parts = result.get("content", [])
                            if content_parts:
                                content_text = ""
                                for part in content_parts:
                                    if isinstance(part, dict) and part.get("type") == "text":
                                        content_text += part.get("text", "")
                                    elif isinstance(part, str):
                                        content_text += part
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_block.id,
                                    "content": content_text or json.dumps(result)
                                })
                            else:
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_block.id,
                                    "content": json.dumps(result)
                                })

                    except Exception as e:
                        logger.error(f"Tool call error {tool_name}: {e}")
                        tool_calls_log.append({
                            "tool": tool_name,
                            "arguments": tool_input,
                            "result": None,
                            "success": False,
                            "error": str(e)
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "is_error": True,
                            "content": f"Error: {str(e)}"
                        })

                # 8. Добавляем результаты tools в историю
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

            # Превышен лимит итераций
            return SubagentResult(
                success=False,
                output="",
                tool_calls=tool_calls_log,
                turns_used=turns_used,
                error=f"Max turns exceeded ({self.config.max_turns})"
            )

        except RecursionLimitExceeded as e:
            return SubagentResult(
                success=False,
                output="",
                tool_calls=tool_calls_log,
                turns_used=0,
                error=str(e)
            )

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            return SubagentResult(
                success=False,
                output="",
                tool_calls=tool_calls_log,
                turns_used=0,
                error=f"Claude API error: {str(e)}"
            )

        except Exception as e:
            logger.error(f"Subagent execution error: {e}")
            return SubagentResult(
                success=False,
                output="",
                tool_calls=tool_calls_log,
                turns_used=0,
                error=str(e)
            )

        finally:
            # Сбрасываем глубину рекурсии
            if depth > 0:
                reset_recursion_depth(depth)

            # Закрываем MCP соединения
            if self.mcp_hub:
                await self.mcp_hub.close()
