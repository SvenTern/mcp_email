import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { BitrixService } from '../services/bitrix-service.js';

export function timeTools(server: McpServer, bitrixService: BitrixService): void {
  // Add time entry
  server.registerTool('bitrix_time_add', {
    description: 'Add a time tracking entry to a task in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID to add time entry to'),
      seconds: z.number().describe('Time spent in seconds'),
      comment: z.string().optional().describe('Comment about the work done'),
      userId: z.number().optional().describe('User ID who spent the time (default: webhook user)'),
      dateStart: z.string().optional().describe('Start datetime in ISO format'),
      dateStop: z.string().optional().describe('End datetime in ISO format'),
    }
  }, async (params) => {
    const fields: Record<string, unknown> = {
      SECONDS: params.seconds,
    };

    if (params.comment) fields.COMMENT_TEXT = params.comment;
    if (params.userId) fields.USER_ID = params.userId;
    if (params.dateStart) fields.DATE_START = params.dateStart;
    if (params.dateStop) fields.DATE_STOP = params.dateStop;

    const entryId = await bitrixService.addElapsedTime(params.taskId, fields as any);

    const hours = Math.floor(params.seconds / 3600);
    const minutes = Math.floor((params.seconds % 3600) / 60);
    const timeStr = `${hours}h ${minutes}m`;

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId: params.taskId,
          entryId,
          timeSpent: timeStr,
          seconds: params.seconds,
          message: `Time entry (${timeStr}) added to task ${params.taskId}`,
        }, null, 2)
      }]
    };
  });

  // Update time entry
  server.registerTool('bitrix_time_update', {
    description: 'Update a time tracking entry in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID'),
      entryId: z.number().describe('Time entry ID to update'),
      seconds: z.number().optional().describe('New time spent in seconds'),
      comment: z.string().optional().describe('New comment'),
    }
  }, async (params) => {
    const fields: Record<string, unknown> = {};

    if (params.seconds !== undefined) fields.SECONDS = params.seconds;
    if (params.comment) fields.COMMENT_TEXT = params.comment;

    await bitrixService.updateElapsedTime(params.taskId, params.entryId, fields as any);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId: params.taskId,
          entryId: params.entryId,
          message: `Time entry ${params.entryId} updated`,
        }, null, 2)
      }]
    };
  });

  // Delete time entry
  server.registerTool('bitrix_time_delete', {
    description: 'Delete a time tracking entry from a task in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID'),
      entryId: z.number().describe('Time entry ID to delete'),
    }
  }, async ({ taskId, entryId }) => {
    await bitrixService.deleteElapsedTime(taskId, entryId);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId,
          entryId,
          message: `Time entry ${entryId} deleted from task ${taskId}`,
        }, null, 2)
      }]
    };
  });

  // Get time entries
  server.registerTool('bitrix_time_list', {
    description: 'Get all time tracking entries for a task in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID to get time entries from'),
    }
  }, async ({ taskId }) => {
    const entries = await bitrixService.getElapsedTime(taskId);

    // Calculate total time
    const totalSeconds = entries.reduce((sum, entry) => sum + (entry.SECONDS || 0), 0);
    const totalHours = Math.floor(totalSeconds / 3600);
    const totalMinutes = Math.floor((totalSeconds % 3600) / 60);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId,
          count: entries.length,
          totalTime: `${totalHours}h ${totalMinutes}m`,
          totalSeconds,
          entries,
        }, null, 2)
      }]
    };
  });
}
