import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { BitrixService } from '../services/bitrix-service.js';

export function commentTools(server: McpServer, bitrixService: BitrixService): void {
  // Add comment
  server.registerTool('bitrix_comment_add', {
    description: 'Add a comment to a task in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID to add comment to'),
      message: z.string().describe('Comment text (supports BB-code formatting)'),
      authorId: z.number().optional().describe('Author user ID (default: webhook user)'),
    }
  }, async (params) => {
    const fields: Record<string, unknown> = {
      POST_MESSAGE: params.message,
    };

    if (params.authorId) fields.AUTHOR_ID = params.authorId;

    const commentId = await bitrixService.addComment(params.taskId, fields as any);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId: params.taskId,
          commentId,
          message: `Comment added to task ${params.taskId}`,
        }, null, 2)
      }]
    };
  });

  // Update comment
  server.registerTool('bitrix_comment_update', {
    description: 'Update a comment in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID'),
      commentId: z.number().describe('Comment ID to update'),
      message: z.string().describe('New comment text'),
    }
  }, async (params) => {
    await bitrixService.updateComment(params.taskId, params.commentId, {
      POST_MESSAGE: params.message,
    });

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId: params.taskId,
          commentId: params.commentId,
          message: `Comment ${params.commentId} updated`,
        }, null, 2)
      }]
    };
  });

  // Delete comment
  server.registerTool('bitrix_comment_delete', {
    description: 'Delete a comment from a task in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID'),
      commentId: z.number().describe('Comment ID to delete'),
    }
  }, async ({ taskId, commentId }) => {
    await bitrixService.deleteComment(taskId, commentId);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId,
          commentId,
          message: `Comment ${commentId} deleted from task ${taskId}`,
        }, null, 2)
      }]
    };
  });

  // Get comments
  server.registerTool('bitrix_comment_list', {
    description: 'Get all comments for a task in Bitrix24',
    inputSchema: {
      taskId: z.number().describe('Task ID to get comments from'),
    }
  }, async ({ taskId }) => {
    const comments = await bitrixService.getComments(taskId);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          taskId,
          count: comments.length,
          comments,
        }, null, 2)
      }]
    };
  });
}
