import { BitrixConfig, BitrixTask, BitrixTaskFields, BitrixTaskSelect, BitrixChecklistItem, BitrixChecklistItemFields, BitrixComment, BitrixCommentFields, BitrixElapsedItem, BitrixElapsedItemFields, BitrixUser, BitrixUserFilter, BitrixDepartment, BitrixDepartmentFilter, BitrixDepartmentTreeNode, BitrixSonetGroup, BitrixGroupMember, BitrixGroupFilter, BitrixFields, IblockTypeId, BitrixList, BitrixListFields, BitrixListMessages, BitrixListElement, BitrixListElementFields, BitrixListElementFilter, BitrixListField, BitrixListFieldCreate, BitrixListFieldUpdate, BitrixListFieldType, BitrixListSection, BitrixListSectionFields, BitrixListSectionFilter } from '../types/bitrix.js';
export declare class BitrixService {
    private client;
    private webhookUrl;
    constructor(config: BitrixConfig);
    private call;
    testConnection(): Promise<{
        success: boolean;
        user: BitrixUser;
    }>;
    getUsers(filter?: Record<string, unknown>): Promise<BitrixUser[]>;
    getCurrentUser(): Promise<BitrixUser>;
    createTask(fields: BitrixTaskFields): Promise<{
        task: BitrixTask;
    }>;
    updateTask(taskId: number, fields: Partial<BitrixTaskFields>): Promise<{
        task: BitrixTask;
    }>;
    getTask(taskId: number, select?: string[]): Promise<{
        task: BitrixTask;
    }>;
    listTasks(params?: BitrixTaskSelect): Promise<{
        tasks: BitrixTask[];
    }>;
    deleteTask(taskId: number): Promise<{
        task: boolean;
    }>;
    getTaskFields(): Promise<{
        fields: BitrixFields;
    }>;
    completeTask(taskId: number): Promise<{
        task: BitrixTask;
    }>;
    renewTask(taskId: number): Promise<{
        task: BitrixTask;
    }>;
    startTask(taskId: number): Promise<{
        task: BitrixTask;
    }>;
    pauseTask(taskId: number): Promise<{
        task: BitrixTask;
    }>;
    deferTask(taskId: number): Promise<{
        task: BitrixTask;
    }>;
    approveTask(taskId: number): Promise<{
        task: BitrixTask;
    }>;
    disapproveTask(taskId: number): Promise<{
        task: BitrixTask;
    }>;
    delegateTask(taskId: number, userId: number): Promise<{
        task: BitrixTask;
    }>;
    addTaskToFavorite(taskId: number): Promise<boolean>;
    removeTaskFromFavorite(taskId: number): Promise<boolean>;
    attachFilesToTask(taskId: number, fileIds: number[]): Promise<boolean>;
    getTaskHistory(taskId: number): Promise<unknown[]>;
    getTaskCounters(userId?: number): Promise<Record<string, number>>;
    addChecklistItem(taskId: number, fields: BitrixChecklistItemFields): Promise<number>;
    updateChecklistItem(taskId: number, itemId: number, fields: Partial<BitrixChecklistItemFields>): Promise<boolean>;
    deleteChecklistItem(taskId: number, itemId: number): Promise<boolean>;
    getChecklistItems(taskId: number): Promise<BitrixChecklistItem[]>;
    completeChecklistItem(taskId: number, itemId: number): Promise<boolean>;
    renewChecklistItem(taskId: number, itemId: number): Promise<boolean>;
    addComment(taskId: number, fields: BitrixCommentFields): Promise<number>;
    updateComment(taskId: number, itemId: number, fields: Partial<BitrixCommentFields>): Promise<boolean>;
    deleteComment(taskId: number, itemId: number): Promise<boolean>;
    getComments(taskId: number): Promise<BitrixComment[]>;
    addElapsedTime(taskId: number, fields: BitrixElapsedItemFields): Promise<number>;
    updateElapsedTime(taskId: number, itemId: number, fields: Partial<BitrixElapsedItemFields>): Promise<boolean>;
    deleteElapsedTime(taskId: number, itemId: number): Promise<boolean>;
    getElapsedTime(taskId: number): Promise<BitrixElapsedItem[]>;
    getUserById(userId: number, select?: string[]): Promise<BitrixUser | null>;
    searchUsers(query: string, active?: boolean): Promise<BitrixUser[]>;
    getUsersFiltered(filter?: BitrixUserFilter, select?: string[], sort?: string, order?: 'ASC' | 'DESC', start?: number): Promise<{
        users: BitrixUser[];
        total?: number;
        next?: number;
    }>;
    getUserFields(): Promise<BitrixFields>;
    getDepartments(filter?: BitrixDepartmentFilter, sort?: string, order?: 'ASC' | 'DESC', start?: number): Promise<{
        departments: BitrixDepartment[];
        total?: number;
        next?: number;
    }>;
    getDepartmentById(departmentId: number): Promise<BitrixDepartment | null>;
    getDepartmentFields(): Promise<BitrixFields>;
    getDepartmentTree(rootId?: number, maxDepth?: number): Promise<BitrixDepartmentTreeNode[]>;
    getDepartmentEmployees(departmentId: number, recursive?: boolean, activeOnly?: boolean): Promise<BitrixUser[]>;
    getGroups(filter?: BitrixGroupFilter, start?: number): Promise<{
        groups: BitrixSonetGroup[];
        total?: number;
        next?: number;
    }>;
    getGroupById(groupId: number): Promise<BitrixSonetGroup | null>;
    getWorkgroupById(groupId: number): Promise<BitrixSonetGroup>;
    getWorkgroups(filter?: Record<string, unknown>, select?: string[], start?: number): Promise<{
        groups: BitrixSonetGroup[];
        total?: number;
        next?: number;
    }>;
    getGroupMembers(groupId: number): Promise<BitrixGroupMember[]>;
    getMyGroups(): Promise<{
        GROUP_ID: number;
        GROUP_NAME: string;
        ROLE: string;
    }[]>;
    checkGroupAccess(groupId: number, feature: string, operation?: string): Promise<boolean>;
    /**
     * Create a new universal list
     */
    createList(iblockTypeId: IblockTypeId, iblockCode: string, fields: BitrixListFields, socnetGroupId?: number, messages?: BitrixListMessages, rights?: Record<string, string>): Promise<number>;
    /**
     * Get list(s) - returns all accessible lists if no ID specified
     */
    getLists(iblockTypeId: IblockTypeId, iblockId?: number, iblockCode?: string, socnetGroupId?: number, start?: number): Promise<{
        lists: BitrixList[];
        total?: number;
        next?: number;
    }>;
    /**
     * Update an existing list
     */
    updateList(iblockTypeId: IblockTypeId, iblockId?: number, iblockCode?: string, fields?: BitrixListFields, messages?: BitrixListMessages, rights?: Record<string, string>): Promise<boolean>;
    /**
     * Delete a list
     */
    deleteList(iblockTypeId: IblockTypeId, iblockId?: number, iblockCode?: string): Promise<boolean>;
    /**
     * Get infoblock type ID
     */
    getIblockTypeId(): Promise<string>;
    /**
     * Create a new list element
     */
    createListElement(iblockTypeId: IblockTypeId, elementCode: string, fields: BitrixListElementFields | Record<string, unknown>, iblockId?: number, iblockCode?: string, sectionId?: number, socnetGroupId?: number): Promise<number>;
    /**
     * Get list element(s)
     */
    getListElements(iblockTypeId: IblockTypeId, iblockId?: number, iblockCode?: string, elementId?: number, elementCode?: string, filter?: BitrixListElementFilter, select?: string[], order?: Record<string, 'asc' | 'desc'>, socnetGroupId?: number, start?: number): Promise<{
        elements: BitrixListElement[];
        total?: number;
        next?: number;
    }>;
    /**
     * Update a list element
     */
    updateListElement(iblockTypeId: IblockTypeId, elementId?: number, elementCode?: string, fields?: BitrixListElementFields | Record<string, unknown>, iblockId?: number, iblockCode?: string, socnetGroupId?: number): Promise<boolean>;
    /**
     * Delete a list element
     */
    deleteListElement(iblockTypeId: IblockTypeId, elementId?: number, elementCode?: string, iblockId?: number, iblockCode?: string, socnetGroupId?: number): Promise<boolean>;
    /**
     * Get file URL from list element
     */
    getListElementFileUrl(iblockTypeId: IblockTypeId, elementId: number, fieldId: string, iblockId?: number, iblockCode?: string, socnetGroupId?: number): Promise<string>;
    /**
     * Create a new field in a list
     */
    createListField(iblockTypeId: IblockTypeId, fields: BitrixListFieldCreate, iblockId?: number, iblockCode?: string, socnetGroupId?: number): Promise<string>;
    /**
     * Get fields of a list
     */
    getListFields(iblockTypeId: IblockTypeId, iblockId?: number, iblockCode?: string, fieldId?: string, socnetGroupId?: number): Promise<Record<string, BitrixListField>>;
    /**
     * Update a list field
     */
    updateListField(iblockTypeId: IblockTypeId, fieldId: string, fields: BitrixListFieldUpdate, iblockId?: number, iblockCode?: string, socnetGroupId?: number): Promise<boolean>;
    /**
     * Delete a list field
     */
    deleteListField(iblockTypeId: IblockTypeId, fieldId: string, iblockId?: number, iblockCode?: string, socnetGroupId?: number): Promise<boolean>;
    /**
     * Get available field types for a list
     */
    getListFieldTypes(iblockTypeId: IblockTypeId, iblockId?: number, iblockCode?: string, socnetGroupId?: number): Promise<BitrixListFieldType[]>;
    /**
     * Create a new section in a list
     */
    createListSection(iblockTypeId: IblockTypeId, sectionCode: string, fields: BitrixListSectionFields, iblockId?: number, iblockCode?: string, parentSectionId?: number, socnetGroupId?: number): Promise<number>;
    /**
     * Get sections of a list
     */
    getListSections(iblockTypeId: IblockTypeId, iblockId?: number, iblockCode?: string, filter?: BitrixListSectionFilter, select?: string[], socnetGroupId?: number): Promise<{
        sections: BitrixListSection[];
        total?: number;
    }>;
    /**
     * Update a list section
     */
    updateListSection(iblockTypeId: IblockTypeId, sectionId?: number, sectionCode?: string, fields?: BitrixListSectionFields, iblockId?: number, iblockCode?: string, socnetGroupId?: number): Promise<boolean>;
    /**
     * Delete a list section
     */
    deleteListSection(iblockTypeId: IblockTypeId, sectionId?: number, sectionCode?: string, iblockId?: number, iblockCode?: string, socnetGroupId?: number): Promise<boolean>;
}
//# sourceMappingURL=bitrix-service.d.ts.map