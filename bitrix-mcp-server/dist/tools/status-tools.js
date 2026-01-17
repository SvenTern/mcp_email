import { z } from 'zod';
export function statusTools(server, bitrixService) {
    // Complete task
    server.registerTool('bitrix_task_complete', {
        description: 'Mark a task as completed in Bitrix24',
        inputSchema: {
            taskId: z.number().describe('Task ID to complete'),
        }
    }, async ({ taskId }) => {
        const result = await bitrixService.completeTask(taskId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        taskId,
                        task: result.task,
                        message: `Task ${taskId} marked as completed`,
                    }, null, 2)
                }]
        };
    });
    // Renew task (reopen)
    server.registerTool('bitrix_task_renew', {
        description: 'Renew (reopen) a completed or deferred task in Bitrix24',
        inputSchema: {
            taskId: z.number().describe('Task ID to renew'),
        }
    }, async ({ taskId }) => {
        const result = await bitrixService.renewTask(taskId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        taskId,
                        task: result.task,
                        message: `Task ${taskId} renewed (reopened)`,
                    }, null, 2)
                }]
        };
    });
    // Start task
    server.registerTool('bitrix_task_start', {
        description: 'Start working on a task in Bitrix24 (changes status to "In Progress")',
        inputSchema: {
            taskId: z.number().describe('Task ID to start'),
        }
    }, async ({ taskId }) => {
        const result = await bitrixService.startTask(taskId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        taskId,
                        task: result.task,
                        message: `Task ${taskId} started (status: In Progress)`,
                    }, null, 2)
                }]
        };
    });
    // Pause task
    server.registerTool('bitrix_task_pause', {
        description: 'Pause a task in Bitrix24 (changes status to "Pending")',
        inputSchema: {
            taskId: z.number().describe('Task ID to pause'),
        }
    }, async ({ taskId }) => {
        const result = await bitrixService.pauseTask(taskId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        taskId,
                        task: result.task,
                        message: `Task ${taskId} paused`,
                    }, null, 2)
                }]
        };
    });
    // Defer task
    server.registerTool('bitrix_task_defer', {
        description: 'Defer a task in Bitrix24 (changes status to "Deferred")',
        inputSchema: {
            taskId: z.number().describe('Task ID to defer'),
        }
    }, async ({ taskId }) => {
        const result = await bitrixService.deferTask(taskId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        taskId,
                        task: result.task,
                        message: `Task ${taskId} deferred`,
                    }, null, 2)
                }]
        };
    });
    // Approve task
    server.registerTool('bitrix_task_approve', {
        description: 'Approve a completed task in Bitrix24 (accept the work)',
        inputSchema: {
            taskId: z.number().describe('Task ID to approve'),
        }
    }, async ({ taskId }) => {
        const result = await bitrixService.approveTask(taskId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        taskId,
                        task: result.task,
                        message: `Task ${taskId} approved (work accepted)`,
                    }, null, 2)
                }]
        };
    });
    // Disapprove task
    server.registerTool('bitrix_task_disapprove', {
        description: 'Disapprove a completed task in Bitrix24 (reject the work, send back for revision)',
        inputSchema: {
            taskId: z.number().describe('Task ID to disapprove'),
        }
    }, async ({ taskId }) => {
        const result = await bitrixService.disapproveTask(taskId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        taskId,
                        task: result.task,
                        message: `Task ${taskId} disapproved (sent back for revision)`,
                    }, null, 2)
                }]
        };
    });
    // Delegate task
    server.registerTool('bitrix_task_delegate', {
        description: 'Delegate a task to another user in Bitrix24',
        inputSchema: {
            taskId: z.number().describe('Task ID to delegate'),
            userId: z.number().describe('User ID to delegate the task to'),
        }
    }, async ({ taskId, userId }) => {
        const result = await bitrixService.delegateTask(taskId, userId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        taskId,
                        newResponsibleId: userId,
                        task: result.task,
                        message: `Task ${taskId} delegated to user ${userId}`,
                    }, null, 2)
                }]
        };
    });
}
//# sourceMappingURL=status-tools.js.map