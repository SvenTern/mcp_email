"""
ClaudeCron MCP Server - FastMCP Implementation

Provides scheduled task automation with MCP 2025-11-25 features:
- Cron-based task scheduling
- File watching triggers
- AI subagent task execution (Mode A: MCP Client Hub, Mode B: Claude CLI)
- Background task support with cron scheduler
"""

import asyncio
import json
import logging
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from typing import Optional
from pathlib import Path

from fastmcp import FastMCP, Context
from fastmcp.server.dependencies import Progress
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from croniter import croniter

from . import __version__, __protocol_version__

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Proxy configuration for Claude API access
PROXY_URL = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
if PROXY_URL:
    logger.info(f"Proxy configured for Claude API: {PROXY_URL}")

# Database path
DB_PATH = os.environ.get("CLAUDECRON_DB_PATH", "/app/data/tasks.db")

# Task storage
tasks_cache: dict[str, dict] = {}

# Scheduler state
_scheduler_started = False


def get_db_connection() -> sqlite3.Connection:
    """Get SQLite database connection."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database schema."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tasks table with subagent fields
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

    # Migration: add missing columns to existing tasks table
    existing_columns = {row[1] for row in cursor.execute("PRAGMA table_info(tasks)").fetchall()}
    new_columns = [
        ("subagent_mode", "TEXT"),
        ("mcp_servers", "TEXT"),
        ("allowed_tools", "TEXT"),
        ("system_prompt", "TEXT"),
        ("max_turns", "INTEGER"),
        ("notification", "TEXT"),  # JSON: {"email": "...", "on_success": true, ...}
    ]
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            cursor.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}")
            logger.info(f"Added column {col_name} to tasks table")

    # Execution history table
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

    # Migration: add missing columns to existing history table
    existing_history_columns = {row[1] for row in cursor.execute("PRAGMA table_info(history)").fetchall()}
    new_history_columns = [
        ("tool_calls", "TEXT"),
        ("turns_used", "INTEGER"),
        ("mode_used", "TEXT"),
    ]
    for col_name, col_type in new_history_columns:
        if col_name not in existing_history_columns:
            cursor.execute(f"ALTER TABLE history ADD COLUMN {col_name} {col_type}")
            logger.info(f"Added column {col_name} to history table")

    # MCP servers registry table
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
    logger.info("Database initialized")


def ensure_initialized():
    """Ensure database is initialized."""
    global _scheduler_started
    if not _scheduler_started:
        init_database()
        _scheduler_started = True


async def execute_task(task_id: str) -> dict:
    """Execute a task and record history."""
    ensure_initialized()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"error": f"Task not found: {task_id}"}

    task = dict(row)

    # Record execution start
    history_id = str(uuid.uuid4())
    started_at = datetime.now(UTC).isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO history (id, task_id, started_at, status) VALUES (?, ?, ?, ?)",
        (history_id, task_id, started_at, "running")
    )
    conn.commit()
    conn.close()

    output = None
    error = None
    status = "success"
    tool_calls = []
    turns_used = 0
    mode_used = None

    try:
        if task['type'] == 'bash':
            # Execute bash command
            proc = await asyncio.create_subprocess_shell(
                task['command'],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

            output = stdout.decode() if stdout else None
            if proc.returncode != 0:
                status = "failed"
                error = stderr.decode() if stderr else f"Exit code: {proc.returncode}"

        elif task['type'] == 'subagent':
            # Execute AI subagent task
            from .subagent import SubagentExecutor, SubagentMode

            executor = SubagentExecutor()

            # Определяем режим
            mode_str = task.get('subagent_mode') or os.environ.get("SUBAGENT_DEFAULT_MODE", "auto")
            if mode_str in ['mcp_client', 'claude_cli']:
                mode = SubagentMode(mode_str)
            else:
                mode = SubagentMode.AUTO

            # Получаем параметры из задачи
            mcp_servers = json.loads(task.get('mcp_servers') or '[]')
            allowed_tools = json.loads(task.get('allowed_tools') or '[]')
            system_prompt = task.get('system_prompt')
            max_turns = task.get('max_turns')

            result = await executor.execute(
                prompt=task['prompt'],
                mode=mode,
                mcp_servers=mcp_servers if mcp_servers else None,
                allowed_tools=allowed_tools if allowed_tools else None,
                system_prompt=system_prompt,
                max_turns=max_turns
            )

            output = result.output
            tool_calls = result.tool_calls
            turns_used = result.turns_used
            mode_used = result.mode_used

            # Добавляем информацию о tool calls в output
            if result.tool_calls:
                output += f"\n\n--- Tool Calls ({result.turns_used} turns) ---\n"
                for tc in result.tool_calls:
                    output += f"- {tc['tool']}: {'✓' if tc.get('success') else '✗'}\n"

            if not result.success:
                status = "failed"
                error = result.error

    except asyncio.TimeoutError:
        status = "failed"
        error = "Task execution timed out"
    except Exception as e:
        status = "failed"
        error = str(e)
        logger.error(f"Task execution error: {e}")

    # Update history
    finished_at = datetime.now(UTC).isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE history SET finished_at = ?, status = ?, output = ?, error = ?,
           tool_calls = ?, turns_used = ?, mode_used = ? WHERE id = ?""",
        (finished_at, status, output, error,
         json.dumps(tool_calls) if tool_calls else None, turns_used, mode_used, history_id)
    )
    conn.commit()
    conn.close()

    logger.info(f"Task {task['name']} completed with status: {status}")

    # Prepare result dict
    result = {
        "task_id": task_id,
        "history_id": history_id,
        "status": status,
        "output": output,
        "error": error,
        "tool_calls": tool_calls,
        "turns_used": turns_used,
        "mode_used": mode_used,
        "started_at": started_at,
        "finished_at": finished_at
    }

    # Send notification if configured
    try:
        from .notifier import NotificationConfig, get_notification_service

        notification_json = task.get('notification')
        notification_config = NotificationConfig.from_json(notification_json)

        if notification_config:
            notifier = get_notification_service()
            await notifier.send_task_notification(task, result, notification_config)
    except Exception as e:
        logger.error(f"Failed to send notification for task {task['name']}: {e}")

    return result


