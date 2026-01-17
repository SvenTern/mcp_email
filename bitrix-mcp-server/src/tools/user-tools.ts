import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { BitrixService } from '../services/bitrix-service.js';
import { BitrixUserFilter } from '../types/bitrix.js';

export function userTools(server: McpServer, bitrixService: BitrixService): void {
  // Get list of users with filtering
  server.registerTool('bitrix_user_list', {
    description: 'Get list of employees (users) from Bitrix24 with optional filtering and pagination',
    inputSchema: {
      active: z.boolean().optional().describe('Filter by active status (true = only active employees)'),
      departmentId: z.number().optional().describe('Filter by department ID'),
      userType: z.enum(['employee', 'extranet', 'email']).optional().describe('Filter by user type'),
      isOnline: z.boolean().optional().describe('Filter by online status'),
      select: z.array(z.string()).optional().describe('Fields to select (e.g., ["ID", "NAME", "LAST_NAME", "EMAIL"])'),
      sort: z.string().optional().describe('Field to sort by (e.g., "LAST_NAME")'),
      order: z.enum(['ASC', 'DESC']).optional().describe('Sort order'),
      start: z.number().optional().describe('Pagination offset (page size is 50)'),
    }
  }, async (params) => {
    const filter: BitrixUserFilter = {};

    if (params.active !== undefined) filter.ACTIVE = params.active;
    if (params.departmentId) filter.UF_DEPARTMENT = params.departmentId;
    if (params.userType) filter.USER_TYPE = params.userType;
    if (params.isOnline !== undefined) filter.IS_ONLINE = params.isOnline ? 'Y' : 'N';

    const result = await bitrixService.getUsersFiltered(
      Object.keys(filter).length > 0 ? filter : undefined,
      params.select,
      params.sort,
      params.order,
      params.start
    );

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
            name: `${u.NAME || ''} ${u.LAST_NAME || ''}`.trim(),
            email: u.EMAIL,
            phone: u.WORK_PHONE || u.PERSONAL_MOBILE,
            position: u.WORK_POSITION,
            departments: u.UF_DEPARTMENT,
            active: u.ACTIVE,
            isOnline: u.IS_ONLINE === 'Y',
          })),
        }, null, 2)
      }]
    };
  });

  // Search users by name/personal data
  server.registerTool('bitrix_user_search', {
    description: 'Quick search for employees by name, last name, middle name, position, or department name',
    inputSchema: {
      query: z.string().describe('Search query (name, last name, position, department)'),
      active: z.boolean().optional().default(true).describe('Search only active employees'),
    }
  }, async (params) => {
    const users = await bitrixService.searchUsers(params.query, params.active);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          count: users.length,
          query: params.query,
          users: users.map(u => ({
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

  // Get specific user by ID
  server.registerTool('bitrix_user_get', {
    description: 'Get detailed information about a specific employee by their ID',
    inputSchema: {
      userId: z.number().describe('User ID'),
      select: z.array(z.string()).optional().describe('Fields to select'),
    }
  }, async (params) => {
    const user = await bitrixService.getUserById(params.userId, params.select);

    if (!user) {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            success: false,
            error: `User with ID ${params.userId} not found`,
          }, null, 2)
        }]
      };
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          user: {
            id: user.ID,
            firstName: user.NAME,
            lastName: user.LAST_NAME,
            middleName: user.SECOND_NAME,
            fullName: `${user.NAME || ''} ${user.LAST_NAME || ''}`.trim(),
            email: user.EMAIL,
            personalPhone: user.PERSONAL_PHONE,
            personalMobile: user.PERSONAL_MOBILE,
            workPhone: user.WORK_PHONE,
            innerPhone: user.UF_PHONE_INNER,
            position: user.WORK_POSITION,
            company: user.WORK_COMPANY,
            departments: user.UF_DEPARTMENT,
            gender: user.PERSONAL_GENDER,
            birthday: user.PERSONAL_BIRTHDAY,
            city: user.PERSONAL_CITY,
            active: user.ACTIVE,
            userType: user.USER_TYPE,
            dateRegister: user.DATE_REGISTER,
            lastLogin: user.LAST_LOGIN,
            lastActivity: user.LAST_ACTIVITY_DATE,
            isOnline: user.IS_ONLINE === 'Y',
          },
        }, null, 2)
      }]
    };
  });

  // Get current user info
  server.registerTool('bitrix_user_current', {
    description: 'Get information about the current authenticated user (webhook owner)',
    inputSchema: {}
  }, async () => {
    const user = await bitrixService.getCurrentUser();

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          currentUser: {
            id: user.ID,
            firstName: user.NAME,
            lastName: user.LAST_NAME,
            fullName: `${user.NAME || ''} ${user.LAST_NAME || ''}`.trim(),
            email: user.EMAIL,
            position: user.WORK_POSITION,
            departments: user.UF_DEPARTMENT,
            active: user.ACTIVE,
          },
        }, null, 2)
      }]
    };
  });

  // Get user fields description
  server.registerTool('bitrix_user_fields', {
    description: 'Get description of all available user profile fields',
    inputSchema: {}
  }, async () => {
    const fields = await bitrixService.getUserFields();

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

  // Get users by department
  server.registerTool('bitrix_user_by_department', {
    description: 'Get all employees from a specific department (with optional recursive search in child departments)',
    inputSchema: {
      departmentId: z.number().describe('Department ID'),
      recursive: z.boolean().optional().default(false).describe('Include employees from child departments'),
      activeOnly: z.boolean().optional().default(true).describe('Return only active employees'),
    }
  }, async (params) => {
    const users = await bitrixService.getDepartmentEmployees(
      params.departmentId,
      params.recursive,
      params.activeOnly
    );

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          departmentId: params.departmentId,
          recursive: params.recursive,
          count: users.length,
          employees: users.map(u => ({
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
}
