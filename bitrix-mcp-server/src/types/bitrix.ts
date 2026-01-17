// Bitrix24 REST API Types

export interface BitrixConfig {
  webhookUrl: string;
  timeout?: number;
}

// Task fields
export interface BitrixTask {
  id: number;
  title: string;
  description?: string;
  responsibleId: number;
  createdBy: number;
  createdDate?: string;
  changedBy?: number;
  changedDate?: string;
  statusChangedBy?: number;
  statusChangedDate?: string;
  closedBy?: number;
  closedDate?: string;
  deadline?: string;
  startDatePlan?: string;
  endDatePlan?: string;
  priority?: TaskPriority;
  status?: TaskStatus;
  accomplices?: number[];
  auditors?: number[];
  tags?: string[];
  groupId?: number;
  parentId?: number;
  timeEstimate?: number;
  timeSpentInLogs?: number;
  allowChangeDeadline?: boolean;
  allowTimeTracking?: boolean;
  taskControl?: boolean;
  addInReport?: boolean;
  mark?: TaskMark;
  forumTopicId?: number;
  commentsCount?: number;
  favorite?: boolean;
  ufCrmTask?: string[];
  ufTaskWebdavFiles?: number[];
}

// Task creation/update fields
export interface BitrixTaskFields {
  TITLE: string;
  DESCRIPTION?: string;
  RESPONSIBLE_ID: number;
  CREATED_BY?: number;
  ACCOMPLICES?: number[];
  AUDITORS?: number[];
  DEADLINE?: string;
  START_DATE_PLAN?: string;
  END_DATE_PLAN?: string;
  PRIORITY?: TaskPriority;
  GROUP_ID?: number;
  PARENT_ID?: number;
  TAGS?: string[];
  TIME_ESTIMATE?: number;
  ALLOW_CHANGE_DEADLINE?: 'Y' | 'N';
  ALLOW_TIME_TRACKING?: 'Y' | 'N';
  TASK_CONTROL?: 'Y' | 'N';
  ADD_IN_REPORT?: 'Y' | 'N';
  UF_CRM_TASK?: string[];
  UF_TASK_WEBDAV_FILES?: string[];
  SE_PARAMETER?: SeParameter[];
}

export interface SeParameter {
  CODE: number;
  VALUE: 'Y' | 'N';
}

export enum TaskPriority {
  LOW = 0,
  NORMAL = 1,
  HIGH = 2,
}

export enum TaskStatus {
  NEW = 1,
  PENDING = 2,
  IN_PROGRESS = 3,
  SUPPOSEDLY_COMPLETED = 4,
  COMPLETED = 5,
  DEFERRED = 6,
}

export enum TaskMark {
  NEGATIVE = 'N',
  POSITIVE = 'P',
}

// Checklist item
export interface BitrixChecklistItem {
  ID: number;
  TASK_ID: number;
  TITLE: string;
  SORT_INDEX: number;
  IS_COMPLETE: 'Y' | 'N';
  PARENT_ID?: number;
  MEMBERS?: number[];
}

export interface BitrixChecklistItemFields {
  TITLE: string;
  SORT_INDEX?: number;
  IS_COMPLETE?: 'Y' | 'N';
  PARENT_ID?: number;
}

// Comment
export interface BitrixComment {
  ID: number;
  TASK_ID: number;
  AUTHOR_ID: number;
  AUTHOR_NAME?: string;
  POST_MESSAGE: string;
  POST_DATE: string;
}

export interface BitrixCommentFields {
  POST_MESSAGE: string;
  AUTHOR_ID?: number;
}

// Elapsed time (time tracking)
export interface BitrixElapsedItem {
  ID: number;
  TASK_ID: number;
  USER_ID: number;
  COMMENT_TEXT?: string;
  SECONDS: number;
  MINUTES?: number;
  CREATED_DATE: string;
  DATE_START?: string;
  DATE_STOP?: string;
}

