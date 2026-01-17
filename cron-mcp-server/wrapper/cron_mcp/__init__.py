"""
ClaudeCron MCP Server - Streamable HTTP transport (MCP 2025-11-25)

A FastMCP-based server for scheduled task automation in Claude Code.

Features (MCP 2025-11-25):
- Background tasks for long-running operations (SEP-1686)
- Progress tracking for task execution
- SSE polling with event resumability (SEP-1699)
- Cron scheduling, file watching, AI subagent tasks
"""

__version__ = "1.0.0"
__protocol_version__ = "2025-11-25"
