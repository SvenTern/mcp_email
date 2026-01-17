"""
Subagent Executor (Mode B) — выполнение AI задач через Claude Code CLI.

Делегирует выполнение в Claude Code CLI:
- claude -p "prompt" --allowedTools "mcp__*"
- Парсинг stdout для получения результата
- Поддержка timeout и max_turns
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CLIConfig:
    """Конфигурация для Claude CLI mode."""
    cli_path: str = "claude"
    timeout: int = 300
    allowed_tools: Optional[list[str]] = None
    max_turns: int = 10
    model: Optional[str] = None


@dataclass
class CLIResult:
    """Результат выполнения через Claude CLI."""
    success: bool
    output: str
    exit_code: int
    error: Optional[str] = None


def validate_claude_cli() -> dict:
    """Проверить доступность Claude CLI."""
    result = {
        "available": False,
        "path": None,
        "version": None,
        "error": None
    }

    cli_path = shutil.which("claude")
    if not cli_path:
        result["error"] = "Claude CLI not found in PATH"
        return result

    result["path"] = cli_path

    try:
        version_output = subprocess.run(
            [cli_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if version_output.returncode == 0:
            result["version"] = version_output.stdout.strip()
            result["available"] = True
        else:
            result["error"] = version_output.stderr
    except subprocess.TimeoutExpired:
        result["error"] = "CLI version check timed out"
    except Exception as e:
        result["error"] = str(e)

    return result


class SubagentExecutorCLI:
    """
    Выполнение subagent задач через Claude Code CLI.

    Пример:
        config = CLIConfig(timeout=300, allowed_tools=["mcp__email__*"])
        executor = SubagentExecutorCLI(config)

        result = await executor.execute(
            prompt="Отправь email на test@example.com",
            allowed_tools=["mcp__email__send_email"]
        )

        print(result.output)
    """

    def __init__(self, config: CLIConfig):
        self.config = config
        self._cli_validated = False
        self._cli_available = False

    def _validate_cli(self) -> bool:
        """Проверить доступность CLI (кешированно)."""
        if self._cli_validated:
            return self._cli_available

        validation = validate_claude_cli()
        self._cli_validated = True
        self._cli_available = validation["available"]

        if validation["available"]:
            logger.info(f"Claude CLI found: {validation['path']} ({validation['version']})")
        else:
            logger.warning(f"Claude CLI not available: {validation['error']}")

        return self._cli_available

    def _build_command(
        self,
        prompt: str,
        allowed_tools: Optional[list[str]] = None,
        system_prompt: Optional[str] = None
    ) -> list[str]:
        """Построить команду для Claude CLI."""
        cli_path = self.config.cli_path

        cmd = [cli_path, "-p", prompt]

        # --allowedTools
        tools = allowed_tools or self.config.allowed_tools
        if tools:
            # Формат: "tool1,tool2,tool3" или паттерн "mcp__*"
            tools_arg = ",".join(tools)
            cmd.extend(["--allowedTools", tools_arg])

        # --max-turns
        cmd.extend(["--max-turns", str(self.config.max_turns)])

        # --model (если указана)
        if self.config.model:
            cmd.extend(["--model", self.config.model])

        # --system-prompt (если указан)
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        # --output-format json для парсинга
        cmd.extend(["--output-format", "json"])

        # --verbose для логов
        # cmd.append("--verbose")

        return cmd

    async def execute(
        self,
        prompt: str,
        allowed_tools: Optional[list[str]] = None,
        system_prompt: Optional[str] = None
    ) -> CLIResult:
        """
        Выполнить задачу через Claude CLI.

        Args:
            prompt: Промпт пользователя
            allowed_tools: Список разрешённых tools (паттерны)
            system_prompt: Системный промпт (не используется в CLI mode)

        Returns:
            CLIResult с результатом выполнения
        """
        # Проверяем доступность CLI
        if not self._validate_cli():
            return CLIResult(
                success=False,
                output="",
                exit_code=-1,
                error="Claude CLI not available"
            )

        # Строим команду
        cmd = self._build_command(prompt, allowed_tools, system_prompt)
        logger.info(f"Executing CLI: {' '.join(cmd)}")

        try:
            # Запускаем процесс асинхронно
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ}
            )

            # Ждём завершения с timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return CLIResult(
                    success=False,
                    output="",
                    exit_code=-1,
                    error=f"CLI execution timed out after {self.config.timeout}s"
                )

            exit_code = process.returncode
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            logger.debug(f"CLI exit code: {exit_code}")
            logger.debug(f"CLI stdout length: {len(stdout_text)}")

            if exit_code != 0:
                return CLIResult(
                    success=False,
                    output=stdout_text,
                    exit_code=exit_code,
                    error=stderr_text or f"CLI exited with code {exit_code}"
                )

            # Парсим JSON output
            output_text = stdout_text
            try:
                # Claude CLI с --output-format json возвращает JSON
                json_output = json.loads(stdout_text)
                if isinstance(json_output, dict):
                    # Извлекаем result или content
                    output_text = json_output.get("result", "")
                    if not output_text:
                        output_text = json_output.get("content", "")
                    if not output_text:
                        output_text = json.dumps(json_output, ensure_ascii=False)
            except json.JSONDecodeError:
                # Не JSON — используем как есть
                pass

            return CLIResult(
                success=True,
                output=output_text,
                exit_code=exit_code
            )

        except FileNotFoundError:
            return CLIResult(
                success=False,
                output="",
                exit_code=-1,
                error=f"Claude CLI not found at: {self.config.cli_path}"
            )

        except Exception as e:
            logger.error(f"CLI execution error: {e}")
            return CLIResult(
                success=False,
                output="",
                exit_code=-1,
                error=str(e)
            )

    @staticmethod
    def get_default_allowed_tools() -> list[str]:
        """Получить стандартный набор allowed tools."""
        # Стандартный набор для email и bitrix
        return [
            "mcp__email__send_email",
            "mcp__email__list_emails",
            "mcp__email__read_email",
            "mcp__bitrix__create_lead",
            "mcp__bitrix__get_leads",
            "mcp__bitrix__update_lead"
        ]
