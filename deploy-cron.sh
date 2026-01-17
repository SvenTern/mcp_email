#!/bin/bash
# =============================================================================
# Deploy script for ClaudeCron MCP Server
# Protocol: MCP 2025-11-25 (Streamable HTTP)
# Version: 2.0.0
# Deploys to remote server 217.199.253.8
# =============================================================================

set -e

# Configuration
REMOTE_HOST="217.199.253.8"
REMOTE_USER="root"
REMOTE_PASSWORD="a8ibcyC-QwPFer"
REMOTE_DIR="/opt/cron-mcp-server"
CONTAINER_NAME="cron-mcp-server"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Deploying ClaudeCron MCP Server v2.0.0 (Streamable HTTP)..."
echo "   Protocol: MCP 2025-11-25"
echo "   Features: Mode A (MCP Client Hub) + Mode B (Claude CLI)"
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

echo "📁 Creating remote directories..."
remote_cmd "mkdir -p $REMOTE_DIR/data $REMOTE_DIR/config"

echo "📦 Copying project files to server..."
remote_copy "$LOCAL_DIR/cron-mcp-server/docker-compose.yml" "$REMOTE_DIR/"
remote_copy "$LOCAL_DIR/cron-mcp-server/wrapper" "$REMOTE_DIR/"
remote_copy "$LOCAL_DIR/cron-mcp-server/mcp-servers.yaml" "$REMOTE_DIR/"

# Copy .env if exists (contains ANTHROPIC_API_KEY)
if [ -f "$LOCAL_DIR/cron-mcp-server/.env" ]; then
    echo "📋 Copying .env configuration..."
    remote_copy "$LOCAL_DIR/cron-mcp-server/.env" "$REMOTE_DIR/"
else
    echo "⚠️  No .env file found. Make sure ANTHROPIC_API_KEY is set on the server."
fi

echo "🛑 Stopping existing container..."
remote_cmd "cd $REMOTE_DIR && docker-compose down 2>/dev/null || true"

echo "🔨 Building Docker image..."
remote_cmd "cd $REMOTE_DIR && docker-compose build --no-cache"

echo "🚀 Starting container..."
remote_cmd "cd $REMOTE_DIR && docker-compose up -d"

echo "⏳ Waiting for server to initialize (15s)..."
sleep 15

echo "🔍 Checking health..."
HEALTH=$(remote_cmd "curl -s http://localhost:3010/health" || echo '{"status":"error"}')
echo "Health response: $HEALTH"

if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    echo ""
    echo "✅ ClaudeCron MCP Server v2.0.0 deployed successfully!"
    echo ""
    echo "📊 Server Info:"
    remote_cmd "curl -s http://localhost:3010/" | python3 -m json.tool 2>/dev/null || true
    echo ""
    echo "🔗 Access URLs:"
    echo "   - Health:  https://mcp.svsfinpro.ru/cron/health"
    echo "   - Info:    https://mcp.svsfinpro.ru/cron/"
    echo "   - MCP:     https://mcp.svsfinpro.ru/cron/mcp"
    echo ""
    echo "📝 Claude Desktop config:"
    cat << 'EOF'
{
  "mcpServers": {
    "cron": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.svsfinpro.ru/cron/mcp"]
    }
  }
}
EOF
    echo ""
    echo "🧪 Test commands:"
    echo "   # Initialize MCP session"
    echo '   curl -X POST "https://mcp.svsfinpro.ru/cron/mcp" \'
    echo '     -H "Content-Type: application/json" \'
    echo '     -H "Accept: application/json, text/event-stream" \'
    echo '     -d '\''{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}'\'''
else
    echo ""
    echo "❌ Health check failed!"
    echo "📋 Container logs:"
    remote_cmd "docker logs --tail 100 $CONTAINER_NAME"
    exit 1
fi

echo ""
echo "🎉 Deployment complete!"
