import { z } from 'zod';
const listActionSchema = z.enum([
    'add', 'get', 'update', 'delete', 'get_iblock_type'
]).describe('Action to perform on lists');
const iblockTypeSchema = z.enum(['lists', 'bitrix_processes', 'lists_socnet'])
    .describe('List type: lists (standard), bitrix_processes (processes), lists_socnet (group lists)');
export function registerListTool(server, bitrixService) {
    server.registerTool('bitrix_list', {
        description: `Universal list (infoblock) management. Actions:
- add: Create list (requires iblockTypeId, iblockCode, name)
- get: Get list(s) (requires iblockTypeId)
- update: Update list (requires iblockTypeId and iblockId or iblockCode)
- delete: Delete list (requires iblockTypeId and iblockId or iblockCode)
- get_iblock_type: Get infoblock type identifier`,
        inputSchema: {
            action: listActionSchema,
            iblockTypeId: iblockTypeSchema.optional().describe('List type (required for all except get_iblock_type)'),
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            name: z.string().optional().describe('List name (required for add)'),
            description: z.string().optional().describe('List description'),
            sort: z.number().optional().describe('Sort order'),
            bizproc: z.boolean().optional().describe('Enable business process support'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
            start: z.number().optional().describe('Pagination offset'),
        }
    }, async (params) => {
        const { action } = params;
        switch (action) {
            case 'add': {
                if (!params.iblockTypeId || !params.iblockCode || !params.name) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'iblockTypeId, iblockCode, and name are required' }) }] };
                }
                const listId = await bitrixService.createList(params.iblockTypeId, params.iblockCode, {
                    NAME: params.name,
                    DESCRIPTION: params.description,
                    SORT: params.sort,
                    BIZPROC: params.bizproc ? 'Y' : 'N',
                }, params.socnetGroupId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: true, listId }) }] };
            }
            case 'get': {
                if (!params.iblockTypeId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'iblockTypeId is required' }) }] };
                }
                const result = await bitrixService.getLists(params.iblockTypeId, params.iblockId, params.iblockCode, params.socnetGroupId, params.start);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                count: result.lists.length,
                                total: result.total,
                                next: result.next,
                                lists: result.lists.map(l => ({
                                    id: l.ID,
                                    name: l.NAME,
                                    description: l.DESCRIPTION,
                                    type: l.IBLOCK_TYPE_ID,
                                    code: l.IBLOCK_CODE,
                                    sort: l.SORT,
                                    active: l.ACTIVE === 'Y',
                                    bizproc: l.BIZPROC === 'Y',
                                    socnetGroupId: l.SOCNET_GROUP_ID,
                                })),
                            }, null, 2)
                        }]
                };
            }
            case 'update': {
                if (!params.iblockTypeId || (!params.iblockId && !params.iblockCode)) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'iblockTypeId and iblockId or iblockCode are required' }) }] };
                }
                const fields = {};
                if (params.name)
                    fields.NAME = params.name;
                if (params.description !== undefined)
                    fields.DESCRIPTION = params.description;
                if (params.sort !== undefined)
                    fields.SORT = params.sort;
                if (params.bizproc !== undefined)
                    fields.BIZPROC = params.bizproc ? 'Y' : 'N';
                const success = await bitrixService.updateList(params.iblockTypeId, params.iblockId, params.iblockCode, fields);
                return { content: [{ type: 'text', text: JSON.stringify({ success }) }] };
            }
            case 'delete': {
                if (!params.iblockTypeId || (!params.iblockId && !params.iblockCode)) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'iblockTypeId and iblockId or iblockCode are required' }) }] };
                }
                const success = await bitrixService.deleteList(params.iblockTypeId, params.iblockId, params.iblockCode);
                return { content: [{ type: 'text', text: JSON.stringify({ success }) }] };
            }
            case 'get_iblock_type': {
                const iblockTypeId = await bitrixService.getIblockTypeId();
                return { content: [{ type: 'text', text: JSON.stringify({ success: true, iblockTypeId }) }] };
            }
            default:
                return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: `Unknown action: ${action}` }) }] };
        }
    });
}
//# sourceMappingURL=list-tool.js.map