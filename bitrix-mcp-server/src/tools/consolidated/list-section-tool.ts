import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { BitrixService } from '../../services/bitrix-service.js';
import { IblockTypeId } from '../../types/bitrix.js';

const listSectionActionSchema = z.enum([
  'add', 'get', 'update', 'delete'
]).describe('Action to perform on list sections');

const iblockTypeSchema = z.enum(['lists', 'bitrix_processes', 'lists_socnet']);

export function registerListSectionTool(server: McpServer, bitrixService: BitrixService): void {
  server.registerTool('bitrix_list_section', {
    description: `List section management. Actions:
- add: Create section (requires iblockTypeId, sectionCode, name)
- get: Get section(s) (requires iblockTypeId)
- update: Update section (requires iblockTypeId, sectionId or sectionCode)
- delete: Delete section (requires iblockTypeId, sectionId or sectionCode)`,
    inputSchema: {
      action: listSectionActionSchema,
      iblockTypeId: iblockTypeSchema.describe('List type'),
      iblockId: z.number().optional().describe('List ID'),
      iblockCode: z.string().optional().describe('List symbolic code'),
      sectionId: z.number().optional().describe('Section ID'),
      sectionCode: z.string().optional().describe('Section symbolic code'),
      name: z.string().optional().describe('Section name'),
      parentSectionId: z.number().optional().describe('Parent section ID (0 for root)'),
      sort: z.number().optional().describe('Sort order'),
      active: z.boolean().optional().describe('Active status'),
      filter: z.record(z.unknown()).optional().describe('Filter conditions'),
      select: z.array(z.string()).optional().describe('Fields to return'),
      socnetGroupId: z.number().optional().describe('Group ID for group lists'),
    }
  }, async (params) => {
    const { action, iblockTypeId } = params;

    switch (action) {
      case 'add': {
        if (!params.sectionCode || !params.name) {
          return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'sectionCode and name are required' }) }] };
        }
        const sectionId = await bitrixService.createListSection(
          iblockTypeId as IblockTypeId,
          params.sectionCode,
          {
            NAME: params.name,
            SORT: params.sort,
            ACTIVE: params.active === false ? 'N' : 'Y',
          },
          params.iblockId,
          params.iblockCode,
          params.parentSectionId,
          params.socnetGroupId
        );
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, sectionId }) }] };
      }

      case 'get': {
        const result = await bitrixService.getListSections(
          iblockTypeId as IblockTypeId,
          params.iblockId,
          params.iblockCode,
          params.filter,
          params.select,
          params.socnetGroupId
        );
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              count: result.sections.length,
              total: result.total,
              sections: result.sections.map(s => ({
                id: s.ID,
                name: s.NAME,
                code: s.CODE,
                iblockId: s.IBLOCK_ID,
                parentSectionId: s.IBLOCK_SECTION_ID,
                active: s.ACTIVE === 'Y',
                sort: s.SORT,
                depthLevel: s.DEPTH_LEVEL,
              })),
            }, null, 2)
          }]
        };
      }

      case 'update': {
        if (!params.sectionId && !params.sectionCode) {
          return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'sectionId or sectionCode is required' }) }] };
        }
        const fields: Record<string, unknown> = {};
        if (params.name) fields.NAME = params.name;
        if (params.sort !== undefined) fields.SORT = params.sort;
        if (params.active !== undefined) fields.ACTIVE = params.active ? 'Y' : 'N';

        const success = await bitrixService.updateListSection(
          iblockTypeId as IblockTypeId,
          params.sectionId,
          params.sectionCode,
          Object.keys(fields).length > 0 ? fields as any : undefined,
          params.iblockId,
          params.iblockCode,
          params.socnetGroupId
        );
        return { content: [{ type: 'text', text: JSON.stringify({ success }) }] };
      }

      case 'delete': {
        if (!params.sectionId && !params.sectionCode) {
          return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'sectionId or sectionCode is required' }) }] };
        }
        const success = await bitrixService.deleteListSection(
          iblockTypeId as IblockTypeId,
          params.sectionId,
          params.sectionCode,
          params.iblockId,
          params.iblockCode,
          params.socnetGroupId
        );
        return { content: [{ type: 'text', text: JSON.stringify({ success }) }] };
      }

      default:
        return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: `Unknown action: ${action}` }) }] };
    }
  });
}
