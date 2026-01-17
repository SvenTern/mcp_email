import { z } from 'zod';
const taskActionSchema = z.enum([
    'create', 'get', 'list', 'update', 'delete',
    'start', 'pause', 'complete', 'defer', 'renew',
    'approve', 'disapprove', 'delegate',
    'attach_files', 'counters', 'history',
    'favorite_add', 'favorite_remove', 'get_fields'
]).describe('Action to perform on task');
export function registerTaskTool(server, bitrixService) {
    server.registerTool('bitrix_task', {
        description: `Task management tool. Actions:
- create: Create new task (requires title, responsibleId)
- get: Get task by ID (requires taskId)
- list: List tasks with filters
- update: Update task (requires taskId)
- delete: Delete task (requires taskId)
- start/pause/complete/defer/renew: Change task status (requires taskId)
- approve/disapprove: Accept/reject completed task (requires taskId)
- delegate: Delegate task (requires taskId, newResponsibleId)
- attach_files: Attach files (requires taskId, fileIds)
- counters: Get task counters
- history: Get task history (requires taskId)
- favorite_add/favorite_remove: Manage favorites (requires taskId)
- get_fields: Get available task fields`,
        inputSchema: {
            action: taskActionSchema,
            taskId: z.number().optional().describe('Task ID (required for most actions except create, list, counters, get_fields)'),
            title: z.string().optional().describe('Task title (required for create)'),
            description: z.string().optional().describe('Task description'),
            responsibleId: z.number().optional().describe('Responsible user ID (required for create)'),
            deadline: z.string().optional().describe('Deadline in ISO format'),
            startDatePlan: z.string().optional().describe('Planned start date'),
            endDatePlan: z.string().optional().describe('Planned end date'),
            priority: z.number().optional().describe('Priority: 0=low, 1=normal, 2=high'),
            groupId: z.number().optional().describe('Workgroup ID'),
            parentId: z.number().optional().describe('Parent task ID'),
            accomplices: z.array(z.number()).optional().describe('Accomplice user IDs'),
            auditors: z.array(z.number()).optional().describe('Auditor user IDs'),
            tags: z.array(z.string()).optional().describe('Task tags'),
            allowChangeDeadline: z.boolean().optional().describe('Allow deadline changes'),
            taskControl: z.boolean().optional().describe('Enable task control'),
            allowTimeTracking: z.boolean().optional().describe('Enable time tracking'),
            filter: z.record(z.unknown()).optional().describe('Filter conditions for list'),
            select: z.array(z.string()).optional().describe('Fields to return'),
            order: z.record(z.enum(['asc', 'desc'])).optional().describe('Sort order'),
            start: z.number().optional().describe('Pagination offset'),
            limit: z.number().optional().default(20).describe('Max tasks to return (default: 20)'),
            newResponsibleId: z.number().optional().describe('New responsible user ID (for delegate)'),
            fileIds: z.array(z.number()).optional().describe('File IDs to attach'),
        }
    }, async (params) => {
        const { action } = params;
        switch (action) {
            case 'create': {
                if (!params.title || !params.responsibleId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'title and responsibleId are required for create' }) }] };
                }
                const result = await bitrixService.createTask({
                    TITLE: params.title,
                    RESPONSIBLE_ID: params.responsibleId,
                    DESCRIPTION: params.description,
                    PRIORITY: params.priority,
                    DEADLINE: params.deadline,
                    START_DATE_PLAN: params.startDatePlan,
                    END_DATE_PLAN: params.endDatePlan,
                    GROUP_ID: params.groupId,
                    PARENT_ID: params.parentId,
                    ACCOMPLICES: params.accomplices,
                    AUDITORS: params.auditors,
                    TAGS: params.tags,
                    ALLOW_CHANGE_DEADLINE: params.allowChangeDeadline ? 'Y' : 'N',
                    TASK_CONTROL: params.taskControl ? 'Y' : 'N',
                    ALLOW_TIME_TRACKING: params.allowTimeTracking ? 'Y' : 'N',
                });
                return { content: [{ type: 'text', text: JSON.stringify({ success: true, taskId: result.task?.id }) }] };
            }
            case 'get': {
                if (!params.taskId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId is required' }) }] };
                }
                try {
                    const result = await bitrixService.getTask(params.taskId);
                    if (!result.task) {
                        return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: `Task ${params.taskId} not found` }) }] };
                    }
                    return { content: [{ type: 'text', text: JSON.stringify({ success: true, task: result.task }, null, 2) }] };
                }
                catch (error) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to get task' }) }] };
                }
            }
            case 'list': {
                const limit = params.limit ?? 20;
                // Default minimal fields to reduce response size
                const defaultSelect = ['ID', 'TITLE', 'STATUS', 'RESPONSIBLE_ID', 'DEADLINE', 'PRIORITY', 'CREATED_BY', 'GROUP_ID'];
                const result = await bitrixService.listTasks({
                    filter: params.filter,
                    select: params.select ?? defaultSelect,
                    order: params.order,
                    start: params.start,
                    limit: limit,
                });
                // Limit results on server side in case API ignores limit param
                const limitedTasks = result.tasks.slice(0, limit);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                count: limitedTasks.length,
                                total: result.tasks.length,
                                tasks: limitedTasks.map((t) => ({
                                    id: t.id,
                                    title: t.title,
                                    status: t.status,
                                    responsibleId: t.responsibleId,
                                    deadline: t.deadline,
                                    priority: t.priority,
                                })),
                            }, null, 2)
                        }]
                };
            }
            case 'update': {
                if (!params.taskId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId is required' }) }] };
                }
                const fields = {};
                if (params.title)
                    fields.TITLE = params.title;
                if (params.description !== undefined)
                    fields.DESCRIPTION = params.description;
                if (params.responsibleId)
                    fields.RESPONSIBLE_ID = params.responsibleId;
                if (params.deadline)
                    fields.DEADLINE = params.deadline;
                if (params.priority !== undefined)
                    fields.PRIORITY = params.priority;
                if (params.groupId !== undefined)
                    fields.GROUP_ID = params.groupId;
                if (params.accomplices)
                    fields.ACCOMPLICES = params.accomplices;
                if (params.auditors)
                    fields.AUDITORS = params.auditors;
                if (params.tags)
                    fields.TAGS = params.tags;
                const result = await bitrixService.updateTask(params.taskId, fields);
                return { content: [{ type: 'text', text: JSON.stringify({ success: true, taskId: params.taskId, updated: result }) }] };
            }
            case 'delete': {
                if (!params.taskId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId is required' }) }] };
                }
                const result = await bitrixService.deleteTask(params.taskId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: result.task, taskId: params.taskId }) }] };
            }
            case 'start': {
                if (!params.taskId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId is required' }) }] };
                }
                const result = await bitrixService.startTask(params.taskId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: result, taskId: params.taskId, status: 'in_progress' }) }] };
            }
            case 'pause': {
                if (!params.taskId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId is required' }) }] };
                }
                const result = await bitrixService.pauseTask(params.taskId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: result, taskId: params.taskId, status: 'paused' }) }] };
            }
            case 'complete': {
                if (!params.taskId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId is required' }) }] };
                }
                const result = await bitrixService.completeTask(params.taskId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: result, taskId: params.taskId, status: 'completed' }) }] };
            }
            case 'defer': {
                if (!params.taskId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId is required' }) }] };
                }
                const result = await bitrixService.deferTask(params.taskId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: result, taskId: params.taskId, status: 'deferred' }) }] };
            }
            case 'renew': {
                if (!params.taskId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId is required' }) }] };
                }
                const result = await bitrixService.renewTask(params.taskId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: result, taskId: params.taskId, status: 'pending' }) }] };
            }
            case 'approve': {
                if (!params.taskId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId is required' }) }] };
                }
                const result = await bitrixService.approveTask(params.taskId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: result, taskId: params.taskId, approved: true }) }] };
            }
            case 'disapprove': {
                if (!params.taskId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId is required' }) }] };
                }
                const result = await bitrixService.disapproveTask(params.taskId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: result, taskId: params.taskId, approved: false }) }] };
            }
            case 'delegate': {
                if (!params.taskId || !params.newResponsibleId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId and newResponsibleId are required' }) }] };
                }
                const result = await bitrixService.delegateTask(params.taskId, params.newResponsibleId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: result, taskId: params.taskId, newResponsibleId: params.newResponsibleId }) }] };
            }
            case 'attach_files': {
                if (!params.taskId || !params.fileIds?.length) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId and fileIds are required' }) }] };
                }
                const result = await bitrixService.attachFilesToTask(params.taskId, params.fileIds);
                return { content: [{ type: 'text', text: JSON.stringify({ success: result, taskId: params.taskId, attachedFiles: params.fileIds.length }) }] };
            }
            case 'counters': {
                const counters = await bitrixService.getTaskCounters();
                return { content: [{ type: 'text', text: JSON.stringify({ success: true, counters }, null, 2) }] };
            }
            case 'history': {
                if (!params.taskId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId is required' }) }] };
                }
                const history = await bitrixService.getTaskHistory(params.taskId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: true, taskId: params.taskId, history }, null, 2) }] };
            }
            case 'favorite_add': {
                if (!params.taskId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId is required' }) }] };
                }
                const result = await bitrixService.addTaskToFavorite(params.taskId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: result, taskId: params.taskId, favorite: true }) }] };
            }
            case 'favorite_remove': {
                if (!params.taskId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'taskId is required' }) }] };
                }
                const result = await bitrixService.removeTaskFromFavorite(params.taskId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: result, taskId: params.taskId, favorite: false }) }] };
            }
            case 'get_fields': {
                const result = await bitrixService.getTaskFields();
                return { content: [{ type: 'text', text: JSON.stringify({ success: true, fields: result.fields }, null, 2) }] };
            }
            default:
                return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: `Unknown action: ${action}` }) }] };
        }
    });
}
//# sourceMappingURL=task-tool.js.map