# Lifespan for scheduler - combined with FastMCP lifespan
def create_combined_lifespan(mcp_app):
    """Create combined lifespan for scheduler + FastMCP."""
    from .scheduler import start_scheduler, stop_scheduler
    from .mcp_registry import init_registry

    @asynccontextmanager
    async def combined_lifespan(app: Starlette):
        """Lifecycle manager combining ClaudeCron scheduler and FastMCP."""
        # Startup: ClaudeCron
        init_database()
        await init_registry(DB_PATH)
        await start_scheduler(DB_PATH, task_executor=execute_task)
        logger.info("ClaudeCron started with scheduler")

        # Startup: FastMCP (manages session handlers, etc.)
        async with mcp_app.lifespan(app):
            yield

        # Shutdown: ClaudeCron (FastMCP shutdown happens inside context manager)
        await stop_scheduler()
        logger.info("ClaudeCron stopped")

    return combined_lifespan


# Initialize FastMCP server
mcp = FastMCP(
    "ClaudeCron MCP Server",
    version=__version__,
    instructions="""ClaudeCron - scheduled task automation for Claude Code with AI subagent support.

## Quick Start - Creating Subagent Tasks

To create an AI subagent task that uses external MCP servers:

```json
claudecron_add_task(
  name="my_task",
  type="subagent",
  subagent_mode="mcp_client",
  mcp_servers=["bitrix_api", "email"],  // Use server names from registry
  prompt="Your task description here",
  schedule="0 9 * * *"  // Optional: run daily at 9 AM
)
```

After creating, run immediately with: `claudecron_run_task(task_id="...")`

To get task results: `claudecron_get_task_result(task_id="...")` or `claudecron_get_history(task_id="...")`

## Available Tools

### Task Management
- **claudecron_add_task**: Create scheduled tasks (bash or subagent)
- **claudecron_list_tasks**: List all tasks
- **claudecron_run_task**: Run a task immediately
- **claudecron_delete_task**: Delete a task
- **claudecron_toggle_task**: Enable/disable a task

### Results & History
- **claudecron_get_task_result**: Get the latest result/output of a specific task
- **claudecron_get_history**: Get full execution history with outputs

### MCP Servers
- **claudecron_list_mcp_servers**: List registered MCP servers (use names in mcp_servers param)
- **claudecron_add_mcp_server**: Add a new MCP server to registry

### Status
- **claudecron_scheduler_status**: Get scheduler status

## Subagent Task Types

1. **mcp_client** (recommended): Connects to MCP servers directly
   - Use `mcp_servers` parameter with server names from registry
   - Example: `mcp_servers=["bitrix_api", "email", "telegram"]`

2. **claude_cli**: Uses Claude Code CLI
   - Use `allowed_tools` parameter
   - Requires Claude CLI installed on server

## Registered MCP Servers

Use `claudecron_list_mcp_servers()` to see available servers. Common servers:
- bitrix_api: Bitrix24 API documentation search
- email: Email sending/receiving via IMAP/SMTP
- bitrix: Bitrix24 CRM integration
- telegram: Telegram bot notifications
"""
)


