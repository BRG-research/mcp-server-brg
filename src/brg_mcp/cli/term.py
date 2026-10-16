"""The BRG terminal: a full-screen prompt_toolkit application.  The banner stays at the top, the
transcript scrolls in the middle (wheel, PageUp/PageDown), a status line shows what the model is doing,
the input sits above a one-line bar.  rich renders the content (Markdown, equations, chains, drawings)
to ANSI lines that prompt_toolkit lays out; the engines, the step chain, the tools and the modes are
unchanged."""

from __future__ import annotations

import argparse
import asyncio
import inspect
import io
import os
import re
import shutil
import subprocess
import time
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path

from prompt_toolkit.application import Application
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import ANSI, to_formatted_text
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import (CompletionsMenu, Float, FloatContainer, FormattedTextControl, HSplit, Layout,
                                   Window)
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea
from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding
from rich.segment import Segment, Segments
from rich.text import Text

from brg_mcp.cli import banner, commands, images, models
from brg_mcp.cli import markdown as md
from brg_mcp.cli.mcp_bridge import MCPBridge
from brg_mcp.cli.providers import PROVIDERS, Provider
from brg_mcp.cli.providers.base import EFFORTS, MODES, STYLES, Event, drawings_in
from brg_mcp.cli.screen import ansi_lines
from brg_mcp.cli.trace import GREY, Trace, legend, metrics_line

try:
    VERSION = package_version("brg-mcp")
except PackageNotFoundError:
    VERSION = "0.1.0"

BACKGROUND = os.environ.get("BRG_BACKGROUND", "")             # empty: the terminal's own colours
HEADER_ROWS = 4                                                # the banner: the logo's height
TEXT_WIDTH = 110                   # replies wrap at this width at most: easier to read
INDENT = 2                         # replies, chains and metrics sit this far from the left edge
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
MAX_LINES = 50_000
_OSC = re.compile("\x1b\\][^\x07\x1b]*(?:\x07|\x1b\\\\)")

APP_STYLE = Style.from_dict({
    "": f"bg:{BACKGROUND}" if BACKGROUND else "",
    "caret": "bold #58a6ff",
    "input": "#e6edf3",
    "hints": "#6e7681",
    "status": "#c9d1d9",
    "completion-menu": "bg:#161b22 #c9d1d9",
    "completion-menu.completion.current": "bg:#1f6feb #ffffff bold",
    "completion-menu.meta.completion": "bg:#161b22 #8b949e",
    "completion-menu.meta.completion.current": "bg:#1f6feb #ffffff",
})


def find_data_root(start: Path | None = None) -> Path:
    """The checkout that holds config/ and knowledge/: the given path, the cwd, or the package's own repo."""
    candidates = [start] if start else []
    candidates += [Path.cwd(), Path(__file__).resolve().parents[3]]
    for c in candidates:
        if c and (c / "config" / "knowledge.yaml").is_file():
            return c.resolve()
    raise SystemExit("could not find a BRG checkout (config/knowledge.yaml); pass --data-root")




class SlashCompleter(Completer):
    """Commands after `/`, models after `/model `, engines after `/provider ` and `/login `."""

    def __init__(self, terminal: "Terminal") -> None:
        self.terminal = terminal

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return
        head, _, rest = text.partition(" ")
        if " " not in text:
            for name, doc in commands.COMMANDS.items():
                if name.startswith(text.lower()):
                    yield Completion(name, start_position=-len(text), display=name, display_meta=doc)
            return
        if head == "/model":
            r = rest.lower()
            for e in self.terminal.model_entries:
                if r in e.name.lower() or r in e.model.lower() or any(r in a.lower() for a in e.aliases):
                    yield Completion(e.name, start_position=-len(rest), display=e.name, display_meta=e.note)
        elif head == "/provider":
            for k in PROVIDERS:
                if k.startswith(rest):
                    yield Completion(k, start_position=-len(rest), display=k, display_meta="engine")
        elif head == "/login":
            for k in ("claude", "codex"):
                if k.startswith(rest):
                    yield Completion(k, start_position=-len(rest), display=k, display_meta="sign in")
        elif head == "/effort":
            for k in EFFORTS + ("default",):
                if k.startswith(rest):
                    yield Completion(k, start_position=-len(rest), display=k)
        elif head == "/style":
            for k in STYLES:
                if k.startswith(rest):
                    yield Completion(k, start_position=-len(rest), display=k)
        elif head == "/mode":
            for k, doc in MODES.items():
                if k.startswith(rest):
                    yield Completion(k, start_position=-len(rest), display=k, display_meta=doc)
        elif head == "/figures":
            for k in images.MODES:
                if k.startswith(rest):
                    yield Completion(k, start_position=-len(rest), display=k)


