import { z } from 'zod';
export function taskTools(server, bitrixService) {
    // Create task
    server.registerTool('bitrix_task_create', {
        description: 'Create a new task in Bitrix24. Required fields: title and responsibleId (assignee user ID)',
        inputSchema: {
            title: z.string().describe('Task title (required)'),
            responsibleId: z.number().describe('Assignee user ID (required)'),
            description: z.string().optional().describe('Task description'),
            createdBy: z.number().optional().describe('Creator user ID (default: webhook user)'),
            accomplices: z.array(z.number()).optional().describe('Co-executors user IDs array'),
            auditors: z.array(z.number()).optional().describe('Observers user IDs array'),
            deadline: z.string().optional().describe('Deadline in ISO format (e.g., 2025-01-20T18:00:00)'),
            startDatePlan: z.string().optional().describe('Planned start date'),
            endDatePlan: z.string().optional().describe('Planned end date'),
            priority: z.number().min(0).max(2).optional().describe('Priority: 0=low, 1=normal, 2=high'),
            groupId: z.number().optional().describe('Project/group ID'),
            parentId: z.number().optional().describe('Parent task ID for subtasks'),
            tags: z.array(z.string()).optional().describe('Tags array'),
            timeEstimate: z.number().optional().describe('Estimated time in seconds'),
            allowChangeDeadline: z.boolean().optional().describe('Allow assignee to change deadline'),
            allowTimeTracking: z.boolean().optional().describe('Enable time tracking'),
            taskControl: z.boolean().optional().describe('Require task acceptance'),
            addInReport: z.boolean().optional().describe('Include in report'),
        }
    }, async (params) => {
        const fields = {
            TITLE: params.title,
            RESPONSIBLE_ID: params.responsibleId,
        };
        if (params.description)
            fields.DESCRIPTION = params.description;
        if (params.createdBy)
            fields.CREATED_BY = params.createdBy;
        if (params.accomplices)
            fields.ACCOMPLICES = params.accomplices;
        if (params.auditors)
            fields.AUDITORS = params.auditors;
        if (params.deadline)
            fields.DEADLINE = params.deadline;
        if (params.startDatePlan)
            fields.START_DATE_PLAN = params.startDatePlan;
        if (params.endDatePlan)
            fields.END_DATE_PLAN = params.endDatePlan;
        if (params.priority !== undefined)
            fields.PRIORITY = params.priority;
        if (params.groupId)
            fields.GROUP_ID = params.groupId;
        if (params.parentId)
            fields.PARENT_ID = params.parentId;
        if (params.tags)
            fields.TAGS = params.tags;
        if (params.timeEstimate)
            fields.TIME_ESTIMATE = params.timeEstimate;
        if (params.allowChangeDeadline !== undefined)
            fields.ALLOW_CHANGE_DEADLINE = params.allowChangeDeadline ? 'Y' : 'N';
        if (params.allowTimeTracking !== undefined)
            fields.ALLOW_TIME_TRACKING = params.allowTimeTracking ? 'Y' : 'N';
        if (params.taskControl !== undefined)
            fields.TASK_CONTROL = params.taskControl ? 'Y' : 'N';
        if (params.addInReport !== undefined)
            fields.ADD_IN_REPORT = params.addInReport ? 'Y' : 'N';
        const result = await bitrixService.createTask(fields);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        taskId: result.task.id,
                        task: result.task,
                        message: `Task "${params.title}" created successfully`,
                    }, null, 2)
                }]
        };
    });
    // Update task
    server.registerTool('bitrix_task_update', {
        description: 'Update an existing task in Bitrix24',
        inputSchema: {
            taskId: z.number().describe('Task ID to update'),
            title: z.string().optional().describe('New task title'),
            description: z.string().optional().describe('New task description'),
            responsibleId: z.number().optional().describe('New assignee user ID'),
            accomplices: z.array(z.number()).optional().describe('New co-executors user IDs'),
            auditors: z.array(z.number()).optional().describe('New observers user IDs'),
            deadline: z.string().optional().describe('New deadline in ISO format'),
            startDatePlan: z.string().optional().describe('New planned start date'),
            endDatePlan: z.string().optional().describe('New planned end date'),
            priority: z.number().min(0).max(2).optional().describe('New priority: 0=low, 1=normal, 2=high'),
            groupId: z.number().optional().describe('New project/group ID'),
            parentId: z.number().optional().describe('New parent task ID'),
            tags: z.array(z.string()).optional().describe('New tags array'),
            timeEstimate: z.number().optional().describe('New estimated time in seconds'),
        }
    }, async (params) => {
        const fields = {};
        if (params.title)
            fields.TITLE = params.title;
        if (params.description)
            fields.DESCRIPTION = params.description;
        if (params.responsibleId)
            fields.RESPONSIBLE_ID = params.responsibleId;
        if (params.accomplices)
            fields.ACCOMPLICES = params.accomplices;
        if (params.auditors)
            fields.AUDITORS = params.auditors;
        if (params.deadline)
            fields.DEADLINE = params.deadline;
        if (params.startDatePlan)
            fields.START_DATE_PLAN = params.startDatePlan;
        if (params.endDatePlan)
            fields.END_DATE_PLAN = params.endDatePlan;
        if (params.priority !== undefined)
            fields.PRIORITY = params.priority;
        if (params.groupId)
            fields.GROUP_ID = params.groupId;
        if (params.parentId)
            fields.PARENT_ID = params.parentId;
        if (params.tags)
            fields.TAGS = params.tags;
        if (params.timeEstimate)
            fields.TIME_ESTIMATE = params.timeEstimate;
        const result = await bitrixService.updateTask(params.taskId, fields);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        taskId: params.taskId,
                        task: result.task,
                        message: `Task ${params.taskId} updated successfully`,
                    }, null, 2)
                }]
        };
    });
    // Get task
    server.registerTool('bitrix_task_get', {
        description: 'Get task details by ID from Bitrix24',
        inputSchema: {
            taskId: z.number().describe('Task ID to retrieve'),
            select: z.array(z.string()).optional().describe('Fields to select (default: all)'),
        }
    }, async ({ taskId, select }) => {
        const result = await bitrixService.getTask(taskId, select);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        task: result.task,
                    }, null, 2)
                }]
        };
    });
    // List tasks
    server.registerTool('bitrix_task_list', {
        description: 'Get list of tasks from Bitrix24 with filtering and sorting',
        inputSchema: {
            responsibleId: z.number().optional().describe('Filter by assignee user ID'),
            createdBy: z.number().optional().describe('Filter by creator user ID'),
            groupId: z.number().optional().describe('Filter by project/group ID'),
            parentId: z.number().optional().describe('Filter by parent task ID'),
            status: z.number().optional().describe('Filter by status: 1=new, 2=pending, 3=in_progress, 4=supposedly_completed, 5=completed, 6=deferred'),
            priority: z.number().optional().describe('Filter by priority: 0=low, 1=normal, 2=high'),
            titleSearch: z.string().optional().describe('Search in task title'),
            deadlineFrom: z.string().optional().describe('Filter deadline from date (ISO format)'),
            deadlineTo: z.string().optional().describe('Filter deadline to date (ISO format)'),
            orderBy: z.string().optional().describe('Sort field (e.g., DEADLINE, CREATED_DATE, PRIORITY)'),
            orderDir: z.enum(['asc', 'desc']).optional().describe('Sort direction'),
            limit: z.number().optional().describe('Maximum tasks to return (default: 50)'),
            start: z.number().optional().describe('Offset for pagination'),
        }
    }, async (params) => {
        const filter = {};
        const order = {};
        if (params.responsibleId)
            filter.RESPONSIBLE_ID = params.responsibleId;
        if (params.createdBy)
            filter.CREATED_BY = params.createdBy;
        if (params.groupId)
            filter.GROUP_ID = params.groupId;
        if (params.parentId)
            filter.PARENT_ID = params.parentId;
        if (params.status)
            filter.STATUS = params.status;
        if (params.priority !== undefined)
            filter.PRIORITY = params.priority;
        if (params.titleSearch)
            filter['%TITLE'] = params.titleSearch;
        if (params.deadlineFrom)
            filter['>=DEADLINE'] = params.deadlineFrom;
        if (params.deadlineTo)
            filter['<=DEADLINE'] = params.deadlineTo;
        if (params.orderBy) {
            order[params.orderBy] = params.orderDir || 'asc';
        }
        const result = await bitrixService.listTasks({
            filter: Object.keys(filter).length > 0 ? filter : undefined,
            order: Object.keys(order).length > 0 ? order : undefined,
            limit: params.limit || 50,
            start: params.start,
        });
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        count: result.tasks.length,
                        tasks: result.tasks,
                    }, null, 2)
                }]
        };
    });
    // Delete task
    server.registerTool('bitrix_task_delete', {
        description: 'Delete a task from Bitrix24',
        inputSchema: {
            taskId: z.number().describe('Task ID to delete'),
        }
    }, async ({ taskId }) => {
        await bitrixService.deleteTask(taskId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        taskId,
                        message: `Task ${taskId} deleted successfully`,
                    }, null, 2)
                }]
        };
    });
    // Get task fields
    server.registerTool('bitrix_task_get_fields', {
        description: 'Get list of available task field names from Bitrix24',
        inputSchema: {}
    }, async () => {
        const result = await bitrixService.getTaskFields();
        // Return only field names to avoid chunk limit
        const fieldNames = Object.keys(result.fields);
        // Group fields by category for better usability
        const categories = {
            basic: ['ID', 'TITLE', 'DESCRIPTION', 'PRIORITY', 'STATUS'],
            dates: fieldNames.filter(f => f.includes('DATE') || f.includes('DEADLINE')),
            users: fieldNames.filter(f => f.includes('_BY') || f.includes('_ID') && (f.includes('CREATED') || f.includes('RESPONSIBLE') || f.includes('CHANGED'))),
            other: []
        };
        categories.other = fieldNames.filter(f => !categories.basic.includes(f) &&
            !categories.dates.includes(f) &&
            !categories.users.includes(f));
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        totalFields: fieldNames.length,
                        categories
                    })
                }]
        };
    });
}
//# sourceMappingURL=task-tools.js.map