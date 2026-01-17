"""
STDIO Bridge for imap-mcp-server

Provides asynchronous communication with the Node.js-based
imap-mcp-server via STDIO subprocess.
"""

import asyncio
import json
import logging
import os
from typing import Optional, Any

logger = logging.getLogger(__name__)


class StdioBridge:
    """
    Bridge between FastMCP HTTP server and STDIO-based imap-mcp-server.

    Manages a subprocess running the Node.js imap-mcp-server and
    provides async methods for JSON-RPC communication.
    """

    def __init__(self, server_path: str):
        """
        Initialize the STDIO bridge.

        Args:
            server_path: Path to the imap-mcp-server entry point (index.js)
        """
        self.server_path = server_path
        self.process: Optional[asyncio.subprocess.Process] = None
        self._lock = asyncio.Lock()
        self._started = False
        self._read_buffer = ""
        self._request_id = 0

    async def start(self) -> None:
        """Start the STDIO subprocess."""
        if self._started:
            return

        logger.info(f"Starting imap-mcp-server: {self.server_path}")

        # Verify server exists
        if not os.path.exists(self.server_path):
            raise FileNotFoundError(f"imap-mcp-server not found: {self.server_path}")

        # Increase limit to 50MB to handle large base64 attachments
        # Default asyncio limit is 64KB which is too small for attachments
        limit = 50 * 1024 * 1024  # 50MB
        self.process = await asyncio.create_subprocess_exec(
            "node", self.server_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "NODE_ENV": "production"},
            limit=limit
        )

        self._started = True
        logger.info(f"imap-mcp-server started with PID: {self.process.pid}")

        # Start stderr reader for logging
        asyncio.create_task(self._read_stderr())

    async def _read_stderr(self) -> None:
        """Read and log stderr from subprocess."""
        if not self.process or not self.process.stderr:
            return

        while True:
            try:
                line = await self.process.stderr.readline()
                if not line:
                    break
                logger.info(f"[imap-mcp-server] {line.decode().strip()}")
            except Exception as e:
                logger.error(f"Error reading stderr: {e}")
                break

    async def _restart(self) -> None:
        """Restart the subprocess after a crash."""
        logger.warning("Restarting imap-mcp-server subprocess...")
        self._started = False
        if self.process:
            try:
                self.process.kill()
                await self.process.wait()
            except Exception:
                pass
        self.process = None
        await self.start()

    async def call(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Send a JSON-RPC request and receive response.

        Args:
            request: JSON-RPC request dictionary

        Returns:
            JSON-RPC response dictionary
        """
        # Check if process is alive, restart if dead
        if not self.is_running():
            logger.warning("imap-mcp-server process not running, restarting...")
            await self._restart()

        async with self._lock:
            try:
                # Double-check process is still alive after acquiring lock
                if not self.is_running():
                    await self._restart()

                # Send request
                request_str = json.dumps(request) + "\n"
                logger.debug(f"Sending to imap-mcp-server: {request_str[:200]}...")

                self.process.stdin.write(request_str.encode())
                await self.process.stdin.drain()

                # Read response (5 min timeout for large mailbox operations)
                response_line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=300.0
                )

                if not response_line:
                    raise RuntimeError("No response from imap-mcp-server")

                response = json.loads(response_line.decode())
                logger.debug(f"Received from imap-mcp-server: {str(response)[:200]}...")

                return response

            except asyncio.TimeoutError:
                logger.error("Timeout waiting for response from imap-mcp-server")
                # Restart on timeout
                await self._restart()
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {e}")
                raise
            except (ConnectionResetError, BrokenPipeError, RuntimeError) as e:
                logger.error(f"Connection error with imap-mcp-server: {e}")
                # Restart on connection errors
                await self._restart()
                raise
            except Exception as e:
                logger.error(f"Error communicating with imap-mcp-server: {e}")
                # Restart on any error
                await self._restart()
                raise

    async def stop(self) -> None:
        """Stop the STDIO subprocess."""
        if self.process:
            logger.info("Stopping imap-mcp-server...")
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Force killing imap-mcp-server")
                self.process.kill()
                await self.process.wait()

            self._started = False
            logger.info("imap-mcp-server stopped")

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
            server_path: Path to imap-mcp-server
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
