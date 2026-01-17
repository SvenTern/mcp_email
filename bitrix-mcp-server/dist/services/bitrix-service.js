import axios from 'axios';
export class BitrixService {
    client;
    webhookUrl;
    constructor(config) {
        this.webhookUrl = config.webhookUrl.endsWith('/')
            ? config.webhookUrl.slice(0, -1)
            : config.webhookUrl;
        this.client = axios.create({
            baseURL: this.webhookUrl,
            timeout: config.timeout || 30000,
            headers: {
                'Content-Type': 'application/json',
            },
        });
    }
    async call(method, params) {
        try {
            const response = await this.client.post(`/${method}`, params || {});
            return response.data.result;
        }
        catch (error) {
            if (axios.isAxiosError(error)) {
                const axiosError = error;
                if (axiosError.response?.data?.error) {
                    throw new Error(`Bitrix24 API Error: ${axiosError.response.data.error} - ${axiosError.response.data.error_description}`);
                }
                throw new Error(`HTTP Error: ${axiosError.message}`);
            }
            throw error;
        }
    }
    // ==================== Connection Test ====================
    async testConnection() {
        const result = await this.call('user.current');
        return { success: true, user: result };
    }
    // ==================== Users ====================
    async getUsers(filter) {
        return this.call('user.get', { filter });
    }
    async getCurrentUser() {
        return this.call('user.current');
    }
    // ==================== Task CRUD ====================
    async createTask(fields) {
        return this.call('tasks.task.add', { fields });
    }
    async updateTask(taskId, fields) {
        return this.call('tasks.task.update', {
            taskId,
            fields,
        });
    }
    async getTask(taskId, select) {
        const params = { taskId };
        if (select) {
            params.select = select;
        }
        return this.call('tasks.task.get', params);
    }
    async listTasks(params) {
        return this.call('tasks.task.list', params);
    }
    async deleteTask(taskId) {
        return this.call('tasks.task.delete', { taskId });
    }
    async getTaskFields() {
        return this.call('tasks.task.getFields');
    }
    // ==================== Task Status Management ====================
    async completeTask(taskId) {
        return this.call('tasks.task.complete', { taskId });
    }
    async renewTask(taskId) {
        return this.call('tasks.task.renew', { taskId });
    }
    async startTask(taskId) {
        return this.call('tasks.task.start', { taskId });
    }
    async pauseTask(taskId) {
        return this.call('tasks.task.pause', { taskId });
    }
    async deferTask(taskId) {
        return this.call('tasks.task.defer', { taskId });
    }
    async approveTask(taskId) {
        return this.call('tasks.task.approve', { taskId });
    }
    async disapproveTask(taskId) {
        return this.call('tasks.task.disapprove', { taskId });
    }
    async delegateTask(taskId, userId) {
        return this.call('tasks.task.delegate', {
            taskId,
            userId,
        });
    }
    // ==================== Favorites ====================
    async addTaskToFavorite(taskId) {
        return this.call('tasks.task.favorite.add', { taskId });
    }
    async removeTaskFromFavorite(taskId) {
        return this.call('tasks.task.favorite.remove', { taskId });
    }
    // ==================== Files ====================
    async attachFilesToTask(taskId, fileIds) {
        return this.call('tasks.task.files.attach', {
            taskId,
            fileIds,
        });
    }
    // ==================== History ====================
    async getTaskHistory(taskId) {
        return this.call('tasks.task.history.list', { taskId });
    }
    // ==================== Counters ====================
    async getTaskCounters(userId) {
        const params = {};
        if (userId) {
            params.userId = userId;
        }
        return this.call('tasks.task.counters.get', params);
    }
    // ==================== Checklist Items ====================
    async addChecklistItem(taskId, fields) {
        return this.call('task.checklistitem.add', {
            TASKID: taskId,
            FIELDS: fields,
        });
    }
    async updateChecklistItem(taskId, itemId, fields) {
        return this.call('task.checklistitem.update', {
            TASKID: taskId,
            ITEMID: itemId,
            FIELDS: fields,
        });
    }
    async deleteChecklistItem(taskId, itemId) {
        return this.call('task.checklistitem.delete', {
            TASKID: taskId,
            ITEMID: itemId,
        });
    }
    async getChecklistItems(taskId) {
        return this.call('task.checklistitem.getlist', {
            TASKID: taskId,
        });
    }
    async completeChecklistItem(taskId, itemId) {
        return this.call('task.checklistitem.complete', {
            TASKID: taskId,
            ITEMID: itemId,
        });
    }
    async renewChecklistItem(taskId, itemId) {
        return this.call('task.checklistitem.renew', {
            TASKID: taskId,
            ITEMID: itemId,
        });
    }
    // ==================== Comments ====================
    async addComment(taskId, fields) {
        return this.call('task.commentitem.add', {
            TASKID: taskId,
            FIELDS: fields,
        });
    }
    async updateComment(taskId, itemId, fields) {
        return this.call('task.commentitem.update', {
            TASKID: taskId,
            ITEMID: itemId,
            FIELDS: fields,
        });
    }
    async deleteComment(taskId, itemId) {
        return this.call('task.commentitem.delete', {
            TASKID: taskId,
            ITEMID: itemId,
        });
    }
    async getComments(taskId) {
        return this.call('task.commentitem.getlist', {
            TASKID: taskId,
        });
    }
    // ==================== Elapsed Time (Time Tracking) ====================
    async addElapsedTime(taskId, fields) {
        return this.call('task.elapseditem.add', {
            TASKID: taskId,
            FIELDS: fields,
        });
    }
    async updateElapsedTime(taskId, itemId, fields) {
        return this.call('task.elapseditem.update', {
            TASKID: taskId,
            ITEMID: itemId,
            FIELDS: fields,
        });
    }
    async deleteElapsedTime(taskId, itemId) {
        return this.call('task.elapseditem.delete', {
            TASKID: taskId,
            ITEMID: itemId,
        });
    }
    async getElapsedTime(taskId) {
        return this.call('task.elapseditem.getlist', {
            TASKID: taskId,
        });
    }
    // ==================== Extended Users ====================
    async getUserById(userId, select) {
        const params = {
            filter: { ID: userId },
        };
        if (select) {
            params.FIELDS = select;
        }
        const users = await this.call('user.get', params);
        return users.length > 0 ? users[0] : null;
    }
    async searchUsers(query, active) {
        const params = {
            FIND: query,
        };
        if (active !== undefined) {
            params.ACTIVE = active;
        }
        return this.call('user.search', params);
    }
    async getUsersFiltered(filter, select, sort, order, start) {
        const params = {};
        if (filter)
            params.filter = filter;
        if (select)
            params.FIELDS = select;
        if (sort)
            params.sort = sort;
        if (order)
            params.order = order;
        if (start !== undefined)
            params.start = start;
        const response = await this.client.post('/user.get', params);
        return {
            users: response.data.result,
            total: response.data.total,
            next: response.data.next,
        };
    }
    async getUserFields() {
        return this.call('user.fields');
    }
    // ==================== Departments ====================
    async getDepartments(filter, sort, order, start) {
        const params = {};
        if (filter) {
            if (filter.ID !== undefined)
                params.ID = filter.ID;
            if (filter.NAME)
                params.NAME = filter.NAME;
            if (filter.SORT !== undefined)
                params.SORT = filter.SORT;
            if (filter.PARENT !== undefined)
                params.PARENT = filter.PARENT;
            if (filter.UF_HEAD !== undefined)
                params.UF_HEAD = filter.UF_HEAD;
        }
        if (sort)
            params.sort = sort;
        if (order)
            params.order = order;
        if (start !== undefined)
            params.START = start;
        const response = await this.client.post('/department.get', params);
        return {
            departments: response.data.result,
            total: response.data.total,
            next: response.data.next,
        };
    }
    async getDepartmentById(departmentId) {
        const result = await this.getDepartments({ ID: departmentId });
        return result.departments.length > 0 ? result.departments[0] : null;
    }
    async getDepartmentFields() {
        return this.call('department.fields');
    }
    async getDepartmentTree(rootId, maxDepth) {
        // Get all departments
        const allDepartments = [];
        let start = 0;
        let hasMore = true;
        while (hasMore) {
            const result = await this.getDepartments(undefined, 'SORT', 'ASC', start);
            allDepartments.push(...result.departments);
            if (result.next) {
                start = result.next;
            }
            else {
                hasMore = false;
            }
        }
        // Build tree structure
        const buildTree = (parentId, depth = 0) => {
            if (maxDepth !== undefined && depth >= maxDepth) {
                return [];
            }
            return allDepartments
                .filter(d => (parentId === undefined ? !d.PARENT : d.PARENT === parentId))
                .map(d => ({
                ...d,
                children: buildTree(d.ID, depth + 1),
            }));
        };
        return buildTree(rootId);
    }
    async getDepartmentEmployees(departmentId, recursive = false, activeOnly = true) {
        const departmentIds = [departmentId];
        // If recursive, get all child departments
        if (recursive) {
            const allDepartments = [];
            let start = 0;
            let hasMore = true;
            while (hasMore) {
                const result = await this.getDepartments(undefined, undefined, undefined, start);
                allDepartments.push(...result.departments);
                if (result.next) {
                    start = result.next;
                }
                else {
                    hasMore = false;
                }
            }
            const findChildren = (parentId) => {
                const children = allDepartments.filter(d => d.PARENT === parentId);
                for (const child of children) {
                    if (!departmentIds.includes(child.ID)) {
                        departmentIds.push(child.ID);
                        findChildren(child.ID);
                    }
                }
            };
            findChildren(departmentId);
        }
        // Get employees from all collected departments
        const allUsers = [];
        const userIds = new Set();
        for (const deptId of departmentIds) {
            let start = 0;
            let hasMore = true;
            while (hasMore) {
                const filter = {
                    UF_DEPARTMENT: deptId,
                };
                if (activeOnly) {
                    filter.ACTIVE = true;
                }
                const result = await this.getUsersFiltered(filter, undefined, undefined, undefined, start);
                for (const user of result.users) {
                    if (!userIds.has(user.ID)) {
                        userIds.add(user.ID);
                        allUsers.push(user);
                    }
                }
                if (result.next) {
                    start = result.next;
                }
                else {
                    hasMore = false;
                }
            }
        }
        return allUsers;
    }
    // ==================== Sonet Groups ====================
    async getGroups(filter, start) {
        const params = {};
        if (filter)
            params.FILTER = filter;
        if (start !== undefined)
            params.start = start;
        const response = await this.client.post('/sonet_group.get', params);
        return {
            groups: response.data.result,
            total: response.data.total,
            next: response.data.next,
        };
    }
    async getGroupById(groupId) {
        const params = {
            FILTER: { ID: groupId },
        };
        const groups = await this.call('sonet_group.get', params);
        return groups.length > 0 ? groups[0] : null;
    }
    async getWorkgroupById(groupId) {
        return this.call('socialnetwork.api.workgroup.get', {
            params: { groupId },
        });
    }
    async getWorkgroups(filter, select, start) {
        const params = {};
        if (filter)
            params.filter = filter;
        // Always request essential fields for proper display
        params.select = select || ['ID', 'NAME', 'DESCRIPTION', 'OWNER_ID', 'NUMBER_OF_MEMBERS', 'PROJECT', 'VISIBLE', 'OPENED'];
        if (start !== undefined)
            params.start = start;
        const response = await this.client.post('/socialnetwork.api.workgroup.list', params);
        // Map API response (camelCase) to our interface format (UPPER_CASE)
        const workgroups = response.data.result?.workgroups || [];
        const groups = workgroups.map(w => ({
            ID: parseInt(w.id, 10),
            NAME: w.name,
            DESCRIPTION: w.description,
            OWNER_ID: parseInt(w.ownerId, 10),
            NUMBER_OF_MEMBERS: w.numberOfMembers ? parseInt(w.numberOfMembers, 10) : undefined,
            PROJECT: w.project,
            VISIBLE: w.visible,
            OPENED: w.opened,
        }));
        return {
            groups,
            total: response.data.total,
            next: response.data.next,
        };
    }
    async getGroupMembers(groupId) {
        return this.call('sonet_group.user.get', {
            ID: groupId,
        });
    }
    async getMyGroups() {
        // sonet_group.user.groups returns simplified format: {GROUP_ID, GROUP_NAME, ROLE}
        return this.call('sonet_group.user.groups');
    }
    async checkGroupAccess(groupId, feature, operation = 'view') {
        const result = await this.call('sonet_group.feature.access', {
            GROUP_ID: groupId,
            FEATURE: feature,
            OPERATION: operation,
        });
        return result === true;
    }
    // ==================== Universal Lists ====================
    /**
     * Create a new universal list
     */
    async createList(iblockTypeId, iblockCode, fields, socnetGroupId, messages, rights) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
            IBLOCK_CODE: iblockCode,
            FIELDS: fields,
        };
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        if (messages)
            params.MESSAGES = messages;
        if (rights)
            params.RIGHTS = rights;
        return this.call('lists.add', params);
    }
    /**
     * Get list(s) - returns all accessible lists if no ID specified
     */
    async getLists(iblockTypeId, iblockId, iblockCode, socnetGroupId, start) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        if (start !== undefined)
            params.start = start;
        const response = await this.client.post('/lists.get', params);
        return {
            lists: response.data.result || [],
            total: response.data.total,
            next: response.data.next,
        };
    }
    /**
     * Update an existing list
     */
    async updateList(iblockTypeId, iblockId, iblockCode, fields, messages, rights) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (fields)
            params.FIELDS = fields;
        if (messages)
            params.MESSAGES = messages;
        if (rights)
            params.RIGHTS = rights;
        return this.call('lists.update', params);
    }
    /**
     * Delete a list
     */
    async deleteList(iblockTypeId, iblockId, iblockCode) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        return this.call('lists.delete', params);
    }
    /**
     * Get infoblock type ID
     */
    async getIblockTypeId() {
        return this.call('lists.get.iblock.type.id');
    }
    // ==================== List Elements ====================
    /**
     * Create a new list element
     */
    async createListElement(iblockTypeId, elementCode, fields, iblockId, iblockCode, sectionId, socnetGroupId) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
            ELEMENT_CODE: elementCode,
            FIELDS: fields,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (sectionId !== undefined)
            params.IBLOCK_SECTION_ID = sectionId;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        return this.call('lists.element.add', params);
    }
    /**
     * Get list element(s)
     */
    async getListElements(iblockTypeId, iblockId, iblockCode, elementId, elementCode, filter, select, order, socnetGroupId, start) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (elementId)
            params.ELEMENT_ID = elementId;
        if (elementCode)
            params.ELEMENT_CODE = elementCode;
        if (filter)
            params.FILTER = filter;
        if (select)
            params.SELECT = select;
        if (order)
            params.ELEMENT_ORDER = order;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        if (start !== undefined)
            params.start = start;
        const response = await this.client.post('/lists.element.get', params);
        return {
            elements: response.data.result || [],
            total: response.data.total,
            next: response.data.next,
        };
    }
    /**
     * Update a list element
     */
    async updateListElement(iblockTypeId, elementId, elementCode, fields, iblockId, iblockCode, socnetGroupId) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (elementId)
            params.ELEMENT_ID = elementId;
        if (elementCode)
            params.ELEMENT_CODE = elementCode;
        if (fields)
            params.FIELDS = fields;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        return this.call('lists.element.update', params);
    }
    /**
     * Delete a list element
     */
    async deleteListElement(iblockTypeId, elementId, elementCode, iblockId, iblockCode, socnetGroupId) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (elementId)
            params.ELEMENT_ID = elementId;
        if (elementCode)
            params.ELEMENT_CODE = elementCode;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        return this.call('lists.element.delete', params);
    }
    /**
     * Get file URL from list element
     */
    async getListElementFileUrl(iblockTypeId, elementId, fieldId, iblockId, iblockCode, socnetGroupId) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
            ELEMENT_ID: elementId,
            FIELD_ID: fieldId,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        return this.call('lists.element.get.file.url', params);
    }
    // ==================== List Fields ====================
    /**
     * Create a new field in a list
     */
    async createListField(iblockTypeId, fields, iblockId, iblockCode, socnetGroupId) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
            FIELDS: fields,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        return this.call('lists.field.add', params);
    }
    /**
     * Get fields of a list
     */
    async getListFields(iblockTypeId, iblockId, iblockCode, fieldId, socnetGroupId) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (fieldId)
            params.FIELD_ID = fieldId;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        return this.call('lists.field.get', params);
    }
    /**
     * Update a list field
     */
    async updateListField(iblockTypeId, fieldId, fields, iblockId, iblockCode, socnetGroupId) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
            FIELD_ID: fieldId,
            FIELDS: fields,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        return this.call('lists.field.update', params);
    }
    /**
     * Delete a list field
     */
    async deleteListField(iblockTypeId, fieldId, iblockId, iblockCode, socnetGroupId) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
            FIELD_ID: fieldId,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        return this.call('lists.field.delete', params);
    }
    /**
     * Get available field types for a list
     */
    async getListFieldTypes(iblockTypeId, iblockId, iblockCode, socnetGroupId) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        const result = await this.call('lists.field.type.get', params);
        // Convert object to array
        return Object.entries(result).map(([type, info]) => ({
            TYPE: type,
            NAME: info.NAME,
            DESCRIPTION: info.DESCRIPTION,
        }));
    }
    // ==================== List Sections ====================
    /**
     * Create a new section in a list
     */
    async createListSection(iblockTypeId, sectionCode, fields, iblockId, iblockCode, parentSectionId, socnetGroupId) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
            SECTION_CODE: sectionCode,
            FIELDS: fields,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (parentSectionId !== undefined)
            params.IBLOCK_SECTION_ID = parentSectionId;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        return this.call('lists.section.add', params);
    }
    /**
     * Get sections of a list
     */
    async getListSections(iblockTypeId, iblockId, iblockCode, filter, select, socnetGroupId) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (filter)
            params.FILTER = filter;
        if (select)
            params.SELECT = select;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        const response = await this.client.post('/lists.section.get', params);
        return {
            sections: response.data.result || [],
            total: response.data.total,
        };
    }
    /**
     * Update a list section
     */
    async updateListSection(iblockTypeId, sectionId, sectionCode, fields, iblockId, iblockCode, socnetGroupId) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (sectionId)
            params.SECTION_ID = sectionId;
        if (sectionCode)
            params.SECTION_CODE = sectionCode;
        if (fields)
            params.FIELDS = fields;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        return this.call('lists.section.update', params);
    }
    /**
     * Delete a list section
     */
    async deleteListSection(iblockTypeId, sectionId, sectionCode, iblockId, iblockCode, socnetGroupId) {
        const params = {
            IBLOCK_TYPE_ID: iblockTypeId,
        };
        if (iblockId)
            params.IBLOCK_ID = iblockId;
        if (iblockCode)
            params.IBLOCK_CODE = iblockCode;
        if (sectionId)
            params.SECTION_ID = sectionId;
        if (sectionCode)
            params.SECTION_CODE = sectionCode;
        if (socnetGroupId)
            params.SOCNET_GROUP_ID = socnetGroupId;
        return this.call('lists.section.delete', params);
    }
}
//# sourceMappingURL=bitrix-service.js.map