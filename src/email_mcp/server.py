"""
Email MCP Server - FastMCP with Streamable HTTP Transport

Provides HTTP transport for the STDIO-based nikolausm/imap-mcp-server,
implementing MCP protocol version 2025-11-25.

Features:
- Background tasks for long-running operations (SEP-1686)
- Progress tracking for bulk operations
- SSE polling with event resumability (SEP-1699)
"""

import logging
import os
import base64
import hashlib
import time
from datetime import datetime
from typing import Any, List, Optional

from fastmcp import FastMCP, Context
from fastmcp.server.http import Request
from fastmcp.dependencies import Progress
from starlette.responses import JSONResponse, Response

from . import __version__, __protocol_version__
from .stdio_bridge import StdioBridgePool

# Temporary storage for attachments (in-memory cache with TTL)
# Format: {token: {"content": base64_str, "filename": str, "contentType": str, "expires": timestamp}}
_attachment_cache: dict[str, dict] = {}
ATTACHMENT_CACHE_TTL = 300  # 5 minutes

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
IMAP_SERVER_PATH = os.getenv(
    "IMAP_SERVER_PATH",
    "/app/imap-mcp-server/dist/index.js"
)
# Public base URL for external access (used for download links)
# Should be set to the public URL where this server is accessible
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://mcp.svsfinpro.ru/email")

# Initialize FastMCP server
mcp = FastMCP(
    name="email-mcp-server",
    version=__version__,
)

# Global bridge pool
bridge_pool: StdioBridgePool = None


def get_bridge_pool() -> StdioBridgePool:
    """Get or create the bridge pool."""
    global bridge_pool
    if bridge_pool is None:
        bridge_pool = StdioBridgePool(IMAP_SERVER_PATH)
    return bridge_pool


# =============================================================================
# Custom HTTP Routes
# =============================================================================

