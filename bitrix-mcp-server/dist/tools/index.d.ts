import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { BitrixService } from '../services/bitrix-service.js';
/**
 * Register all Bitrix24 MCP tools
 *
 * Consolidated architecture: 12 tools instead of 71
 * Each tool uses an 'action' parameter to route to specific functionality
 *
 * Tools:
 * - bitrix_task (19 actions: create, get, list, update, delete, start, pause, complete, defer, renew, approve, disapprove, delegate, attach_files, counters, history, favorite_add, favorite_remove, get_fields)
 * - bitrix_checklist (6 actions: add, list, update, delete, complete, renew)
 * - bitrix_comment (4 actions: add, list, update, delete)
 * - bitrix_time (4 actions: add, list, update, delete)
 * - bitrix_user (7 actions: list, get, get_many, current, search, fields, by_department)
 * - bitrix_department (5 actions: list, get, tree, employees, fields)
 * - bitrix_group (6 actions: list, get, members, my, search, access_check)
 * - bitrix_list (5 actions: add, get, update, delete, get_iblock_type)
 * - bitrix_list_element (5 actions: add, get, update, delete, file_url)
 * - bitrix_list_field (5 actions: add, get, update, delete, types)
 * - bitrix_list_section (4 actions: add, get, update, delete)
 * - bitrix_system (2 actions: test_connection, get_users)
 */
export declare function registerTools(server: McpServer, bitrixService: BitrixService): void;
//# sourceMappingURL=index.d.ts.map