# =============================================================================
# Dockerfile for Bitrix24 MCP Server
# Multi-stage build: Node.js server + Python FastMCP wrapper
# Protocol: MCP 2025-03-26 (Streamable HTTP)
# =============================================================================

# Stage 1: Build Node.js server
FROM node:20-alpine AS builder

WORKDIR /build

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY tsconfig.json ./
COPY src/ ./src/

# Build TypeScript
RUN npm run build

# Stage 2: Production image
FROM python:3.11-slim

WORKDIR /app

# Install Node.js and curl for healthcheck
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /app/bitrix-mcp-server/dist \
    && mkdir -p /app/src/bitrix_mcp

# Copy built Node.js server from builder
COPY --from=builder /build/dist /app/bitrix-mcp-server/dist
COPY --from=builder /build/node_modules /app/bitrix-mcp-server/node_modules
COPY --from=builder /build/package.json /app/bitrix-mcp-server/

# Install Python dependencies (FastMCP)
RUN pip install --no-cache-dir fastmcp uvicorn

# Copy Python FastMCP wrapper
COPY wrapper/bitrix_mcp/ /app/src/bitrix_mcp/

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=8080
ENV BITRIX_SERVER_PATH=/app/bitrix-mcp-server/dist/index.js
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run FastMCP server
CMD ["python", "-m", "bitrix_mcp.server"]
