#!/bin/bash
# =============================================================================
# Deploy script for Bitrix24 MCP Server
# Protocol: MCP 2025-11-25 (Streamable HTTP with Background Tasks)
# Deploys to remote server 217.199.253.8
# =============================================================================

set -e

# Configuration
REMOTE_HOST="217.199.253.8"
REMOTE_USER="root"
REMOTE_PASSWORD="a8ibcyC-QwPFer"
REMOTE_DIR="/opt/bitrix-mcp-server"
CONTAINER_NAME="bitrix-mcp-server"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Deploying Bitrix24 MCP Server (Streamable HTTP)..."
echo "   Protocol: MCP 2025-11-25"
echo "   Target: $REMOTE_HOST"
echo ""

# Function to run remote commands
remote_cmd() {
    sshpass -p "$REMOTE_PASSWORD" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "$1"
}

# Function to copy files
remote_copy() {
    sshpass -p "$REMOTE_PASSWORD" scp -o StrictHostKeyChecking=no -r "$1" "$REMOTE_USER@$REMOTE_HOST:$2"
}

echo "📁 Creating remote directory..."
remote_cmd "mkdir -p $REMOTE_DIR"

echo "📦 Copying project files to server..."
remote_copy "$LOCAL_DIR/bitrix-mcp-server/Dockerfile" "$REMOTE_DIR/"
remote_copy "$LOCAL_DIR/bitrix-mcp-server/package.json" "$REMOTE_DIR/"
remote_copy "$LOCAL_DIR/bitrix-mcp-server/package-lock.json" "$REMOTE_DIR/"
remote_copy "$LOCAL_DIR/bitrix-mcp-server/tsconfig.json" "$REMOTE_DIR/"
remote_copy "$LOCAL_DIR/bitrix-mcp-server/src" "$REMOTE_DIR/"
remote_copy "$LOCAL_DIR/bitrix-mcp-server/dist" "$REMOTE_DIR/"
remote_copy "$LOCAL_DIR/bitrix-mcp-server/wrapper" "$REMOTE_DIR/"

# Copy docker-compose from root (it has bitrix-mcp service)
echo "📦 Creating docker-compose.yml for bitrix..."
remote_cmd "cat > $REMOTE_DIR/docker-compose.yml << 'EOF'
version: '3.8'

services:
  bitrix-mcp:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: bitrix-mcp-server
    ports:
      - \"3009:8080\"
    environment:
      - BITRIX24_WEBHOOK_URL=\${BITRIX24_WEBHOOK_URL}
    healthcheck:
      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:8080/health\"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
EOF"

# Copy .env if exists
if [ -f "$LOCAL_DIR/.env" ]; then
    echo "📦 Copying .env file..."
    remote_copy "$LOCAL_DIR/.env" "$REMOTE_DIR/"
fi

echo "🛑 Stopping existing container..."
remote_cmd "cd $REMOTE_DIR && docker-compose down 2>/dev/null || true"

echo "🔨 Building Docker image..."
remote_cmd "cd $REMOTE_DIR && docker-compose build --no-cache"

echo "🚀 Starting container..."
remote_cmd "cd $REMOTE_DIR && docker-compose up -d"

echo "⏳ Waiting for server to initialize..."
sleep 15

echo "🔍 Checking health..."
HEALTH=$(remote_cmd "curl -s http://localhost:3009/health" || echo '{"status":"error"}')
echo "Health response: $HEALTH"

if echo "$HEALTH" | grep -q '"status":"ok"'; then
    echo ""
    echo "✅ Bitrix24 MCP Server deployed successfully!"
    echo ""
    echo "📊 Server Info:"
    remote_cmd "curl -s http://localhost:3009/" | python3 -m json.tool 2>/dev/null || true
    echo ""
    echo "🔗 Access URLs:"
    echo "   - Health:  https://mcp.svsfinpro.ru/bitrix/health"
    echo "   - Info:    https://mcp.svsfinpro.ru/bitrix/"
    echo "   - MCP:     https://mcp.svsfinpro.ru/bitrix/mcp"
    echo ""
    echo "📝 Claude Desktop config:"
    cat << 'EOF'
{
  "mcpServers": {
    "bitrix": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.svsfinpro.ru/bitrix/mcp"]
    }
  }
}
EOF
else
    echo ""
    echo "❌ Health check failed!"
    echo "📋 Container logs:"
    remote_cmd "docker logs --tail 100 $CONTAINER_NAME"
    exit 1
fi

echo ""
echo "🎉 Deployment complete!"
