import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  BitrixConfig,
  BitrixResponse,
  BitrixTask,
  BitrixTaskFields,
  BitrixTaskSelect,
  BitrixChecklistItem,
  BitrixChecklistItemFields,
  BitrixComment,
  BitrixCommentFields,
  BitrixElapsedItem,
  BitrixElapsedItemFields,
  BitrixUser,
  BitrixUserFilter,
  BitrixDepartment,
  BitrixDepartmentFilter,
  BitrixDepartmentTreeNode,
  BitrixSonetGroup,
  BitrixGroupMember,
  BitrixGroupFilter,
  BitrixFields,
  BitrixError,
  // Lists types
  IblockTypeId,
  BitrixList,
  BitrixListFields,
  BitrixListMessages,
  BitrixListElement,
  BitrixListElementFields,
  BitrixListElementFilter,
  BitrixListField,
  BitrixListFieldCreate,
  BitrixListFieldUpdate,
  BitrixListFieldType,
  BitrixListSection,
  BitrixListSectionFields,
  BitrixListSectionFilter,
} from '../types/bitrix.js';

export class BitrixService {
  private client: AxiosInstance;
  private webhookUrl: string;

  constructor(config: BitrixConfig) {
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

  private async call<T>(method: string, params?: Record<string, unknown>): Promise<T> {
    try {
      const response = await this.client.post<BitrixResponse<T>>(
        `/${method}`,
        params || {}
      );
      return response.data.result;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<BitrixError>;
        if (axiosError.response?.data?.error) {
          throw new Error(
            `Bitrix24 API Error: ${axiosError.response.data.error} - ${axiosError.response.data.error_description}`
          );
        }
        throw new Error(`HTTP Error: ${axiosError.message}`);
      }
      throw error;
    }
  }

  // ==================== Connection Test ====================

  async testConnection(): Promise<{ success: boolean; user: BitrixUser }> {
    const result = await this.call<BitrixUser>('user.current');
    return { success: true, user: result };
  }

  // ==================== Users ====================

  async getUsers(filter?: Record<string, unknown>): Promise<BitrixUser[]> {
    return this.call<BitrixUser[]>('user.get', { filter });
  }

  async getCurrentUser(): Promise<BitrixUser> {
    return this.call<BitrixUser>('user.current');
  }

  // ==================== Task CRUD ====================

  async createTask(fields: BitrixTaskFields): Promise<{ task: BitrixTask }> {
    return this.call<{ task: BitrixTask }>('tasks.task.add', { fields });
  }

  async updateTask(taskId: number, fields: Partial<BitrixTaskFields>): Promise<{ task: BitrixTask }> {
    return this.call<{ task: BitrixTask }>('tasks.task.update', {
      taskId,
      fields,
    });
  }

  async getTask(taskId: number, select?: string[]): Promise<{ task: BitrixTask }> {
    const params: Record<string, unknown> = { taskId };
    if (select) {
      params.select = select;
    }
    return this.call<{ task: BitrixTask }>('tasks.task.get', params);
  }

  async listTasks(params?: BitrixTaskSelect): Promise<{ tasks: BitrixTask[] }> {
    return this.call<{ tasks: BitrixTask[] }>('tasks.task.list', params as Record<string, unknown> | undefined);
  }

  async deleteTask(taskId: number): Promise<{ task: boolean }> {
    return this.call<{ task: boolean }>('tasks.task.delete', { taskId });
  }

  async getTaskFields(): Promise<{ fields: BitrixFields }> {
    return this.call<{ fields: BitrixFields }>('tasks.task.getFields');
  }

  // ==================== Task Status Management ====================

  async completeTask(taskId: number): Promise<{ task: BitrixTask }> {
    return this.call<{ task: BitrixTask }>('tasks.task.complete', { taskId });
  }

  async renewTask(taskId: number): Promise<{ task: BitrixTask }> {
    return this.call<{ task: BitrixTask }>('tasks.task.renew', { taskId });
  }

  async startTask(taskId: number): Promise<{ task: BitrixTask }> {
    return this.call<{ task: BitrixTask }>('tasks.task.start', { taskId });
  }

  async pauseTask(taskId: number): Promise<{ task: BitrixTask }> {
    return this.call<{ task: BitrixTask }>('tasks.task.pause', { taskId });
  }

  async deferTask(taskId: number): Promise<{ task: BitrixTask }> {
    return this.call<{ task: BitrixTask }>('tasks.task.defer', { taskId });
  }

