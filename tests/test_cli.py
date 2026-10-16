"""The BRG terminal without any model: banner, commands, MCP bridge, model registry, and the
terminal driven through a pipe (prompt_toolkit's test input)."""

import asyncio
import io
import json
from pathlib import Path

import pytest
from prompt_toolkit import PromptSession
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from rich.console import Console

from brg_mcp.cli import banner, commands, models
from brg_mcp.cli.mcp_bridge import MCPBridge
from brg_mcp.cli.providers.agent_cli import mcp_config_file

ROOT = Path(__file__).resolve().parents[1]


def test_logo_is_pixel_art_in_blues():
    text = banner.logo()
    assert "▀" in text.plain or "▄" in text.plain
    assert len(text.plain.splitlines()) == 4          # 8 pixel rows -> 4 terminal lines
    styles = {str(span.style) for span in text.spans}
    assert any("#1f6feb" in s or "#5fb3ff" in s for s in styles)


def test_command_parsing_and_help():
    assert commands.parse("hello") is None
    cmd = commands.parse("/model  Claude Opus 5.5 ")
    assert cmd.name == "/model" and cmd.argument == "Claude Opus 5.5"
    assert commands.parse("/exit").name == "/quit"
    assert "/model" in commands.help_text()


def test_bridge_lists_tools_and_calls_them():
    async def check():
        bridge = MCPBridge(ROOT)
        await bridge.start()
        try:
            assert {t.name for t in bridge.tools} >= {"search_knowledge", "read_knowledge", "list_domains", "search_books"}
            result = await bridge.call_tool("search_knowledge", {"query": "force density"})
            assert "form-finding-compas-fd" in result
            note = await bridge.read_resource("brg://knowledge/equilibrium")
            assert "A f + p = 0" in note
            config = json.loads(mcp_config_file(bridge).read_text())
            assert config["mcpServers"]["brg"]["args"][-1] == str(ROOT)
        finally:
            await bridge.stop()
    asyncio.run(asyncio.wait_for(check(), timeout=30))


def test_model_registry_from_the_accounts():
    server_models = [
        {"value": "default", "resolvedModel": "claude-opus-5-5", "displayName": "Default (recommended)", "description": "x"},
        {"value": "opus", "resolvedModel": "claude-opus-5-5", "displayName": "Opus 5.5", "description": "For complex work"},
        {"value": "fable", "resolvedModel": "claude-fable-5-1", "displayName": "Fable 5.1", "description": "For your toughest challenges"},
    ]
    entries = models.claude_entries(server_models) + [models.ModelEntry("Codex Astra", "codex", "gpt-6-astra", "gpt-6-astra", ("gpt-6-astra",))]
    assert [e.name for e in entries] == ["Claude Opus 5.5", "Claude Fable 5.1", "Codex Astra"]   # no "default"
    assert models.claude_default_model(server_models) == "claude-fable-5-1"      # the strongest, not "default"
    assert models.claude_default_model(server_models[:2]) == "claude-opus-5-5"
    assert models.resolve("fable", entries).model == "claude-fable-5-1"
    assert models.resolve("Claude Opus 5.5", entries).model == "claude-opus-5-5"
    assert models.resolve("astra", entries).provider == "codex"
    assert models.resolve("api:gpt-5", entries).provider == "openai"
    assert models.resolve("nonsense-model", entries) is None
    assert models.codex_display_name("gpt-6.1-sol") == "Codex Sol"


@pytest.mark.asyncio
async def test_terminal_through_a_pipe(tmp_path, monkeypatch):
    """Drive the real loop: commands are typed into a pipe, output goes to a string console."""
    from brg_mcp.cli.term import SlashCompleter, Terminal
    monkeypatch.setenv("BRG_HISTORY", str(tmp_path / "history"))
    out = io.StringIO()
    console = Console(file=out, force_terminal=False, width=120)
    with create_pipe_input() as pipe:
        session = PromptSession(input=pipe, output=DummyOutput())
        terminal = Terminal(ROOT, provider="claude", console=console, session=session)
        session.completer = SlashCompleter(terminal)
        for line in ["/help", "/tools", "/search force density", "/model astra", "/model fable", "/status", "/trace", "/quit"]:
            pipe.send_text(line + "\n")
        await asyncio.wait_for(terminal.run(), timeout=90)
    text = out.getvalue()
    assert "BRG Terminal" in text and "/model" in text                     # banner and help
    assert "search_knowledge" in text and "form-finding-compas-fd" in text  # tools and a direct search
    assert "Codex Astra" in text                                            # switched engine
    assert "Claude Fable 5.1" in text                                       # and back, named in /status
    assert terminal.provider_name == "claude" and terminal.provider.model == "claude-fable-5-1"
    assert "no steps yet" in text                                           # /trace before any reply
    # the completer offers commands after "/" and models after "/model "
    from prompt_toolkit.document import Document
    comp = SlashCompleter(terminal)
    assert {c.text for c in comp.get_completions(Document("/mo"), None)} == {"/model", "/models"}
    assert any("Fable 5.1" in c.text for c in comp.get_completions(Document("/model fab"), None))


