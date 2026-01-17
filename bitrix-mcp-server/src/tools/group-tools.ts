import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { BitrixService } from '../services/bitrix-service.js';
import { BitrixGroupFilter } from '../types/bitrix.js';

export function groupTools(server: McpServer, bitrixService: BitrixService): void {
  // Get list of groups
  server.registerTool('bitrix_group_list', {
    description: 'Get list of workgroups (social network groups/projects) from Bitrix24',
    inputSchema: {
      ownerId: z.number().optional().describe('Filter by group owner user ID'),
      visible: z.boolean().optional().describe('Filter by visibility (true = visible groups)'),
      opened: z.boolean().optional().describe('Filter by open/closed status (true = open groups)'),
      project: z.boolean().optional().describe('Filter by project type (true = only projects)'),
      active: z.boolean().optional().describe('Filter by active status'),
      start: z.number().optional().describe('Pagination offset (page size is 50)'),
    }
  }, async (params) => {
    const filter: BitrixGroupFilter = {};

    if (params.ownerId !== undefined) filter.OWNER_ID = params.ownerId;
    if (params.visible !== undefined) filter.VISIBLE = params.visible ? 'Y' : 'N';
    if (params.opened !== undefined) filter.OPENED = params.opened ? 'Y' : 'N';
    if (params.project !== undefined) filter.PROJECT = params.project ? 'Y' : 'N';
    if (params.active !== undefined) filter.ACTIVE = params.active ? 'Y' : 'N';

    const result = await bitrixService.getGroups(
      Object.keys(filter).length > 0 ? filter : undefined,
      params.start
    );

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          count: result.groups.length,
          total: result.total,
          next: result.next,
          groups: result.groups.map(g => ({
            id: g.ID,
            name: g.NAME,
            description: g.DESCRIPTION,
            ownerId: g.OWNER_ID,
            membersCount: g.NUMBER_OF_MEMBERS,
            moderatorsCount: g.NUMBER_OF_MODERATORS,
            isProject: g.PROJECT === 'Y',
            isVisible: g.VISIBLE === 'Y',
            isOpened: g.OPENED === 'Y',
            isClosed: g.CLOSED === 'Y',
            isActive: g.ACTIVE === 'Y',
            dateCreate: g.DATE_CREATE,
            dateActivity: g.DATE_ACTIVITY,
          })),
        }, null, 2)
      }]
    };
  });

  // Get specific group by ID
  server.registerTool('bitrix_group_get', {
    description: 'Get detailed information about a specific workgroup by its ID',
    inputSchema: {
      groupId: z.number().describe('Group ID'),
    }
  }, async (params) => {
    const group = await bitrixService.getGroupById(params.groupId);

    if (!group) {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            success: false,
            error: `Group with ID ${params.groupId} not found`,
          }, null, 2)
        }]
      };
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          group: {
            id: group.ID,
            name: group.NAME,
            description: group.DESCRIPTION,
            ownerId: group.OWNER_ID,
            membersCount: group.NUMBER_OF_MEMBERS,
            moderatorsCount: group.NUMBER_OF_MODERATORS,
            isProject: group.PROJECT === 'Y',
            isVisible: group.VISIBLE === 'Y',
            isOpened: group.OPENED === 'Y',
            isClosed: group.CLOSED === 'Y',
            isActive: group.ACTIVE === 'Y',
            dateCreate: group.DATE_CREATE,
            dateUpdate: group.DATE_UPDATE,
            dateActivity: group.DATE_ACTIVITY,
            keywords: group.KEYWORDS,
            projectDateStart: group.PROJECT_DATE_START,
            projectDateFinish: group.PROJECT_DATE_FINISH,
            scrumOwnerId: group.SCRUM_OWNER_ID,
            scrumMasterId: group.SCRUM_MASTER_ID,
          },
        }, null, 2)
      }]
    };
  });

  // Get group members
  server.registerTool('bitrix_group_members', {
    description: 'Get list of members (participants) of a workgroup',
    inputSchema: {
      groupId: z.number().describe('Group ID'),
      role: z.enum(['owner', 'moderator', 'member', 'all']).optional().default('all')
        .describe('Filter by role: owner (A), moderator (E), member (K), or all'),
    }
  }, async (params) => {
    const members = await bitrixService.getGroupMembers(params.groupId);

    // Role mapping: A=owner, E=moderator, K=member, M=waiting
    const roleNames: Record<string, string> = {
      'A': 'owner',
      'E': 'moderator',
      'K': 'member',
      'M': 'waiting',
    };

    const roleFilter: Record<string, string> = {
      'owner': 'A',
      'moderator': 'E',
      'member': 'K',
    };

    let filteredMembers = members;
    if (params.role && params.role !== 'all') {
      const filterRole = roleFilter[params.role];
      filteredMembers = members.filter(m => m.ROLE === filterRole);
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          groupId: params.groupId,
          roleFilter: params.role,
          totalCount: members.length,
          filteredCount: filteredMembers.length,
          members: filteredMembers.map(m => ({
            userId: m.USER_ID,
            role: roleNames[m.ROLE] || m.ROLE,
            roleCode: m.ROLE,
            autoMember: m.AUTO_MEMBER === 'Y',
            dateCreate: m.DATE_CREATE,
            user: m.USER ? {
              id: m.USER.ID,
              name: `${m.USER.NAME || ''} ${m.USER.LAST_NAME || ''}`.trim(),
              email: m.USER.EMAIL,
              position: m.USER.WORK_POSITION,
            } : null,
          })),
        }, null, 2)
      }]
    };
  });

  // Get my groups (current user's groups)
  server.registerTool('bitrix_group_my', {
    description: 'Get list of workgroups that the current user (webhook owner) belongs to',
    inputSchema: {}
  }, async () => {
    const groups = await bitrixService.getMyGroups();

    // Role mapping: A=owner, E=moderator, K=member
    const roleNames: Record<string, string> = {
      'A': 'owner',
      'E': 'moderator',
      'K': 'member',
    };

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          count: groups.length,
          myGroups: groups.map(g => ({
            id: g.GROUP_ID,
            name: g.GROUP_NAME,
            role: roleNames[g.ROLE] || g.ROLE,
            roleCode: g.ROLE,
          })),
        }, null, 2)
      }]
    };
  });

  // Search groups
  server.registerTool('bitrix_group_search', {
    description: 'Search for workgroups by name or filter criteria',
    inputSchema: {
      name: z.string().optional().describe('Search by group name (partial match)'),
      ownerId: z.number().optional().describe('Filter by owner user ID'),
      project: z.boolean().optional().describe('Filter by project type'),
      visible: z.boolean().optional().describe('Filter by visibility'),
      start: z.number().optional().describe('Pagination offset'),
    }
  }, async (params) => {
    const filter: Record<string, unknown> = {};

    if (params.name) filter['%NAME'] = params.name;
    if (params.ownerId !== undefined) filter.OWNER_ID = params.ownerId;
    if (params.project !== undefined) filter.PROJECT = params.project ? 'Y' : 'N';
    if (params.visible !== undefined) filter.VISIBLE = params.visible ? 'Y' : 'N';

    const result = await bitrixService.getWorkgroups(
      Object.keys(filter).length > 0 ? filter : undefined,
      undefined,
      params.start
    );

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          searchCriteria: params,
          count: result.groups.length,
          total: result.total,
          next: result.next,
          groups: result.groups.map(g => ({
            id: g.ID,
            name: g.NAME,
            description: g.DESCRIPTION,
            ownerId: g.OWNER_ID,
            membersCount: g.NUMBER_OF_MEMBERS,
            isProject: g.PROJECT === 'Y',
            isVisible: g.VISIBLE === 'Y',
            isOpened: g.OPENED === 'Y',
          })),
        }, null, 2)
      }]
    };
  });

  // Check group access
  server.registerTool('bitrix_group_access_check', {
    description: 'Check if current user has access to a specific feature/operation in a workgroup',
    inputSchema: {
      groupId: z.number().describe('Group ID'),
      feature: z.string().describe('Feature to check (e.g., "blog", "files", "tasks", "calendar", "photo", "forum", "wiki")'),
      operation: z.string().optional().default('view').describe('Operation to check (e.g., "view", "write_post", "moderate_post", "full_post")'),
    }
  }, async (params) => {
    const operation = params.operation || 'view';
    const hasAccess = await bitrixService.checkGroupAccess(params.groupId, params.feature, operation);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          groupId: params.groupId,
          feature: params.feature,
          operation,
          hasAccess,
        }, null, 2)
      }]
    };
  });
}
