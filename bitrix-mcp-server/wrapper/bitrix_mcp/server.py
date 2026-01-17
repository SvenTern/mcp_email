"""
Bitrix24 MCP Server - FastMCP with Streamable HTTP Transport

Provides HTTP transport for the STDIO-based bitrix-mcp-server,
implementing MCP protocol version 2025-11-25.

Features:
- Background tasks for long-running list operations (SEP-1686)
- Progress tracking for bulk operations
- SSE polling with event resumability (SEP-1699)

Consolidated architecture: 12 tools instead of 71.
Each tool uses an 'action' parameter to route to specific functionality.
"""

import logging
import os
from datetime import datetime
from typing import Any, List, Optional

from fastmcp import FastMCP, Context
from fastmcp.server.http import Request
from fastmcp.dependencies import Progress
from starlette.responses import JSONResponse

from . import __version__, __protocol_version__
from .stdio_bridge import StdioBridgePool

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
BITRIX_SERVER_PATH = os.getenv(
    "BITRIX_SERVER_PATH",
    "/app/bitrix-mcp-server/dist/index.js"
)

# Initialize FastMCP server
mcp = FastMCP(
    name="bitrix-mcp-server",
    version=__version__,
)

# Global bridge pool
bridge_pool: StdioBridgePool = None

# Consolidated tools (12 instead of 71)
BITRIX_TOOLS = [
    "bitrix_task",           # 19 actions
    "bitrix_checklist",      # 6 actions
    "bitrix_comment",        # 4 actions
    "bitrix_time",           # 4 actions
    "bitrix_user",           # 7 actions
    "bitrix_department",     # 5 actions
    "bitrix_group",          # 6 actions
    "bitrix_list",           # 5 actions
    "bitrix_list_element",   # 5 actions
    "bitrix_list_field",     # 5 actions
    "bitrix_list_section",   # 4 actions
    "bitrix_system",         # 2 actions
]


def get_bridge_pool() -> StdioBridgePool:
    """Get or create the bridge pool."""
    global bridge_pool
    if bridge_pool is None:
        bridge_pool = StdioBridgePool(BITRIX_SERVER_PATH)
    return bridge_pool


# =============================================================================
# Custom HTTP Routes
# =============================================================================