@mcp.custom_route("/", methods=["GET"])
async def server_info(request: Request) -> JSONResponse:
    """Server information endpoint (gateway compatible)."""
    pool = get_bridge_pool()
    return JSONResponse({
        "name": "email-mcp-server",
        "version": __version__,
        "description": "IMAP/SMTP Email MCP Server with Streamable HTTP transport",
        "protocol_version": __protocol_version__,
        "transport": "streamable-http",
        "endpoints": {
            "info": "/",
            "health": "/health",
            "mcp": "/mcp",
            "download_attachment": "/download/attachment/{token}"
        },
        "tools": [
            "imap_add_account",
            "imap_list_accounts",
            "imap_remove_account",
            "imap_connect",
            "imap_disconnect",
            "imap_test_account",
            "imap_search_emails",
            "imap_get_email",
            "imap_get_attachment",
            "imap_get_latest_emails",
            "imap_mark_as_read",
            "imap_mark_as_unread",
            "imap_delete_email",
            "imap_bulk_delete",
            "imap_bulk_delete_by_search",
            "imap_send_email",
            "imap_reply_to_email",
            "imap_forward_email",
            "imap_list_folders",
            "imap_folder_status",
            "imap_get_unread_count",
            "imap_move_emails",
            "imap_copy_emails",
            "imap_create_folder",
            "imap_delete_folder",
            "imap_rename_folder",
            "imap_get_sorting_plan",
            "imap_save_sorting_plan",
            "imap_delete_sorting_plan",
            "imap_list_sorting_plans",
            "imap_add_sorting_rule",
            "imap_update_sorting_rule",
            "imap_delete_sorting_rule",
            "imap_reorder_sorting_rules",
            "imap_apply_sorting_rules",
            "imap_test_sorting_rule",
            "imap_create_folders_from_plan",
            "imap_validate_sorting_plan",
            "imap_set_sorting_plans_directory",
            "imap_get_sorting_plans_directory"
        ],
        "active_sessions": pool.active_count
    })


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint."""
    imap_server_exists = os.path.exists(IMAP_SERVER_PATH)
    pool = get_bridge_pool()

    return JSONResponse({
        "status": "ok" if imap_server_exists else "degraded",
        "server": "email-mcp-server",
        "version": __version__,
        "protocol_version": __protocol_version__,
        "imap_server_available": imap_server_exists,
        "active_sessions": pool.active_count,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@mcp.custom_route("/download/attachment/{token}", methods=["GET"])
async def download_attachment(request: Request) -> Response:
    """
    Download attachment by temporary token.

    Returns the file directly with proper Content-Type and Content-Disposition headers.
    Token expires after 5 minutes.
    """
    token = request.path_params.get("token")
    logger.info(f"[download_attachment] Requested token: {token}")
    logger.info(f"[download_attachment] Cache has {len(_attachment_cache)} entries: {list(_attachment_cache.keys())}")

    if not token:
        return JSONResponse({"error": "Token required"}, status_code=400)

    # Clean expired entries
    current_time = time.time()
    expired_tokens = [k for k, v in _attachment_cache.items() if v["expires"] < current_time]
    for t in expired_tokens:
        logger.info(f"[download_attachment] Removing expired token: {t}")
        del _attachment_cache[t]

    # Get attachment from cache
    attachment = _attachment_cache.get(token)
    if not attachment:
        logger.warning(f"[download_attachment] Token not found in cache: {token}")
        return JSONResponse({"error": "Attachment not found or expired"}, status_code=404)

    # Decode base64 content
    try:
        content = base64.b64decode(attachment["content"])
    except Exception as e:
        logger.error(f"Failed to decode attachment: {e}")
        return JSONResponse({"error": "Failed to decode attachment"}, status_code=500)

    # Return file with proper headers
    filename = attachment["filename"]
    content_type = attachment["contentType"]

    # Remove from cache after download (one-time use)
    del _attachment_cache[token]

    # Build Content-Disposition header with proper encoding for non-ASCII filenames
    # RFC 5987: use filename* with UTF-8 encoding for Unicode filenames
    try:
        # Try ASCII first (simple case)
        filename.encode('ascii')
        content_disposition = f'attachment; filename="{filename}"'
    except UnicodeEncodeError:
        # Fallback to RFC 5987 encoding for non-ASCII filenames
        from urllib.parse import quote
        # ASCII fallback + UTF-8 encoded filename
        ascii_filename = filename.encode('ascii', 'ignore').decode('ascii') or 'attachment'
        encoded_filename = quote(filename, safe='')
        content_disposition = f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": content_disposition,
            "Content-Length": str(len(content))
        }
    )


def _generate_attachment_token(accountId: str, folder: str, uid: int, filename: str) -> str:
    """Generate a unique token for attachment download."""
    data = f"{accountId}:{folder}:{uid}:{filename}:{time.time()}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]


def _cache_attachment(token: str, content: str, filename: str, content_type: str) -> None:
    """Cache attachment for download."""
    _attachment_cache[token] = {
        "content": content,
        "filename": filename,
        "contentType": content_type,
        "expires": time.time() + ATTACHMENT_CACHE_TTL
    }


# =============================================================================
# MCP Resources - Email Attachments
# =============================================================================

@mcp.resource("email-attachment://{token}")
async def get_attachment_resource(token: str) -> bytes:
    """
    MCP Resource for email attachments.

    Clients can use resources/read to fetch attachment content by token.
    The token is obtained from imap_get_attachment tool response.

    Returns binary content of the attachment.
    """
    # Clean expired entries
    current_time = time.time()
    expired_tokens = [k for k, v in _attachment_cache.items() if v["expires"] < current_time]
    for t in expired_tokens:
        del _attachment_cache[t]

    attachment = _attachment_cache.get(token)
    if not attachment:
        raise ValueError(f"Attachment not found or expired: {token}")

    # Return decoded content
    return base64.b64decode(attachment["content"])


# =============================================================================
# MCP Tools - Proxied to imap-mcp-server via STDIO
# =============================================================================

async def _call_imap_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """
    Proxy a tool call to imap-mcp-server.

    Args:
        tool_name: Name of the MCP tool
        arguments: Tool arguments

    Returns:
        Tool result from imap-mcp-server
    """
    pool = get_bridge_pool()
    bridge = await pool.get_bridge("default")

    # Generate unique request ID
    bridge._request_id += 1
    request_id = bridge._request_id

    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": request_id
    }

    response = await bridge.call(request)

    if "error" in response:
        raise RuntimeError(f"Tool error: {response['error']}")

    return response.get("result", {})


# -----------------------------------------------------------------------------
# Account Management Tools
# -----------------------------------------------------------------------------

@mcp.tool()
async def imap_add_account(
    name: str,
    host: str,
    user: str,
    password: str,
    port: int = 993,
    tls: bool = True
) -> dict:
    """
    Add a new IMAP email account.

    Args:
        name: Friendly name for the account (e.g., 'work', 'personal')
        host: IMAP server hostname (e.g., imap.gmail.com, mail.nortex.ru)
        user: Username/email for authentication
        password: Password for authentication (use app password for Gmail)
        port: IMAP server port (default: 993 for SSL)
        tls: Use TLS/SSL connection (default: True)

    Returns:
        Account creation result with accountId
    """
    return await _call_imap_tool("imap_add_account", {
        "name": name,
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "tls": tls
    })


@mcp.tool()
async def imap_list_accounts() -> dict:
    """
    List all configured email accounts.

    Returns:
        List of accounts with id, name, host, port, user, tls
    """
    return await _call_imap_tool("imap_list_accounts", {})


@mcp.tool()
async def imap_remove_account(accountId: str) -> dict:
    """
    Remove an email account configuration.

    Args:
        accountId: ID of the account to remove

    Returns:
        Removal result
    """
    return await _call_imap_tool("imap_remove_account", {"accountId": accountId})


@mcp.tool()
async def imap_connect(
    accountId: str = None,
    accountName: str = None
) -> dict:
    """
    Connect to an email account.

    Args:
        accountId: Account ID to connect to (from imap_list_accounts)
        accountName: Account name to connect to (alternative to accountId)

    Returns:
        Connection result
    """
    args = {}
    if accountId:
        args["accountId"] = accountId
    if accountName:
        args["accountName"] = accountName
    return await _call_imap_tool("imap_connect", args)


@mcp.tool()
async def imap_disconnect(accountId: str) -> dict:
    """
    Disconnect from an email account.

    Args:
        accountId: Account ID to disconnect from

    Returns:
        Disconnection result
    """
    return await _call_imap_tool("imap_disconnect", {"accountId": accountId})


@mcp.tool()
async def imap_test_account(accountId: str) -> dict:
    """
    Test an existing account connection without re-entering credentials.

    Args:
        accountId: Account ID to test

    Returns:
        Test result with folder count and message count
    """
    return await _call_imap_tool("imap_test_account", {"accountId": accountId})


# -----------------------------------------------------------------------------
# Email Operations Tools
# -----------------------------------------------------------------------------

@mcp.tool(task=True)
async def imap_search_emails(
    accountId: str,
    folder: str = "INBOX",
    from_addr: str = None,
    to_addr: str = None,
    subject: str = None,
    body: str = None,
    since: str = None,
    before: str = None,
    seen: bool = None,
    flagged: bool = None,
    limit: int = 50,
    ctx: Context = None,
    progress: Progress = Progress()
) -> dict:
    """
    Search for emails in a folder.

    This is a background task - may take time for large mailboxes.

    Args:
        accountId: Account ID
        folder: Folder name (default: INBOX)
        from_addr: Search by sender
        to_addr: Search by recipient
        subject: Search by subject
        body: Search in body text
        since: Search emails since date (YYYY-MM-DD)
        before: Search emails before date (YYYY-MM-DD)
        seen: Filter by read/unread status (True=read, False=unread)
        flagged: Filter by flagged status
        limit: Maximum number of results (default: 50)

    Returns:
        List of matching emails with totalFound, returned, messages
    """
    await progress.set_message(f"Searching emails in {folder}...")

    args = {"accountId": accountId, "folder": folder, "limit": limit}
    if from_addr:
        args["from"] = from_addr
    if to_addr:
        args["to"] = to_addr
    if subject:
        args["subject"] = subject
    if body:
        args["body"] = body
    if since:
        args["since"] = since
    if before:
        args["before"] = before
    if seen is not None:
        args["seen"] = seen
    if flagged is not None:
        args["flagged"] = flagged

    if ctx:
        await ctx.info(f"Searching emails in {folder}")

    result = await _call_imap_tool("imap_search_emails", args)
    await progress.set_message("Search complete")

    return result


@mcp.tool()
async def imap_get_email(
    accountId: str,
    uid: int,
    folder: str = "INBOX",
    maxContentLength: int = 10000,
    includeAttachmentText: bool = True,
    maxAttachmentTextChars: int = 100000
) -> dict:
    """
    Get the full content of an email.

    Args:
        accountId: Account ID
        uid: Email UID
        folder: Folder name (default: INBOX)
        maxContentLength: Max chars for text/HTML body (default: 10000)
        includeAttachmentText: Include text attachment previews (default: True)
        maxAttachmentTextChars: Max chars per text attachment (default: 100000)

    Returns:
        Full email content with headers, body, attachments
    """
    return await _call_imap_tool("imap_get_email", {
        "accountId": accountId,
        "folder": folder,
        "uid": uid,
        "maxContentLength": maxContentLength,
        "includeAttachmentText": includeAttachmentText,
        "maxAttachmentTextChars": maxAttachmentTextChars
    })


@mcp.tool(task=True)
async def imap_get_attachment(
    accountId: str,
    uid: int,
    folder: str = "INBOX",
    filename: str = None,
    attachmentIndex: int = None,
    maxSizeMB: int = 25,
    ctx: Context = None,
    progress: Progress = Progress()
) -> dict:
    """
    Get email attachment metadata and download URL.

    This is a background task - may take time for large attachments.

    IMPORTANT: This tool returns metadata and a temporary download URL.
    The actual file content is NOT included in the response to save context space.

    To download the file, use the provided 'downloadUrl' - it's a direct HTTP link
    that will return the file with proper Content-Type headers.
    The download URL expires in 5 minutes and can only be used once.

    Args:
        accountId: Account ID
        uid: Email UID
        folder: Folder name (default: INBOX)
        filename: Attachment filename to download (optional)
        attachmentIndex: Attachment index 0-based (optional). Use either filename or attachmentIndex.
        maxSizeMB: Maximum attachment size in MB (default: 25MB)

    Returns:
        Attachment metadata with download URL:
        - filename: Original filename
        - contentType: MIME type
        - size: Size in bytes
        - downloadUrl: Temporary URL to download the file (expires in 5 minutes)
        - expiresIn: Seconds until the download URL expires
    """
    await progress.set_message("Downloading attachment from IMAP server...")

    args = {
        "accountId": accountId,
        "folder": folder,
        "uid": uid,
        "maxSizeMB": maxSizeMB
    }
    if filename is not None:
        args["filename"] = filename
    if attachmentIndex is not None:
        args["attachmentIndex"] = attachmentIndex

    if ctx:
        await ctx.info(f"Getting attachment from email UID {uid}")

    # Get attachment from IMAP server (includes base64 content)
    result = await _call_imap_tool("imap_get_attachment", args)
    await progress.set_message("Processing attachment...")

    # Parse the result to extract attachment data
    import json
    if isinstance(result, dict) and "content" in result:
        # Result is in MCP format: {"content": [{"type": "text", "text": "..."}]}
        content_list = result.get("content", [])
        if content_list and isinstance(content_list[0], dict):
            text_content = content_list[0].get("text", "{}")
            attachment_data = json.loads(text_content)
        else:
            attachment_data = result
    else:
        attachment_data = result

    # Generate download token and cache the attachment
    att_filename = attachment_data.get("filename", "attachment")
    token = _generate_attachment_token(accountId, folder, uid, att_filename)
    _cache_attachment(
        token=token,
        content=attachment_data.get("content", ""),
        filename=att_filename,
        content_type=attachment_data.get("contentType", "application/octet-stream")
    )

    # Return metadata with download URL and resource URI (without base64 content)
    # Use full public URL so clients can download from anywhere
    download_url = f"{PUBLIC_BASE_URL}/download/attachment/{token}"

    await progress.set_message(f"Attachment ready: {att_filename}")

    return {
        "filename": att_filename,
        "contentType": attachment_data.get("contentType", "application/octet-stream"),
        "size": attachment_data.get("size", 0),
        "downloadUrl": download_url,
        "resourceUri": f"email-attachment://{token}",
        "expiresIn": ATTACHMENT_CACHE_TTL,
        "note": "Use downloadUrl (HTTP GET) to download the file. URL expires in 5 minutes and is single-use."
    }


@mcp.tool()
async def imap_get_latest_emails(
    accountId: str,
    folder: str = "INBOX",
    count: int = 10
) -> dict:
    """
    Get the latest emails from a folder.

    Args:
        accountId: Account ID
        folder: Folder name (default: INBOX)
        count: Number of emails to retrieve (default: 10)

    Returns:
        List of recent emails
    """
    return await _call_imap_tool("imap_get_latest_emails", {
        "accountId": accountId,
        "folder": folder,
        "count": count
    })


@mcp.tool()
async def imap_mark_as_read(accountId: str, uid: int, folder: str = "INBOX") -> dict:
    """
    Mark an email as read.

    Args:
        accountId: Account ID
        uid: Email UID
        folder: Folder name (default: INBOX)

    Returns:
        Operation result
    """
    return await _call_imap_tool("imap_mark_as_read", {
        "accountId": accountId,
        "folder": folder,
        "uid": uid
    })


@mcp.tool()
async def imap_mark_as_unread(accountId: str, uid: int, folder: str = "INBOX") -> dict:
    """
    Mark an email as unread.

    Args:
        accountId: Account ID
        uid: Email UID
        folder: Folder name (default: INBOX)

    Returns:
        Operation result
    """
    return await _call_imap_tool("imap_mark_as_unread", {
        "accountId": accountId,
        "folder": folder,
        "uid": uid
    })


@mcp.tool()
async def imap_delete_email(accountId: str, uid: int, folder: str = "INBOX") -> dict:
    """
    Delete an email (moves to trash or expunges).

    Args:
        accountId: Account ID
        uid: Email UID
        folder: Folder name (default: INBOX)

    Returns:
        Deletion result
    """
    return await _call_imap_tool("imap_delete_email", {
        "accountId": accountId,
        "folder": folder,
        "uid": uid
    })


@mcp.tool(task=True)
async def imap_bulk_delete(
    accountId: str,
    uids: List[int],
    folder: str = "INBOX",
    chunkSize: int = 50,
    ctx: Context = None,
    progress: Progress = Progress()
) -> dict:
    """
    Delete multiple emails at once with chunking and auto-reconnection.

    This is a background task with progress reporting.

    Args:
        accountId: Account ID
        uids: Array of email UIDs to delete
        folder: Folder name (default: INBOX)
        chunkSize: Number of emails to delete per batch (default: 50)

    Returns:
        Result with deleted count, failed count, errors
    """
    total_emails = len(uids)
    await progress.set_total(total_emails)
    await progress.set_message(f"Starting bulk delete of {total_emails} emails...")

    if ctx:
        await ctx.info(f"Bulk delete: {total_emails} emails in {folder}")

    result = await _call_imap_tool("imap_bulk_delete", {
        "accountId": accountId,
        "folder": folder,
        "uids": uids,
        "chunkSize": chunkSize
    })

    await progress.set_message(f"Deleted {total_emails} emails")
    await progress.increment(total_emails)

    return result


@mcp.tool(task=True)
async def imap_bulk_delete_by_search(
    accountId: str,
    folder: str = "INBOX",
    from_addr: str = None,
    to_addr: str = None,
    subject: str = None,
    before: str = None,
    since: str = None,
    chunkSize: int = 50,
    dryRun: bool = False,
    ctx: Context = None,
    progress: Progress = Progress()
) -> dict:
    """
    Search for emails and delete them all. Useful for cleaning up spam.

    This is a background task with progress reporting.

    Args:
        accountId: Account ID
        folder: Folder name (default: INBOX)
        from_addr: Delete emails from this sender
        to_addr: Delete emails to this recipient
        subject: Delete emails with this subject
        before: Delete emails before this date (YYYY-MM-DD)
        since: Delete emails since this date (YYYY-MM-DD)
        chunkSize: Number of emails to delete per batch (default: 50)
        dryRun: If True, only return what would be deleted (default: False)

    Returns:
        Result with found count, deleted count, samples (if dryRun)
    """
    await progress.set_message("Searching for emails matching criteria...")

    args = {
        "accountId": accountId,
        "folder": folder,
        "chunkSize": chunkSize,
        "dryRun": dryRun
    }
    if from_addr:
        args["from"] = from_addr
    if to_addr:
        args["to"] = to_addr
    if subject:
        args["subject"] = subject
    if before:
        args["before"] = before
    if since:
        args["since"] = since

    if ctx:
        await ctx.info(f"Bulk delete by search in {folder}")

    result = await _call_imap_tool("imap_bulk_delete_by_search", args)

    if dryRun:
        await progress.set_message("Dry run complete - no emails deleted")
    else:
        await progress.set_message("Bulk delete by search complete")

    return result


@mcp.tool()
async def imap_send_email(
    accountId: str,
    to: str,
    subject: str,
    text: str = None,
    html: str = None,
    cc: str = None,
    bcc: str = None,
    replyTo: str = None
) -> dict:
    """
    Send an email using SMTP.

    Args:
        accountId: Account ID to send from
        to: Recipient email address(es), comma-separated or array
        subject: Email subject
        text: Plain text content
        html: HTML content
        cc: CC recipients
        bcc: BCC recipients
        replyTo: Reply-to address

    Returns:
        Send result with messageId
    """
    args = {
        "accountId": accountId,
        "to": to,
        "subject": subject
    }
    if text:
        args["text"] = text
    if html:
        args["html"] = html
    if cc:
        args["cc"] = cc
    if bcc:
        args["bcc"] = bcc
    if replyTo:
        args["replyTo"] = replyTo

    return await _call_imap_tool("imap_send_email", args)


@mcp.tool()
async def imap_reply_to_email(
    accountId: str,
    uid: int,
    folder: str = "INBOX",
    text: str = None,
    html: str = None,
    replyAll: bool = False
) -> dict:
    """
    Reply to an existing email.

    Args:
        accountId: Account ID
        uid: UID of the email to reply to
        folder: Folder containing the original email (default: INBOX)
        text: Plain text reply content
        html: HTML reply content
        replyAll: Reply to all recipients (default: False)

    Returns:
        Reply result with messageId
    """
    args = {
        "accountId": accountId,
        "folder": folder,
        "uid": uid,
        "replyAll": replyAll
    }
    if text:
        args["text"] = text
    if html:
        args["html"] = html

    return await _call_imap_tool("imap_reply_to_email", args)


@mcp.tool()
async def imap_forward_email(
    accountId: str,
    uid: int,
    to: str,
    folder: str = "INBOX",
    text: str = None,
    includeAttachments: bool = True
) -> dict:
    """
    Forward an existing email.

    Args:
        accountId: Account ID
        uid: UID of the email to forward
        to: Forward to email address(es)
        folder: Folder containing the original email (default: INBOX)
        text: Additional text to include
        includeAttachments: Include original attachments (default: True)

    Returns:
        Forward result with messageId
    """
    args = {
        "accountId": accountId,
        "folder": folder,
        "uid": uid,
        "to": to,
        "includeAttachments": includeAttachments
    }
    if text:
        args["text"] = text

    return await _call_imap_tool("imap_forward_email", args)


# -----------------------------------------------------------------------------
# Folder Operations Tools
# -----------------------------------------------------------------------------

@mcp.tool()
async def imap_list_folders(accountId: str) -> dict:
    """
    List all folders/mailboxes in an IMAP account.

    Args:
        accountId: Account ID

    Returns:
        List of folders with name, delimiter, attributes
    """
    return await _call_imap_tool("imap_list_folders", {"accountId": accountId})


@mcp.tool()
async def imap_folder_status(accountId: str, folder: str) -> dict:
    """
    Get status information about a folder.

    Args:
        accountId: Account ID
        folder: Folder name (required)

    Returns:
        Folder status with messages count, uidvalidity, flags
    """
    return await _call_imap_tool("imap_folder_status", {
        "accountId": accountId,
        "folder": folder
    })


@mcp.tool()
async def imap_get_unread_count(
    accountId: str,
    folders: List[str] = None
) -> dict:
    """
    Get the count of unread emails in specified folders.

    Args:
        accountId: Account ID
        folders: List of folders to check (default: all folders)

    Returns:
        Unread count with totalUnread and byFolder breakdown
    """
    args = {"accountId": accountId}
    if folders:
        args["folders"] = folders

    return await _call_imap_tool("imap_get_unread_count", args)


@mcp.tool()
async def imap_move_emails(
    accountId: str,
    uids: List[int],
    targetFolder: str,
    sourceFolder: str = "INBOX"
) -> dict:
    """
    Move one or more emails to another folder.

    Args:
        accountId: Account ID
        uids: List of email UIDs to move
        targetFolder: Target folder name
        sourceFolder: Source folder name (default: INBOX)

    Returns:
        Result with moved count, failed count, errors
    """
    return await _call_imap_tool("imap_move_emails", {
        "accountId": accountId,
        "uids": uids,
        "targetFolder": targetFolder,
        "sourceFolder": sourceFolder
    })


@mcp.tool()
async def imap_copy_emails(
    accountId: str,
    uids: List[int],
    targetFolder: str,
    sourceFolder: str = "INBOX"
) -> dict:
    """
    Copy one or more emails to another folder.

    Args:
        accountId: Account ID
        uids: List of email UIDs to copy
        targetFolder: Target folder name
        sourceFolder: Source folder name (default: INBOX)

    Returns:
        Result with copied count, failed count, errors
    """
    return await _call_imap_tool("imap_copy_emails", {
        "accountId": accountId,
        "uids": uids,
        "targetFolder": targetFolder,
        "sourceFolder": sourceFolder
    })


@mcp.tool()
async def imap_create_folder(
    accountId: str,
    folderName: str
) -> dict:
    """
    Create a new folder/mailbox.

    Args:
        accountId: Account ID
        folderName: Name of the folder to create (use delimiter for nested, e.g., "Parent/Child")

    Returns:
        Creation result
    """
    return await _call_imap_tool("imap_create_folder", {
        "accountId": accountId,
        "folderName": folderName
    })


@mcp.tool()
async def imap_delete_folder(
    accountId: str,
    folderName: str
) -> dict:
    """
    Delete a folder/mailbox. The folder must be empty.

    Args:
        accountId: Account ID
        folderName: Name of the folder to delete

    Returns:
        Deletion result
    """
    return await _call_imap_tool("imap_delete_folder", {
        "accountId": accountId,
        "folderName": folderName
    })


@mcp.tool()
async def imap_rename_folder(
    accountId: str,
    oldName: str,
    newName: str
) -> dict:
    """
    Rename a folder/mailbox.

    Args:
        accountId: Account ID
        oldName: Current folder name
        newName: New folder name

    Returns:
        Rename result
    """
    return await _call_imap_tool("imap_rename_folder", {
        "accountId": accountId,
        "oldName": oldName,
        "newName": newName
    })


# -----------------------------------------------------------------------------
# Sorting Rules Tools
# -----------------------------------------------------------------------------

@mcp.tool()
async def imap_get_sorting_plan(accountId: str) -> dict:
    """
    Get the sorting plan for an account.

    Args:
        accountId: Account ID

    Returns:
        Sorting plan with rules, folder structure, and settings
    """
    return await _call_imap_tool("imap_get_sorting_plan", {"accountId": accountId})


@mcp.tool()
async def imap_save_sorting_plan(
    accountId: str,
    enabled: bool = None,
    folderStructure: List[dict] = None,
    rules: List[dict] = None
) -> dict:
    """
    Save or update sorting plan for an account.

    Args:
        accountId: Account ID
        enabled: Enable/disable the plan
        folderStructure: List of folder definitions with path, description, autoCreate
        rules: List of sorting rules with conditions and actions

    Returns:
        Saved plan
    """
    args = {"accountId": accountId}
    if enabled is not None:
        args["enabled"] = enabled
    if folderStructure is not None:
        args["folderStructure"] = folderStructure
    if rules is not None:
        args["rules"] = rules
    return await _call_imap_tool("imap_save_sorting_plan", args)


@mcp.tool()
async def imap_delete_sorting_plan(accountId: str) -> dict:
    """
    Delete the sorting plan for an account.

    Args:
        accountId: Account ID

    Returns:
        Deletion result
    """
    return await _call_imap_tool("imap_delete_sorting_plan", {"accountId": accountId})


@mcp.tool()
async def imap_list_sorting_plans() -> dict:
    """
    List all sorting plans.

    Returns:
        List of plans with accountId, accountName, enabled, rulesCount
    """
    return await _call_imap_tool("imap_list_sorting_plans", {})


@mcp.tool()
async def imap_add_sorting_rule(
    accountId: str,
    name: str,
    conditions: dict,
    action: dict,
    enabled: bool = True,
    priority: int = 50,
    stopProcessing: bool = False,
    onlyUnread: bool = None,
    sourceFolder: str = None
) -> dict:
    """
    Add a new sorting rule to an existing plan.

    Args:
        accountId: Account ID
        name: Rule name
        conditions: Rule conditions (supports AND/OR/NOT logic with field conditions)
        action: Action to perform (type: move/copy/markRead/delete, targetFolder for move/copy)
        enabled: Enable/disable the rule (default: True)
        priority: Rule priority, lower = higher priority (default: 50)
        stopProcessing: Stop processing other rules if this matches (default: False)
        onlyUnread: Only apply to unread emails
        sourceFolder: Source folder (default: INBOX)

    Returns:
        Created rule with generated ID
    """
    args = {
        "accountId": accountId,
        "name": name,
        "conditions": conditions,
        "action": action,
        "enabled": enabled,
        "priority": priority,
        "stopProcessing": stopProcessing
    }
    if onlyUnread is not None:
        args["onlyUnread"] = onlyUnread
    if sourceFolder is not None:
        args["sourceFolder"] = sourceFolder
    return await _call_imap_tool("imap_add_sorting_rule", args)


@mcp.tool()
async def imap_update_sorting_rule(
    accountId: str,
    ruleId: str,
    name: str = None,
    conditions: dict = None,
    action: dict = None,
    enabled: bool = None,
    priority: int = None,
    stopProcessing: bool = None,
    onlyUnread: bool = None,
    sourceFolder: str = None
) -> dict:
    """
    Update an existing sorting rule.

    Args:
        accountId: Account ID
        ruleId: Rule ID to update
        name: New rule name
        conditions: New conditions
        action: New action
        enabled: Enable/disable
        priority: New priority
        stopProcessing: Stop processing flag
        onlyUnread: Only unread flag
        sourceFolder: Source folder

    Returns:
        Updated rule
    """
    args = {"accountId": accountId, "ruleId": ruleId}
    if name is not None:
        args["name"] = name
    if conditions is not None:
        args["conditions"] = conditions
    if action is not None:
        args["action"] = action
    if enabled is not None:
        args["enabled"] = enabled
    if priority is not None:
        args["priority"] = priority
    if stopProcessing is not None:
        args["stopProcessing"] = stopProcessing
    if onlyUnread is not None:
        args["onlyUnread"] = onlyUnread
    if sourceFolder is not None:
        args["sourceFolder"] = sourceFolder
    return await _call_imap_tool("imap_update_sorting_rule", args)


@mcp.tool()
async def imap_delete_sorting_rule(accountId: str, ruleId: str) -> dict:
    """
    Delete a sorting rule.

    Args:
        accountId: Account ID
        ruleId: Rule ID to delete

    Returns:
        Deletion result
    """
    return await _call_imap_tool("imap_delete_sorting_rule", {
        "accountId": accountId,
        "ruleId": ruleId
    })


@mcp.tool()
async def imap_reorder_sorting_rules(accountId: str, ruleIds: List[str]) -> dict:
    """
    Reorder sorting rules by setting new priorities based on array order.

    Args:
        accountId: Account ID
        ruleIds: Rule IDs in desired order (first = highest priority)

    Returns:
        Reordered rules with new priorities
    """
    return await _call_imap_tool("imap_reorder_sorting_rules", {
        "accountId": accountId,
        "ruleIds": ruleIds
    })


@mcp.tool()
async def imap_apply_sorting_rules(
    accountId: str,
    folder: str = "INBOX",
    dryRun: bool = False,
    limit: int = 100,
    onlyUnread: bool = False,
    sinceDate: str = None
) -> dict:
    """
    Apply sorting rules to emails. Use dryRun=True to preview without making changes.

    Args:
        accountId: Account ID
        folder: Source folder to process (default: INBOX)
        dryRun: Preview without making changes (default: False)
        limit: Maximum emails to process (default: 100)
        onlyUnread: Only process unread emails (default: False)
        sinceDate: Only process emails since this date (YYYY-MM-DD)

    Returns:
        Result with processed, matched, moved counts and details
    """
    args = {
        "accountId": accountId,
        "folder": folder,
        "dryRun": dryRun,
        "limit": limit,
        "onlyUnread": onlyUnread
    }
    if sinceDate is not None:
        args["sinceDate"] = sinceDate
    return await _call_imap_tool("imap_apply_sorting_rules", args)


@mcp.tool()
async def imap_test_sorting_rule(
    accountId: str,
    rule: dict,
    folder: str = "INBOX",
    sampleSize: int = 50
) -> dict:
    """
    Test a sorting rule against emails without applying any changes.

    Args:
        accountId: Account ID
        rule: Rule to test (with name, conditions, action)
        folder: Folder to test against (default: INBOX)
        sampleSize: Number of emails to test (default: 50)

    Returns:
        Test result with matched count and sample emails
    """
    return await _call_imap_tool("imap_test_sorting_rule", {
        "accountId": accountId,
        "rule": rule,
        "folder": folder,
        "sampleSize": sampleSize
    })


@mcp.tool()
async def imap_create_folders_from_plan(accountId: str) -> dict:
    """
    Create all folders defined in the sorting plan.

    Args:
        accountId: Account ID

    Returns:
        Result with created, existing, and error lists
    """
    return await _call_imap_tool("imap_create_folders_from_plan", {"accountId": accountId})


@mcp.tool()
async def imap_validate_sorting_plan(plan: dict) -> dict:
    """
    Validate a sorting plan without saving it.

    Args:
        plan: Plan to validate (with enabled, folderStructure, rules)

    Returns:
        Validation result with valid flag, errors, warnings
    """
    return await _call_imap_tool("imap_validate_sorting_plan", {"plan": plan})


@mcp.tool()
async def imap_set_sorting_plans_directory(directory: str) -> dict:
    """
    Set the directory where sorting plans are stored.

    Args:
        directory: Absolute path to the plans directory

    Returns:
        Confirmation with current directory path
    """
    return await _call_imap_tool("imap_set_sorting_plans_directory", {"directory": directory})


@mcp.tool()
async def imap_get_sorting_plans_directory() -> dict:
    """
    Get the current directory where sorting plans are stored.

    Returns:
        Current directory path
    """
    return await _call_imap_tool("imap_get_sorting_plans_directory", {})


# =============================================================================
# Server Entry Point
# =============================================================================

def main():
    """Start the Email MCP Server."""
    logger.info(f"Starting Email MCP Server v{__version__}")
    logger.info(f"Protocol version: {__protocol_version__}")
    logger.info(f"IMAP server path: {IMAP_SERVER_PATH}")
    logger.info(f"Listening on {HOST}:{PORT}")

    mcp.run(
        transport="http",
        host=HOST,
        port=PORT,
        path="/mcp"
    )


if __name__ == "__main__":
    main()
