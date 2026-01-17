import { z } from 'zod';
// Zod enum for iblock type
const iblockTypeSchema = z.enum(['lists', 'bitrix_processes', 'lists_socnet'])
    .describe('List type: lists (standard), bitrix_processes (processes), lists_socnet (group lists)');
export function listTools(server, bitrixService) {
    // =============================================================================
    // List Management Tools (5 tools)
    // =============================================================================
    // Create a new list
    server.registerTool('bitrix_list_add', {
        description: 'Create a new universal list in Bitrix24',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockCode: z.string().describe('Unique symbolic code for the list'),
            name: z.string().describe('List display name'),
            description: z.string().optional().describe('List description'),
            sort: z.number().optional().describe('Sort order (default: 500)'),
            bizproc: z.boolean().optional().describe('Enable business process support'),
            socnetGroupId: z.number().optional().describe('Group ID (required for lists_socnet type)'),
        }
    }, async (params) => {
        const fields = {
            NAME: params.name,
        };
        if (params.description)
            fields.DESCRIPTION = params.description;
        if (params.sort !== undefined)
            fields.SORT = params.sort;
        if (params.bizproc !== undefined)
            fields.BIZPROC = params.bizproc ? 'Y' : 'N';
        const listId = await bitrixService.createList(params.iblockTypeId, params.iblockCode, fields, params.socnetGroupId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        listId,
                        message: `List "${params.name}" created with ID ${listId}`,
                    }, null, 2)
                }]
        };
    });
    // Get lists
    server.registerTool('bitrix_list_get', {
        description: 'Get list(s) from Bitrix24. Returns all accessible lists if no ID/code specified',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('Specific list ID'),
            iblockCode: z.string().optional().describe('Specific list symbolic code'),
            socnetGroupId: z.number().optional().describe('Group ID (required for group lists)'),
            start: z.number().optional().describe('Pagination offset (page size: 50)'),
        }
    }, async (params) => {
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
                            code: l.IBLOCK_CODE,
                            name: l.NAME,
                            description: l.DESCRIPTION,
                            type: l.IBLOCK_TYPE_ID,
                            sort: l.SORT,
                            active: l.ACTIVE === 'Y',
                            bizproc: l.BIZPROC === 'Y',
                            socnetGroupId: l.SOCNET_GROUP_ID,
                        })),
                    }, null, 2)
                }]
        };
    });
    // Update a list
    server.registerTool('bitrix_list_update', {
        description: 'Update an existing universal list',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            name: z.string().optional().describe('New list name'),
            description: z.string().optional().describe('New description'),
            sort: z.number().optional().describe('New sort order'),
            bizproc: z.boolean().optional().describe('Enable/disable business process support'),
        }
    }, async (params) => {
        const fields = {};
        if (params.name)
            fields.NAME = params.name;
        if (params.description !== undefined)
            fields.DESCRIPTION = params.description;
        if (params.sort !== undefined)
            fields.SORT = params.sort;
        if (params.bizproc !== undefined)
            fields.BIZPROC = params.bizproc ? 'Y' : 'N';
        const success = await bitrixService.updateList(params.iblockTypeId, params.iblockId, params.iblockCode, Object.keys(fields).length > 0 ? fields : undefined);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success,
                        message: success ? 'List updated successfully' : 'Failed to update list',
                    }, null, 2)
                }]
        };
    });
    // Delete a list
    server.registerTool('bitrix_list_delete', {
        description: 'Delete a universal list',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
        }
    }, async (params) => {
        const success = await bitrixService.deleteList(params.iblockTypeId, params.iblockId, params.iblockCode);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success,
                        message: success ? 'List deleted successfully' : 'Failed to delete list',
                    }, null, 2)
                }]
        };
    });
    // Get iblock type ID
    server.registerTool('bitrix_list_get_iblock_type', {
        description: 'Get the infoblock type identifier for lists',
        inputSchema: {}
    }, async () => {
        const typeId = await bitrixService.getIblockTypeId();
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        iblockTypeId: typeId,
                    }, null, 2)
                }]
        };
    });
    // =============================================================================
    // List Element Tools (5 tools)
    // =============================================================================
    // Create element
    server.registerTool('bitrix_list_element_add', {
        description: 'Create a new element in a Bitrix24 list',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            elementCode: z.string().describe('Symbolic code for the element'),
            name: z.string().describe('Element name/title'),
            sectionId: z.number().optional().describe('Section ID (0 or omit for root)'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
            properties: z.record(z.unknown()).optional()
                .describe('Custom field values as {"PROPERTY_ID": value} or {"fieldCode": value}'),
        }
    }, async (params) => {
        const fields = {
            NAME: params.name,
        };
        // Add custom properties
        if (params.properties) {
            for (const [key, value] of Object.entries(params.properties)) {
                const fieldKey = key.startsWith('PROPERTY_') ? key : `PROPERTY_${key}`;
                fields[fieldKey] = value;
            }
        }
        const elementId = await bitrixService.createListElement(params.iblockTypeId, params.elementCode, fields, params.iblockId, params.iblockCode, params.sectionId, params.socnetGroupId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        elementId,
                        message: `Element "${params.name}" created with ID ${elementId}`,
                    }, null, 2)
                }]
        };
    });
    // Get elements
    server.registerTool('bitrix_list_element_get', {
        description: 'Get element(s) from a Bitrix24 list',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            elementId: z.number().optional().describe('Specific element ID'),
            elementCode: z.string().optional().describe('Specific element code'),
            filter: z.record(z.unknown()).optional().describe('Filter conditions (NAME, CREATED_BY, etc.)'),
            select: z.array(z.string()).optional().describe('Fields to return'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
            start: z.number().optional().describe('Pagination offset (page size: 50)'),
        }
    }, async (params) => {
        const result = await bitrixService.getListElements(params.iblockTypeId, params.iblockId, params.iblockCode, params.elementId, params.elementCode, params.filter, params.select, undefined, params.socnetGroupId, params.start);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        count: result.elements.length,
                        total: result.total,
                        next: result.next,
                        elements: result.elements,
                    }, null, 2)
                }]
        };
    });
    // Update element
    server.registerTool('bitrix_list_element_update', {
        description: 'Update a list element',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            elementId: z.number().optional().describe('Element ID'),
            elementCode: z.string().optional().describe('Element code'),
            name: z.string().describe('Element name (required)'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
            properties: z.record(z.unknown()).optional()
                .describe('Custom field values to update'),
        }
    }, async (params) => {
        const fields = {
            NAME: params.name,
        };
        if (params.properties) {
            for (const [key, value] of Object.entries(params.properties)) {
                const fieldKey = key.startsWith('PROPERTY_') ? key : `PROPERTY_${key}`;
                fields[fieldKey] = value;
            }
        }
        const success = await bitrixService.updateListElement(params.iblockTypeId, params.elementId, params.elementCode, fields, params.iblockId, params.iblockCode, params.socnetGroupId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success,
                        message: success ? 'Element updated successfully' : 'Failed to update element',
                    }, null, 2)
                }]
        };
    });
    // Delete element
    server.registerTool('bitrix_list_element_delete', {
        description: 'Delete a list element',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            elementId: z.number().optional().describe('Element ID'),
            elementCode: z.string().optional().describe('Element code'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
        }
    }, async (params) => {
        const success = await bitrixService.deleteListElement(params.iblockTypeId, params.elementId, params.elementCode, params.iblockId, params.iblockCode, params.socnetGroupId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success,
                        message: success ? 'Element deleted successfully' : 'Failed to delete element',
                    }, null, 2)
                }]
        };
    });
    // Get element file URL
    server.registerTool('bitrix_list_element_file_url', {
        description: 'Get file URL from a list element field',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            elementId: z.number().describe('Element ID'),
            fieldId: z.string().describe('Field ID (e.g., PROPERTY_123 or field code)'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
        }
    }, async (params) => {
        const fieldId = params.fieldId.startsWith('PROPERTY_')
            ? params.fieldId
            : `PROPERTY_${params.fieldId}`;
        const url = await bitrixService.getListElementFileUrl(params.iblockTypeId, params.elementId, fieldId, params.iblockId, params.iblockCode, params.socnetGroupId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        elementId: params.elementId,
                        fieldId: fieldId,
                        url,
                    }, null, 2)
                }]
        };
    });
    // =============================================================================
    // List Field Tools (5 tools)
    // =============================================================================
    // Create field
    server.registerTool('bitrix_list_field_add', {
        description: 'Add a new field to a Bitrix24 list',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            name: z.string().describe('Field display name'),
            type: z.string().describe('Field type (S, N, L, F, S:Date, S:DateTime, S:HTML, etc.)'),
            code: z.string().optional().describe('Symbolic code (required for custom fields)'),
            isRequired: z.boolean().optional().describe('Make field required'),
            multiple: z.boolean().optional().describe('Allow multiple values'),
            sort: z.number().optional().describe('Sort order'),
            defaultValue: z.unknown().optional().describe('Default value'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
            listValues: z.array(z.string()).optional()
                .describe('Values for List (L) type fields'),
        }
    }, async (params) => {
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
        if (params.defaultValue !== undefined)
            fields.DEFAULT_VALUE = params.defaultValue;
        // Handle list values for L type
        if (params.listValues && params.type === 'L') {
            fields.LIST_TEXT_VALUES = params.listValues.join('\n');
        }
        const fieldId = await bitrixService.createListField(params.iblockTypeId, fields, params.iblockId, params.iblockCode, params.socnetGroupId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        fieldId,
                        message: `Field "${params.name}" created with ID ${fieldId}`,
                    }, null, 2)
                }]
        };
    });
    // Get fields
    server.registerTool('bitrix_list_field_get', {
        description: 'Get field(s) of a Bitrix24 list',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            fieldId: z.string().optional().describe('Specific field ID (omit for all fields)'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
        }
    }, async (params) => {
        const fields = await bitrixService.getListFields(params.iblockTypeId, params.iblockId, params.iblockCode, params.fieldId, params.socnetGroupId);
        // Convert to array for easier display
        const fieldArray = Object.entries(fields).map(([id, field]) => ({
            fieldId: id,
            name: field.NAME,
            type: field.TYPE || field.PROPERTY_TYPE,
            userType: field.USER_TYPE,
            sort: field.SORT,
            required: field.IS_REQUIRED === 'Y',
            multiple: field.MULTIPLE === 'Y',
            code: field.CODE,
            defaultValue: field.DEFAULT_VALUE,
            listValues: field.DISPLAY_VALUES_FORM,
        }));
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        count: fieldArray.length,
                        fields: fieldArray,
                    }, null, 2)
                }]
        };
    });
    // Update field
    server.registerTool('bitrix_list_field_update', {
        description: 'Update a list field',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            fieldId: z.string().describe('Field ID to update'),
            name: z.string().optional().describe('New field name'),
            isRequired: z.boolean().optional().describe('Make field required'),
            multiple: z.boolean().optional().describe('Allow multiple values'),
            sort: z.number().optional().describe('Sort order'),
            defaultValue: z.unknown().optional().describe('Default value'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
            listValues: z.array(z.string()).optional()
                .describe('New values for List (L) type fields'),
        }
    }, async (params) => {
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
        if (params.listValues)
            fields.LIST_TEXT_VALUES = params.listValues.join('\n');
        const success = await bitrixService.updateListField(params.iblockTypeId, params.fieldId, fields, params.iblockId, params.iblockCode, params.socnetGroupId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success,
                        message: success ? 'Field updated successfully' : 'Failed to update field',
                    }, null, 2)
                }]
        };
    });
    // Delete field
    server.registerTool('bitrix_list_field_delete', {
        description: 'Delete a list field',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            fieldId: z.string().describe('Field ID to delete'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
        }
    }, async (params) => {
        const success = await bitrixService.deleteListField(params.iblockTypeId, params.fieldId, params.iblockId, params.iblockCode, params.socnetGroupId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success,
                        message: success ? 'Field deleted successfully' : 'Failed to delete field',
                    }, null, 2)
                }]
        };
    });
    // Get field types
    server.registerTool('bitrix_list_field_types', {
        description: 'Get available field types for a Bitrix24 list',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
        }
    }, async (params) => {
        const types = await bitrixService.getListFieldTypes(params.iblockTypeId, params.iblockId, params.iblockCode, params.socnetGroupId);
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
    });
    // =============================================================================
    // List Section Tools (4 tools)
    // =============================================================================
    // Create section
    server.registerTool('bitrix_list_section_add', {
        description: 'Create a new section in a Bitrix24 list',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            sectionCode: z.string().describe('Symbolic code for the section'),
            name: z.string().describe('Section name'),
            parentSectionId: z.number().optional().describe('Parent section ID (0 or omit for root)'),
            sort: z.number().optional().describe('Sort order'),
            active: z.boolean().optional().describe('Active status'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
        }
    }, async (params) => {
        const fields = {
            NAME: params.name,
        };
        if (params.sort !== undefined)
            fields.SORT = params.sort;
        if (params.active !== undefined)
            fields.ACTIVE = params.active ? 'Y' : 'N';
        const sectionId = await bitrixService.createListSection(params.iblockTypeId, params.sectionCode, fields, params.iblockId, params.iblockCode, params.parentSectionId, params.socnetGroupId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success: true,
                        sectionId,
                        message: `Section "${params.name}" created with ID ${sectionId}`,
                    }, null, 2)
                }]
        };
    });
    // Get sections
    server.registerTool('bitrix_list_section_get', {
        description: 'Get section(s) of a Bitrix24 list',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            filter: z.record(z.unknown()).optional().describe('Filter conditions'),
            select: z.array(z.string()).optional().describe('Fields to return'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
        }
    }, async (params) => {
        const result = await bitrixService.getListSections(params.iblockTypeId, params.iblockId, params.iblockCode, params.filter, params.select, params.socnetGroupId);
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
                            parentSectionId: s.IBLOCK_SECTION_ID,
                            sort: s.SORT,
                            active: s.ACTIVE === 'Y',
                            depthLevel: s.DEPTH_LEVEL,
                        })),
                    }, null, 2)
                }]
        };
    });
    // Update section
    server.registerTool('bitrix_list_section_update', {
        description: 'Update a list section',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            sectionId: z.number().optional().describe('Section ID'),
            sectionCode: z.string().optional().describe('Section code'),
            name: z.string().optional().describe('New section name'),
            sort: z.number().optional().describe('New sort order'),
            active: z.boolean().optional().describe('Active status'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
        }
    }, async (params) => {
        const fields = {};
        if (params.name)
            fields.NAME = params.name;
        if (params.sort !== undefined)
            fields.SORT = params.sort;
        if (params.active !== undefined)
            fields.ACTIVE = params.active ? 'Y' : 'N';
        const success = await bitrixService.updateListSection(params.iblockTypeId, params.sectionId, params.sectionCode, Object.keys(fields).length > 0 ? fields : undefined, params.iblockId, params.iblockCode, params.socnetGroupId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success,
                        message: success ? 'Section updated successfully' : 'Failed to update section',
                    }, null, 2)
                }]
        };
    });
    // Delete section
    server.registerTool('bitrix_list_section_delete', {
        description: 'Delete a list section',
        inputSchema: {
            iblockTypeId: iblockTypeSchema,
            iblockId: z.number().optional().describe('List ID'),
            iblockCode: z.string().optional().describe('List symbolic code'),
            sectionId: z.number().optional().describe('Section ID'),
            sectionCode: z.string().optional().describe('Section code'),
            socnetGroupId: z.number().optional().describe('Group ID for group lists'),
        }
    }, async (params) => {
        const success = await bitrixService.deleteListSection(params.iblockTypeId, params.sectionId, params.sectionCode, params.iblockId, params.iblockCode, params.socnetGroupId);
        return {
            content: [{
                    type: 'text',
                    text: JSON.stringify({
                        success,
                        message: success ? 'Section deleted successfully' : 'Failed to delete section',
                    }, null, 2)
                }]
        };
    });
}
//# sourceMappingURL=list-tools.js.map