def test_trace_chain_and_table():
    """The step chain: thinking and tool badges, results colour them, text starts a new chain."""
    from brg_mcp.cli.providers.base import Event
    from brg_mcp.cli.trace import Trace, metrics_line
    t = Trace()
    assert t.add(Event("thinking"))
    assert t.add(Event("tool_call", "search_knowledge"))
    assert not t.add(Event("tool_args", "search_knowledge", '{"query": "force density"}'))
    assert t.add(Event("tool_result", "", "3 notes", ok=True))
    assert t.running() == "Working…"
    chain = t.chain_text()
    assert chain.plain == ' ◐  thinking ›  ≣  search_knowledge "force density"'      # badge + label
    assert any("link brg://search_knowledge?query=force+density" in str(span.style) for span in chain.spans)
    t.text_started()
    assert t.chain == [] and len(t.steps) == 2
    t.add(Event("tool_call", "read_book_section")); t.add(Event("tool_result", "", "boom", ok=False))
    assert t.chain_text().plain == " ✗  read_book_section"
    table = Console(file=io.StringIO(), width=100); table.print(t.table())
    out = table.file.getvalue()
    assert 'query="force density"' in out and "→ 3 notes" in out and "(failed)" in out
    line = metrics_line({"input": 1000, "output": 200, "cache_read": 800, "tools": 2, "cost": 0.5}, 24.0, 55, show_cost=False).plain
    assert "in 2k" in line and "cache 800" in line and "2 tools" in line and "ctx ▰▰▱▱▱▱▱▱ 24%" in line and "$" not in line


def test_equations_become_unicode():
    from brg_mcp.cli.mathtext import mathify, tex_to_unicode
    assert tex_to_unicode(r"\mathbf{A}\mathbf{f} + \mathbf{p} = \mathbf{0}") == "𝐀𝐟 + 𝐩 = 𝟎"
    assert tex_to_unicode(r"H = \frac{w L^2}{8 f}") == "H = (w L²)/(8 f)"
    assert tex_to_unicode(r"\alpha_{max} \le 30^\circ") == "αₘₐₓ ≤ 30°"
    text = mathify("Fix $q = f/l$ per edge.\n\n$$\\sum_i q_i = Q$$\n\n`$x$` stays; $5 and $6 are prices.")
    assert "Fix q = f/l per edge." in text and "> ∑ᵢ qᵢ = Q" in text
    assert "`$x$`" in text and "$5 and $6" in text


def test_figures_render_as_blocks(tmp_path):
    from PIL import Image
    from brg_mcp.cli import images
    png = tmp_path / "fig.png"
    Image.new("RGB", (8, 4), (255, 0, 0)).save(png)
    out = io.StringIO()
    console = Console(file=out, force_terminal=True, width=60, color_system="truecolor")
    images.show(console, png, "a red figure", max_cols=8)
    text = out.getvalue()
    assert "▀" in text and "255;0;0" in text and "a red figure" in text and "file://" in text
    assert images.resolve("nonexistent.png", [ROOT]) is None
    assert images.IMAGE_LINK.findall("see ![Schek fig 3](images/schek_fig3.png) here") == [("Schek fig 3", "images/schek_fig3.png")]


def test_trimmed_output_has_no_trailing_padding():
    from prompt_toolkit.output import DummyOutput
    from brg_mcp.cli.term import Terminal
    out = io.StringIO()
    terminal = Terminal(ROOT, console=Console(file=out, force_terminal=False, width=120),
                        session=PromptSession(input=create_pipe_input(), output=DummyOutput()))
    terminal.print(terminal.trimmed(terminal.reply_markdown("Short line with $q = f/l$.\n\nSecond paragraph.")))
    lines = out.getvalue().splitlines()
    assert lines[0] == "Short line with q = f/l." and all(line == line.rstrip() for line in lines)
