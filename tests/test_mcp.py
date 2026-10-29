"""Exercise the actual stdio entry point, independent of working directory."""

import asyncio
from pathlib import Path
import sys

import pytest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError


def test_stdio_protocol(tmp_path):
    async def check():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "brg_mcp.server", "--data-root", str(Path(__file__).resolve().parents[1])],
            cwd=str(tmp_path),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                assert "get_book_guide" in initialized.instructions
                tools = await session.list_tools()
                assert {tool.name for tool in tools.tools} == {
                    "list_domains", "search_knowledge",
        "read_knowledge",
        "funicular_cable", "draw_diagram", "list_packages",
                    "list_books", "list_book_sections", "search_books", "read_book_section", "get_book_guide",
                    "look_at_figure", "compas_box_notebook", "compas_primitives_notebook", "compas_primitives_add"
                }
                result = await session.call_tool("search_knowledge", {"query": "equilibrium"})
                assert not result.isError
                assert "brg://knowledge/equilibrium" in str(result)
                resource = await session.read_resource("brg://knowledge/equilibrium")
                assert "A f + p = 0" in resource.contents[0].text
                guide = await session.read_resource("brg://books/guide")
                assert "GRAPHIC-STATICS-NOTATION.md" in guide.contents[0].text
                result = await session.call_tool("get_book_guide", {"include_library_map": False})
                assert not result.isError
                assert "Processing a new book" in result.content[0].text
                prompts = await session.list_prompts()
                assert "books_process" in {prompt.name for prompt in prompts.prompts}
                source = "/tmp/scans/A book.pdf"
                prompt = await session.get_prompt("books_process", {
                    "source": source, "workspace": "/tmp/Books", "language": "English"
                })
                text = prompt.messages[0].content.text
                assert source in text
                assert "PROCESSING.md" in text
                assert "source language" in text
                assert "Processing a new book" in text
                assert "$ARGUMENTS" not in text
                with pytest.raises(McpError):
                    await session.get_prompt("books_process", {"source": " "})

    asyncio.run(asyncio.wait_for(check(), timeout=20))


def test_http_app_allows_web_pages_to_list_and_call_tools():
    from starlette.testclient import TestClient
    from brg_mcp.server import create_server, http_app
    rpc = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
           "Origin": "https://brg-teaching.github.io"}
    # as deployed: bound to 0.0.0.0 (no localhost-only host check), stateless JSON
    server = create_server(Path(__file__).resolve().parents[1], host="0.0.0.0", stateless_http=True, json_response=True)
    with TestClient(http_app(server), base_url="http://127.0.0.1:8000") as client:
        preflight = client.options("/mcp", headers={"Origin": "https://brg-teaching.github.io",
                                                    "Access-Control-Request-Method": "POST",
                                                    "Access-Control-Request-Headers": "content-type"})
        assert preflight.status_code == 200 and preflight.headers["access-control-allow-origin"] in ("*", "https://brg-teaching.github.io")
        tools = client.post("/mcp", headers=rpc, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert tools.headers["access-control-allow-origin"] == "*"
        assert "compas_box_notebook" in {t["name"] for t in tools.json()["result"]["tools"]}
        box = client.post("/mcp", headers=rpc, json={"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                                     "params": {"name": "compas_box_notebook", "arguments": {"xsize": 3}}})
        assert '"brg_mcp.ipynb"' in box.json()["result"]["content"][0]["text"]
