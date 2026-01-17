import { z } from 'zod';
const timeActionSchema = z.enum([
    'add', 'list', 'update', 'delete'
]).describe('Action to perform on time record');
export function registerTimeTool(server, bitrixService) {
    server.registerTool('bitrix_time', {
        description: `Task time tracking management. Actions:
- add: Add time record (requires taskId, seconds)
- list: List time records (requires taskId)
- update: Update record (requires taskId, recordId)
- delete: Delete record (requires taskId, recordId)`,
        inputSchema: {
            action: timeActionSchema,
            taskId: z.number().describe('Task ID'),
            recordId: z.number().optional().describe('Time record ID (required for update/delete)'),
            seconds: z.number().optional().describe('Time spent in seconds (required for add)'),
            comment: z.string().optional().describe('Comment for time record'),
            dateStart: z.string().optional().describe('Start date/time'),
            dateStop: z.string().optional().describe('Stop date/time'),
        }
    }, async (params) => {
        const { action, taskId } = params;
        switch (action) {
            case 'add': {
                if (params.seconds === undefined) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'seconds is required' }) }] };
                }
                const recordId = await bitrixService.addElapsedTime(taskId, {
                    SECONDS: params.seconds,
                    COMMENT_TEXT: params.comment
                });
                return { content: [{ type: 'text', text: JSON.stringify({ success: true, taskId, recordId, seconds: params.seconds }) }] };
            }
            case 'list': {
                const records = await bitrixService.getElapsedTime(taskId);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                taskId,
                                count: records.length,
                                totalSeconds: records.reduce((sum, r) => sum + (r.SECONDS || 0), 0),
                                records: records.map(r => ({
                                    id: r.ID,
                                    userId: r.USER_ID,
                                    seconds: r.SECONDS,
                                    comment: r.COMMENT_TEXT,
                                    dateStart: r.DATE_START,
                                    dateStop: r.DATE_STOP,
                                    createdDate: r.CREATED_DATE,
                                })),
                            }, null, 2)
                        }]
                };
            }
            case 'update': {
                if (!params.recordId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'recordId is required' }) }] };
                }
                const fields = {};
                if (params.seconds !== undefined)
                    fields.SECONDS = params.seconds;
                if (params.comment)
                    fields.COMMENT_TEXT = params.comment;
                const success = await bitrixService.updateElapsedTime(taskId, params.recordId, fields);
                return { content: [{ type: 'text', text: JSON.stringify({ success, taskId, recordId: params.recordId }) }] };
            }
            case 'delete': {
                if (!params.recordId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'recordId is required' }) }] };
                }
                const success = await bitrixService.deleteElapsedTime(taskId, params.recordId);
                return { content: [{ type: 'text', text: JSON.stringify({ success, taskId, recordId: params.recordId }) }] };
            }
            default:
                return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: `Unknown action: ${action}` }) }] };
        }
    });
}
//# sourceMappingURL=time-tool.js.map