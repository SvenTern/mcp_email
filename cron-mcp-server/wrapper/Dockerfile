# ClaudeCron MCP Server - MCP 2025-11-25
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY cron_mcp/ ./cron_mcp/

# Create data directory
RUN mkdir -p /app/data

# Environment
ENV PORT=3010
ENV PYTHONUNBUFFERED=1
ENV CLAUDECRON_DB_PATH=/app/data/tasks.db

# Expose port (note: with network_mode: host this is informational only)
EXPOSE 3010

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3010/health || exit 1

# Run server
CMD ["python", "-m", "cron_mcp.server"]