  async approveTask(taskId: number): Promise<{ task: BitrixTask }> {
    return this.call<{ task: BitrixTask }>('tasks.task.approve', { taskId });
  }

  async disapproveTask(taskId: number): Promise<{ task: BitrixTask }> {
    return this.call<{ task: BitrixTask }>('tasks.task.disapprove', { taskId });
  }

  async delegateTask(taskId: number, userId: number): Promise<{ task: BitrixTask }> {
    return this.call<{ task: BitrixTask }>('tasks.task.delegate', {
      taskId,
      userId,
    });
  }

  // ==================== Favorites ====================

  async addTaskToFavorite(taskId: number): Promise<boolean> {
    return this.call<boolean>('tasks.task.favorite.add', { taskId });
  }

  async removeTaskFromFavorite(taskId: number): Promise<boolean> {
    return this.call<boolean>('tasks.task.favorite.remove', { taskId });
  }

  // ==================== Files ====================

  async attachFilesToTask(taskId: number, fileIds: number[]): Promise<boolean> {
    return this.call<boolean>('tasks.task.files.attach', {
      taskId,
      fileIds,
    });
  }

  // ==================== History ====================

  async getTaskHistory(taskId: number): Promise<unknown[]> {
    return this.call<unknown[]>('tasks.task.history.list', { taskId });
  }

  // ==================== Counters ====================

  async getTaskCounters(userId?: number): Promise<Record<string, number>> {
    const params: Record<string, unknown> = {};
    if (userId) {
      params.userId = userId;
    }
    return this.call<Record<string, number>>('tasks.task.counters.get', params);
  }

  // ==================== Checklist Items ====================

  async addChecklistItem(
    taskId: number,
    fields: BitrixChecklistItemFields
  ): Promise<number> {
    return this.call<number>('task.checklistitem.add', {
      TASKID: taskId,
      FIELDS: fields,
    });
  }

  async updateChecklistItem(
    taskId: number,
    itemId: number,
    fields: Partial<BitrixChecklistItemFields>
  ): Promise<boolean> {
    return this.call<boolean>('task.checklistitem.update', {
      TASKID: taskId,
      ITEMID: itemId,
      FIELDS: fields,
    });
  }

  async deleteChecklistItem(taskId: number, itemId: number): Promise<boolean> {
    return this.call<boolean>('task.checklistitem.delete', {
      TASKID: taskId,
      ITEMID: itemId,
    });
  }

  async getChecklistItems(taskId: number): Promise<BitrixChecklistItem[]> {
    return this.call<BitrixChecklistItem[]>('task.checklistitem.getlist', {
      TASKID: taskId,
    });
  }

  async completeChecklistItem(taskId: number, itemId: number): Promise<boolean> {
    return this.call<boolean>('task.checklistitem.complete', {
      TASKID: taskId,
      ITEMID: itemId,
    });
  }

  async renewChecklistItem(taskId: number, itemId: number): Promise<boolean> {
    return this.call<boolean>('task.checklistitem.renew', {
      TASKID: taskId,
      ITEMID: itemId,
    });
  }

  // ==================== Comments ====================

  async addComment(taskId: number, fields: BitrixCommentFields): Promise<number> {
    return this.call<number>('task.commentitem.add', {
      TASKID: taskId,
      FIELDS: fields,
    });
  }

  async updateComment(
    taskId: number,
    itemId: number,
    fields: Partial<BitrixCommentFields>
  ): Promise<boolean> {
    return this.call<boolean>('task.commentitem.update', {
      TASKID: taskId,
      ITEMID: itemId,
      FIELDS: fields,
    });
  }

  async deleteComment(taskId: number, itemId: number): Promise<boolean> {
    return this.call<boolean>('task.commentitem.delete', {
      TASKID: taskId,
      ITEMID: itemId,
    });
  }

  async getComments(taskId: number): Promise<BitrixComment[]> {
    return this.call<BitrixComment[]>('task.commentitem.getlist', {
      TASKID: taskId,
    });
  }

  // ==================== Elapsed Time (Time Tracking) ====================

  async addElapsedTime(
    taskId: number,
    fields: BitrixElapsedItemFields
  ): Promise<number> {
    return this.call<number>('task.elapseditem.add', {
      TASKID: taskId,
      FIELDS: fields,
    });
  }

