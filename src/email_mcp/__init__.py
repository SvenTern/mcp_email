"""
Email MCP Server - Streamable HTTP transport (MCP 2025-11-25)

A FastMCP-based wrapper for nikolausm/imap-mcp-server providing
HTTP transport for Claude Web and remote access.

Features (MCP 2025-11-25):
- Background tasks for long-running operations (SEP-1686)
- Progress tracking for bulk operations
- SSE polling with event resumability (SEP-1699)
"""

__version__ = "3.0.0"
__protocol_version__ = "2025-11-25"
