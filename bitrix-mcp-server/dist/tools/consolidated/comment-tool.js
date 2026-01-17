import { z } from 'zod';
const commentActionSchema = z.enum([
    'add', 'list', 'update', 'delete'
]).describe('Action to perform on comment');
export function registerCommentTool(server, bitrixService) {
    server.registerTool('bitrix_comment', {
        description: `Task comment management. Actions:
- add: Add comment (requires taskId, text)
- list: List comments (requires taskId)
- update: Update comment (requires taskId, commentId, text)
- delete: Delete comment (requires taskId, commentId)`,
        inputSchema: {
            action: commentActionSchema,
            taskId: z.number().describe('Task ID'),
            commentId: z.number().optional().describe('Comment ID (required for update/delete)'),
            text: z.string().optional().describe('Comment text (required for add/update)'),
        }
    }, async (params) => {
        const { action, taskId } = params;
        switch (action) {
            case 'add': {
                if (!params.text) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'text is required' }) }] };
                }
                const commentId = await bitrixService.addComment(taskId, { POST_MESSAGE: params.text });
                return { content: [{ type: 'text', text: JSON.stringify({ success: true, taskId, commentId }) }] };
            }
            case 'list': {
                const comments = await bitrixService.getComments(taskId);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                taskId,
                                count: comments.length,
                                comments: comments.map(c => ({
                                    id: c.ID,
                                    authorId: c.AUTHOR_ID,
                                    authorName: c.AUTHOR_NAME,
                                    text: c.POST_MESSAGE,
                                    date: c.POST_DATE,
                                })),
                            }, null, 2)
                        }]
                };
            }
            case 'update': {
                if (!params.commentId || !params.text) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'commentId and text are required' }) }] };
                }
                const success = await bitrixService.updateComment(taskId, params.commentId, { POST_MESSAGE: params.text });
                return { content: [{ type: 'text', text: JSON.stringify({ success, taskId, commentId: params.commentId }) }] };
            }
            case 'delete': {
                if (!params.commentId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'commentId is required' }) }] };
                }
                const success = await bitrixService.deleteComment(taskId, params.commentId);
                return { content: [{ type: 'text', text: JSON.stringify({ success, taskId, commentId: params.commentId }) }] };
            }
            default:
                return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: `Unknown action: ${action}` }) }] };
        }
    });
}
//# sourceMappingURL=comment-tool.js.map