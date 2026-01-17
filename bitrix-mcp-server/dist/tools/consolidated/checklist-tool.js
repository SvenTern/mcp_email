import { z } from 'zod';
const checklistActionSchema = z.enum([
    'add', 'list', 'update', 'delete', 'complete', 'renew'
]).describe('Action to perform on checklist');
export function registerChecklistTool(server, bitrixService) {
    server.registerTool('bitrix_checklist', {
        description: `Task checklist management. Actions:
- add: Add checklist item (requires taskId, title)
- list: List checklist items (requires taskId)
- update: Update item (requires taskId, checklistId, title)
- delete: Delete item (requires taskId, checklistId)
- complete: Mark item complete (requires taskId, checklistId)
- renew: Mark item incomplete (requires taskId, checklistId)`,
        inputSchema: {
            action: checklistActionSchema,
            taskId: z.number().describe('Task ID'),
            checklistId: z.number().optional().describe('Checklist item ID (required for update/delete/complete/renew)'),
            title: z.string().optional().describe('Checklist item title (required for add/update)'),
            isComplete: z.boolean().optional().describe('Completion status'),
        }
    }, async (params) => {
        const { action, taskId } = params;
        switch (action) {
            case 'add': {
                if (!params.title) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'title is required' }) }] };
                }
                const checklistId = await bitrixService.addChecklistItem(taskId, { TITLE: params.title });
                return { content: [{ type: 'text', text: JSON.stringify({ success: true, taskId, checklistId }) }] };
            }
            case 'list': {
                const items = await bitrixService.getChecklistItems(taskId);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                taskId,
                                count: items.length,
                                items: items.map(item => ({
                                    id: item.ID,
                                    title: item.TITLE,
                                    isComplete: item.IS_COMPLETE === 'Y',
                                    sortIndex: item.SORT_INDEX,
                                })),
                            }, null, 2)
                        }]
                };
            }
            case 'update': {
                if (!params.checklistId || !params.title) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'checklistId and title are required' }) }] };
                }
                const success = await bitrixService.updateChecklistItem(taskId, params.checklistId, { TITLE: params.title });
                return { content: [{ type: 'text', text: JSON.stringify({ success, taskId, checklistId: params.checklistId }) }] };
            }
            case 'delete': {
                if (!params.checklistId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'checklistId is required' }) }] };
                }
                const success = await bitrixService.deleteChecklistItem(taskId, params.checklistId);
                return { content: [{ type: 'text', text: JSON.stringify({ success, taskId, checklistId: params.checklistId }) }] };
            }
            case 'complete': {
                if (!params.checklistId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'checklistId is required' }) }] };
                }
                const success = await bitrixService.completeChecklistItem(taskId, params.checklistId);
                return { content: [{ type: 'text', text: JSON.stringify({ success, taskId, checklistId: params.checklistId, isComplete: true }) }] };
            }
            case 'renew': {
                if (!params.checklistId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'checklistId is required' }) }] };
                }
                const success = await bitrixService.renewChecklistItem(taskId, params.checklistId);
                return { content: [{ type: 'text', text: JSON.stringify({ success, taskId, checklistId: params.checklistId, isComplete: false }) }] };
            }
            default:
                return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: `Unknown action: ${action}` }) }] };
        }
    });
}
//# sourceMappingURL=checklist-tool.js.map