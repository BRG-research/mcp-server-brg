"""Exercise the actual stdio entry point, independent of working directory."""

import asyncio
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_stdio_protocol(tmp_path):
    async def check():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "brg_mcp.server", "--data-root", str(Path(__file__).resolve().parents[1])],
            cwd=str(tmp_path),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert {tool.name for tool in tools.tools} == {
                    "list_domains", "search_knowledge", "list_packages"
                }
                result = await session.call_tool("search_knowledge", {"query": "equilibrium"})
                assert not result.isError
                assert "brg://knowledge/equilibrium" in str(result)
                resource = await session.read_resource("brg://knowledge/equilibrium")
                assert "A f + p = 0" in resource.contents[0].text

    asyncio.run(asyncio.wait_for(check(), timeout=20))
