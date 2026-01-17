import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { BitrixService } from '../services/bitrix-service.js';
import { BitrixDepartmentFilter } from '../types/bitrix.js';

export function departmentTools(server: McpServer, bitrixService: BitrixService): void {
  // Get list of departments
  server.registerTool('bitrix_department_list', {
    description: 'Get list of all departments (organizational structure) from Bitrix24',
    inputSchema: {
      parentId: z.number().optional().describe('Filter by parent department ID (get only child departments)'),
      headId: z.number().optional().describe('Filter by department head user ID'),
      sort: z.enum(['ID', 'NAME', 'SORT', 'PARENT']).optional().describe('Field to sort by'),
      order: z.enum(['ASC', 'DESC']).optional().describe('Sort order'),
      start: z.number().optional().describe('Pagination offset (page size is 50)'),
    }
  }, async (params) => {
    const filter: BitrixDepartmentFilter = {};

    if (params.parentId !== undefined) filter.PARENT = params.parentId;
    if (params.headId !== undefined) filter.UF_HEAD = params.headId;

    const result = await bitrixService.getDepartments(
      Object.keys(filter).length > 0 ? filter : undefined,
      params.sort,
      params.order,
      params.start
    );

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
            sort: d.SORT,
            parentId: d.PARENT,
            headId: d.UF_HEAD,
          })),
        }, null, 2)
      }]
    };
  });

  // Get specific department by ID
  server.registerTool('bitrix_department_get', {
    description: 'Get information about a specific department by its ID',
    inputSchema: {
      departmentId: z.number().describe('Department ID'),
    }
  }, async (params) => {
    const department = await bitrixService.getDepartmentById(params.departmentId);

    if (!department) {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            success: false,
            error: `Department with ID ${params.departmentId} not found`,
          }, null, 2)
        }]
      };
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          department: {
            id: department.ID,
            name: department.NAME,
            sort: department.SORT,
            parentId: department.PARENT,
            headId: department.UF_HEAD,
          },
        }, null, 2)
      }]
    };
  });

  // Get department tree (hierarchical structure)
  server.registerTool('bitrix_department_tree', {
    description: 'Get hierarchical tree of organizational structure (departments with nested children)',
    inputSchema: {
      rootId: z.number().optional().describe('Root department ID (if not specified, returns full tree from top)'),
      maxDepth: z.number().optional().describe('Maximum depth of the tree (e.g., 2 = only 2 levels)'),
    }
  }, async (params) => {
    const tree = await bitrixService.getDepartmentTree(params.rootId, params.maxDepth);

    // Helper to count total nodes
    const countNodes = (nodes: typeof tree): number => {
      return nodes.reduce((sum, node) => {
        return sum + 1 + (node.children ? countNodes(node.children) : 0);
      }, 0);
    };

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          rootId: params.rootId || 'all',
          maxDepth: params.maxDepth || 'unlimited',
          totalDepartments: countNodes(tree),
          tree,
        }, null, 2)
      }]
    };
  });

  // Get employees of a department
  server.registerTool('bitrix_department_employees', {
    description: 'Get all employees from a department (with optional recursive search in child departments)',
    inputSchema: {
      departmentId: z.number().describe('Department ID'),
      recursive: z.boolean().optional().default(true).describe('Include employees from all nested child departments'),
      activeOnly: z.boolean().optional().default(true).describe('Return only active employees'),
    }
  }, async (params) => {
    // Get department info first
    const department = await bitrixService.getDepartmentById(params.departmentId);

    const employees = await bitrixService.getDepartmentEmployees(
      params.departmentId,
      params.recursive,
      params.activeOnly
    );

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          department: department ? {
            id: department.ID,
            name: department.NAME,
          } : null,
          departmentId: params.departmentId,
          recursive: params.recursive,
          activeOnly: params.activeOnly,
          count: employees.length,
          employees: employees.map(u => ({
            id: u.ID,
            name: `${u.NAME || ''} ${u.LAST_NAME || ''}`.trim(),
            email: u.EMAIL,
            phone: u.WORK_PHONE || u.PERSONAL_MOBILE,
            position: u.WORK_POSITION,
            departments: u.UF_DEPARTMENT,
            active: u.ACTIVE,
          })),
        }, null, 2)
      }]
    };
  });

  // Get department fields description
  server.registerTool('bitrix_department_fields', {
    description: 'Get description of all available department fields',
    inputSchema: {}
  }, async () => {
    const fields = await bitrixService.getDepartmentFields();

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          fields,
        }, null, 2)
      }]
    };
  });
}