@mcp.tool(task=True)
async def claudecron_add_task(
    name: str,
    type: str,
    schedule: Optional[str] = None,
    command: Optional[str] = None,
    prompt: Optional[str] = None,
    timezone: str = "UTC",
    enabled: bool = True,
    trigger_type: Optional[str] = None,
    trigger_path: Optional[str] = None,
    subagent_mode: Optional[str] = None,
    mcp_servers: Optional[list[str]] = None,
    allowed_tools: Optional[list[str]] = None,
    system_prompt: Optional[str] = None,
    max_turns: Optional[int] = None,
    notification: Optional[dict] = None,
    ctx: Context = None,
    progress: Progress = Progress()
) -> str:
    """
    Create a new scheduled task (bash command or AI subagent).

    ## Subagent Task Example (recommended for AI tasks):
    ```
    claudecron_add_task(
        name="search_bitrix_docs",
        type="subagent",
        subagent_mode="mcp_client",
        mcp_servers=["bitrix_api"],
        prompt="Find documentation for crm.deal.list method and summarize parameters"
    )
    ```

    ## Bash Task Example:
    ```
    claudecron_add_task(
        name="backup_db",
        type="bash",
        command="pg_dump mydb > /backup/db.sql",
        schedule="0 2 * * *"
    )
    ```

    Args:
        name: Unique task name (e.g., 'daily_report', 'search_docs')
        type: Task type - 'bash' for shell commands, 'subagent' for AI tasks
        schedule: Cron expression (min hour day month weekday). Examples:
            - "0 9 * * *" = daily at 9:00
            - "*/15 * * * *" = every 15 minutes
            - "0 0 * * 1" = weekly on Monday at midnight
            - None = manual run only (use claudecron_run_task)
        command: Shell command (required for type='bash')
        prompt: AI task description (required for type='subagent')
        timezone: Timezone for schedule (default: UTC)
        enabled: Whether task is active (default: True)
        trigger_type: Optional trigger - 'file-watch' for file change triggers
        trigger_path: Path to watch (required if trigger_type='file-watch')
        subagent_mode: AI execution mode:
            - 'mcp_client' (recommended): Direct MCP server connection
            - 'claude_cli': Use Claude Code CLI
            - 'auto': Auto-select based on available resources
        mcp_servers: List of MCP server names from registry (use claudecron_list_mcp_servers to see available).
            Examples: ["bitrix_api"], ["email", "telegram"], ["bitrix_api", "bitrix"]
        allowed_tools: List of allowed tool names (for claude_cli mode only)
        system_prompt: Custom system prompt for AI subagent
        max_turns: Maximum AI conversation turns (default: 10)
        notification: Email notification settings (dict):
            - email: Email address to send notifications to
            - on_success: Send on successful completion (default: True)
            - on_failure: Send on failure (default: True)
            - include_output: Include task output in email (default: True)
            - include_tool_calls: Include tool calls list (default: False)
            Example: {"email": "user@example.com", "on_success": True, "on_failure": True}

    Returns:
        JSON with created task including task_id. Use task_id with claudecron_run_task to execute.
    """
    ensure_initialized()

    await progress.set_total(100)
    await progress.set_message("Creating task...")

    if ctx:
        await ctx.info(f"Creating task: {name}")

    # Validate type
    if type not in ['bash', 'subagent']:
        return json.dumps({"error": "Type must be 'bash' or 'subagent'"})

    # Validate required fields
    if type == 'bash' and not command:
        return json.dumps({"error": "Command required for bash type"})
    if type == 'subagent' and not prompt:
        return json.dumps({"error": "Prompt required for subagent type"})

    # Validate cron expression
    if schedule:
        try:
            croniter(schedule)
        except ValueError as e:
            return json.dumps({"error": f"Invalid cron expression: {e}"})

    await progress.increment(30)

    # Resolve MCP server names to URLs if needed
    resolved_mcp_servers = []
    if mcp_servers:
        from .mcp_registry import get_registry
        registry = get_registry()
        if registry:
            for server in mcp_servers:
                if server.startswith("http"):
                    resolved_mcp_servers.append(server)
                else:
                    # Resolve by name
                    srv = await registry.get_server_by_name(server)
                    if srv:
                        resolved_mcp_servers.append(srv.url)
                    else:
                        resolved_mcp_servers.append(server)
        else:
            resolved_mcp_servers = mcp_servers

    # Create task
    task_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    # Serialize lists to JSON
    mcp_servers_json = json.dumps(resolved_mcp_servers) if resolved_mcp_servers else None
    allowed_tools_json = json.dumps(allowed_tools) if allowed_tools else None
    notification_json = json.dumps(notification) if notification else None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (
            id, name, type, schedule, command, prompt, timezone, enabled,
            trigger_type, trigger_path, subagent_mode, mcp_servers,
            allowed_tools, system_prompt, max_turns, notification, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        task_id, name, type, schedule, command, prompt, timezone,
        1 if enabled else 0, trigger_type, trigger_path,
        subagent_mode, mcp_servers_json, allowed_tools_json,
        system_prompt, max_turns, notification_json, now, now
    ))
    conn.commit()
    conn.close()

    await progress.increment(30)

    # Add to cache
    task_dict = {
        "id": task_id,
        "name": name,
        "type": type,
        "schedule": schedule,
        "command": command,
        "prompt": prompt,
        "timezone": timezone,
        "enabled": enabled,
        "trigger_type": trigger_type,
        "trigger_path": trigger_path,
        "subagent_mode": subagent_mode,
        "mcp_servers": resolved_mcp_servers,
        "allowed_tools": allowed_tools,
        "system_prompt": system_prompt,
        "max_turns": max_turns,
        "notification": notification,
        "created_at": now,
        "updated_at": now
    }

    tasks_cache[task_id] = task_dict

    await progress.increment(40)
    await progress.set_message("Task created successfully")

    logger.info(f"Created task: {name} ({task_id})")

    return json.dumps({
        "success": True,
        "task": task_dict
    }, default=str)