@mcp.custom_route("/", methods=["GET"])
async def server_info(request: Request) -> JSONResponse:
    """Server information endpoint (gateway compatible)."""
    pool = get_bridge_pool()
    return JSONResponse({
        "name": "bitrix-mcp-server",
        "version": __version__,
        "description": "Bitrix24 MCP Server with Streamable HTTP transport (Consolidated 12 tools)",
        "protocol_version": __protocol_version__,
        "transport": "streamable-http",
        "endpoints": {
            "info": "/",
            "health": "/health",
            "mcp": "/mcp"
        },
        "tools": BITRIX_TOOLS,
        "active_sessions": pool.active_count
    })


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint."""
    bitrix_server_exists = os.path.exists(BITRIX_SERVER_PATH)
    pool = get_bridge_pool()

    return JSONResponse({
        "status": "ok" if bitrix_server_exists else "degraded",
        "server": "bitrix-mcp-server",
        "version": __version__,
        "protocol_version": __protocol_version__,
        "bitrix_server_available": bitrix_server_exists,
        "active_sessions": pool.active_count,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


# =============================================================================
# MCP Tools - Proxied to bitrix-mcp-server via STDIO
# =============================================================================

async def _call_bitrix_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """
    Proxy a tool call to bitrix-mcp-server.

    Args:
        tool_name: Name of the MCP tool
        arguments: Tool arguments

    Returns:
        Tool result from bitrix-mcp-server
    """
    pool = get_bridge_pool()
    bridge = await pool.get_bridge("default")

    # Build JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 1
    }

    response = await bridge.call(request)

    if "error" in response:
        error = response["error"]
        raise Exception(f"Bitrix24 API error: {error.get('message', str(error))}")

    result = response.get("result", {})
    content = result.get("content", [])

    if content and len(content) > 0:
        text = content[0].get("text", "")
        return text

    return result


# =============================================================================
# CONSOLIDATED TOOL: bitrix_task (19 actions)
# =============================================================================

@mcp.tool(task=True)
async def bitrix_task(
    action: str,
    task_id: int = 0,
    title: str = "",
    description: str = "",
    responsible_id: int = 0,
    deadline: str = "",
    start_date_plan: str = "",
    end_date_plan: str = "",
    priority: int = -1,
    group_id: int = 0,
    parent_id: int = 0,
    accomplices: List[int] = None,
    auditors: List[int] = None,
    tags: List[str] = None,
    allow_change_deadline: bool = None,
    task_control: bool = None,
    allow_time_tracking: bool = None,
    filter: dict = None,
    select: List[str] = None,
    order: dict = None,
    start: int = 0,
    limit: int = 20,
    new_responsible_id: int = 0,
    file_ids: List[int] = None,
    ctx: Context = None,
    progress: Progress = Progress()
) -> str:
    """
    Task management tool. Actions:
    - create: Create new task (requires title, responsibleId)
    - get: Get task by ID (requires taskId)
    - list: List tasks with filters
    - update: Update task (requires taskId)
    - delete: Delete task (requires taskId)
    - start/pause/complete/defer/renew: Change task status (requires taskId)
    - approve/disapprove: Accept/reject completed task (requires taskId)
    - delegate: Delegate task (requires taskId, newResponsibleId)
    - attach_files: Attach files (requires taskId, fileIds)
    - counters: Get task counters
    - history: Get task history (requires taskId)
    - favorite_add/favorite_remove: Manage favorites (requires taskId)
    - get_fields: Get available task fields

    Args:
        action: Action to perform
        task_id: Task ID (required for most actions)
        title: Task title (required for create)
        description: Task description
        responsible_id: Responsible user ID (required for create)
        deadline: Deadline in ISO format
        start_date_plan: Planned start date
        end_date_plan: Planned end date
        priority: Priority (0=low, 1=normal, 2=high)
        group_id: Workgroup ID
        parent_id: Parent task ID
        accomplices: Accomplice user IDs
        auditors: Auditor user IDs
        tags: Task tags
        allow_change_deadline: Allow deadline changes
        task_control: Enable task control
        allow_time_tracking: Enable time tracking
        filter: Filter conditions for list
        select: Fields to return
        order: Sort order
        start: Pagination offset
        limit: Max tasks to return (default: 20)
        new_responsible_id: New responsible user ID (for delegate)
        file_ids: File IDs to attach
    """
    await progress.set_total(100)
    await progress.set_message(f"Executing task action: {action}")

    if ctx:
        await ctx.info(f"Bitrix task action: {action}")

    args = {"action": action}
    if limit > 0:
        args["limit"] = limit
    if task_id > 0:
        args["taskId"] = task_id
    if title:
        args["title"] = title
    if description:
        args["description"] = description
    if responsible_id > 0:
        args["responsibleId"] = responsible_id
    if deadline:
        args["deadline"] = deadline
    if start_date_plan:
        args["startDatePlan"] = start_date_plan
    if end_date_plan:
        args["endDatePlan"] = end_date_plan
    if priority >= 0:
        args["priority"] = priority
    if group_id > 0:
        args["groupId"] = group_id
    if parent_id > 0:
        args["parentId"] = parent_id
    if accomplices:
        args["accomplices"] = accomplices
    if auditors:
        args["auditors"] = auditors
    if tags:
        args["tags"] = tags
    if allow_change_deadline is not None:
        args["allowChangeDeadline"] = allow_change_deadline
    if task_control is not None:
        args["taskControl"] = task_control
    if allow_time_tracking is not None:
        args["allowTimeTracking"] = allow_time_tracking
    if filter:
        args["filter"] = filter
    if select:
        args["select"] = select
    if order:
        args["order"] = order
    if start > 0:
        args["start"] = start
    if new_responsible_id > 0:
        args["newResponsibleId"] = new_responsible_id
    if file_ids:
        args["fileIds"] = file_ids

    await progress.increment(20)

    result = await _call_bitrix_tool("bitrix_task", args)

    await progress.set_message(f"Task action '{action}' completed")
    await progress.increment(80)

    return result


# =============================================================================
# CONSOLIDATED TOOL: bitrix_checklist (6 actions)
# =============================================================================

@mcp.tool()
async def bitrix_checklist(
    action: str,
    task_id: int,
    checklist_id: int = 0,
    title: str = "",
    is_complete: bool = None
) -> str:
    """
    Task checklist management. Actions:
    - add: Add checklist item (requires taskId, title)
    - list: List checklist items (requires taskId)
    - update: Update item (requires taskId, checklistId, title)
    - delete: Delete item (requires taskId, checklistId)
    - complete: Mark item complete (requires taskId, checklistId)
    - renew: Mark item incomplete (requires taskId, checklistId)

    Args:
        action: Action to perform
        task_id: Task ID
        checklist_id: Checklist item ID (required for update/delete/complete/renew)
        title: Checklist item title (required for add/update)
        is_complete: Completion status
    """
    args = {"action": action, "taskId": task_id}
    if checklist_id > 0:
        args["checklistId"] = checklist_id
    if title:
        args["title"] = title
    if is_complete is not None:
        args["isComplete"] = is_complete

    return await _call_bitrix_tool("bitrix_checklist", args)


# =============================================================================
# CONSOLIDATED TOOL: bitrix_comment (4 actions)
# =============================================================================

@mcp.tool()
async def bitrix_comment(
    action: str,
    task_id: int,
    comment_id: int = 0,
    text: str = ""
) -> str:
    """
    Task comment management. Actions:
    - add: Add comment (requires taskId, text)
    - list: List comments (requires taskId)
    - update: Update comment (requires taskId, commentId, text)
    - delete: Delete comment (requires taskId, commentId)

    Args:
        action: Action to perform
        task_id: Task ID
        comment_id: Comment ID (required for update/delete)
        text: Comment text (required for add/update)
    """
    args = {"action": action, "taskId": task_id}
    if comment_id > 0:
        args["commentId"] = comment_id
    if text:
        args["text"] = text

    return await _call_bitrix_tool("bitrix_comment", args)


# =============================================================================
# CONSOLIDATED TOOL: bitrix_time (4 actions)
# =============================================================================

@mcp.tool()
async def bitrix_time(
    action: str,
    task_id: int,
    record_id: int = 0,
    seconds: int = 0,
    comment: str = "",
    date_start: str = "",
    date_stop: str = ""
) -> str:
    """
    Task time tracking management. Actions:
    - add: Add time record (requires taskId, seconds)
    - list: List time records (requires taskId)
    - update: Update record (requires taskId, recordId)
    - delete: Delete record (requires taskId, recordId)

    Args:
        action: Action to perform
        task_id: Task ID
        record_id: Time record ID (required for update/delete)
        seconds: Time spent in seconds (required for add)
        comment: Comment for time record
        date_start: Start date/time
        date_stop: Stop date/time
    """
    args = {"action": action, "taskId": task_id}
    if record_id > 0:
        args["recordId"] = record_id
    if seconds > 0:
        args["seconds"] = seconds
    if comment:
        args["comment"] = comment
    if date_start:
        args["dateStart"] = date_start
    if date_stop:
        args["dateStop"] = date_stop

    return await _call_bitrix_tool("bitrix_time", args)


# =============================================================================
# CONSOLIDATED TOOL: bitrix_user (7 actions)
# =============================================================================

@mcp.tool(task=True)
async def bitrix_user(
    action: str,
    user_id: int = 0,
    user_ids: List[int] = None,
    department_id: int = 0,
    query: str = "",
    filter: dict = None,
    start: int = 0,
    ctx: Context = None,
    progress: Progress = Progress()
) -> str:
    """
    User/employee management. Actions:
    - list: List all users with filters
    - get: Get user by ID (requires userId)
    - get_many: Get multiple users by IDs (requires userIds)
    - current: Get current user (webhook owner)
    - search: Search users (requires query)
    - fields: Get available user fields
    - by_department: Get users by department (requires departmentId)

    This is a background task that reports progress.

    Args:
        action: Action to perform
        user_id: User ID (required for get)
        user_ids: User IDs (required for get_many)
        department_id: Department ID (required for by_department)
        query: Search query (required for search)
        filter: Filter conditions for list
        start: Pagination offset
    """
    await progress.set_total(100)
    await progress.set_message(f"Executing user action: {action}")

    if ctx:
        await ctx.info(f"Bitrix user action: {action}")

    args = {"action": action}
    if user_id > 0:
        args["userId"] = user_id
    if user_ids:
        args["userIds"] = user_ids
    if department_id > 0:
        args["departmentId"] = department_id
    if query:
        args["query"] = query
    if filter:
        args["filter"] = filter
    if start > 0:
        args["start"] = start

    await progress.increment(20)

    result = await _call_bitrix_tool("bitrix_user", args)

    await progress.set_message(f"User action '{action}' completed")
    await progress.increment(80)

    return result


# =============================================================================
# CONSOLIDATED TOOL: bitrix_department (5 actions)
# =============================================================================

@mcp.tool()
async def bitrix_department(
    action: str,
    department_id: int = 0,
    parent_id: int = 0,
    include_subordinates: bool = None,
    start: int = 0
) -> str:
    """
    Company org structure management. Actions:
    - list: List all departments
    - get: Get department by ID (requires departmentId)
    - tree: Get department tree/hierarchy
    - employees: Get department employees (requires departmentId)
    - fields: Get available department fields

    Args:
        action: Action to perform
        department_id: Department ID
        parent_id: Parent department ID
        include_subordinates: Include subordinate departments
        start: Pagination offset
    """
    args = {"action": action}
    if department_id > 0:
        args["departmentId"] = department_id
    if parent_id > 0:
        args["parentId"] = parent_id
    if include_subordinates is not None:
        args["includeSubordinates"] = include_subordinates
    if start > 0:
        args["start"] = start

    return await _call_bitrix_tool("bitrix_department", args)


# =============================================================================
# CONSOLIDATED TOOL: bitrix_group (6 actions)
# =============================================================================

@mcp.tool()
async def bitrix_group(
    action: str,
    group_id: int = 0,
    query: str = "",
    feature: str = "",
    operation: str = "",
    filter: dict = None,
    start: int = 0
) -> str:
    """
    Workgroup management. Actions:
    - list: List all workgroups
    - get: Get group by ID (requires groupId)
    - members: Get group members (requires groupId)
    - my: Get current user's groups
    - search: Search groups (requires query)
    - access_check: Check feature access (requires groupId, feature)

    Args:
        action: Action to perform
        group_id: Group ID
        query: Search query
        feature: Feature to check (blog, files, tasks, calendar, etc.)
        operation: Operation to check (view, write_post, etc.)
        filter: Filter conditions
        start: Pagination offset
    """
    args = {"action": action}
    if group_id > 0:
        args["groupId"] = group_id
    if query:
        args["query"] = query
    if feature:
        args["feature"] = feature
    if operation:
        args["operation"] = operation
    if filter:
        args["filter"] = filter
    if start > 0:
        args["start"] = start

    return await _call_bitrix_tool("bitrix_group", args)


# =============================================================================
# CONSOLIDATED TOOL: bitrix_list (5 actions)
# =============================================================================

@mcp.tool()
async def bitrix_list(
    action: str,
    iblock_type_id: str,
    iblock_id: int = 0,
    iblock_code: str = "",
    name: str = "",
    description: str = "",
    sort: int = -1,
    socnet_group_id: int = 0,
    start: int = 0
) -> str:
    """
    Universal list management. Actions:
    - add: Create new list (requires iblockTypeId, iblockCode, name)
    - get: Get list(s) (requires iblockTypeId)
    - update: Update list
    - delete: Delete list
    - get_iblock_type: Get infoblock type ID

    Args:
        action: Action to perform
        iblock_type_id: List type (lists, bitrix_processes, lists_socnet)
        iblock_id: List ID
        iblock_code: List symbolic code
        name: List name
        description: List description
        sort: Sort order
        socnet_group_id: Workgroup ID for group lists
        start: Pagination offset
    """
    args = {"action": action, "iblockTypeId": iblock_type_id}
    if iblock_id > 0:
        args["iblockId"] = iblock_id
    if iblock_code:
        args["iblockCode"] = iblock_code
    if name:
        args["name"] = name
    if description:
        args["description"] = description
    if sort >= 0:
        args["sort"] = sort
    if socnet_group_id > 0:
        args["socnetGroupId"] = socnet_group_id
    if start > 0:
        args["start"] = start

    return await _call_bitrix_tool("bitrix_list", args)


# =============================================================================
# CONSOLIDATED TOOL: bitrix_list_element (5 actions)
# =============================================================================

@mcp.tool()
async def bitrix_list_element(
    action: str,
    iblock_type_id: str,
    iblock_id: int = 0,
    iblock_code: str = "",
    element_id: int = 0,
    element_code: str = "",
    name: str = "",
    section_id: int = 0,
    filter: dict = None,
    select: List[str] = None,
    order: dict = None,
    properties: dict = None,
    field_id: str = "",
    socnet_group_id: int = 0,
    start: int = 0
) -> str:
    """
    List element management. Actions:
    - add: Create element (requires iblockTypeId, elementCode, name)
    - get: Get element(s)
    - update: Update element
    - delete: Delete element
    - file_url: Get file URL (requires elementId, fieldId)

    Args:
        action: Action to perform
        iblock_type_id: List type
        iblock_id: List ID
        iblock_code: List symbolic code
        element_id: Element ID
        element_code: Element symbolic code
        name: Element name
        section_id: Section ID
        filter: Filter conditions
        select: Fields to return
        order: Sort order
        properties: Custom field values
        field_id: Field ID for file_url
        socnet_group_id: Workgroup ID
        start: Pagination offset
    """
    args = {"action": action, "iblockTypeId": iblock_type_id}
    if iblock_id > 0:
        args["iblockId"] = iblock_id
    if iblock_code:
        args["iblockCode"] = iblock_code
    if element_id > 0:
        args["elementId"] = element_id
    if element_code:
        args["elementCode"] = element_code
    if name:
        args["name"] = name
    if section_id > 0:
        args["sectionId"] = section_id
    if filter:
        args["filter"] = filter
    if select:
        args["select"] = select
    if order:
        args["order"] = order
    if properties:
        args["properties"] = properties
    if field_id:
        args["fieldId"] = field_id
    if socnet_group_id > 0:
        args["socnetGroupId"] = socnet_group_id
    if start > 0:
        args["start"] = start

    return await _call_bitrix_tool("bitrix_list_element", args)


# =============================================================================
# CONSOLIDATED TOOL: bitrix_list_field (5 actions)
# =============================================================================

@mcp.tool()
async def bitrix_list_field(
    action: str,
    iblock_type_id: str,
    iblock_id: int = 0,
    iblock_code: str = "",
    field_id: str = "",
    name: str = "",
    field_type: str = "",
    code: str = "",
    is_required: bool = None,
    multiple: bool = None,
    sort: int = -1,
    default_value: str = "",
    list_values: List[str] = None,
    socnet_group_id: int = 0
) -> str:
    """
    List field management. Actions:
    - add: Create field (requires name, type)
    - get: Get field(s)
    - update: Update field (requires fieldId)
    - delete: Delete field (requires fieldId)
    - types: Get available field types

    Args:
        action: Action to perform
        iblock_type_id: List type
        iblock_id: List ID
        iblock_code: List symbolic code
        field_id: Field ID
        name: Field name
        field_type: Field type (S, N, L, F, etc.)
        code: Symbolic code
        is_required: Required field
        multiple: Allow multiple values
        sort: Sort order
        default_value: Default value
        list_values: Values for List type
        socnet_group_id: Workgroup ID
    """
    args = {"action": action, "iblockTypeId": iblock_type_id}
    if iblock_id > 0:
        args["iblockId"] = iblock_id
    if iblock_code:
        args["iblockCode"] = iblock_code
    if field_id:
        args["fieldId"] = field_id
    if name:
        args["name"] = name
    if field_type:
        args["type"] = field_type
    if code:
        args["code"] = code
    if is_required is not None:
        args["isRequired"] = is_required
    if multiple is not None:
        args["multiple"] = multiple
    if sort >= 0:
        args["sort"] = sort
    if default_value:
        args["defaultValue"] = default_value
    if list_values:
        args["listValues"] = list_values
    if socnet_group_id > 0:
        args["socnetGroupId"] = socnet_group_id

    return await _call_bitrix_tool("bitrix_list_field", args)


# =============================================================================
# CONSOLIDATED TOOL: bitrix_list_section (4 actions)
# =============================================================================

@mcp.tool()
async def bitrix_list_section(
    action: str,
    iblock_type_id: str,
    iblock_id: int = 0,
    iblock_code: str = "",
    section_id: int = 0,
    section_code: str = "",
    name: str = "",
    parent_section_id: int = 0,
    sort: int = -1,
    active: bool = None,
    filter: dict = None,
    select: List[str] = None,
    socnet_group_id: int = 0
) -> str:
    """
    List section management. Actions:
    - add: Create section (requires sectionCode, name)
    - get: Get section(s)
    - update: Update section
    - delete: Delete section

    Args:
        action: Action to perform
        iblock_type_id: List type
        iblock_id: List ID
        iblock_code: List symbolic code
        section_id: Section ID
        section_code: Section symbolic code
        name: Section name
        parent_section_id: Parent section ID
        sort: Sort order
        active: Active status
        filter: Filter conditions
        select: Fields to return
        socnet_group_id: Workgroup ID
    """
    args = {"action": action, "iblockTypeId": iblock_type_id}
    if iblock_id > 0:
        args["iblockId"] = iblock_id
    if iblock_code:
        args["iblockCode"] = iblock_code
    if section_id > 0:
        args["sectionId"] = section_id
    if section_code:
        args["sectionCode"] = section_code
    if name:
        args["name"] = name
    if parent_section_id > 0:
        args["parentSectionId"] = parent_section_id
    if sort >= 0:
        args["sort"] = sort
    if active is not None:
        args["active"] = active
    if filter:
        args["filter"] = filter
    if select:
        args["select"] = select
    if socnet_group_id > 0:
        args["socnetGroupId"] = socnet_group_id

    return await _call_bitrix_tool("bitrix_list_section", args)


# =============================================================================
# CONSOLIDATED TOOL: bitrix_system (2 actions)
# =============================================================================

@mcp.tool()
async def bitrix_system(
    action: str,
    user_ids: List[int] = None
) -> str:
    """
    System utilities. Actions:
    - test_connection: Test Bitrix24 API connection
    - get_users: Get multiple users by IDs (requires userIds)

    Args:
        action: Action to perform
        user_ids: User IDs for get_users
    """
    args = {"action": action}
    if user_ids:
        args["userIds"] = user_ids

    return await _call_bitrix_tool("bitrix_system", args)


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Run the Bitrix24 MCP server with HTTP transport."""
    logger.info(f"Starting Bitrix24 MCP Server on {HOST}:{PORT}")
    logger.info(f"Protocol version: {__protocol_version__}")
    logger.info(f"Bitrix server path: {BITRIX_SERVER_PATH}")
    logger.info("Consolidated architecture: 12 tools")

    mcp.run(
        transport="http",
        host=HOST,
        port=PORT,
        path="/mcp"
    )


if __name__ == "__main__":
    main()