  async updateElapsedTime(
    taskId: number,
    itemId: number,
    fields: Partial<BitrixElapsedItemFields>
  ): Promise<boolean> {
    return this.call<boolean>('task.elapseditem.update', {
      TASKID: taskId,
      ITEMID: itemId,
      FIELDS: fields,
    });
  }

  async deleteElapsedTime(taskId: number, itemId: number): Promise<boolean> {
    return this.call<boolean>('task.elapseditem.delete', {
      TASKID: taskId,
      ITEMID: itemId,
    });
  }

  async getElapsedTime(taskId: number): Promise<BitrixElapsedItem[]> {
    return this.call<BitrixElapsedItem[]>('task.elapseditem.getlist', {
      TASKID: taskId,
    });
  }

  // ==================== Extended Users ====================

  async getUserById(userId: number, select?: string[]): Promise<BitrixUser | null> {
    const params: Record<string, unknown> = {
      filter: { ID: userId },
    };
    if (select) {
      params.FIELDS = select;
    }
    const users = await this.call<BitrixUser[]>('user.get', params);
    return users.length > 0 ? users[0] : null;
  }

  async searchUsers(query: string, active?: boolean): Promise<BitrixUser[]> {
    const params: Record<string, unknown> = {
      FIND: query,
    };
    if (active !== undefined) {
      params.ACTIVE = active;
    }
    return this.call<BitrixUser[]>('user.search', params);
  }

  async getUsersFiltered(
    filter?: BitrixUserFilter,
    select?: string[],
    sort?: string,
    order?: 'ASC' | 'DESC',
    start?: number
  ): Promise<{ users: BitrixUser[]; total?: number; next?: number }> {
    const params: Record<string, unknown> = {};
    if (filter) params.filter = filter;
    if (select) params.FIELDS = select;
    if (sort) params.sort = sort;
    if (order) params.order = order;
    if (start !== undefined) params.start = start;

    const response = await this.client.post<BitrixResponse<BitrixUser[]>>(
      '/user.get',
      params
    );
    return {
      users: response.data.result,
      total: response.data.total,
      next: response.data.next,
    };
  }

  async getUserFields(): Promise<BitrixFields> {
    return this.call<BitrixFields>('user.fields');
  }

  // ==================== Departments ====================

  async getDepartments(
    filter?: BitrixDepartmentFilter,
    sort?: string,
    order?: 'ASC' | 'DESC',
    start?: number
  ): Promise<{ departments: BitrixDepartment[]; total?: number; next?: number }> {
    const params: Record<string, unknown> = {};
    if (filter) {
      if (filter.ID !== undefined) params.ID = filter.ID;
      if (filter.NAME) params.NAME = filter.NAME;
      if (filter.SORT !== undefined) params.SORT = filter.SORT;
      if (filter.PARENT !== undefined) params.PARENT = filter.PARENT;
      if (filter.UF_HEAD !== undefined) params.UF_HEAD = filter.UF_HEAD;
    }
    if (sort) params.sort = sort;
    if (order) params.order = order;
    if (start !== undefined) params.START = start;

    const response = await this.client.post<BitrixResponse<BitrixDepartment[]>>(
      '/department.get',
      params
    );
    return {
      departments: response.data.result,
      total: response.data.total,
      next: response.data.next,
    };
  }

  async getDepartmentById(departmentId: number): Promise<BitrixDepartment | null> {
    const result = await this.getDepartments({ ID: departmentId });
    return result.departments.length > 0 ? result.departments[0] : null;
  }

  async getDepartmentFields(): Promise<BitrixFields> {
    return this.call<BitrixFields>('department.fields');
  }

