import { registerTaskTool } from './task-tool.js';
import { registerChecklistTool } from './checklist-tool.js';
import { registerCommentTool } from './comment-tool.js';
import { registerTimeTool } from './time-tool.js';
import { registerUserTool } from './user-tool.js';
import { registerDepartmentTool } from './department-tool.js';
import { registerGroupTool } from './group-tool.js';
import { registerListTool } from './list-tool.js';
import { registerListElementTool } from './list-element-tool.js';
import { registerListFieldTool } from './list-field-tool.js';
import { registerListSectionTool } from './list-section-tool.js';
import { registerSystemTool } from './system-tool.js';
/**
 * Register all consolidated tools (12 tools instead of 71)
 * Each tool uses an 'action' parameter to route to specific functionality
 */
export function registerConsolidatedTools(server, bitrixService) {
    // Task management (19 actions)
    registerTaskTool(server, bitrixService);
    // Task checklist (6 actions)
    registerChecklistTool(server, bitrixService);
    // Task comments (4 actions)
    registerCommentTool(server, bitrixService);
    // Time tracking (4 actions)
    registerTimeTool(server, bitrixService);
    // User/employee management (7 actions)
    registerUserTool(server, bitrixService);
    // Department/org structure (5 actions)
    registerDepartmentTool(server, bitrixService);
    // Workgroups (6 actions)
    registerGroupTool(server, bitrixService);
    // Universal lists (5 actions)
    registerListTool(server, bitrixService);
    // List elements (5 actions)
    registerListElementTool(server, bitrixService);
    // List fields (5 actions)
    registerListFieldTool(server, bitrixService);
    // List sections (4 actions)
    registerListSectionTool(server, bitrixService);
    // System utilities (2 actions)
    registerSystemTool(server, bitrixService);
}
//# sourceMappingURL=index.js.map