class Terminal:
    def __init__(self, data_root: Path, provider: str = "claude", model: str | None = None,
                 input=None, output=None, console: Console | None = None) -> None:
        self.data_root = data_root
        # rich renders into this console; its lines are read back as ANSI for the transcript
        self.console = console or Console(file=io.StringIO(), force_terminal=True, color_system="truecolor",
                                          width=100, highlight=False, theme=md.THEME)
        self.bridge = MCPBridge(data_root)
        self.provider_name = provider
        self.requested_model = model
        self.provider: Provider | None = None
        self.model_entries: list[models.ModelEntry] = []
        self.turn: asyncio.Task | None = None
        self.trace: Trace | None = None          # the steps of the last reply (/trace)
        self.context_pct: float | None = None
        self.figures_mode = os.environ.get("BRG_FIGURES", "link")
        if self.figures_mode not in images.MODES:
            self.figures_mode = "link"
        self.mode = os.environ.get("BRG_MODE", "read") if os.environ.get("BRG_MODE") in MODES else "read"
        self.effort = os.environ.get("BRG_EFFORT") if os.environ.get("BRG_EFFORT") in EFFORTS else None
        self.style = os.environ.get("BRG_STYLE", "caveman") if os.environ.get("BRG_STYLE", "caveman") in STYLES else "caveman"
        self.workdir = Path.cwd()                 # where the file tools act in edit/auto mode
        self.mouse = os.environ.get("BRG_MOUSE", "on") != "off"
        self.lines: list[list[tuple[str, str]]] = []     # the transcript, formatted
        self.plain: list[str] = []                        # and as plain text
        self.follow = True                        # the view sticks to the newest line
        self.view_line = 0                        # the line kept in view when not following
        self.status: list[tuple[str, str]] = []   # the line above the input
        self.question: asyncio.Future | None = None   # a y/N question waiting for the next input
        self.interrupts = 0
        history_path = Path(os.environ.get("BRG_HISTORY", Path.home() / ".brg_history"))
        self.input = TextArea(multiline=False, prompt=[("class:caret", "> ")], style="class:input",
                              completer=SlashCompleter(self), complete_while_typing=True,
                              history=FileHistory(str(history_path)), accept_handler=self.on_submit)
        self.transcript_window = Window(
            FormattedTextControl(self.transcript_fragments, focusable=False,
                                 get_cursor_position=lambda: Point(0, self.cursor_line())),
            wrap_lines=True, always_hide_cursor=True)
        root = FloatContainer(
            HSplit([
                Window(FormattedTextControl(self.header_fragments), height=HEADER_ROWS),
                Window(height=1),
                self.transcript_window,
                Window(FormattedTextControl(self.status_fragments), height=1, style="class:status"),
                self.input,
                Window(FormattedTextControl(self.toolbar_fragments), height=1, style="class:hints"),
            ]),
            floats=[Float(xcursor=True, ycursor=True, content=CompletionsMenu(max_height=12, scroll_offset=1))])
        self.app = Application(layout=Layout(root, focused_element=self.input), key_bindings=self.key_bindings(),
                               style=APP_STYLE, full_screen=True, mouse_support=self.mouse,
                               input=input, output=output)

    # ------------------------------------------------------------------ keys
    def key_bindings(self) -> KeyBindings:
        kb = KeyBindings()

        @kb.add("escape", eager=True)
        def _escape(event) -> None:                 # interrupt a running reply, or answer no
            if self.turn is not None and not self.turn.done():
                self.turn.cancel()
            elif self.question is not None and not self.question.done():
                self.question.set_result(False)

        @kb.add("c-c")
        def _ctrl_c(event) -> None:
            if self.turn is not None and not self.turn.done():
                self.turn.cancel()
                return
            self.interrupts += 1
            if self.interrupts >= 2:
                self.app.exit()
            else:
                self.event("Ctrl+C again (or /quit) to leave")

        @kb.add("c-d")
        def _ctrl_d(event) -> None:
            self.app.exit()

        kb.add("pageup")(lambda event: self.scroll(-(self.page_rows() - 2)))
        kb.add("pagedown")(lambda event: self.scroll(self.page_rows() - 2))
        kb.add("s-up")(lambda event: self.scroll(-3))
        kb.add("s-down")(lambda event: self.scroll(3))
        kb.add("end")(lambda event: self.scroll_to_end())

        @kb.add(Keys.Vt100MouseEvent)
        def _mouse(event) -> None:                  # the wheel scrolls the transcript; other mouse events are ignored
            m = re.match(r"\x1b\[<(\d+);(\d+);(\d+)[mM]", event.data or "")
            if m and int(m.group(1)) & 64:
                self.scroll(3 if int(m.group(1)) & 1 else -3)
        return kb

    # ------------------------------------------------------------------ scrolling
    def page_rows(self) -> int:
        info = self.transcript_window.render_info
        return info.window_height if info else 20

    def cursor_line(self) -> int:
        last = max(0, len(self.lines) - 1)
        return last if self.follow else min(self.view_line, last)

    def scroll(self, delta: int) -> None:
        info = self.transcript_window.render_info
        top = info.vertical_scroll if info else self.cursor_line()
        height = self.page_rows()
        last = max(0, len(self.lines) - 1)
        if delta < 0:
            self.follow = False
            self.view_line = max(0, top + delta)
        else:
            self.view_line = min(last, top + height - 1 + delta)
            if self.view_line >= last:
                self.follow = True
        self.app.invalidate()

    def scroll_to_end(self) -> None:
        self.follow = True
        self.app.invalidate()

    # ------------------------------------------------------------------ the boxes
    def header_fragments(self):
        ctx = f"ctx {self.context_pct:.0f}%" if self.context_pct is not None else "ctx 0%"
        effort = f"effort {self.effort}" if self.effort else "effort default"
        busy = self.turn is not None and not self.turn.done()
        state = ("#d29922", "● Working") if busy else ("#3fb950", "● Idle")
        account = self.provider.status() if self.provider else "starting the BRG MCP server…"
        right = [
            [("bold #e6edf3", "BRG Terminal"), ("#8b949e", f"  v{VERSION}   "), state],
            [("#c9d1d9", f"{self.model_label()} · {effort} · style {self.style} · mode {self.mode} · {ctx}")],
            [("#8b949e", f"{account} · {len(self.bridge.tools)} BRG tools")],
            [("#6e7681", str(self.workdir if self.mode != "read" else self.data_root))],
        ]
        out: list[tuple[str, str]] = []
        for i, (logo_line, text_line) in enumerate(zip(banner.logo_fragments(), right)):
            if i:
                out.append(("", "\n"))
            out.append(("", " "))
            out.extend((style.replace(" noreverse", "").replace("noreverse", ""), text) for style, text in logo_line)
            out.append(("", "   "))
            out.extend(text_line)
        return out

    def transcript_fragments(self):
        out: list[tuple[str, str]] = []
        for i, line in enumerate(self.lines):
            if i:
                out.append(("", "\n"))
            out.extend(line)
        return out

    def status_fragments(self):
        if self.status:
            return self.status
        if not self.follow:
            back = max(0, len(self.lines) - 1 - self.cursor_line())
            return [("#d29922", f" ▲ {back} lines back · End or wheel down returns")]
        return [("", "")]

    def toolbar_fragments(self):
        scroll = "wheel or PgUp/PgDn scroll" if self.mouse else "PgUp/PgDn scroll"
        return [("", f" ? shortcuts · ↑↓ history · / commands · {scroll} · Esc interrupts a reply · /quit leaves")]

    def set_title(self) -> None:
        ctx = f" · ctx {self.context_pct:.0f}%" if self.context_pct is not None else ""
        try:
            self.app.output.set_title(f"BRG · {self.model_label()}{ctx}")
        except Exception:                                              # noqa: BLE001
            pass

    def text_width(self) -> int:
        """Replies wrap to this many columns (the console follows the window width)."""
        try:
            cols = self.app.output.get_size().columns
        except Exception:                                              # noqa: BLE001
            cols = 100
        self.console.width = max(40, cols - 1)
        return min(TEXT_WIDTH, self.console.width - 1) - INDENT

    # ------------------------------------------------------------------ output
    def print(self, *args, **kwargs) -> None:
        """Render with rich and append the lines to the transcript."""
        self.text_width()
        if not args:
            lines = [""]
        else:
            lines = []
            for a in args:
                try:
                    lines += ansi_lines(self.console, Text(a) if isinstance(a, str) else a)
                except Exception as exc:                               # noqa: BLE001
                    lines += [f"(could not render: {exc})"]
        for line in lines:
            line = _OSC.sub("", line)
            self.lines.append(to_formatted_text(ANSI(line)))
            self.plain.append(Text.from_ansi(line).plain)
        if len(self.lines) > MAX_LINES:
            del self.lines[: len(self.lines) - MAX_LINES]
            del self.plain[: len(self.plain) - MAX_LINES]
        self.app.invalidate()

    def transcript_text(self) -> str:
        return "\n".join(self.plain)

    def event(self, text: str) -> None:
        self.print(Text.assemble(("● ", "bold #3fb950"), (text, "#c9d1d9")))

    def error(self, text: str) -> None:
        self.print(Text.assemble(("● ", "bold #f85149"), (text, "#f85149")))

    def figure_line(self, path: Path, caption: str = "") -> None:
        """A figure: its caption and path; opened in the image viewer as well in mode open."""
        self.print(Text.assemble(("  ▣ ", "#58a6ff"), (caption or path.name, "bold #c9d1d9"), ("  ", ""),
                                 (str(path), "#8b949e"), ("   /show open <path> opens it", "#484f58")))
        if self.figures_mode == "open":
            images.open_external(path)

    def trimmed(self, renderable, width: int | None = None):
        """A renderable rendered now, without the padding to the full width: lines keep no trailing
        spaces, so a later narrowing of the window does not wrap them into blank lines."""
        self.text_width()
        width = min(width or TEXT_WIDTH, self.console.width)
        renderable = Padding(renderable, (0, 0, 0, INDENT))
        lines = self.console.render_lines(renderable, self.console.options.update_width(width), pad=False)
        out: list[Segment] = []
        for line in lines:
            while line and not line[-1].control and not line[-1].text.strip():
                line.pop()
            if line and not line[-1].control:
                line[-1] = Segment(line[-1].text.rstrip(), line[-1].style)
            out.extend(line)
            out.append(Segment.line())
        while len(out) >= 2 and out[-1].text == "\n" and out[-2].text == "\n":      # no trailing blank lines
            out.pop()
        return Segments(out)

    def reply_markdown(self, text: str):
        """The reply as renderables: Markdown with plain-notation equations, image lines removed
        (the figures are shown below the text)."""
        return md.reply(images.IMAGE_LINK.sub("", text))

    def show_figures(self, text: str, limit: int = 4) -> None:
        """Display the images referenced in a reply (![caption](path)), at most `limit`."""
        seen: set[Path] = set()
        for caption, ref in images.IMAGE_LINK.findall(text):
            if ref.startswith(("http://", "https://")):
                continue
            path = images.resolve(ref, [self.data_root, Path.cwd()])
            if path is None or path in seen or len(seen) >= limit:
                continue
            seen.add(path)
            self.figure_line(path, caption)

    def current_entry(self) -> models.ModelEntry | None:
        if self.provider is None:
            return None
        model = getattr(self.provider, "actual_model", None) or self.provider.model
        for e in self.model_entries:
            if e.provider == self.provider_name and e.model == model:
                return e
        return None

    def model_label(self) -> str:
        entry = self.current_entry()
        if entry is not None:
            return entry.name
        return self.provider.model if self.provider and self.provider.model else "no model"

    def model_line(self) -> str:
        if self.provider is None:
            return "starting the BRG MCP server…"
        mode = "" if self.mode == "read" else f" · mode {self.mode} in {self.workdir}"
        effort = f" · effort {self.effort}" if self.effort else ""
        return f"{self.model_label()} · {self.provider.status()} · {len(self.bridge.tools)} BRG tools{mode}{effort}"

    # ------------------------------------------------------------------ engines
    async def set_provider(self, name: str, model: str | None = None, announce: bool = True) -> None:
        cls = PROVIDERS.get(name)
        if cls is None:
            self.error(f"unknown provider {name!r}; choose from {', '.join(PROVIDERS)}")
            return
        if self.provider is not None and hasattr(self.provider, "close"):
            await self.provider.close()
        self.provider = cls(self.bridge, model)
        self.provider.terminal_width = self.text_width() + INDENT
        self.provider.mode = self.mode
        self.provider.style = self.style
        self.provider.effort = self.effort
        self.provider.workdir = str(self.workdir)
        self.provider.ask_permission = self.ask_permission
        if name == "codex":
            from brg_mcp.cli.providers.agent_cli import codex_account
            self.provider.account = await codex_account()
        self.provider_name = name
        self.set_title()
        self.app.invalidate()
        if announce:
            self.event(f"{self.model_label()} · {self.provider.status()} (new conversation)")

    async def reset_provider(self) -> None:
        result = self.provider.reset()
        if inspect.isawaitable(result):
            await result

    async def load_models(self) -> None:
        """The model list from the accounts: Claude Code's own list (live session) and Codex's config."""
        entries: list[models.ModelEntry] = []
        claude = self.provider if self.provider_name == "claude" else None
        if claude is not None and hasattr(claude, "warm"):
            try:
                info = await claude.warm()
                entries += models.claude_entries(info.get("models") or [], "Claude")
                if not claude.model:
                    claude.model = models.claude_default_model(info.get("models") or []) or ""
            except Exception as exc:                                  # noqa: BLE001
                self.error(f"could not read the Claude model list: {exc}")
        entries += models.codex_entries()
        self.model_entries = entries
        if self.provider_name == "codex" and self.provider and not self.provider.model:
            first = next((e for e in entries if e.provider == "codex"), None)
            if first:
                self.provider.model = first.model

    def first_run_check(self) -> None:
        if self.provider is None:
            return
        ok, todo = self.provider.ready()
        if ok:
            return
        self.error(todo)
        other = "codex" if self.provider_name == "claude" else "claude"
        self.event(f"Accounts: /login claude (Claude account), /login codex (ChatGPT account). /models lists the models; "
                   f"/model {other} switches engine. No account at all? api:<model> with ANTHROPIC_API_KEY or OPENAI_API_KEY also works.")

    async def set_mode(self, mode: str) -> None:
        if mode not in MODES:
            self.error("/mode read | edit | auto")
            return
        if self.provider is None or not self.provider.supports_modes:
            self.error("this engine has only the BRG tools; /mode works with the Claude and Codex engines")
            return
        self.mode = mode
        await self.provider.set_mode(mode)
        note = {"read": "", "edit": " · the model may read, change and run things here; you confirm each change and command",
                "auto": " · no confirmations: the model changes files and runs commands on its own"}[mode]
        self.event(f"mode {mode} in {self.workdir}{note} (new conversation)")
        self.set_title()
        self.app.invalidate()

    def effort_line(self) -> str:
        if self.effort:
            return f"effort {self.effort}"
        default = self.provider.default_effort() if self.provider else "the engine's default"
        return f"effort default ({default})"

    async def set_effort(self, value: str) -> None:
        if value not in EFFORTS and value != "default":
            self.error("/effort low | medium | high | xhigh | max | default")
            return
        self.effort = None if value == "default" else value
        if self.provider is not None:
            await self.provider.set_effort(self.effort)
        fresh = " (new conversation)" if self.provider_name == "claude" else ""
        self.event(f"{self.effort_line()}{fresh}")
        self.app.invalidate()

    async def switch_model(self, name: str) -> None:
        if self.provider is None or not name:
            return
        entry = models.resolve(name, self.model_entries)
        if entry is None:
            self.error(f"unknown model {name!r}; /models lists them")
            return
        if entry.provider != self.provider_name:
            await self.set_provider(entry.provider, entry.model, announce=False)
            self.event(f"model: {entry.name} ({entry.note}); new engine, so a new conversation")
        else:
            if hasattr(self.provider, "set_model"):
                await self.provider.set_model(entry.model)
            else:
                self.provider.model = entry.model
            self.event(f"model: {entry.name} ({entry.note})")
        self.set_title()
        self.app.invalidate()

    async def login(self, which: str) -> None:
        cls = PROVIDERS.get(which)
        command = getattr(cls, "login_command", None)
        if not command:
            self.error(f"/login works for claude and codex, not {which!r}")
            return
        if not shutil.which(command[0]):
            self.error(f"{command[0]} is not installed; see /help")
            return
        with self.app.suspend_to_background():                         # the login runs in the terminal itself
            subprocess.run(command)
        await self.set_provider(which, self.provider.model if self.provider else None, announce=False)
        ok, todo = self.provider.ready()
        (self.event if ok else self.error)(f"signed in: {self.provider.status()}" if ok else todo)

    # ------------------------------------------------------------------ commands
    async def run_command(self, command: commands.Command) -> bool:
        """Returns False when the terminal should exit."""
        name, arg = command.name, command.argument
        if name == "/help":
            self.print(commands.help_text())
        elif name == "/quit":
            return False
        elif name == "/mouse":
            if arg in ("on", "off"):
                self.mouse = arg == "on"
                self.app.mouse_support = self.mouse
            self.event("mouse wheel pages the transcript; hold Shift to select text" if self.mouse
                       else "mouse off: the terminal selects text as usual; PageUp/PageDown page the transcript")
        elif name == "/style":
            if arg in STYLES:
                self.style = arg
                if self.provider is not None:
                    await self.provider.set_style(arg)
                fresh = " (new conversation)" if self.provider_name == "claude" else ""
                self.event(f"style {arg}{fresh}")
                self.app.invalidate()
            else:
                self.event(f"style {self.style} · caveman: fewest words; plain: short prose; full: complete treatment")
        elif name == "/effort":
            if arg:
                await self.set_effort(arg)
            else:
                self.event(f"{self.effort_line()} · low is fastest, high is the model's own default, max thinks longest")
        elif name == "/mode":
            if arg:
                await self.set_mode(arg)
            else:
                self.event(f"mode {self.mode}: {MODES[self.mode]} (directory {self.workdir})")
        elif name == "/status":
            self.event(f"{self.model_line()} · data root {self.data_root}")
        elif name == "/provider":
            await self.set_provider(arg or self.provider_name)
        elif name == "/model":
            if arg:
                await self.switch_model(arg)
            else:
                self.print(models.listing(self.model_entries, self.provider.model if self.provider else None))
        elif name == "/models":
            self.print(models.listing(self.model_entries, self.provider.model if self.provider else None))
        elif name == "/login":
            await self.login(arg or self.provider_name)
        elif name == "/tools":
            for t in self.bridge.tools:
                self.event(f"{t.name}: {t.description.strip().splitlines()[0] if t.description else ''}")
        elif name == "/search":
            self.print(await self.bridge.call_tool("search_knowledge", {"query": arg}))
        elif name == "/read":
            note = await self.bridge.read_resource(f"brg://knowledge/{arg}")
            self.print(self.trimmed(self.reply_markdown(note)))
            self.show_figures(note, limit=12)
        elif name == "/books":
            self.print(await self.bridge.call_tool("search_books", {"query": arg}))
        elif name == "/show":
            await self.show_command(arg)
        elif name == "/figures":
            if arg in images.MODES:
                self.figures_mode = arg
            elif arg:
                self.error(f"/figures auto | link | open | blocks (now: {self.figures_mode})")
                return True
            self.event(f"figures: {self.figures_mode} · link: the path is printed; open: each figure also opens in your image viewer")
        elif name == "/legend":
            self.print(self.trimmed(legend(), width=self.console.width))
        elif name == "/trace":
            if self.trace is None or not self.trace.steps:
                self.event("no steps yet: ask something first")
            else:
                self.print(self.trimmed(self.trace.table(), width=self.console.width))
        elif name == "/clear":
            if self.provider:
                await self.reset_provider()
            self.event("conversation cleared")
        else:
            self.error(f"unknown command {name}; type /help")
        return True

    async def show_command(self, arg: str) -> None:
        """/show <image path>  displays that image; /show <note id>  displays the note's figures;
        /show open <path>  opens the file in the system viewer."""
        if not arg:
            self.error("/show <image path> | /show <note id> | /show open <path>")
            return
        if arg.startswith("open "):
            path = images.resolve(arg[5:].strip(), [self.data_root, Path.cwd()])
            if path is None or not images.open_external(path):
                self.error("could not open that file")
            return
        path = images.resolve(arg, [self.data_root, Path.cwd()])
        if path is not None and path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            self.figure_line(path)
            return
        try:
            note = await self.bridge.read_resource(f"brg://knowledge/{arg}")
        except Exception as exc:                                      # noqa: BLE001
            self.error(f"no image or note {arg!r}: {exc}")
            return
        if not images.IMAGE_LINK.search(note):
            self.event(f"note {arg} has no figures")
            return
        self.show_figures(note, limit=12)

    # ------------------------------------------------------------------ a model turn
    async def ask_permission(self, tool: str, tool_input: dict) -> bool:
        """Asked by the engine before a file change or a command in edit mode: show what it wants and
        take y / N from the input line (Esc declines)."""
        what = describe_action(tool, tool_input)
        self.print(Text.assemble(("? ", "bold #d29922"), (what, "#e6edf3"), ("   allow?  y / N", "#d29922")))
        self.question = asyncio.get_running_loop().create_future()
        self.app.invalidate()
        try:
            allowed = await self.question
        finally:
            self.question = None
        self.event(("allowed: " if allowed else "declined: ") + what.splitlines()[0])
        return allowed

    # ------------------------------------------------------------------ a model turn
    async def ask(self, line: str) -> None:
        """Run one reply.  The status line shows what the model is doing (spinner, elapsed time, the chain
        so far); the chain is printed when text follows it, each paragraph or code block when complete."""
        trace = Trace()
        self.trace = trace
        started = time.monotonic()
        buffer: list[str] = []                       # the paragraph being received
        full: list[str] = []                         # the whole reply, for the figures
        slow_noted = {"at": 0.0}
        self.follow = True

        def tick() -> None:
            label = "Writing…" if buffer else trace.running()
            elapsed = time.monotonic() - started
            frame = SPINNER[int(elapsed * 10) % len(SPINNER)]
            status = [("#58a6ff", f" {frame} "), ("bold #58a6ff", "BRG "), ("#8b949e", f"{self.model_label()} · "),
                      ("#c9d1d9", f"{label} "), ("#6e7681", f"{elapsed:.0f}s")]
            if trace.chain and not buffer:
                chain = trace.status_chain(max(10, self.console.width - 50))
                status.append(("", "   "))
                status.extend(to_formatted_text(ANSI(_OSC.sub("", ansi_lines(self.console, chain)[0]))))
            status.append(("#484f58", "   Esc interrupts"))
            self.status = status
            step_s = trace.current_step_seconds()
            if step_s > 45 and elapsed - slow_noted["at"] > 45:
                slow_noted["at"] = elapsed
                self.print(Text.assemble(("● ", "bold #d29922"),
                                         (f"still waiting on {label.rstrip('…')} ({step_s:.0f}s on this step, {elapsed:.0f}s in all); "
                                          "Esc interrupts, /trace shows the steps afterwards", "#8b949e")))
            self.app.invalidate()

        async def ticker() -> None:
            while True:
                tick()
                await asyncio.sleep(0.1)

        def flush_chain() -> None:
            if trace.chain:
                self.print(self.trimmed(trace.chain_text(self.text_width())))
                self.print()
                trace.text_started()

        def flush_text(final: bool = False) -> None:
            """Print the complete paragraphs (never cutting an open code fence)."""
            text = "".join(buffer)
            if final:
                done, rest = text, ""
            else:
                cut, skip = block_boundary(text)
                if cut < 0:
                    return
                done, rest = text[:cut], text[cut + skip:]
            if done.strip():
                self.print(self.trimmed(self.reply_markdown(done)))
                self.print()                                          # one blank line between blocks
            buffer[:] = [rest] if rest else []

        def on_text(fragment: str) -> None:
            if not fragment:
                return
            if not buffer:
                flush_chain()
            buffer.append(fragment)
            full.append(fragment)
            flush_text()

        def show_drawing(drawing: dict) -> None:
            """A drawing a tool produced: printed now, between the chain so far and what follows."""
            flush_text(final=True)
            flush_chain()
            block = Text()
            if drawing.get("title"):
                block.append(drawing["title"] + "\n", style="bold #e6edf3")
            for line in str(drawing["text"]).splitlines():
                block.append("▌ ", style="#3fb950")
                block.append(line + "\n", style="#e6edf3")
            self.print(self.trimmed(block, width=self.console.width))
            image = drawing.get("image")
            if image and Path(image).is_file():
                self.figure_line(Path(image), drawing.get("title", "").split(":")[0])
            self.print()

        def on_event(event: Event) -> None:
            if event.kind in ("note", "error"):
                style = "#c9d1d9" if event.kind == "note" else "#f85149"
                self.print(Text.assemble(("● ", f"bold {style}"), (event.detail, style)))
                return
            if event.kind in ("thinking", "tool_call") and buffer:
                flush_text(final=True)
            trace.add(event)
            if event.kind == "tool_result" and event.data and event.ok is not False:
                for drawing in drawings_in(event.data.get("text", "")):
                    show_drawing(drawing)

        ticking = asyncio.create_task(ticker())
        try:
            await self.provider.send(line, on_text, on_event)
            if not full and not trace.steps:
                buffer.append("*(no text in the reply)*")
        except asyncio.CancelledError:
            buffer.append("\n\n*(interrupted)*")
        except Exception as exc:                                  # noqa: BLE001
            buffer.append(f"\n\n**{type(exc).__name__}**: {exc}")
        finally:
            ticking.cancel()
            self.status = []
        flush_chain()
        flush_text(final=True)
        self.show_figures("".join(full))
        if self.provider is not None:
            usage = await self.provider.context_usage()
            if usage and usage.get("percentage") is not None:
                self.context_pct = float(usage["percentage"])
        self.set_title()
        self.print(self.trimmed(metrics_line(trace.usage, self.context_pct, time.monotonic() - started,
                                             show_cost=self.provider_name in ("anthropic", "openai"))))   # accounts: no $
        self.print()

    async def send(self, line: str) -> None:
        """Run a reply as a task; Esc (or Ctrl+C) cancels it."""
        self.turn = asyncio.create_task(self.ask(line))
        self.app.invalidate()
        try:
            await self.turn
        finally:
            self.turn = None
            self.app.invalidate()

    # ------------------------------------------------------------------ main loop
    def on_submit(self, buffer) -> bool:
        """Enter in the input line."""
        line = buffer.text.strip()
        if self.question is not None and not self.question.done():
            self.question.set_result(line.lower() in ("y", "yes"))
            return False
        if not line:
            return False
        self.interrupts = 0
        self.follow = True
        self.print(Text.assemble(("> ", "bold #58a6ff"), (line, "#e6edf3")))
        if self.turn is not None and not self.turn.done():
            self.error("a reply is still running: Esc interrupts it")
            return False
        self.app.create_background_task(self.handle(line))
        return False                                                   # clear the input

    async def handle(self, line: str) -> None:
        try:
            if line in ("?", "/"):
                self.print(Text(commands.help_text()))
                return
            command = commands.parse(line)
            if command:
                if not await self.run_command(command):
                    self.app.exit()
                return
            if self.provider is None:
                self.error("no provider; the MCP server did not start")
                return
            ok, todo = self.provider.ready()
            if not ok:
                self.error(todo)
                return
            await self.send(line)
        except Exception as exc:                                      # noqa: BLE001
            self.error(f"{type(exc).__name__}: {exc}")

    async def startup(self) -> None:
        self.status = [("#58a6ff", " ⠋ "), ("#8b949e", "starting the BRG MCP server and your account…")]
        try:
            await self.bridge.start()
        except Exception as exc:                                      # noqa: BLE001
            self.error(f"could not start the BRG MCP server: {exc}")
            self.status = []
            return
        await self.set_provider(self.provider_name, self.requested_model, announce=False)
        if self.provider is not None and self.provider.ready()[0]:
            await self.load_models()
        self.status = []
        self.set_title()
        self.event("Type a question, or /help. /legend explains the symbols.")
        self.first_run_check()
        self.app.invalidate()

    async def run(self) -> None:
        self.app.create_background_task(self.startup())
        try:
            await self.app.run_async()
        finally:
            if self.provider is not None and hasattr(self.provider, "close"):
                await self.provider.close()
            await self.bridge.stop()


