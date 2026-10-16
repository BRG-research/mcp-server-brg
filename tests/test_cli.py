"""The BRG terminal without any model: banner, commands, MCP bridge, model registry, and the
terminal driven through a pipe (prompt_toolkit's test input)."""

import asyncio
import io
import json
import time
from pathlib import Path

import pytest
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
    assert models.claude_default_model(server_models) == "claude-opus-5-5"       # Opus by default
    assert models.claude_default_model([server_models[0], server_models[2]]) == "claude-opus-5-5"   # the account default
    assert models.resolve("fable", entries).model == "claude-fable-5-1"
    assert models.resolve("Claude Opus 5.5", entries).model == "claude-opus-5-5"
    assert models.resolve("astra", entries).provider == "codex"
    assert models.resolve("api:gpt-5", entries).provider == "openai"
    assert models.resolve("nonsense-model", entries) is None
    assert models.codex_display_name("gpt-6.1-sol") == "Codex Sol"


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
    for _ in range(3):
        t.add(Event("tool_call", "search_knowledge")); t.add(Event("tool_args", "search_knowledge", '{"query": "funicular"}'))
    packed = t.chain_text(width=60).plain.splitlines()
    assert len(packed) > 1 and all(len(l) <= 60 for l in packed) and packed[0].endswith(" ›")   # broken between steps only
    table = Console(file=io.StringIO(), width=100); table.print(t.table())
    out = table.file.getvalue()
    assert 'query="force density"' in out and "→ 3 notes" in out and "(failed)" in out
    line = metrics_line({"input": 1000, "output": 200, "cache_read": 800, "tools": 2, "cost": 0.5}, 24.0, 55, show_cost=False).plain
    assert "in 2k" in line and "cache 800" in line and "2 tools" in line and "ctx ▰▰▱▱▱▱▱▱ 24%" in line and "$" not in line


def test_equations_in_plain_notation():
    from brg_mcp.cli.mathtext import blocks, mathify, tex_to_plain
    assert tex_to_plain(r"\mathbf{C}^T \mathbf{Q} \mathbf{C} \mathbf{x} = \mathbf{p}") == "C^T Q C x = p"
    assert tex_to_plain(r"H = \frac{w L^2}{8 f}") == "H = (w L²)/(8 f)"
    assert tex_to_plain(r"\alpha_{max} \le 30^\circ") == "α_max ≤ 30°"
    assert tex_to_plain(r"\bar{C}^{\mathsf T} Q \hat{x}_{i+1} = \sqrt{a + b}") == "bar(C)^T Q hat(x)_(i+1) = √(a + b)"
    assert tex_to_plain(r"\sum_{i=1}^{n} q_i l_i^2 \to \infty") == "∑_(i=1)^n q_i l_i² → ∞"
    assert tex_to_plain(r"L^{-1} s") == "L⁻¹ s"
    assert tex_to_plain(r"E = \frac{1}{2}\sum_i q_i l_i^2") == "E = 1/2 ∑_i q_i l_i²"
    assert tex_to_plain(r"\begin{bmatrix} a & b \\ c & d \end{bmatrix}") == "[a b ; c d]"
    text = mathify("Fix $q = f/l$ per edge.\n\n$$\\sum_i q_i = Q$$\n\n`$x$` stays; $5 and $6 are prices.")
    assert "Fix `q = f/l` per edge." in text and "`$x$`" in text and "$5 and $6" in text
    parts = blocks("Text before\n\n$$\\mathbf{D} \\mathbf{x} = \\mathbf{p}$$\n\nafter ```$$ not math $$```")
    assert [k for k, _ in parts] == ["md", "eq", "md"] and parts[1][1] == "\\mathbf{D} \\mathbf{x} = \\mathbf{p}"


def test_figures_render_as_blocks(tmp_path):
    from PIL import Image
    from brg_mcp.cli import images
    png = tmp_path / "fig.png"
    Image.new("RGB", (8, 4), (255, 0, 0)).save(png)
    out = io.StringIO()
    console = Console(file=out, force_terminal=True, width=60, color_system="truecolor")
    images.show(console, png, "a red figure", max_cols=8)                  # auto in a plain terminal: a link, no pixels
    text = out.getvalue()
    assert "▀" not in text and "a red figure" in text and "file://" in text and "Ctrl+click" in text
    images.show(console, png, "a red figure", max_cols=8, mode="blocks")   # the pixel rendering only on request
    assert "▀" in out.getvalue() and "255;0;0" in out.getvalue()
    assert images.resolve("nonexistent.png", [ROOT]) is None
    assert images.IMAGE_LINK.findall("see ![Schek fig 3](images/schek_fig3.png) here") == [("Schek fig 3", "images/schek_fig3.png")]


