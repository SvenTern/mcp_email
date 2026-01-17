import { z } from 'zod';
const listElementActionSchema = z.enum([
    'add', 'get', 'update', 'delete', 'file_url'
]).describe('Action to perform on list elements');
const iblockTypeSchema = z.enum(['lists', 'bitrix_processes', 'lists_socnet']);
export function registerListElementTool(server, bitrixService) {
    server.registerTool('bitrix_list_element', {
        description: `List element management. Actions:
- add: Create element (requires iblockTypeId, elementCode, name)
- get: Get element(s) (requires iblockTypeId)
- update: Update element (requires iblockTypeId, elementId or elementCode, name)
- delete: Delete element (requires iblockTypeId, elementId or elementCode)
- file_url: Get file URL (requires iblockTypeId, elementId, fieldId)`,
        inputSchema: {
            action: listElementActionSchema,
            iblockTypeId: iblockTypeSchema.describe('List type'),
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            elementId: z.number().optional().describe('Element ID'),
            elementCode: z.string().optional().describe('Element symbolic code'),
            name: z.string().optional().describe('Element name (required for add/update)'),
            sectionId: z.number().optional().describe('Section ID (0 for root)'),
            properties: z.record(z.unknown()).optional().describe('Custom field values as {"PROPERTY_ID": value}'),
            fieldId: z.string().optional().describe('Field ID for file_url action'),
            filter: z.record(z.unknown()).optional().describe('Filter conditions'),
            select: z.array(z.string()).optional().describe('Fields to return'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
            start: z.number().optional().describe('Pagination offset'),
        }
    }, async (params) => {
        const { action, iblockTypeId } = params;
        switch (action) {
            case 'add': {
                if (!params.elementCode || !params.name) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'elementCode and name are required' }) }] };
                }
                const fields = { NAME: params.name };
                if (params.properties) {
                    for (const [key, value] of Object.entries(params.properties)) {
                        const fieldKey = key.startsWith('PROPERTY_') ? key : `PROPERTY_${key}`;
                        fields[fieldKey] = value;
                    }
                }
                const elementId = await bitrixService.createListElement(iblockTypeId, params.elementCode, fields, params.iblockId, params.iblockCode, params.sectionId, params.socnetGroupId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: true, elementId }) }] };
            }
            case 'get': {
                const result = await bitrixService.getListElements(iblockTypeId, params.iblockId, params.iblockCode, params.elementId, params.elementCode, params.filter, params.select, undefined, params.socnetGroupId, params.start);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                count: result.elements.length,
                                total: result.total,
                                next: result.next,
                                elements: result.elements.map(e => {
                                    const props = {};
                                    for (const [key, value] of Object.entries(e)) {
                                        if (key.startsWith('PROPERTY_')) {
                                            props[key] = value;
                                        }
                                    }
                                    return {
                                        id: e.ID,
                                        name: e.NAME,
                                        code: e.CODE,
                                        iblockId: e.IBLOCK_ID,
                                        sectionId: e.IBLOCK_SECTION_ID,
                                        createdBy: e.CREATED_BY,
                                        dateCreate: e.DATE_CREATE,
                                        properties: Object.keys(props).length > 0 ? props : undefined,
                                    };
                                }),
                            }, null, 2)
                        }]
                };
            }
            case 'update': {
                if (!params.name || (!params.elementId && !params.elementCode)) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'name and elementId or elementCode are required' }) }] };
                }
                const fields = { NAME: params.name };
                if (params.properties) {
                    for (const [key, value] of Object.entries(params.properties)) {
                        const fieldKey = key.startsWith('PROPERTY_') ? key : `PROPERTY_${key}`;
                        fields[fieldKey] = value;
                    }
                }
                const success = await bitrixService.updateListElement(iblockTypeId, params.elementId, params.elementCode, fields, params.iblockId, params.iblockCode, params.socnetGroupId);
                return { content: [{ type: 'text', text: JSON.stringify({ success }) }] };
            }
            case 'delete': {
                if (!params.elementId && !params.elementCode) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'elementId or elementCode is required' }) }] };
                }
                const success = await bitrixService.deleteListElement(iblockTypeId, params.elementId, params.elementCode, params.iblockId, params.iblockCode, params.socnetGroupId);
                return { content: [{ type: 'text', text: JSON.stringify({ success }) }] };
            }
            case 'file_url': {
                if (!params.elementId || !params.fieldId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'elementId and fieldId are required' }) }] };
                }
                const url = await bitrixService.getListElementFileUrl(iblockTypeId, params.elementId, params.fieldId, params.iblockId, params.iblockCode, params.socnetGroupId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: true, url }) }] };
            }
            default:
                return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: `Unknown action: ${action}` }) }] };
        }
    });
}
//# sourceMappingURL=list-element-tool.js.map