_LIST_LINE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+")
_BLOCK_START = re.compile(r"^(#{1,6}\s|\s*([-*+]|\d+[.)])\s+|```|\||>)")


def block_boundary(text: str) -> tuple[int, int]:
    """Where the complete part of a streaming Markdown text ends: at the last blank line, or at the last
    line break between two list items or after a heading, never inside a code fence.  Returns (cut, skip)
    with skip the length of the separator, or (-1, 0) when nothing is complete yet."""
    best = (-1, 0)
    for i in range(len(text) - 1, -1, -1):
        if text[i] != "\n":
            continue
        before = text[:i]
        if before.count("```") % 2 == 1:
            continue
        if text.startswith("\n\n", i):
            return (i, 2)
        prev_line = before.rsplit("\n", 1)[-1]
        next_line = text[i + 1:].split("\n", 1)[0]
        if prev_line.startswith("#") or (_LIST_LINE.match(prev_line) and _LIST_LINE.match(next_line)):
            return (i, 1)                              # a finished heading, or a finished list item before the next
    return best


def describe_action(tool: str, tool_input: dict) -> str:
    """One readable line (or a few) for a tool call the user must approve; paths relative to the directory."""
    tool_input = dict(tool_input)
    for key in ("file_path", "path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and os.path.isabs(value):
            try:
                tool_input[key] = os.path.relpath(value)
            except ValueError:
                pass
    if tool == "Bash":
        return f"run: {tool_input.get('command', '')}"
    if tool in ("Write", "NotebookEdit"):
        content = str(tool_input.get("content", ""))
        lines = content.count("\n") + 1 if content else 0
        return f"write {tool_input.get('file_path', '?')} ({lines} lines)"
    if tool == "Edit":
        old, new = str(tool_input.get("old_string", "")), str(tool_input.get("new_string", ""))
        return f"edit {tool_input.get('file_path', '?')}\n    - {old[:200]!r}\n    + {new[:200]!r}"
    if tool in ("WebFetch", "WebSearch"):
        return f"{tool.lower()}: {tool_input.get('url') or tool_input.get('query', '')}"
    args = ", ".join(f"{k}={str(v)[:80]!r}" for k, v in tool_input.items())
    return f"{tool}({args})"



def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="brg", description="BRG terminal: chat with your own Claude or ChatGPT account over the BRG MCP server")
    parser.add_argument("--data-root", type=Path, default=None, help="checkout with config/ and knowledge/ (default: auto-detect)")
    parser.add_argument("--provider", default=os.environ.get("BRG_PROVIDER", "claude"), choices=list(PROVIDERS))
    parser.add_argument("--model", default=os.environ.get("BRG_MODEL"), help="model name (default: the account's)")
    parser.add_argument("--mode", default=None, choices=list(MODES), help="read (default), edit or auto; see /mode")
    parser.add_argument("--effort", default=None, choices=list(EFFORTS), help="how hard the model thinks; see /effort")
    args = parser.parse_args(argv)
    provider, model = args.provider, args.model
    entry = models.resolve(model, []) if model else None
    if entry is not None:
        provider, model = entry.provider, entry.model
    if args.mode:
        os.environ["BRG_MODE"] = args.mode
    if args.effort:
        os.environ["BRG_EFFORT"] = args.effort
    asyncio.run(Terminal(find_data_root(args.data_root), provider, model).run())


if __name__ == "__main__":
    main()
