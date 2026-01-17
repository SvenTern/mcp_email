import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import dotenv from 'dotenv';
import { BitrixService } from './services/bitrix-service.js';
import { registerTools } from './tools/index.js';
// Load environment variables
dotenv.config();
// Silence any package version output to stdout
const originalWrite = process.stdout.write.bind(process.stdout);
process.stdout.write = function (chunk, encoding, callback) {
    // Only allow JSON-RPC messages through
    if (typeof chunk === 'string' && (chunk.startsWith('{') || chunk === '\n')) {
        return originalWrite(chunk, encoding, callback);
    }
    return true;
};
// Validate webhook URL
const webhookUrl = process.env.BITRIX24_WEBHOOK_URL;
if (!webhookUrl) {
    console.error('ERROR: BITRIX24_WEBHOOK_URL environment variable is required');
    console.error('Example: BITRIX24_WEBHOOK_URL=https://portal.bitrix24.ru/rest/1/abc123xyz/');
    process.exit(1);
}
// Create MCP server
const server = new McpServer({
    name: 'bitrix-mcp-server',
    version: '1.0.0',
});
// Create Bitrix24 service
const bitrixService = new BitrixService({
    webhookUrl,
    timeout: parseInt(process.env.BITRIX24_TIMEOUT || '30000', 10),
});
// Register all tools
registerTools(server, bitrixService);
async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('Bitrix24 MCP Server started');
    const maskedUrl = webhookUrl ? webhookUrl.replace(/\/rest\/\d+\/[^/]+\/?$/, '/rest/***/***/') : 'not set';
    console.error(`Webhook URL: ${maskedUrl}`);
}
main().catch((error) => {
    console.error('Server error:', error);
    process.exit(1);
});
//# sourceMappingURL=index.js.map