export interface BitrixElapsedItemFields {
  SECONDS: number;
  COMMENT_TEXT?: string;
  USER_ID?: number;
  DATE_START?: string;
  DATE_STOP?: string;
}

// User (extended)
export interface BitrixUser {
  ID: number;
  NAME: string;
  LAST_NAME: string;
  SECOND_NAME?: string;
  EMAIL?: string;
  PERSONAL_PHONE?: string;
  PERSONAL_MOBILE?: string;
  PERSONAL_PHOTO?: string;
  PERSONAL_GENDER?: string;
  PERSONAL_BIRTHDAY?: string;
  PERSONAL_CITY?: string;
  WORK_PHONE?: string;
  WORK_POSITION?: string;
  WORK_COMPANY?: string;
  UF_DEPARTMENT?: number[];
  UF_PHONE_INNER?: string;
  ACTIVE: boolean;
  IS_ONLINE?: string;
  DATE_REGISTER?: string;
  LAST_LOGIN?: string;
  LAST_ACTIVITY_DATE?: string;
  USER_TYPE?: 'employee' | 'extranet' | 'email';
}

// User filter for user.get
export interface BitrixUserFilter {
  ID?: number | number[];
  ACTIVE?: boolean;
  UF_DEPARTMENT?: number | number[];
  IS_ONLINE?: 'Y' | 'N';
  USER_TYPE?: 'employee' | 'extranet' | 'email';
  NAME_SEARCH?: string;
  '%NAME'?: string;
  '%LAST_NAME'?: string;
  '%WORK_POSITION'?: string;
}

// Department
export interface BitrixDepartment {
  ID: number;
  NAME: string;
  SORT: number;
  PARENT?: number;
  UF_HEAD?: number;
}

// Department filter for department.get
export interface BitrixDepartmentFilter {
  ID?: number;
  NAME?: string;
  SORT?: number;
  PARENT?: number;
  UF_HEAD?: number;
}

// Department tree node (for hierarchical structure)
export interface BitrixDepartmentTreeNode extends BitrixDepartment {
  children?: BitrixDepartmentTreeNode[];
  employees?: BitrixUser[];
}

// Sonet Group (Workgroup)
export interface BitrixSonetGroup {
  ID: number;
  NAME: string;
  DESCRIPTION?: string;
  DATE_CREATE?: string;
  DATE_UPDATE?: string;
  DATE_ACTIVITY?: string;
  ACTIVE?: string;
  VISIBLE?: string;
  OPENED?: string;
  CLOSED?: string;
  SUBJECT_ID?: number;
  OWNER_ID: number;
  KEYWORDS?: string;
  IMAGE_ID?: number;
  NUMBER_OF_MEMBERS?: number;
  NUMBER_OF_MODERATORS?: number;
  INITIATE_PERMS?: string;
  SPAM_PERMS?: string;
  PROJECT?: string;
  PROJECT_DATE_START?: string;
  PROJECT_DATE_FINISH?: string;
  SCRUM_OWNER_ID?: number;
  SCRUM_MASTER_ID?: number;
  SCRUM_SPRINT_DURATION?: number;
  SCRUM_TASK_RESPONSIBLE?: string;
}

// Group member
export interface BitrixGroupMember {
  USER_ID: number;
  ROLE: 'A' | 'E' | 'K' | 'M';  // A=owner, E=moderator, K=member, M=waiting
  AUTO_MEMBER?: string;
  DATE_CREATE?: string;
  DATE_UPDATE?: string;
  USER?: BitrixUser;
}

// Group filter for sonet_group.get
export interface BitrixGroupFilter {
  ID?: number | number[];
  SITE_ID?: string;
  NAME?: string;
  OWNER_ID?: number;
  VISIBLE?: 'Y' | 'N';
  OPENED?: 'Y' | 'N';
  CLOSED?: 'Y' | 'N';
  PROJECT?: 'Y' | 'N';
  ACTIVE?: 'Y' | 'N';
}

