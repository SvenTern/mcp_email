import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { BitrixService } from '../../services/bitrix-service.js';

const userActionSchema = z.enum([
  'list', 'get', 'current', 'search', 'fields', 'by_department', 'get_many'
]).describe('Action to perform on users');

export function registerUserTool(server: McpServer, bitrixService: BitrixService): void {
  server.registerTool('bitrix_user', {
    description: `User/employee management. Actions:
- list: List all users with filters
- get: Get user by ID (requires userId)
- get_many: Get multiple users by IDs (requires userIds)
- current: Get current user (webhook owner)
- search: Search users (requires query)
- fields: Get available user fields
- by_department: Get users by department (requires departmentId)`,
    inputSchema: {
      action: userActionSchema,
      userId: z.number().optional().describe('User ID (required for get)'),
      userIds: z.array(z.number()).optional().describe('User IDs (required for get_many)'),
      departmentId: z.number().optional().describe('Department ID (required for by_department)'),
      query: z.string().optional().describe('Search query (required for search)'),
      filter: z.record(z.unknown()).optional().describe('Filter conditions for list'),
      start: z.number().optional().describe('Pagination offset'),
    }
  }, async (params) => {
    const { action } = params;

    switch (action) {
      case 'list': {
        const result = await bitrixService.getUsersFiltered(params.filter as Record<string, unknown> | undefined, undefined, undefined, undefined, params.start);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              count: result.users.length,
              total: result.total,
              next: result.next,
              users: result.users.map(u => ({
                id: u.ID,
                name: `${u.NAME} ${u.LAST_NAME}`.trim(),
                email: u.EMAIL,
                department: u.UF_DEPARTMENT,
                active: u.ACTIVE,
                position: u.WORK_POSITION,
              })),
            }, null, 2)
          }]
        };
      }

      case 'get': {
        if (!params.userId) {
          return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'userId is required' }) }] };
        }
        const user = await bitrixService.getUserById(params.userId);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              user: user ? {
                id: user.ID,
                name: `${user.NAME} ${user.LAST_NAME}`.trim(),
                email: user.EMAIL,
                phone: user.PERSONAL_PHONE || user.WORK_PHONE,
                department: user.UF_DEPARTMENT,
                position: user.WORK_POSITION,
                active: user.ACTIVE,
              } : null,
            }, null, 2)
          }]
        };
      }

      case 'get_many': {
        if (!params.userIds?.length) {
          return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'userIds is required' }) }] };
        }
        const users = await bitrixService.getUsers({ ID: params.userIds });
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
                department: u.UF_DEPARTMENT,
              })),
            }, null, 2)
          }]
        };
      }

      case 'current': {
        const user = await bitrixService.getCurrentUser();
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              user: {
                id: user.ID,
                name: `${user.NAME} ${user.LAST_NAME}`.trim(),
                email: user.EMAIL,
                department: user.UF_DEPARTMENT,
                position: user.WORK_POSITION,
              },
            }, null, 2)
          }]
        };
      }

      case 'search': {
        if (!params.query) {
          return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'query is required' }) }] };
        }
        const users = await bitrixService.searchUsers(params.query);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              query: params.query,
              count: users.length,
              users: users.map(u => ({
                id: u.ID,
                name: `${u.NAME} ${u.LAST_NAME}`.trim(),
                email: u.EMAIL,
                position: u.WORK_POSITION,
              })),
            }, null, 2)
          }]
        };
      }

      case 'fields': {
        const fields = await bitrixService.getUserFields();
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, fields }, null, 2) }] };
      }

      case 'by_department': {
        if (!params.departmentId) {
          return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'departmentId is required' }) }] };
        }
        const users = await bitrixService.getDepartmentEmployees(params.departmentId);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              departmentId: params.departmentId,
              count: users.length,
              users: users.map(u => ({
                id: u.ID,
                name: `${u.NAME} ${u.LAST_NAME}`.trim(),
                email: u.EMAIL,
                position: u.WORK_POSITION,
              })),
            }, null, 2)
          }]
        };
      }

      default:
        return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: `Unknown action: ${action}` }) }] };
    }
  });
}