  async getDepartmentTree(rootId?: number, maxDepth?: number): Promise<BitrixDepartmentTreeNode[]> {
    // Get all departments
    const allDepartments: BitrixDepartment[] = [];
    let start = 0;
    let hasMore = true;

    while (hasMore) {
      const result = await this.getDepartments(undefined, 'SORT', 'ASC', start);
      allDepartments.push(...result.departments);
      if (result.next) {
        start = result.next;
      } else {
        hasMore = false;
      }
    }

    // Build tree structure
    const buildTree = (parentId?: number, depth: number = 0): BitrixDepartmentTreeNode[] => {
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

  async getDepartmentEmployees(
    departmentId: number,
    recursive: boolean = false,
    activeOnly: boolean = true
  ): Promise<BitrixUser[]> {
    const departmentIds: number[] = [departmentId];

    // If recursive, get all child departments
    if (recursive) {
      const allDepartments: BitrixDepartment[] = [];
      let start = 0;
      let hasMore = true;

      while (hasMore) {
        const result = await this.getDepartments(undefined, undefined, undefined, start);
        allDepartments.push(...result.departments);
        if (result.next) {
          start = result.next;
        } else {
          hasMore = false;
        }
      }

      const findChildren = (parentId: number) => {
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
    const allUsers: BitrixUser[] = [];
    const userIds = new Set<number>();

    for (const deptId of departmentIds) {
      let start = 0;
      let hasMore = true;

      while (hasMore) {
        const filter: BitrixUserFilter = {
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
        } else {
          hasMore = false;
        }
      }
    }

    return allUsers;
  }

  // ==================== Sonet Groups ====================

  async getGroups(
    filter?: BitrixGroupFilter,
    start?: number
  ): Promise<{ groups: BitrixSonetGroup[]; total?: number; next?: number }> {
    const params: Record<string, unknown> = {};
    if (filter) params.FILTER = filter;
    if (start !== undefined) params.start = start;

    const response = await this.client.post<BitrixResponse<BitrixSonetGroup[]>>(
      '/sonet_group.get',
      params
    );
    return {
      groups: response.data.result,
      total: response.data.total,
      next: response.data.next,
    };
  }

  async getGroupById(groupId: number): Promise<BitrixSonetGroup | null> {
    const params = {
      FILTER: { ID: groupId },
    };
    const groups = await this.call<BitrixSonetGroup[]>('sonet_group.get', params);
    return groups.length > 0 ? groups[0] : null;
  }

  async getWorkgroupById(groupId: number): Promise<BitrixSonetGroup> {
    return this.call<BitrixSonetGroup>('socialnetwork.api.workgroup.get', {
      params: { groupId },
    });
  }

  async getWorkgroups(
    filter?: Record<string, unknown>,
    select?: string[],
    start?: number
  ): Promise<{ groups: BitrixSonetGroup[]; total?: number; next?: number }> {
    const params: Record<string, unknown> = {};
    if (filter) params.filter = filter;
    // Always request essential fields for proper display
    params.select = select || ['ID', 'NAME', 'DESCRIPTION', 'OWNER_ID', 'NUMBER_OF_MEMBERS', 'PROJECT', 'VISIBLE', 'OPENED'];
    if (start !== undefined) params.start = start;

    // API returns {result: {workgroups: [...], ...}}
    interface WorkgroupListResponse {
      workgroups: Array<{
        id: string;
        name: string;
        description?: string;
        ownerId: string;
        numberOfMembers?: string;
        project?: string;
        visible?: string;
        opened?: string;
      }>;
    }

    const response = await this.client.post<BitrixResponse<WorkgroupListResponse>>(
      '/socialnetwork.api.workgroup.list',
      params
    );

    // Map API response (camelCase) to our interface format (UPPER_CASE)
    const workgroups = response.data.result?.workgroups || [];
    const groups: BitrixSonetGroup[] = workgroups.map(w => ({
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

  async getGroupMembers(groupId: number): Promise<BitrixGroupMember[]> {
    return this.call<BitrixGroupMember[]>('sonet_group.user.get', {
      ID: groupId,
    });
  }

  async getMyGroups(): Promise<{ GROUP_ID: number; GROUP_NAME: string; ROLE: string }[]> {
    // sonet_group.user.groups returns simplified format: {GROUP_ID, GROUP_NAME, ROLE}
    return this.call<{ GROUP_ID: number; GROUP_NAME: string; ROLE: string }[]>('sonet_group.user.groups');
  }

  async checkGroupAccess(groupId: number, feature: string, operation: string = 'view'): Promise<boolean> {
    const result = await this.call<boolean>('sonet_group.feature.access', {
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
  async createList(
    iblockTypeId: IblockTypeId,
    iblockCode: string,
    fields: BitrixListFields,
    socnetGroupId?: number,
    messages?: BitrixListMessages,
    rights?: Record<string, string>
  ): Promise<number> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
      IBLOCK_CODE: iblockCode,
      FIELDS: fields,
    };
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;
    if (messages) params.MESSAGES = messages;
    if (rights) params.RIGHTS = rights;

    return this.call<number>('lists.add', params);
  }

  /**
   * Get list(s) - returns all accessible lists if no ID specified
   */
  async getLists(
    iblockTypeId: IblockTypeId,
    iblockId?: number,
    iblockCode?: string,
    socnetGroupId?: number,
    start?: number
  ): Promise<{ lists: BitrixList[]; total?: number; next?: number }> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;
    if (start !== undefined) params.start = start;

    const response = await this.client.post<BitrixResponse<BitrixList[]>>(
      '/lists.get',
      params
    );
    return {
      lists: response.data.result || [],
      total: response.data.total,
      next: response.data.next,
    };
  }

  /**
   * Update an existing list
   */
  async updateList(
    iblockTypeId: IblockTypeId,
    iblockId?: number,
    iblockCode?: string,
    fields?: BitrixListFields,
    messages?: BitrixListMessages,
    rights?: Record<string, string>
  ): Promise<boolean> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (fields) params.FIELDS = fields;
    if (messages) params.MESSAGES = messages;
    if (rights) params.RIGHTS = rights;

    return this.call<boolean>('lists.update', params);
  }

  /**
   * Delete a list
   */
  async deleteList(
    iblockTypeId: IblockTypeId,
    iblockId?: number,
    iblockCode?: string
  ): Promise<boolean> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;

    return this.call<boolean>('lists.delete', params);
  }

  /**
   * Get infoblock type ID
   */
  async getIblockTypeId(): Promise<string> {
    return this.call<string>('lists.get.iblock.type.id');
  }

  // ==================== List Elements ====================

  /**
   * Create a new list element
   */
  async createListElement(
    iblockTypeId: IblockTypeId,
    elementCode: string,
    fields: BitrixListElementFields | Record<string, unknown>,
    iblockId?: number,
    iblockCode?: string,
    sectionId?: number,
    socnetGroupId?: number
  ): Promise<number> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
      ELEMENT_CODE: elementCode,
      FIELDS: fields,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (sectionId !== undefined) params.IBLOCK_SECTION_ID = sectionId;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;

    return this.call<number>('lists.element.add', params);
  }

  /**
   * Get list element(s)
   */
  async getListElements(
    iblockTypeId: IblockTypeId,
    iblockId?: number,
    iblockCode?: string,
    elementId?: number,
    elementCode?: string,
    filter?: BitrixListElementFilter,
    select?: string[],
    order?: Record<string, 'asc' | 'desc'>,
    socnetGroupId?: number,
    start?: number
  ): Promise<{ elements: BitrixListElement[]; total?: number; next?: number }> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (elementId) params.ELEMENT_ID = elementId;
    if (elementCode) params.ELEMENT_CODE = elementCode;
    if (filter) params.FILTER = filter;
    if (select) params.SELECT = select;
    if (order) params.ELEMENT_ORDER = order;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;
    if (start !== undefined) params.start = start;

    const response = await this.client.post<BitrixResponse<BitrixListElement[]>>(
      '/lists.element.get',
      params
    );
    return {
      elements: response.data.result || [],
      total: response.data.total,
      next: response.data.next,
    };
  }

  /**
   * Update a list element
   */
  async updateListElement(
    iblockTypeId: IblockTypeId,
    elementId?: number,
    elementCode?: string,
    fields?: BitrixListElementFields | Record<string, unknown>,
    iblockId?: number,
    iblockCode?: string,
    socnetGroupId?: number
  ): Promise<boolean> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (elementId) params.ELEMENT_ID = elementId;
    if (elementCode) params.ELEMENT_CODE = elementCode;
    if (fields) params.FIELDS = fields;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;

    return this.call<boolean>('lists.element.update', params);
  }

  /**
   * Delete a list element
   */
  async deleteListElement(
    iblockTypeId: IblockTypeId,
    elementId?: number,
    elementCode?: string,
    iblockId?: number,
    iblockCode?: string,
    socnetGroupId?: number
  ): Promise<boolean> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (elementId) params.ELEMENT_ID = elementId;
    if (elementCode) params.ELEMENT_CODE = elementCode;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;

    return this.call<boolean>('lists.element.delete', params);
  }

  /**
   * Get file URL from list element
   */
  async getListElementFileUrl(
    iblockTypeId: IblockTypeId,
    elementId: number,
    fieldId: string,
    iblockId?: number,
    iblockCode?: string,
    socnetGroupId?: number
  ): Promise<string> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
      ELEMENT_ID: elementId,
      FIELD_ID: fieldId,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;

    return this.call<string>('lists.element.get.file.url', params);
  }

  // ==================== List Fields ====================

  /**
   * Create a new field in a list
   */
  async createListField(
    iblockTypeId: IblockTypeId,
    fields: BitrixListFieldCreate,
    iblockId?: number,
    iblockCode?: string,
    socnetGroupId?: number
  ): Promise<string> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
      FIELDS: fields,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;

    return this.call<string>('lists.field.add', params);
  }