// API Response types
export interface BitrixResponse<T> {
  result: T;
  time?: {
    start: number;
    finish: number;
    duration: number;
    processing: number;
    date_start: string;
    date_finish: string;
  };
  total?: number;
  next?: number;
}

export interface BitrixTaskResponse {
  task: BitrixTask;
}

export interface BitrixTaskListResponse {
  tasks: BitrixTask[];
}

export interface BitrixError {
  error: string;
  error_description: string;
}

// Filter types for task list
export interface BitrixTaskFilter {
  ID?: number | number[];
  PARENT_ID?: number;
  GROUP_ID?: number;
  CREATED_BY?: number;
  RESPONSIBLE_ID?: number;
  ACCOMPLICE?: number;
  AUDITOR?: number;
  STATUS?: TaskStatus | TaskStatus[];
  PRIORITY?: TaskPriority;
  REAL_STATUS?: number;
  MARK?: TaskMark;
  TAG?: string;
  '>=DEADLINE'?: string;
  '<=DEADLINE'?: string;
  '>=CREATED_DATE'?: string;
  '<=CREATED_DATE'?: string;
  TITLE?: string;
  '%TITLE'?: string;
}

export interface BitrixTaskSelect {
  select?: string[];
  order?: Record<string, 'asc' | 'desc'>;
  filter?: BitrixTaskFilter;
  start?: number;
  limit?: number;
}

// Field description from getFields
export interface BitrixFieldDescription {
  title: string;
  type: string;
  primary?: boolean;
  required?: boolean;
}

export type BitrixFields = Record<string, BitrixFieldDescription>;

// =============================================================================
// Universal Lists (Списки) Types
// =============================================================================

// List (Infoblock) types
export type IblockTypeId = 'lists' | 'bitrix_processes' | 'lists_socnet';

// List structure from lists.get
export interface BitrixList {
  ID: number;
  IBLOCK_TYPE_ID: IblockTypeId;
  IBLOCK_CODE?: string;
  NAME: string;
  DESCRIPTION?: string;
  SORT: number;
  ACTIVE: 'Y' | 'N';
  DATE_CREATE?: string;
  TIMESTAMP_X?: string;
  BIZPROC?: 'Y' | 'N';
  SOCNET_GROUP_ID?: number;
  ELEMENT_NAME?: string;
  ELEMENTS_NAME?: string;
  SECTION_NAME?: string;
  SECTIONS_NAME?: string;
}

// Fields for creating/updating a list
export interface BitrixListFields {
  NAME: string;
  DESCRIPTION?: string;
  SORT?: number;
  PICTURE?: { fileData: [string, string] };  // [filename, base64]
  BIZPROC?: 'Y' | 'N';
}

// Messages customization for list
export interface BitrixListMessages {
  ELEMENTS_NAME?: string;
  ELEMENT_NAME?: string;
  ELEMENT_ADD?: string;
  ELEMENT_EDIT?: string;
  ELEMENT_DELETE?: string;
  SECTIONS_NAME?: string;
  SECTION_NAME?: string;
  SECTION_ADD?: string;
  SECTION_EDIT?: string;
  SECTION_DELETE?: string;
}

// List Element structure from lists.element.get
export interface BitrixListElement {
  ID: string;
  IBLOCK_ID: string;
  NAME: string;
  CODE?: string;
  IBLOCK_SECTION_ID?: string | null;
  CREATED_BY: string;
  DATE_CREATE: string;
  MODIFIED_BY?: string;
  TIMESTAMP_X?: string;
  ACTIVE?: 'Y' | 'N';
  SORT?: number;
  // Custom properties are stored as PROPERTY_{ID}: { value: ... }
  [key: `PROPERTY_${string}`]: Record<string, unknown> | unknown;
}

// Fields for creating/updating list element
export interface BitrixListElementFields {
  NAME: string;
  CODE?: string;
  IBLOCK_SECTION_ID?: number;
  ACTIVE?: 'Y' | 'N';
  SORT?: number;
  // Custom properties
  [key: `PROPERTY_${string}`]: unknown;
}

