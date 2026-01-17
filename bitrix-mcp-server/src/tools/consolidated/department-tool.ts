import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { BitrixService } from '../../services/bitrix-service.js';

const departmentActionSchema = z.enum([
  'list', 'get', 'tree', 'employees', 'fields'
]).describe('Action to perform on departments');

export function registerDepartmentTool(server: McpServer, bitrixService: BitrixService): void {
  server.registerTool('bitrix_department', {
    description: `Company org structure management. Actions:
- list: List all departments
- get: Get department by ID (requires departmentId)
- tree: Get department tree/hierarchy
- employees: Get department employees (requires departmentId)
- fields: Get available department fields`,
    inputSchema: {
      action: departmentActionSchema,
      departmentId: z.number().optional().describe('Department ID'),
      parentId: z.number().optional().describe('Parent department ID'),
      includeSubordinates: z.boolean().optional().describe('Include subordinate departments'),
      start: z.number().optional().describe('Pagination offset'),
    }
  }, async (params) => {
    const { action } = params;

    switch (action) {
      case 'list': {
        const result = await bitrixService.getDepartments(undefined, undefined, undefined, params.start);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              count: result.departments.length,
              total: result.total,
              next: result.next,
              departments: result.departments.map(d => ({
                id: d.ID,
                name: d.NAME,
                parentId: d.PARENT,
                sort: d.SORT,
                headId: d.UF_HEAD,
              })),
            }, null, 2)
          }]
        };
      }

      case 'get': {
        if (!params.departmentId) {
          return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'departmentId is required' }) }] };
        }
        const result = await bitrixService.getDepartments({ ID: params.departmentId });
        const dept = result.departments[0];
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              department: dept ? {
                id: dept.ID,
                name: dept.NAME,
                parentId: dept.PARENT,
                sort: dept.SORT,
                headId: dept.UF_HEAD,
              } : null,
            }, null, 2)
          }]
        };
      }

      case 'tree': {
        const tree = await bitrixService.getDepartmentTree(params.parentId);
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, tree }, null, 2) }] };
      }

      case 'employees': {
        if (!params.departmentId) {
          return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'departmentId is required' }) }] };
        }
        const employees = await bitrixService.getDepartmentEmployees(
          params.departmentId,
          params.includeSubordinates
        );
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              departmentId: params.departmentId,
              count: employees.length,
              employees: employees.map(e => ({
                id: e.ID,
                name: `${e.NAME} ${e.LAST_NAME}`.trim(),
                email: e.EMAIL,
                position: e.WORK_POSITION,
              })),
            }, null, 2)
          }]
        };
      }

      case 'fields': {
        const fields = await bitrixService.getDepartmentFields();
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, fields }, null, 2) }] };
      }

      default:
        return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: `Unknown action: ${action}` }) }] };
    }
  });
}