def test_describe_action_and_modes():
    from brg_mcp.cli.providers.base import MODES
    from brg_mcp.cli.term import describe_action
    assert set(MODES) == {"read", "edit", "auto"}
    assert describe_action("Bash", {"command": "ls -la"}) == "run: ls -la"
    assert describe_action("Write", {"file_path": "a.py", "content": "x\ny"}) == "write a.py (2 lines)"
    assert describe_action("Edit", {"file_path": "a.py", "old_string": "1", "new_string": "2"}).startswith("edit a.py")


def test_display_equations_are_typeset_in_two_dimensions():
    from brg_mcp.cli.mathbox import typeset
    assert typeset(r"\sum_j \frac{s_j}{l_j} (x_k - x_i) + p_i = 0") == [
        "   sⱼ",
        "∑ ──── (xₖ − xᵢ) + pᵢ = 0",
        "j  lⱼ",
    ]
    assert typeset(r"H = \frac{w L^2}{8 f}") == ["     w L²", "H = ──────", "     8 f"]
    assert typeset(r"E = \frac{1}{2} \sum_{i=1}^{n} q_i l_i^2")[1] == "E = ───   ∑   qᵢ lᵢ²"
    assert typeset(r"\begin{bmatrix} k & -k \\ -k & k \end{bmatrix}") == ["⎡k   −k⎤", "⎣−k  k ⎦"]
    assert typeset(r"\alpha_{max} \le 30^\circ") == ["αₘₐₓ ≤ 30°"]
    assert typeset(r"\int_0^L w(x) dx")[0].strip() == "L"           # upper limit above the integral
    assert typeset(r"\left( \frac{a}{b} \right)^2") == ["⎛ a ⎞", "⎜───⎟²", "⎝ b ⎠"]
    assert typeset(r"\frac{a}{b") is None                            # unparsable: the caller falls back


def test_block_boundary_and_status_chain():
    from brg_mcp.cli.term import block_boundary
    from brg_mcp.cli.trace import Trace
    from brg_mcp.cli.providers.base import Event
    assert block_boundary("one paragraph still streaming") == (-1, 0)
    assert block_boundary("done.\n\nnext") == (5, 2)
    assert block_boundary("- a\n- b\n- c") == (7, 1)                        # between list items, last line still open
    assert block_boundary("## Head\nbody\n") == (7, 1)
    assert block_boundary("```\nx\n\ny\n```\n\nz") == (12, 2)                # not inside the fence
    t = Trace()
    for _ in range(6):
        t.add(Event("tool_call", "search_knowledge")); t.add(Event("tool_args", "search_knowledge", '{"query": "funicular"}'))
    short = t.status_chain(40)
    assert short.cell_len <= 40 and short.plain.startswith("… ")


def test_funicular_tool_solves_and_draws():
    from brg_mcp.graphics import funicular
    from brg_mcp.cli.providers.base import drawings_in
    sol = funicular.solve(6, [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1)], 1.0)
    assert [round(z, 2) for _, z in sol["nodes"]] == [0, -2.5, -4.0, -4.5, -4.0, -2.5, 0]
    assert round(sol["segments"][0]["force"], 2) == 2.69 and sol["reactions"]["A"]["vertical"] == 2.5
    steps = funicular.drawings(sol, 80, 20)
    assert len(steps) == 5 and all(s["text"].strip() for s in steps) and "Bow" in steps[0]["title"]
    assert all(len(line) <= 80 for s in steps[:4] for line in s["text"].splitlines())   # the canvas drawings
    assert any("\u2800" <= ch <= "\u28ff" for ch in steps[3]["text"])          # Braille lines
    assert "span 6" in steps[0]["text"] and "pole" in steps[2]["text"]
    result = json.dumps({"result": json.dumps({**sol, "drawings": steps})})
    assert [d["title"] for d in drawings_in(result)] == [s["title"] for s in steps]
    assert drawings_in('{"result": "plain text"}') == [] and drawings_in("not json") == []



async def drive(terminal, pipe, lines, timeout=90):
    """Type the lines into the application (Enter after each) and run it until it exits."""
    async def typist():
        await asyncio.sleep(4)                                        # after the start-up (MCP server, account)
        for line in lines:
            pipe.send_text(line + "\r")
            await asyncio.sleep(1.5)
    asyncio.get_running_loop().create_task(typist())
    await asyncio.wait_for(terminal.run(), timeout=timeout)