// List Field structure from lists.field.get
export interface BitrixListField {
  FIELD_ID: string;
  NAME: string;
  TYPE?: string;
  PROPERTY_TYPE?: string;
  USER_TYPE?: string;
  SORT: number;
  IS_REQUIRED: 'Y' | 'N';
  MULTIPLE: 'Y' | 'N';
  DEFAULT_VALUE?: unknown;
  CODE?: string;
  LINK_IBLOCK_ID?: number;
  SETTINGS?: Record<string, unknown>;
  DISPLAY_VALUES_FORM?: Record<string, string>;  // For L type (list values)
}

// Fields for creating a list field
export interface BitrixListFieldCreate {
  NAME: string;
  TYPE: string;
  CODE?: string;
  IS_REQUIRED?: 'Y' | 'N';
  MULTIPLE?: 'Y' | 'N';
  SORT?: number;
  DEFAULT_VALUE?: unknown;
  SETTINGS?: Record<string, unknown>;
  USER_TYPE_SETTINGS?: Record<string, unknown>;
  LIST?: Record<string, { SORT: number; VALUE: string }>;  // For L type values
  LIST_TEXT_VALUES?: string;  // Alternative: newline-separated values
}

// Fields for updating a list field
export interface BitrixListFieldUpdate {
  NAME?: string;
  IS_REQUIRED?: 'Y' | 'N';
  MULTIPLE?: 'Y' | 'N';
  SORT?: number;
  DEFAULT_VALUE?: unknown;
  SETTINGS?: Record<string, unknown>;
  LIST?: Record<string, { SORT: number; VALUE: string }>;
  LIST_TEXT_VALUES?: string;
}

// List Field Type from lists.field.type.get
export interface BitrixListFieldType {
  TYPE: string;
  NAME: string;
  DESCRIPTION?: string;
}

// List Section structure from lists.section.get
export interface BitrixListSection {
  ID: string;
  IBLOCK_ID: string;
  IBLOCK_SECTION_ID?: string | null;
  NAME: string;
  CODE?: string;
  XML_ID?: string;
  EXTERNAL_ID?: string;
  ACTIVE: 'Y' | 'N';
  SORT: number;
  DATE_CREATE?: string;
  TIMESTAMP_X?: string;
  CREATED_BY?: string;
  MODIFIED_BY?: string;
  DEPTH_LEVEL?: number;
  LEFT_MARGIN?: number;
  RIGHT_MARGIN?: number;
}

// Fields for creating/updating a section
export interface BitrixListSectionFields {
  NAME: string;
  CODE?: string;
  XML_ID?: string;
  EXTERNAL_ID?: string;
  SORT?: number;
  ACTIVE?: 'Y' | 'N';
}

// Filter for lists.element.get
export interface BitrixListElementFilter {
  ID?: number | string;
  NAME?: string;
  '%NAME'?: string;
  CODE?: string;
  IBLOCK_SECTION_ID?: number | string;
  CREATED_BY?: number | string;
  '>=DATE_CREATE'?: string;
  '<=DATE_CREATE'?: string;
  ACTIVE?: 'Y' | 'N';
  // Custom property filters
  [key: `PROPERTY_${string}` | `>${string}` | `<${string}` | `>=${string}` | `<=${string}` | `%${string}` | `!${string}`]: unknown;
}

// Filter for lists.section.get
export interface BitrixListSectionFilter {
  ID?: number | string;
  NAME?: string;
  '%NAME'?: string;
  CODE?: string;
  XML_ID?: string;
  ACTIVE?: 'Y' | 'N';
  IBLOCK_SECTION_ID?: number | string;
  DEPTH_LEVEL?: number;
  '>=DEPTH_LEVEL'?: number;
  '<=DEPTH_LEVEL'?: number;
}
