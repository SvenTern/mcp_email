import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { BitrixService } from '../services/bitrix-service.js';

export function extraTools(server: McpServer, bitrixService: BitrixService): void {
  // Test connection
  server.registerTool('bitrix_test_connection', {
    description: 'Test connection to Bitrix24 API and get current user info',
    inputSchema: {}
  }, async () => {
    const result = await bitrixService.testConnection();

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          message: 'Successfully connected to Bitrix24',
          currentUser: result.user,
        }, null, 2)
      }]
    };
  });

  // Get users
  server.registerTool('bitrix_users_get', {
    description: 'Get list of users from Bitrix24 (useful to find user IDs for task assignment)',
    inputSchema: {
      active: z.boolean().optional().describe('Filter by active status'),
      departmentId: z.number().optional().describe('Filter by department ID'),
      nameSearch: z.string().optional().describe('Search by name'),
    }
  }, async (params) => {
    const filter: Record<string, unknown> = {};

    if (params.active !== undefined) filter.ACTIVE = params.active;
    if (params.departmentId) filter.UF_DEPARTMENT = params.departmentId;
    if (params.nameSearch) filter.NAME = `%${params.nameSearch}%`;

    const users = await bitrixService.getUsers(
      Object.keys(filter).length > 0 ? filter : undefined
    );

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
            position: u.WORK_POSITION,
            active: u.ACTIVE,
          })),
        }, null, 2)
      }]
    };
  });

  // Add task to favorites
  server.registerTool('bitrix_task_favorite_add', {
    description: 'Add a task to favorites in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID to add to favorites'),
    }
  }, async ({ taskId }) => {
    await bitrixService.addTaskToFavorite(taskId);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId,
          message: `Task ${taskId} added to favorites`,
        }, null, 2)
      }]
    };
  });

  // Remove task from favorites
  server.registerTool('bitrix_task_favorite_remove', {
    description: 'Remove a task from favorites in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID to remove from favorites'),
    }
  }, async ({ taskId }) => {
    await bitrixService.removeTaskFromFavorite(taskId);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId,
          message: `Task ${taskId} removed from favorites`,
        }, null, 2)
      }]
    };
  });

  // Attach files to task
  server.registerTool('bitrix_task_attach_files', {
    description: 'Attach files to a task in Bitrix24 (files must be already uploaded to Bitrix24)',
    inputSchema: {
      taskId: z.number().describe('Task ID to attach files to'),
      fileIds: z.array(z.number()).describe('Array of file IDs to attach'),
    }
  }, async ({ taskId, fileIds }) => {
    await bitrixService.attachFilesToTask(taskId, fileIds);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId,
          fileIds,
          message: `${fileIds.length} file(s) attached to task ${taskId}`,
        }, null, 2)
      }]
    };
  });

  // Get task history
  server.registerTool('bitrix_task_history', {
    description: 'Get change history for a task in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID to get history for'),
    }
  }, async ({ taskId }) => {
    const history = await bitrixService.getTaskHistory(taskId);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId,
          count: Array.isArray(history) ? history.length : 0,
          history,
        }, null, 2)
      }]
    };
  });

  // Get task counters
  server.registerTool('bitrix_task_counters', {
    description: 'Get task counters (statistics) for a user in Bitrix24',
    inputSchema: {
      userId: z.number().optional().describe('User ID to get counters for (default: current user)'),
    }
  }, async ({ userId }) => {
    const counters = await bitrixService.getTaskCounters(userId);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          userId: userId || 'current',
          counters,
        }, null, 2)
      }]
    };
  });
}
