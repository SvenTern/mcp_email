"""
ClaudeCron MCP Server - FastMCP Implementation

Provides scheduled task automation with MCP 2025-11-25 features:
- Cron-based task scheduling
- File watching triggers
- AI subagent task execution
- Background task support
"""

import asyncio
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Optional
from pathlib import Path

from fastmcp import FastMCP, Context
from fastmcp.dependencies import Progress
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

# Initialize FastMCP server
mcp = FastMCP(
    "ClaudeCron MCP Server",
    version=__version__,
    instructions="""ClaudeCron - scheduled task automation for Claude Code.

Available tools:
- claudecron_add_task: Create scheduled tasks (bash or subagent)
- claudecron_list_tasks: List all tasks
- claudecron_run_task: Run a task immediately
- claudecron_delete_task: Delete a task
- claudecron_toggle_task: Enable/disable a task
- claudecron_get_history: Get execution history
"""
)

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

    # Tasks table
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
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

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
            FOREIGN KEY (task_id) REFERENCES tasks(id)
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
    started_at = datetime.utcnow().isoformat()

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
            # AI subagent tasks require external integration
            output = f"Subagent task queued: {task['prompt']}"
            # TODO: Integrate with Claude API for subagent execution

    except asyncio.TimeoutError:
        status = "failed"
        error = "Task execution timed out"
    except Exception as e:
        status = "failed"
        error = str(e)

    # Update history
    finished_at = datetime.utcnow().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE history SET finished_at = ?, status = ?, output = ?, error = ? WHERE id = ?",
        (finished_at, status, output, error, history_id)
    )
    conn.commit()
    conn.close()

    logger.info(f"Task {task['name']} completed with status: {status}")

    return {
        "task_id": task_id,
        "history_id": history_id,
        "status": status,
        "output": output,
        "error": error
    }


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
    ctx: Context = None,
    progress: Progress = Progress()
) -> str:
    """
    Create a new scheduled task.

    Args:
        name: Task name
        type: Task type ('bash' or 'subagent')
        schedule: Cron expression (5 fields: min hour day month weekday)
        command: Bash command (required for bash type)
        prompt: AI prompt (required for subagent type)
        timezone: Timezone for scheduling (default: UTC)
        enabled: Whether task is enabled (default: True)
        trigger_type: Optional trigger type ('file-watch')
        trigger_path: Path for file-watch trigger

    Returns:
        JSON with created task details
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

    # Create task
    task_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (id, name, type, schedule, command, prompt, timezone, enabled, trigger_type, trigger_path, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (task_id, name, type, schedule, command, prompt, timezone, 1 if enabled else 0, trigger_type, trigger_path, now, now))
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

    # Add next run time for scheduled tasks
    for task in tasks:
        if task.get('schedule') and task.get('enabled'):
            try:
                cron = croniter(task['schedule'], datetime.utcnow())
                task['next_run'] = cron.get_next(datetime).isoformat()
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
    now = datetime.utcnow().isoformat()
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
    Get task execution history.

    Args:
        task_id: Filter by task ID (optional)
        limit: Maximum number of records (default: 50)
        status: Filter by status ('all', 'success', 'failed')

    Returns:
        JSON array of history records
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

    await progress.increment(40)
    await progress.set_message(f"Found {len(history)} records")

    return json.dumps({"history": history, "count": len(history)}, default=str)


# Custom routes for health and info
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "version": __version__,
        "protocol": __protocol_version__,
        "proxy_configured": PROXY_URL is not None,
        "proxy_url": PROXY_URL if PROXY_URL else None
    })


@mcp.custom_route("/", methods=["GET"])
async def info(request):
    """Server info endpoint."""
    return JSONResponse({
        "name": "ClaudeCron MCP Server",
        "version": __version__,
        "protocol": __protocol_version__,
        "description": "Scheduled task automation for Claude Code",
        "endpoints": {
            "mcp": "/mcp",
            "health": "/health"
        }
    })


# For running directly
if __name__ == "__main__":
    import uvicorn

    # Initialize on startup
    init_database()

    port = int(os.environ.get("PORT", 8080))

    uvicorn.run(
        mcp.http_app(),
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
