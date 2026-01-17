"""
STDIO Bridge for bitrix-mcp-server

Provides asynchronous communication with the Node.js-based
bitrix-mcp-server via STDIO subprocess.
"""

import asyncio
import json
import logging
import os
from typing import Optional, Any

logger = logging.getLogger(__name__)


class StdioBridge:
    """
    Bridge between FastMCP HTTP server and STDIO-based bitrix-mcp-server.

    Manages a subprocess running the Node.js bitrix-mcp-server and
    provides async methods for JSON-RPC communication.
    """

    def __init__(self, server_path: str):
        """
        Initialize the STDIO bridge.

        Args:
            server_path: Path to the bitrix-mcp-server entry point (index.js)
        """
        self.server_path = server_path
        self.process: Optional[asyncio.subprocess.Process] = None
        self._lock = asyncio.Lock()
        self._started = False
        self._read_buffer = ""

    async def start(self) -> None:
        """Start the STDIO subprocess."""
        if self._started:
            return

        logger.info(f"Starting bitrix-mcp-server: {self.server_path}")

        # Verify server exists
        if not os.path.exists(self.server_path):
            raise FileNotFoundError(f"bitrix-mcp-server not found: {self.server_path}")

        self.process = await asyncio.create_subprocess_exec(
            "node", self.server_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "NODE_ENV": "production"}
        )

        self._started = True
        logger.info(f"bitrix-mcp-server started with PID: {self.process.pid}")

        # Start stderr reader for logging
        asyncio.create_task(self._read_stderr())

        # Initialize MCP protocol
        await self._initialize_mcp()

    async def _initialize_mcp(self) -> None:
        """Initialize MCP protocol with the subprocess."""
        from . import __version__, __protocol_version__

        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": __protocol_version__,
                "capabilities": {},
                "clientInfo": {
                    "name": "bitrix-mcp-wrapper",
                    "version": __version__
                }
            },
            "id": 0
        }

        try:
            request_str = json.dumps(init_request) + "\n"
            logger.debug(f"Sending MCP initialize: {request_str[:100]}...")

            self.process.stdin.write(request_str.encode())
            await self.process.stdin.drain()

            # Read lines until we get JSON response (skip non-JSON startup messages)
            while True:
                response_line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=30.0
                )

                if not response_line:
                    logger.warning("No response to MCP initialize")
                    break

                line_str = response_line.decode().strip()
                if not line_str:
                    continue

                # Skip non-JSON lines (startup messages)
                if not line_str.startswith('{'):
                    logger.debug(f"Skipping non-JSON line: {line_str}")
                    continue

                response = json.loads(line_str)
                logger.info(f"MCP initialized: {response.get('result', {}).get('serverInfo', {})}")
                break

        except Exception as e:
            logger.error(f"Failed to initialize MCP: {e}")
            raise

    async def _read_stderr(self) -> None:
        """Read and log stderr from subprocess."""
        if not self.process or not self.process.stderr:
            return

        while True:
            try:
                line = await self.process.stderr.readline()
                if not line:
                    break
                logger.debug(f"[bitrix-mcp-server] {line.decode().strip()}")
            except Exception as e:
                logger.error(f"Error reading stderr: {e}")
                break

    async def call(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Send a JSON-RPC request and receive response.

        Args:
            request: JSON-RPC request dictionary

        Returns:
            JSON-RPC response dictionary
        """
        if not self._started or not self.process:
            await self.start()

        async with self._lock:
            try:
                # Send request
                request_str = json.dumps(request) + "\n"
                logger.debug(f"Sending to bitrix-mcp-server: {request_str[:200]}...")

                self.process.stdin.write(request_str.encode())
                await self.process.stdin.drain()

                # Read response (5 min timeout for large operations)
                # Skip non-JSON lines that might appear
                while True:
                    response_line = await asyncio.wait_for(
                        self.process.stdout.readline(),
                        timeout=300.0
                    )

                    if not response_line:
                        raise RuntimeError("No response from bitrix-mcp-server")

                    line_str = response_line.decode().strip()
                    if not line_str:
                        continue

                    # Skip non-JSON lines
                    if not line_str.startswith('{'):
                        logger.debug(f"Skipping non-JSON line: {line_str}")
                        continue

                    response = json.loads(line_str)
                    logger.debug(f"Received from bitrix-mcp-server: {str(response)[:200]}...")
                    break

                return response

            except asyncio.TimeoutError:
                logger.error("Timeout waiting for response from bitrix-mcp-server")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {e}")
                raise
            except Exception as e:
                logger.error(f"Error communicating with bitrix-mcp-server: {e}")
                raise

    async def stop(self) -> None:
        """Stop the STDIO subprocess."""
        if self.process:
            logger.info("Stopping bitrix-mcp-server...")
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Force killing bitrix-mcp-server")
                self.process.kill()
                await self.process.wait()

            self._started = False
            logger.info("bitrix-mcp-server stopped")

    def is_running(self) -> bool:
        """Check if subprocess is running."""
        return self._started and self.process and self.process.returncode is None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()


class StdioBridgePool:
    """
    Pool of STDIO bridges for handling multiple sessions.

    Each session gets its own bridge instance to maintain
    isolation between different users/connections.
    """

    def __init__(self, server_path: str, max_bridges: int = 10):
        """
        Initialize the bridge pool.

        Args:
            server_path: Path to bitrix-mcp-server
            max_bridges: Maximum number of concurrent bridges
        """
        self.server_path = server_path
        self.max_bridges = max_bridges
        self._bridges: dict[str, StdioBridge] = {}
        self._lock = asyncio.Lock()

    async def get_bridge(self, session_id: str) -> StdioBridge:
        """
        Get or create a bridge for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            StdioBridge instance for the session
        """
        async with self._lock:
            if session_id not in self._bridges:
                if len(self._bridges) >= self.max_bridges:
                    # Remove oldest inactive bridge
                    for old_id, bridge in list(self._bridges.items()):
                        if not bridge.is_running():
                            await bridge.stop()
                            del self._bridges[old_id]
                            break
                    else:
                        # Force remove oldest
                        if self._bridges:
                            old_id = next(iter(self._bridges))
                            await self._bridges[old_id].stop()
                            del self._bridges[old_id]

                bridge = StdioBridge(self.server_path)
                await bridge.start()
                self._bridges[session_id] = bridge

            return self._bridges[session_id]

    async def remove_bridge(self, session_id: str) -> None:
        """Remove and stop a bridge."""
        async with self._lock:
            if session_id in self._bridges:
                await self._bridges[session_id].stop()
                del self._bridges[session_id]

    async def cleanup(self) -> None:
        """Stop all bridges."""
        async with self._lock:
            for bridge in self._bridges.values():
                await bridge.stop()
            self._bridges.clear()

    @property
    def active_count(self) -> int:
        """Number of active bridges."""
        return len(self._bridges)
