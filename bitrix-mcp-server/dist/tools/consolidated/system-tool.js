import { z } from 'zod';
const systemActionSchema = z.enum([
    'test_connection', 'get_users'
]).describe('System action');
export function registerSystemTool(server, bitrixService) {
    server.registerTool('bitrix_system', {
        description: `System utilities. Actions:
- test_connection: Test Bitrix24 API connection
- get_users: Get multiple users by IDs (requires userIds)`,
        inputSchema: {
            action: systemActionSchema,
            userIds: z.array(z.number()).optional().describe('User IDs for get_users'),
        }
    }, async (params) => {
        const { action } = params;
        switch (action) {
            case 'test_connection': {
                try {
                    const user = await bitrixService.getCurrentUser();
                    return {
                        content: [{
                                type: 'text',
                                text: JSON.stringify({
                                    success: true,
                                    connected: true,
                                    currentUser: {
                                        id: user.ID,
                                        name: `${user.NAME} ${user.LAST_NAME}`.trim(),
                                        email: user.EMAIL,
                                    },
                                    message: 'Successfully connected to Bitrix24',
                                }, null, 2)
                            }]
                    };
                }
                catch (error) {
                    return {
                        content: [{
                                type: 'text',
                                text: JSON.stringify({
                                    success: false,
                                    connected: false,
                                    error: error instanceof Error ? error.message : 'Unknown error',
                                }, null, 2)
                            }]
                    };
                }
            }
            case 'get_users': {
                if (!params.userIds?.length) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'userIds is required' }) }] };
                }
                const users = await bitrixService.getUsers({ ID: params.userIds });
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                count: users.length,
                                users: users.map(u => ({
                                    id: u.ID,
                                    name: `${u.NAME} ${u.LAST_NAME}`.trim(),
                                    email: u.EMAIL,
                                    department: u.UF_DEPARTMENT,
                                })),
                            }, null, 2)
                        }]
                };
            }
            default:
                return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: `Unknown action: ${action}` }) }] };
        }
    });
}
//# sourceMappingURL=system-tool.js.map