  /**
   * Get fields of a list
   */
  async getListFields(
    iblockTypeId: IblockTypeId,
    iblockId?: number,
    iblockCode?: string,
    fieldId?: string,
    socnetGroupId?: number
  ): Promise<Record<string, BitrixListField>> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (fieldId) params.FIELD_ID = fieldId;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;

    return this.call<Record<string, BitrixListField>>('lists.field.get', params);
  }

  /**
   * Update a list field
   */
  async updateListField(
    iblockTypeId: IblockTypeId,
    fieldId: string,
    fields: BitrixListFieldUpdate,
    iblockId?: number,
    iblockCode?: string,
    socnetGroupId?: number
  ): Promise<boolean> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
      FIELD_ID: fieldId,
      FIELDS: fields,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;

    return this.call<boolean>('lists.field.update', params);
  }

  /**
   * Delete a list field
   */
  async deleteListField(
    iblockTypeId: IblockTypeId,
    fieldId: string,
    iblockId?: number,
    iblockCode?: string,
    socnetGroupId?: number
  ): Promise<boolean> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
      FIELD_ID: fieldId,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;

    return this.call<boolean>('lists.field.delete', params);
  }

  /**
   * Get available field types for a list
   */
  async getListFieldTypes(
    iblockTypeId: IblockTypeId,
    iblockId?: number,
    iblockCode?: string,
    socnetGroupId?: number
  ): Promise<BitrixListFieldType[]> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;

    const result = await this.call<Record<string, { NAME: string; DESCRIPTION?: string }>>('lists.field.type.get', params);
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
  async createListSection(
    iblockTypeId: IblockTypeId,
    sectionCode: string,
    fields: BitrixListSectionFields,
    iblockId?: number,
    iblockCode?: string,
    parentSectionId?: number,
    socnetGroupId?: number
  ): Promise<number> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
      SECTION_CODE: sectionCode,
      FIELDS: fields,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (parentSectionId !== undefined) params.IBLOCK_SECTION_ID = parentSectionId;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;

    return this.call<number>('lists.section.add', params);
  }

  /**
   * Get sections of a list
   */
  async getListSections(
    iblockTypeId: IblockTypeId,
    iblockId?: number,
    iblockCode?: string,
    filter?: BitrixListSectionFilter,
    select?: string[],
    socnetGroupId?: number
  ): Promise<{ sections: BitrixListSection[]; total?: number }> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (filter) params.FILTER = filter;
    if (select) params.SELECT = select;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;

    const response = await this.client.post<BitrixResponse<BitrixListSection[]>>(
      '/lists.section.get',
      params
    );
    return {
      sections: response.data.result || [],
      total: response.data.total,
    };
  }

  /**
   * Update a list section
   */
  async updateListSection(
    iblockTypeId: IblockTypeId,
    sectionId?: number,
    sectionCode?: string,
    fields?: BitrixListSectionFields,
    iblockId?: number,
    iblockCode?: string,
    socnetGroupId?: number
  ): Promise<boolean> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (sectionId) params.SECTION_ID = sectionId;
    if (sectionCode) params.SECTION_CODE = sectionCode;
    if (fields) params.FIELDS = fields;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;

    return this.call<boolean>('lists.section.update', params);
  }

  /**
   * Delete a list section
   */
  async deleteListSection(
    iblockTypeId: IblockTypeId,
    sectionId?: number,
    sectionCode?: string,
    iblockId?: number,
    iblockCode?: string,
    socnetGroupId?: number
  ): Promise<boolean> {
    const params: Record<string, unknown> = {
      IBLOCK_TYPE_ID: iblockTypeId,
    };
    if (iblockId) params.IBLOCK_ID = iblockId;
    if (iblockCode) params.IBLOCK_CODE = iblockCode;
    if (sectionId) params.SECTION_ID = sectionId;
    if (sectionCode) params.SECTION_CODE = sectionCode;
    if (socnetGroupId) params.SOCNET_GROUP_ID = socnetGroupId;

    return this.call<boolean>('lists.section.delete', params);
  }
}
