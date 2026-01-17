# =============================================================================
# Email MCP Server - Multi-stage Dockerfile
# Protocol: MCP 2025-03-26 (Streamable HTTP)
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build imap-mcp-server (Node.js)
# -----------------------------------------------------------------------------
FROM node:20-alpine AS node-builder

WORKDIR /build

# Copy imap-mcp-server source
COPY imap-mcp-server/package*.json ./
RUN npm ci --production=false

COPY imap-mcp-server/ ./
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Python runtime with FastMCP
# -----------------------------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app

# Install Node.js runtime (required for imap-mcp-server)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy built imap-mcp-server from node-builder
COPY --from=node-builder /build/dist /app/imap-mcp-server/dist
COPY --from=node-builder /build/node_modules /app/imap-mcp-server/node_modules
COPY --from=node-builder /build/package.json /app/imap-mcp-server/

# Copy Python source code and config
COPY pyproject.toml ./
COPY src/ ./src/

# Create minimal README for hatchling
RUN echo "# Email MCP Server" > README.md

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Environment variables
ENV HOST=0.0.0.0
ENV PORT=8080
ENV IMAP_SERVER_PATH=/app/imap-mcp-server/dist/index.js
ENV LOG_LEVEL=INFO
ENV PYTHONUNBUFFERED=1

# Create directory for credentials
RUN mkdir -p /root/.imap-mcp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE 8080

# Run the server
CMD ["python", "-m", "email_mcp.server"]
