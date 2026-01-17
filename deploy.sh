#!/bin/bash
# =============================================================================
# Deploy script for Email MCP Server
# Protocol: MCP 2025-03-26 (Streamable HTTP)
# Deploys to remote server 217.199.253.8
# =============================================================================

set -e

# Configuration
REMOTE_HOST="217.199.253.8"
REMOTE_USER="root"
REMOTE_PASSWORD="a8ibcyC-QwPFer"
REMOTE_DIR="/opt/email-mcp-server"
CONTAINER_NAME="email-mcp-server"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Deploying Email MCP Server (Streamable HTTP)..."
echo "   Protocol: MCP 2025-03-26"
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
remote_copy "$LOCAL_DIR/Dockerfile" "$REMOTE_DIR/"
remote_copy "$LOCAL_DIR/docker-compose.yml" "$REMOTE_DIR/"
remote_copy "$LOCAL_DIR/pyproject.toml" "$REMOTE_DIR/"
remote_copy "$LOCAL_DIR/src" "$REMOTE_DIR/"
remote_copy "$LOCAL_DIR/imap-mcp-server" "$REMOTE_DIR/"

echo "🛑 Stopping existing container..."
remote_cmd "cd $REMOTE_DIR && docker-compose down 2>/dev/null || true"

echo "🔨 Building Docker image (multi-stage)..."
remote_cmd "cd $REMOTE_DIR && docker-compose build --no-cache"

echo "🚀 Starting container..."
remote_cmd "cd $REMOTE_DIR && docker-compose up -d"

echo "⏳ Waiting for server to initialize..."
sleep 15

echo "🔍 Checking health..."
HEALTH=$(remote_cmd "curl -s http://localhost:3008/health" || echo '{"status":"error"}')
echo "Health response: $HEALTH"

if echo "$HEALTH" | grep -q '"status":"ok"'; then
    echo ""
    echo "✅ Email MCP Server deployed successfully!"
    echo ""
    echo "📊 Server Info:"
    remote_cmd "curl -s http://localhost:3008/" | python3 -m json.tool 2>/dev/null || true
    echo ""
    echo "🔗 Access URLs:"
    echo "   - Health:  https://mcp.svsfinpro.ru/email/health"
    echo "   - Info:    https://mcp.svsfinpro.ru/email/"
    echo "   - MCP:     https://mcp.svsfinpro.ru/email/mcp"
    echo ""
    echo "📝 Claude Desktop config:"
    cat << 'EOF'
{
  "mcpServers": {
    "email": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.svsfinpro.ru/email/mcp"]
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