@pytest.mark.asyncio
async def test_terminal_application(tmp_path, monkeypatch):
    """Drive the full-screen application: commands typed into a pipe, output read from the transcript."""
    from prompt_toolkit.document import Document
    from brg_mcp.cli.term import SlashCompleter, Terminal
    monkeypatch.setenv("BRG_HISTORY", str(tmp_path / "history"))
    with create_pipe_input() as pipe:
        terminal = Terminal(ROOT, provider="claude", input=pipe, output=DummyOutput())
        await drive(terminal, pipe, ["/help", "/tools", "/search force density", "/model astra", "/model fable",
                                     "/status", "/trace", "/legend", "/mode", "/effort", "/effort low", "/style", "/style plain", "/quit"])
    text = terminal.transcript_text()
    assert "/model" in text and "search_knowledge" in text and "form-finding-compas-fd" in text
    assert "Codex Astra" in text and "Claude Fable 5.1" in text          # switched engine and back
    assert terminal.provider_name == "claude" and terminal.provider.model == "claude-fable-5-1"
    assert "no steps yet" in text and "the model is thinking" in text   # /trace before a reply, /legend
    assert "mode read" in text and "effort default" in text and "effort low" in text and terminal.provider.effort == "low"
    assert "> /help" in text                                            # questions and commands are echoed
    assert "style caveman" in text and "style plain" in text and terminal.provider.style == "plain"
    header = "".join(t for _, t in terminal.header_fragments())
    assert "BRG Terminal" in header and "Claude Fable 5.1" in header and "effort low" in header
    comp = SlashCompleter(terminal)
    assert {c.text for c in comp.get_completions(Document("/mo"), None)} == {"/mode", "/model", "/models", "/mouse"}
    assert {c.text for c in comp.get_completions(Document("/mode "), None)} == {"read", "edit", "auto"}
    assert any("Fable 5.1" in c.text for c in comp.get_completions(Document("/model fab"), None))


def test_print_renders_into_the_transcript(tmp_path, monkeypatch):
    from brg_mcp.cli.term import Terminal
    monkeypatch.setenv("BRG_HISTORY", str(tmp_path / "history"))
    with create_pipe_input() as pipe:
        terminal = Terminal(ROOT, input=pipe, output=DummyOutput())
        terminal.print(terminal.trimmed(terminal.reply_markdown("Short line with $q = f/l$.\n\n$$a = b$$\n\n```python\nx = 1\n```")))
        terminal.print("plain [not markup]")
    lines = terminal.plain
    assert lines[0] == "  Short line with q = f/l." and "  ▌ a = b" in lines and any(l.strip() == "▌ x = 1" for l in lines)
    assert "plain [not markup]" in lines[-1]
    assert all(isinstance(frag, tuple) for line in terminal.lines for frag in line)   # formatted fragments
    assert terminal.cursor_line() == len(lines) - 1                                   # following the newest line


@pytest.mark.asyncio
async def test_escape_interrupts_a_reply(tmp_path, monkeypatch):
    """Esc while the model works cancels the reply."""
    from brg_mcp.cli.term import Terminal
    from brg_mcp.cli.providers.base import Provider
    monkeypatch.setenv("BRG_HISTORY", str(tmp_path / "history"))

    class Slow(Provider):
        name = "slow"
        async def send(self, text, on_text, on_event):
            await asyncio.sleep(20)
            on_text("too late")
            return "too late"

    with create_pipe_input() as pipe:
        terminal = Terminal(ROOT, input=pipe, output=DummyOutput())
        terminal.provider = Slow(terminal.bridge)
        terminal.provider_name = "slow"

        async def script():
            await asyncio.sleep(0.5)
            pipe.send_text("hello\r")
            await asyncio.sleep(1.0)
            pipe.send_text("\x1b")                                    # Esc
            await asyncio.sleep(1.0)
            terminal.app.exit()
        asyncio.get_running_loop().create_task(script())
        started = time.monotonic()
        await asyncio.wait_for(terminal.app.run_async(), timeout=15)
    text = terminal.transcript_text()
    assert time.monotonic() - started < 8 and "interrupted" in text and "too late" not in text


def test_scrolling_the_transcript(tmp_path, monkeypatch):
    from brg_mcp.cli.term import Terminal
    monkeypatch.setenv("BRG_HISTORY", str(tmp_path / "history"))
    with create_pipe_input() as pipe:
        terminal = Terminal(ROOT, input=pipe, output=DummyOutput())
        for i in range(100):
            terminal.print(f"line {i}")
        assert terminal.follow and terminal.cursor_line() == 99
        terminal.scroll(-18)                                           # a page up (no render info: from the cursor line)
        assert not terminal.follow and terminal.cursor_line() == 81
        assert "lines back" in "".join(t for _, t in terminal.status_fragments())
        terminal.scroll(3)
        assert terminal.cursor_line() > 81
        terminal.scroll_to_end()
        assert terminal.follow and terminal.cursor_line() == 99