@mcp.tool(task=True)
async def claudecron_list_tasks(
    status: str = "all",
    ctx: Context = None,
    progress: Progress = Progress()
) -> str:
    """
    List all scheduled tasks.

    Args:
        status: Filter by status ('all', 'enabled', 'disabled')

    Returns:
        JSON array of tasks
    """
    ensure_initialized()

    await progress.set_total(100)
    await progress.set_message("Fetching tasks...")

    if ctx:
        await ctx.info(f"Listing tasks (status: {status})")

    conn = get_db_connection()
    cursor = conn.cursor()

    if status == "enabled":
        cursor.execute("SELECT * FROM tasks WHERE enabled = 1 ORDER BY created_at DESC")
    elif status == "disabled":
        cursor.execute("SELECT * FROM tasks WHERE enabled = 0 ORDER BY created_at DESC")
    else:
        cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")

    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()

    await progress.increment(40)
    await progress.set_message(f"Found {len(tasks)} tasks")

    # Add next run time for scheduled tasks and parse JSON fields
    for task in tasks:
        if task.get('schedule') and task.get('enabled'):
            try:
                cron = croniter(task['schedule'], datetime.now(UTC))
                task['next_run'] = cron.get_next(datetime).isoformat()
            except:
                pass

        # Parse JSON fields
        if task.get('mcp_servers'):
            try:
                task['mcp_servers'] = json.loads(task['mcp_servers'])
            except:
                pass
        if task.get('allowed_tools'):
            try:
                task['allowed_tools'] = json.loads(task['allowed_tools'])
            except:
                pass

    return json.dumps({"tasks": tasks, "count": len(tasks)}, default=str)


