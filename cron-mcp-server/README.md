# ClaudeCron MCP Server

Scheduled task automation for Claude Code with AI subagent support.

## Features

- **Cron Scheduling**: Run tasks on a schedule using standard cron expressions
- **Bash Tasks**: Execute shell commands
- **AI Subagent Tasks**: Execute AI-powered tasks with access to MCP tools
- **Two Execution Modes**:
  - **Mode A (MCP Client Hub)**: Direct connection to MCP servers + Claude API
  - **Mode B (Claude Code CLI)**: Delegate to Claude Code CLI
- **MCP Registry**: Centralized management of MCP server connections
- **Recursion Protection**: Prevent infinite subagent loops

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      ClaudeCron Server                           │
├─────────────────────────────────────────────────────────────────┤
│  Cron Scheduler                                                  │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────┐                                                │
│  │ Task Runner │                                                │
│  └──────┬──────┘                                                │
│         │                                                        │
│    ┌────┴────┬─────────┐                                        │
│    ▼         ▼         ▼                                        │
│  bash    subagent   subagent                                    │
│          (Mode A)   (Mode B)                                    │
│            │           │                                         │
│            ▼           ▼                                         │
│  ┌──────────────┐  ┌─────────────────┐                          │
│  │MCP Client Hub│  │ Claude Code CLI │                          │
│  └──────┬───────┘  └────────┬────────┘                          │
│         │                   │                                    │
│         ▼                   ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              MCP Servers (external)                      │   │
│  │  - Email, Bitrix24, Telegram, etc.                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

### Docker (Recommended)

```bash
cd cron-mcp-server
docker-compose up -d
```

### Manual

```bash
cd cron-mcp-server/wrapper
pip install -r requirements.txt
python -m cron_mcp.server
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3010` | Server port |
| `CLAUDECRON_DB_PATH` | `/app/data/tasks.db` | SQLite database path |
| `ANTHROPIC_API_KEY` | - | Required for Claude API access |
| `SUBAGENT_DEFAULT_MODE` | `auto` | Default mode: `mcp_client`, `claude_cli`, or `auto` |
| `SUBAGENT_TIMEOUT` | `300` | Task timeout in seconds |
| `SUBAGENT_MAX_TURNS` | `10` | Maximum agentic loop iterations |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Claude model to use |
| `HTTP_PROXY` / `HTTPS_PROXY` | - | Proxy for API access |
| `MCP_SERVER_EMAIL` | - | Email MCP server URL |
| `MCP_SERVER_BITRIX` | - | Bitrix24 MCP server URL |

### MCP Servers Configuration

You can configure MCP servers in three ways:

1. **Environment variables**: `MCP_SERVER_<NAME>=<URL>`
2. **YAML config file**: `/app/config/mcp-servers.yaml`
3. **Runtime API**: `claudecron_add_mcp_server` tool

## MCP Tools

### claudecron_add_task

Create a new scheduled task.

```json
{
  "name": "daily-report",
  "type": "subagent",
  "schedule": "0 9 * * *",
  "prompt": "Generate daily sales report and send via email",
  "subagent_mode": "mcp_client",
  "mcp_servers": ["https://mcp.example.com/email/mcp"],
  "max_turns": 10
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Task name |
| `type` | string | Yes | `bash` or `subagent` |
| `schedule` | string | No | Cron expression (5 fields) |
| `command` | string | For bash | Shell command to execute |
| `prompt` | string | For subagent | AI prompt |
| `subagent_mode` | string | No | `mcp_client`, `claude_cli`, or `auto` |
| `mcp_servers` | array | No | MCP server URLs or names |
| `allowed_tools` | array | No | Allowed tools (for CLI mode) |
| `system_prompt` | string | No | Custom system prompt |
| `max_turns` | integer | No | Max agentic loop turns |
| `timezone` | string | No | Timezone (default: UTC) |
| `enabled` | boolean | No | Task enabled (default: true) |

### claudecron_list_tasks

List all scheduled tasks.

```json
{
  "status": "all"  // "all", "enabled", or "disabled"
}
```

### claudecron_run_task

Run a task immediately.

```json
{
  "task_id": "uuid-of-task"
}
```

### claudecron_delete_task

Delete a task.

```json
{
  "task_id": "uuid-of-task"
}
```

### claudecron_toggle_task

Enable or disable a task.

```json
{
  "task_id": "uuid-of-task",
  "enabled": false
}
```

### claudecron_get_history

Get task execution history.

```json
{
  "task_id": "uuid-of-task",  // optional
  "limit": 50,
  "status": "all"  // "all", "success", or "failed"
}
```

### claudecron_scheduler_status

Get scheduler status and running tasks.

### claudecron_list_mcp_servers

List registered MCP servers.

### claudecron_add_mcp_server

Add a new MCP server to registry.

```json
{
  "name": "telegram",
  "url": "https://mcp.example.com/telegram/mcp",
  "transport": "http",
  "description": "Telegram bot integration"
}
```

## Examples

### Bash Task

```json
{
  "name": "cleanup-logs",
  "type": "bash",
  "schedule": "0 2 * * *",
  "command": "find /var/log -name '*.log' -mtime +7 -delete"
}
```

### Subagent Task (Mode A - MCP Client)

```json
{
  "name": "daily-leads-report",
  "type": "subagent",
  "schedule": "0 9 * * *",
  "prompt": "Get new leads from Bitrix24, create a summary report, and send it to manager@company.com",
  "subagent_mode": "mcp_client",
  "mcp_servers": [
    "https://mcp.example.com/bitrix/mcp",
    "https://mcp.example.com/email/mcp"
  ],
  "timezone": "Europe/Moscow",
  "max_turns": 15
}
```

### Subagent Task (Mode B - Claude CLI)

```json
{
  "name": "weekly-summary",
  "type": "subagent",
  "schedule": "0 18 * * 5",
  "prompt": "Analyze git commits for the week and send a summary to Telegram",
  "subagent_mode": "claude_cli",
  "allowed_tools": [
    "mcp__git__log",
    "mcp__telegram__send_message"
  ]
}
```

## Testing

```bash
cd cron-mcp-server
pip install -r wrapper/requirements.txt
pytest tests/ -v
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp` | POST | MCP protocol endpoint |
| `/health` | GET | Health check |
| `/` | GET | Server info |

## Mode Comparison

| Criteria | Mode A: MCP Client Hub | Mode B: Claude Code CLI |
|----------|------------------------|-------------------------|
| Complexity | Higher | Lower |
| Dependencies | anthropic, httpx | Claude CLI |
| Control | Full | Limited |
| Tool call logging | Detailed | Via stdout |
| Docker support | Yes | Yes (CLI pre-installed) |
| Flexibility | High | Medium |

## Security

- **Recursion Protection**: Subagents cannot call `claudecron_*` tools
- **Max Turns Limit**: Prevents infinite agentic loops
- **Timeout**: Configurable execution timeout

## License

MIT
