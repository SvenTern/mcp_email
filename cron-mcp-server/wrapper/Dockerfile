# ClaudeCron MCP Server - MCP 2025-11-25
# Supports: Mode A (MCP Client Hub) + Mode B (Claude Code CLI)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x (required for Claude Code CLI - Mode B)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally (Mode B support)
# Note: Requires ANTHROPIC_API_KEY at runtime
RUN npm install -g @anthropic-ai/claude-code

# Verify installations
RUN node --version && npm --version && claude --version || echo "Claude CLI installed"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY cron_mcp/ ./cron_mcp/

# Create data directory
RUN mkdir -p /app/data

# Create Claude config directory (for Mode B)
RUN mkdir -p /root/.claude

# Environment
ENV PORT=3010
ENV PYTHONUNBUFFERED=1
ENV CLAUDECRON_DB_PATH=/app/data/tasks.db

# Subagent configuration
ENV SUBAGENT_DEFAULT_MODE=auto
ENV SUBAGENT_TIMEOUT=300
ENV SUBAGENT_MAX_TURNS=10
ENV CLAUDE_MODEL=claude-sonnet-4-20250514

# Claude CLI path (Mode B)
ENV CLAUDE_CLI_PATH=/usr/bin/claude

# Expose port (note: with network_mode: host this is informational only)
EXPOSE 3010

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3010/health || exit 1

# Run server
CMD ["python", "-m", "cron_mcp.server"]
