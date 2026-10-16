"""A stdio MCP client to the BRG server, kept open for the life of the terminal."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from brg_mcp.cli import logs


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict


class MCPBridge:
    """Spawns `python -m brg_mcp.server --data-root ...` and exposes its tools and resources."""

    def __init__(self, data_root: Path):
        self.data_root = Path(data_root).resolve()
        self.session: ClientSession | None = None
        self.tools: list[ToolSpec] = []
        self.instructions: str = ""
        self._task: asyncio.Task | None = None
        self._ready: asyncio.Event | None = None
        self._stop: asyncio.Event | None = None
        self._error: BaseException | None = None

    def server_command(self) -> tuple[str, list[str]]:
        return sys.executable, ["-m", "brg_mcp.server", "--data-root", str(self.data_root)]

    async def _run(self) -> None:
        """Owns the connection: the MCP context managers must be entered and exited by the same task."""
        command, args = self.server_command()
        try:
            async with stdio_client(StdioServerParameters(command=command, args=args, cwd=str(self.data_root)),
                                    errlog=logs.handle()) as (read, write):   # never the terminal
                async with ClientSession(read, write) as session:
                    initialized = await session.initialize()
                    self.instructions = initialized.instructions or ""
                    listed = await session.list_tools()
                    self.tools = [ToolSpec(t.name, t.description or "", t.inputSchema or {"type": "object", "properties": {}})
                                  for t in listed.tools]
                    self.session = session
                    self._ready.set()
                    await self._stop.wait()
        except BaseException as exc:                              # noqa: BLE001 - surfaced by start()
            self._error = exc
            self._ready.set()
            raise
        finally:
            self.session = None

    async def start(self) -> None:
        self._ready, self._stop = asyncio.Event(), asyncio.Event()
        self._task = asyncio.create_task(self._run())
        await self._ready.wait()
        if self._error is not None:
            raise RuntimeError(f"BRG MCP server failed to start: {self._error}") from self._error

    async def stop(self) -> None:
        if self._task is not None and self._stop is not None:
            self._stop.set()
            try:
                await self._task
            except BaseException:                                 # noqa: BLE001 - shutting down
                pass
            self._task = None

    async def call_tool(self, name: str, arguments: dict) -> str:
        """Call a tool and return its result as text (JSON for structured results)."""
        assert self.session is not None, "bridge not started"
        result = await self.session.call_tool(name, arguments)
        parts = []
        for block in result.content:
            text = getattr(block, "text", None)
            parts.append(text if text is not None else json.dumps(block.model_dump(), default=str))
        text = "\n".join(parts) if parts else ""
        if result.isError:
            return f"ERROR: {text}"
        return text

    async def read_resource(self, uri: str) -> str:
        assert self.session is not None, "bridge not started"
        result = await self.session.read_resource(uri)
        return "\n".join(getattr(c, "text", "") for c in result.contents)
