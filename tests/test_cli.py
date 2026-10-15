"""The BRG terminal without any model: banner, commands, MCP bridge, and the app driven headless."""

import asyncio
import json
from pathlib import Path

import pytest

from brg_mcp.cli import banner, commands
from brg_mcp.cli.mcp_bridge import MCPBridge
from brg_mcp.cli.providers.agent_cli import mcp_config_file

ROOT = Path(__file__).resolve().parents[1]


def test_logo_is_pixel_art_in_blues():
    text = banner.logo()
    assert "▀" in text.plain or "▄" in text.plain
    assert len(text.plain.splitlines()) == 4          # 8 pixel rows -> 4 terminal lines
    styles = {span.style for span in text.spans}
    assert any("#1f6feb" in str(s) or "#5fb3ff" in str(s) for s in styles)


def test_command_parsing_and_help():
    assert commands.parse("hello") is None
    cmd = commands.parse("/model  claude-opus-5-5 ")
    assert cmd.name == "/model" and cmd.argument == "claude-opus-5-5"
    assert commands.parse("/exit").name == "/quit"
    assert "/provider" in commands.help_text()


def test_bridge_lists_tools_and_calls_them():
    async def check():
        bridge = MCPBridge(ROOT)
        await bridge.start()
        try:
            assert {t.name for t in bridge.tools} >= {"search_knowledge", "list_domains", "search_books"}
            result = await bridge.call_tool("search_knowledge", {"query": "force density"})
            assert "form-finding-compas-fd" in result
            note = await bridge.read_resource("brg://knowledge/equilibrium")
            assert "A f + p = 0" in note
            config = json.loads(mcp_config_file(bridge).read_text())
            assert config["mcpServers"]["brg"]["args"][-1] == str(ROOT)
        finally:
            await bridge.stop()
    asyncio.run(asyncio.wait_for(check(), timeout=30))


@pytest.mark.asyncio
async def test_app_headless_commands():
    from brg_mcp.cli.app import BRGTerminal, Message
    app = BRGTerminal(ROOT, provider="claude")
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(2.0)                               # the MCP server starts in on_mount
        prompt = app.query_one("#prompt")
        for line in ["/help", "/tools", "/search force density", "/status", "/model gpt-6-astra", "/model opus"]:
            prompt.value = line
            await pilot.press("enter")
            await pilot.pause(0.5)
        texts = [m.text for m in app.query(Message)]
        assert any("/provider" in t for t in texts)
        assert any("search_knowledge" in t for t in texts)
        assert any("form-finding-compas-fd" in t for t in texts)
        assert any("Claude account" in t for t in texts)
        assert any("gpt-6-astra" in t and "ChatGPT" in t for t in texts)      # switched engine
        assert app.provider_name == "claude" and app.provider.model == "opus"  # and back
        assert "BRG tools" in str(app.query_one("#title").content)


def test_model_registry_routes_to_engines():
    from brg_mcp.cli import models
    assert models.resolve("opus").provider == "claude" and models.resolve("opus").model == "opus"
    assert models.resolve("gpt-6-astra").provider == "codex"
    assert models.resolve("claude-opus-5-5").provider == "claude"
    assert models.resolve("api:claude-opus-5-5").provider == "anthropic"
    assert models.resolve("api:gpt-5").provider == "openai"
    assert models.resolve("nonsense-model") is None
    assert "opus" in models.listing() and "codex" in models.listing()


@pytest.mark.asyncio
async def test_model_picker_opens_and_selects():
    from brg_mcp.cli.app import BRGTerminal, Message
    from brg_mcp.cli.pickers import Picker
    app = BRGTerminal(ROOT, provider="claude")
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(2.0)
        app.query_one("#prompt").value = "/model"
        await pilot.press("enter")
        await pilot.pause(0.3)
        assert isinstance(app.screen, Picker)
        await pilot.press("down", "enter")            # second entry: opus
        await pilot.pause(0.8)
        assert not isinstance(app.screen, Picker)
        assert app.provider.model == "opus"
        app.query_one("#prompt").value = "/"
        await pilot.press("enter")
        await pilot.pause(0.3)
        assert isinstance(app.screen, Picker)
        await pilot.press("escape")
        await pilot.pause(0.2)
        assert not isinstance(app.screen, Picker)
