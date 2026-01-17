import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { BitrixService } from '../services/bitrix-service.js';

export function checklistTools(server: McpServer, bitrixService: BitrixService): void {
  // Add checklist item
  server.registerTool('bitrix_checklist_add', {
    description: 'Add a new checklist item to a task in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID to add checklist item to'),
      title: z.string().describe('Checklist item title'),
      sortIndex: z.number().optional().describe('Sort order index'),
      isComplete: z.boolean().optional().describe('Mark as completed immediately'),
      parentId: z.number().optional().describe('Parent checklist item ID for nested items'),
    }
  }, async (params) => {
    const fields: Record<string, unknown> = {
      TITLE: params.title,
    };

    if (params.sortIndex !== undefined) fields.SORT_INDEX = params.sortIndex;
    if (params.isComplete !== undefined) fields.IS_COMPLETE = params.isComplete ? 'Y' : 'N';
    if (params.parentId) fields.PARENT_ID = params.parentId;

    const itemId = await bitrixService.addChecklistItem(params.taskId, fields as any);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId: params.taskId,
          itemId,
          message: `Checklist item "${params.title}" added to task ${params.taskId}`,
        }, null, 2)
      }]
    };
  });

  // Update checklist item
  server.registerTool('bitrix_checklist_update', {
    description: 'Update a checklist item in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID'),
      itemId: z.number().describe('Checklist item ID to update'),
      title: z.string().optional().describe('New title'),
      sortIndex: z.number().optional().describe('New sort order index'),
    }
  }, async (params) => {
    const fields: Record<string, unknown> = {};

    if (params.title) fields.TITLE = params.title;
    if (params.sortIndex !== undefined) fields.SORT_INDEX = params.sortIndex;

    await bitrixService.updateChecklistItem(params.taskId, params.itemId, fields as any);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId: params.taskId,
          itemId: params.itemId,
          message: `Checklist item ${params.itemId} updated`,
        }, null, 2)
      }]
    };
  });

  // Delete checklist item
  server.registerTool('bitrix_checklist_delete', {
    description: 'Delete a checklist item from a task in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID'),
      itemId: z.number().describe('Checklist item ID to delete'),
    }
  }, async ({ taskId, itemId }) => {
    await bitrixService.deleteChecklistItem(taskId, itemId);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId,
          itemId,
          message: `Checklist item ${itemId} deleted from task ${taskId}`,
        }, null, 2)
      }]
    };
  });

  // Get checklist items
  server.registerTool('bitrix_checklist_list', {
    description: 'Get all checklist items for a task in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID to get checklist items from'),
    }
  }, async ({ taskId }) => {
    const items = await bitrixService.getChecklistItems(taskId);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId,
          count: items.length,
          items,
        }, null, 2)
      }]
    };
  });

  // Complete checklist item
  server.registerTool('bitrix_checklist_complete', {
    description: 'Mark a checklist item as completed in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID'),
      itemId: z.number().describe('Checklist item ID to complete'),
    }
  }, async ({ taskId, itemId }) => {
    await bitrixService.completeChecklistItem(taskId, itemId);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId,
          itemId,
          message: `Checklist item ${itemId} marked as completed`,
        }, null, 2)
      }]
    };
  });

  // Renew checklist item (uncheck)
  server.registerTool('bitrix_checklist_renew', {
    description: 'Uncheck a completed checklist item in Bitrix24 (mark as incomplete)',
    inputSchema: {
      taskId: z.number().describe('Task ID'),
      itemId: z.number().describe('Checklist item ID to uncheck'),
    }
  }, async ({ taskId, itemId }) => {
    await bitrixService.renewChecklistItem(taskId, itemId);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId,
          itemId,
          message: `Checklist item ${itemId} marked as incomplete`,
        }, null, 2)
      }]
    };
  });
}