@mcp.tool(task=True)
async def claudecron_run_task(
    task_id: str,
    ctx: Context = None,
    progress: Progress = Progress()
) -> str:
    """
    Run a task immediately.

    Args:
        task_id: Task ID to run

    Returns:
        JSON with execution result
    """
    ensure_initialized()

    await progress.set_total(100)
    await progress.set_message("Running task...")

    if ctx:
        await ctx.info(f"Running task: {task_id}")

    # Verify task exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    conn.close()

    if not task:
        return json.dumps({"error": f"Task not found: {task_id}"})

    await progress.increment(30)
    await progress.set_message(f"Executing: {task['name']}")

    # Execute task
    result = await execute_task(task_id)

    await progress.increment(40)
    await progress.set_message("Task completed")

    return json.dumps(result, default=str)


@mcp.tool()
async def claudecron_delete_task(task_id: str) -> str:
    """
    Delete a scheduled task.

    Args:
        task_id: Task ID to delete

    Returns:
        JSON with deletion result
    """
    ensure_initialized()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if task exists
    cursor.execute("SELECT name FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()

    if not task:
        conn.close()
        return json.dumps({"error": f"Task not found: {task_id}"})

    task_name = task['name']

    # Delete task and history
    cursor.execute("DELETE FROM history WHERE task_id = ?", (task_id,))
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    # Remove from cache
    tasks_cache.pop(task_id, None)

    logger.info(f"Deleted task: {task_name} ({task_id})")

    return json.dumps({
        "success": True,
        "message": f"Task '{task_name}' deleted"
    })


@mcp.tool()
async def claudecron_toggle_task(task_id: str, enabled: bool) -> str:
    """
    Enable or disable a task.

    Args:
        task_id: Task ID
        enabled: Whether to enable the task

    Returns:
        JSON with result
    """
    ensure_initialized()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()

    if not task:
        conn.close()
        return json.dumps({"error": f"Task not found: {task_id}"})

    task_dict = dict(task)

    # Update database
    now = datetime.now(UTC).isoformat()
    cursor.execute(
        "UPDATE tasks SET enabled = ?, updated_at = ? WHERE id = ?",
        (1 if enabled else 0, now, task_id)
    )
    conn.commit()
    conn.close()

    # Update cache
    if task_id in tasks_cache:
        tasks_cache[task_id]['enabled'] = enabled

    action = "enabled" if enabled else "disabled"
    logger.info(f"Task {task_dict['name']} {action}")

    return json.dumps({
        "success": True,
        "message": f"Task '{task_dict['name']}' {action}"
    })


@mcp.tool(task=True)
async def claudecron_get_history(
    task_id: Optional[str] = None,
    limit: int = 50,
    status: str = "all",
    ctx: Context = None,
    progress: Progress = Progress()
) -> str:
    """
    Get task execution history with full details including outputs and tool calls.

    Use this to see multiple executions of a task over time.
    For just the latest result, use claudecron_get_task_result instead.

    Args:
        task_id: Filter by specific task ID (optional, shows all tasks if not provided)
        limit: Maximum number of records to return (default: 50)
        status: Filter by execution status:
            - 'all': All executions
            - 'success': Only successful executions
            - 'failed': Only failed executions

    Returns:
        JSON with history array containing:
        - id: History record ID
        - task_id: Task ID
        - task_name: Task name
        - status: 'success' or 'failed'
        - output: Full task output/result
        - error: Error message if failed
        - tool_calls: List of MCP tools called
        - turns_used: AI conversation turns
        - mode_used: Execution mode
        - started_at: Start time
        - finished_at: End time
    """
    ensure_initialized()

    await progress.set_total(100)
    await progress.set_message("Fetching history...")

    if ctx:
        await ctx.info(f"Getting history (task_id: {task_id}, status: {status})")

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT h.*, t.name as task_name
        FROM history h
        LEFT JOIN tasks t ON h.task_id = t.id
        WHERE 1=1
    """
    params = []

    if task_id:
        query += " AND h.task_id = ?"
        params.append(task_id)

    if status == "success":
        query += " AND h.status = 'success'"
    elif status == "failed":
        query += " AND h.status = 'failed'"

    query += " ORDER BY h.started_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Parse JSON fields
    for h in history:
        if h.get('tool_calls'):
            try:
                h['tool_calls'] = json.loads(h['tool_calls'])
            except:
                pass

    await progress.increment(40)
    await progress.set_message(f"Found {len(history)} records")

    return json.dumps({"history": history, "count": len(history)}, default=str)


@mcp.tool()
async def claudecron_get_task_result(
    task_id: Optional[str] = None,
    task_name: Optional[str] = None,
    history_id: Optional[str] = None
) -> str:
    """
    Get the latest execution result for a task.

    This is the primary way to retrieve task output after running a subagent task.
    Returns the full output, any errors, tool calls made, and execution metadata.

    Args:
        task_id: Task ID (from claudecron_add_task response)
        task_name: Task name (alternative to task_id)
        history_id: Specific execution history ID (for specific run)

    Returns:
        JSON with:
        - status: 'success' or 'failed'
        - output: The AI subagent's response/result text
        - error: Error message if failed
        - tool_calls: List of MCP tools called during execution
        - turns_used: Number of AI conversation turns
        - mode_used: Execution mode ('mcp_client' or 'claude_cli')
        - started_at: Execution start time
        - finished_at: Execution end time
        - task_name: Name of the task

    Example:
        # After running a task
        result = claudecron_get_task_result(task_id="abc-123")
        # Returns: {"status": "success", "output": "Here is the documentation...", ...}
    """
    ensure_initialized()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Build query based on provided parameters
    if history_id:
        # Get specific execution by history ID
        cursor.execute("""
            SELECT h.*, t.name as task_name, t.prompt as task_prompt
            FROM history h
            LEFT JOIN tasks t ON h.task_id = t.id
            WHERE h.id = ?
        """, (history_id,))
    elif task_id:
        # Get latest execution for task_id
        cursor.execute("""
            SELECT h.*, t.name as task_name, t.prompt as task_prompt
            FROM history h
            LEFT JOIN tasks t ON h.task_id = t.id
            WHERE h.task_id = ?
            ORDER BY h.started_at DESC
            LIMIT 1
        """, (task_id,))
    elif task_name:
        # Find task by name and get latest execution
        cursor.execute("""
            SELECT h.*, t.name as task_name, t.prompt as task_prompt
            FROM history h
            JOIN tasks t ON h.task_id = t.id
            WHERE t.name = ?
            ORDER BY h.started_at DESC
            LIMIT 1
        """, (task_name,))
    else:
        conn.close()
        return json.dumps({
            "error": "Please provide task_id, task_name, or history_id"
        })

    row = cursor.fetchone()
    conn.close()

    if not row:
        return json.dumps({
            "error": "No execution found for this task",
            "task_id": task_id,
            "task_name": task_name
        })

    result = dict(row)

    # Parse JSON fields
    if result.get('tool_calls'):
        try:
            result['tool_calls'] = json.loads(result['tool_calls'])
        except:
            pass

    # Format response with most important fields first
    response = {
        "status": result.get('status'),
        "output": result.get('output', ''),
        "error": result.get('error'),
        "task_id": result.get('task_id'),
        "task_name": result.get('task_name'),
        "task_prompt": result.get('task_prompt'),
        "history_id": result.get('id'),
        "tool_calls": result.get('tool_calls', []),
        "turns_used": result.get('turns_used'),
        "mode_used": result.get('mode_used'),
        "started_at": result.get('started_at'),
        "finished_at": result.get('finished_at')
    }

    return json.dumps(response, default=str)


@mcp.tool()
async def claudecron_scheduler_status() -> str:
    """
    Get scheduler status and running tasks.

    Returns:
        JSON with scheduler status
    """
    from .scheduler import get_scheduler

    scheduler = get_scheduler()
    if not scheduler:
        return json.dumps({"status": "not_running"})

    return json.dumps({
        "status": "running" if scheduler.is_running() else "stopped",
        "running_tasks": list(scheduler.get_running_tasks()),
        "max_concurrent": scheduler.max_concurrent,
        "check_interval": scheduler.check_interval
    })


@mcp.tool()
async def claudecron_list_mcp_servers() -> str:
    """
    List registered MCP servers.

    Returns:
        JSON array of MCP servers
    """
    from .mcp_registry import get_registry

    registry = get_registry()
    if not registry:
        return json.dumps({"error": "Registry not initialized"})

    servers = await registry.list_servers(enabled_only=False)

    return json.dumps({
        "servers": [
            {
                "id": s.id,
                "name": s.name,
                "url": s.url,
                "transport": s.transport,
                "enabled": s.enabled,
                "health_status": s.health_status,
                "description": s.description
            }
            for s in servers
        ],
        "count": len(servers)
    })


@mcp.tool()
async def claudecron_add_mcp_server(
    name: str,
    url: str,
    transport: str = "http",
    description: Optional[str] = None
) -> str:
    """
    Add a new MCP server to registry.

    Args:
        name: Unique server name (e.g., 'email', 'bitrix')
        url: MCP server URL
        transport: Transport type ('http' or 'stdio')
        description: Optional description

    Returns:
        JSON with result
    """
    from .mcp_registry import get_registry, MCPServerConfig

    registry = get_registry()
    if not registry:
        return json.dumps({"error": "Registry not initialized"})

    server_id = f"manual-{name}"

    await registry.add_server(MCPServerConfig(
        id=server_id,
        name=name,
        url=url,
        transport=transport,
        description=description
    ))

    return json.dumps({
        "success": True,
        "message": f"MCP server '{name}' added",
        "server": {
            "id": server_id,
            "name": name,
            "url": url,
            "transport": transport
        }
    })


# Custom routes for health and info
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint."""
    from .scheduler import get_scheduler

    scheduler = get_scheduler()

    return JSONResponse({
        "status": "healthy",
        "version": __version__,
        "protocol": __protocol_version__,
        "proxy_configured": PROXY_URL is not None,
        "scheduler_running": scheduler.is_running() if scheduler else False
    })


@mcp.custom_route("/", methods=["GET"])
async def info(request):
    """Server info endpoint."""
    return JSONResponse({
        "name": "ClaudeCron MCP Server",
        "version": __version__,
        "protocol": __protocol_version__,
        "description": "Scheduled task automation for Claude Code with AI subagent support",
        "endpoints": {
            "mcp": "/mcp",
            "health": "/health"
        },
        "features": [
            "cron_scheduling",
            "bash_tasks",
            "subagent_mcp_client",
            "subagent_claude_cli",
            "mcp_registry"
        ]
    })


# For running directly
if __name__ == "__main__":
    import uvicorn
    import asyncio
    from starlette.applications import Starlette
    from starlette.routing import Mount

    async def main():
        """Run server with proper initialization and combined lifespan."""
        port = int(os.environ.get("PORT", 8080))

        # Create FastMCP HTTP app
        mcp_app = mcp.http_app(path="/mcp")

        # Create combined lifespan (scheduler + FastMCP)
        combined_lifespan = create_combined_lifespan(mcp_app)

        # Create Starlette app with combined lifespan
        app = Starlette(
            routes=[
                Mount("/", app=mcp_app),
            ],
            lifespan=combined_lifespan,
        )

        logger.info(f"Starting ClaudeCron on port {port}")

        # Run server
        config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(main())
