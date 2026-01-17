import { z } from 'zod';
const listFieldActionSchema = z.enum([
    'add', 'get', 'update', 'delete', 'types'
]).describe('Action to perform on list fields');
const iblockTypeSchema = z.enum(['lists', 'bitrix_processes', 'lists_socnet']);
export function registerListFieldTool(server, bitrixService) {
    server.registerTool('bitrix_list_field', {
        description: `List field management. Actions:
- add: Create field (requires iblockTypeId, name, type)
- get: Get field(s) (requires iblockTypeId)
- update: Update field (requires iblockTypeId, fieldId)
- delete: Delete field (requires iblockTypeId, fieldId)
- types: Get available field types (requires iblockTypeId)`,
        inputSchema: {
            action: listFieldActionSchema,
            iblockTypeId: iblockTypeSchema.describe('List type'),
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            fieldId: z.string().optional().describe('Field ID (e.g., PROPERTY_123)'),
            name: z.string().optional().describe('Field display name'),
            type: z.string().optional().describe('Field type (S, N, L, F, S:Date, S:DateTime, S:HTML, etc.)'),
            code: z.string().optional().describe('Symbolic code'),
            isRequired: z.boolean().optional().describe('Make field required'),
            multiple: z.boolean().optional().describe('Allow multiple values'),
            sort: z.number().optional().describe('Sort order'),
            defaultValue: z.string().optional().describe('Default value'),
            listValues: z.array(z.string()).optional().describe('Values for List (L) type fields'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
        }
    }, async (params) => {
        const { action, iblockTypeId } = params;
        switch (action) {
            case 'add': {
                if (!params.name || !params.type) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'name and type are required' }) }] };
                }
                const fields = {
                    NAME: params.name,
                    TYPE: params.type,
                };
                if (params.code)
                    fields.CODE = params.code;
                if (params.isRequired !== undefined)
                    fields.IS_REQUIRED = params.isRequired ? 'Y' : 'N';
                if (params.multiple !== undefined)
                    fields.MULTIPLE = params.multiple ? 'Y' : 'N';
                if (params.sort !== undefined)
                    fields.SORT = params.sort;
                if (params.defaultValue)
                    fields.DEFAULT_VALUE = params.defaultValue;
                if (params.listValues?.length) {
                    fields.LIST_TEXT_VALUES = params.listValues.join('\n');
                }
                const fieldId = await bitrixService.createListField(iblockTypeId, fields, params.iblockId, params.iblockCode, params.socnetGroupId);
                return { content: [{ type: 'text', text: JSON.stringify({ success: true, fieldId }) }] };
            }
            case 'get': {
                const fieldsResult = await bitrixService.getListFields(iblockTypeId, params.iblockId, params.iblockCode, params.fieldId, params.socnetGroupId);
                const fields = Object.entries(fieldsResult).map(([id, f]) => ({
                    fieldId: f.FIELD_ID || id,
                    name: f.NAME,
                    type: f.TYPE || f.PROPERTY_TYPE,
                    sort: f.SORT,
                    required: f.IS_REQUIRED === 'Y',
                    multiple: f.MULTIPLE === 'Y',
                    code: f.CODE,
                    defaultValue: f.DEFAULT_VALUE,
                    listValues: f.DISPLAY_VALUES_FORM,
                }));
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                count: fields.length,
                                fields,
                            }, null, 2)
                        }]
                };
            }
            case 'update': {
                if (!params.fieldId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'fieldId is required' }) }] };
                }
                const fields = {};
                if (params.name)
                    fields.NAME = params.name;
                if (params.isRequired !== undefined)
                    fields.IS_REQUIRED = params.isRequired ? 'Y' : 'N';
                if (params.multiple !== undefined)
                    fields.MULTIPLE = params.multiple ? 'Y' : 'N';
                if (params.sort !== undefined)
                    fields.SORT = params.sort;
                if (params.defaultValue !== undefined)
                    fields.DEFAULT_VALUE = params.defaultValue;
                if (params.listValues?.length) {
                    fields.LIST_TEXT_VALUES = params.listValues.join('\n');
                }
                const success = await bitrixService.updateListField(iblockTypeId, params.fieldId, fields, params.iblockId, params.iblockCode, params.socnetGroupId);
                return { content: [{ type: 'text', text: JSON.stringify({ success, fieldId: params.fieldId }) }] };
            }
            case 'delete': {
                if (!params.fieldId) {
                    return { content: [{ type: 'text', text: JSON.stringify({ success: false, error: 'fieldId is required' }) }] };
                }
                const success = await bitrixService.deleteListField(iblockTypeId, params.fieldId, params.iblockId, params.iblockCode, params.socnetGroupId);
                return { content: [{ type: 'text', text: JSON.stringify({ success, fieldId: params.fieldId }) }] };
            }
            case 'types': {
                const types = await bitrixService.getListFieldTypes(iblockTypeId, params.iblockId, params.iblockCode, params.socnetGroupId);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({
                                success: true,
                                count: types.length,
                                types: types.map(t => ({
                                    type: t.TYPE,
                                    name: t.NAME,
                                    description: t.DESCRIPTION,
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
//# sourceMappingURL=list-field-tool.js.map