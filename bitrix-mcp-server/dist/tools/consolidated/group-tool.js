import { z } from 'zod';
const groupActionSchema = z.enum([
    'list', 'get', 'members', 'my', 'search', 'access_check'
]).describe('Action to perform on workgroups');
export function registerGroupTool(server, bitrixService) {
    server.registerTool('bitrix_group', {
        description: `Workgroup management. Actions:
- list: List all workgroups
- get: Get group by ID (requires groupId)
- members: Get group members (requires groupId)
- my: Get current user's groups
- search: Search groups (requires query)
- access_check: Check feature access (requires groupId, feature)`,
        inputSchema: {
            action: groupActionSchema,
            groupId: z.number().optional().describe('Group ID'),
            query: z.string().optional().describe('Search query'),
            feature: z.string().optional().describe('Feature to check (blog, files, tasks, calendar, etc.)'),
            operation: z.string().optional().describe('Operation to check (view, write_post, etc.)'),
            filter: z.record(z.unknown()).optional().describe('Filter conditions'),
            start: z.number().optional().describe('Pagination offset'),
        }
    }, async (params) => {
        const { action } = params;
        switch (action) {
            case 'list': {
                const result = await bitrixService.getGroups(params.filter, params.start);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                count: result.groups.length,
                                total: result.total,
                                next: result.next,
                                groups: result.groups.map(g => ({
                                    id: g.ID,
                                    name: g.NAME,
                                    description: g.DESCRIPTION,
                                    active: g.ACTIVE === 'Y',
                                    visible: g.VISIBLE === 'Y',
                                    opened: g.OPENED === 'Y',
                                    membersCount: g.NUMBER_OF_MEMBERS,
                                })),
                            }, null, 2)
                        }]
                };
            }
            case 'get': {
                if (!params.groupId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'groupId is required' }) }] };
                }
                const group = await bitrixService.getGroupById(params.groupId);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                group: group ? {
                                    id: group.ID,
                                    name: group.NAME,
                                    description: group.DESCRIPTION,
                                    active: group.ACTIVE === 'Y',
                                    visible: group.VISIBLE === 'Y',
                                    opened: group.OPENED === 'Y',
                                    ownerId: group.OWNER_ID,
                                    membersCount: group.NUMBER_OF_MEMBERS,
                                    dateCreate: group.DATE_CREATE,
                                } : null,
                            }, null, 2)
                        }]
                };
            }
            case 'members': {
                if (!params.groupId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'groupId is required' }) }] };
                }
                const members = await bitrixService.getGroupMembers(params.groupId);
                const roleNames = {
                    'A': 'owner',
                    'E': 'moderator',
                    'K': 'member',
                };
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                groupId: params.groupId,
                                count: members.length,
                                members: members.map(m => ({
                                    userId: m.USER_ID,
                                    role: roleNames[m.ROLE] || m.ROLE,
                                    roleCode: m.ROLE,
                                })),
                            }, null, 2)
                        }]
                };
            }
            case 'my': {
                const groups = await bitrixService.getMyGroups();
                const roleNames = {
                    'A': 'owner',
                    'E': 'moderator',
                    'K': 'member',
                };
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                count: groups.length,
                                myGroups: groups.map(g => ({
                                    id: g.GROUP_ID,
                                    name: g.GROUP_NAME,
                                    role: roleNames[g.ROLE] || g.ROLE,
                                    roleCode: g.ROLE,
                                })),
                            }, null, 2)
                        }]
                };
            }
            case 'search': {
                if (!params.query) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'query is required' }) }] };
                }
                // Use getWorkgroups with filter for search
                const result = await bitrixService.getWorkgroups({ '%NAME': params.query });
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                query: params.query,
                                count: result.groups.length,
                                groups: result.groups.map(g => ({
                                    id: g.ID,
                                    name: g.NAME,
                                    description: g.DESCRIPTION,
                                    membersCount: g.NUMBER_OF_MEMBERS,
                                })),
                            }, null, 2)
                        }]
                };
            }
            case 'access_check': {
                if (!params.groupId || !params.feature) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'groupId and feature are required' }) }] };
                }
                const operation = params.operation || 'view';
                const hasAccess = await bitrixService.checkGroupAccess(params.groupId, params.feature, operation);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                groupId: params.groupId,
                                feature: params.feature,
                                operation,
                                hasAccess,
                            }, null, 2)
                        }]
                };
            }
            default:
                return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: `Unknown action: ${action}` }) }] };
        }
    });
}
//# sourceMappingURL=group-tool.js.map