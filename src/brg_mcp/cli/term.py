"""The BRG terminal, built on the terminal itself: the transcript is printed into the terminal's own
scrollback (its scrollbar, selection and copy work as usual) and only the prompt line is live, as in
Claude Code.  prompt_toolkit draws the prompt, the completion menu under it and the history;
rich prints the banner, the streamed Markdown replies and the events."""

from __future__ import annotations

import argparse
import asyncio
import inspect
import os
import re
import shutil
import signal
import subprocess
import time
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.padding import Padding
from rich.segment import Segment, Segments
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from brg_mcp.cli import banner, commands, models
from brg_mcp.cli.mcp_bridge import MCPBridge
from brg_mcp.cli.providers import PROVIDERS, Provider
from brg_mcp.cli import images
from brg_mcp.cli import markdown as md
from brg_mcp.cli.providers.base import EFFORTS, MODES, Event, drawings_in
from brg_mcp.cli.screen import PinnedScreen, ansi_lines
from brg_mcp.cli.trace import GREY, Trace, legend, metrics_line

TEXT_WIDTH = 110                   # replies wrap at this width at most: easier to read, fewer reflow problems
INDENT = 2                         # replies, chains and metrics sit this far from the left edge

BACKGROUND = os.environ.get("BRG_BACKGROUND", "#0b1220")      # the terminal's background while brg runs (OSC 11)
HEADER_ROWS = 5                                                # the pinned banner: 4 rows of logo + 1 blank

try:
    VERSION = package_version("brg-mcp")
except PackageNotFoundError:
    VERSION = "0.1.0"

PROMPT_STYLE = Style.from_dict({
    "caret": "bold #58a6ff",
    "bottom-toolbar": "#6e7681 noreverse",
    "bottom-toolbar.title": "bold #e6edf3 noreverse",
    "bottom-toolbar.model": "#c9d1d9 noreverse",
    "bottom-toolbar.idle": "#3fb950 noreverse",
    "completion-menu": "bg:#161b22 #c9d1d9",
    "completion-menu.completion.current": "bg:#1f6feb #ffffff bold",
    "completion-menu.meta.completion": "bg:#161b22 #8b949e",
    "completion-menu.meta.completion.current": "bg:#1f6feb #ffffff",
})


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
                 console: Console | None = None, session: PromptSession | None = None) -> None:
        self.data_root = data_root
        self.console = console or Console(highlight=False, theme=md.THEME)
        if console is not None:
            self.console.push_theme(md.THEME)
        self.bridge = MCPBridge(data_root)
        self.provider_name = provider
        self.requested_model = model
        self.provider: Provider | None = None
        self.model_entries: list[models.ModelEntry] = []
        self.turn: asyncio.Task | None = None
        self.trace: Trace | None = None          # the steps of the last reply (/trace)
        self.context_pct: float | None = None
        self.figures_mode = os.environ.get("BRG_FIGURES", "auto")
        if self.figures_mode not in images.MODES:
            self.figures_mode = "auto"
        self.mode = os.environ.get("BRG_MODE", "read") if os.environ.get("BRG_MODE") in MODES else "read"
        self.effort = os.environ.get("BRG_EFFORT") if os.environ.get("BRG_EFFORT") in EFFORTS else None
        self.workdir = Path.cwd()                 # where the file tools act in edit/auto mode
        self.live: Live | None = None             # the status line of a running turn, paused for questions
        self.pinned = os.environ.get("BRG_HEADER", "top") != "scroll" and self.console.is_terminal
        self.screen = PinnedScreen(self.console, HEADER_ROWS)
        history_path = Path(os.environ.get("BRG_HISTORY", Path.home() / ".brg_history"))
        self.session = session or PromptSession(
            message=[("class:caret", "> ")],
            completer=SlashCompleter(self),
            complete_while_typing=True,
            history=FileHistory(str(history_path)),
            style=PROMPT_STYLE,
            bottom_toolbar=self.toolbar,
            key_bindings=self.key_bindings(),
        )

    def key_bindings(self) -> KeyBindings:
        """PageUp/PageDown (and Shift+Up/Down) page back through the transcript the terminal no longer holds."""
        kb = KeyBindings()
        kb.add("pageup")(lambda event: self.screen.page(self.screen.view_rows - 2))
        kb.add("pagedown")(lambda event: self.screen.page(-(self.screen.view_rows - 2)))
        kb.add("s-up")(lambda event: self.screen.page(3))
        kb.add("s-down")(lambda event: self.screen.page(-3))
        kb.add("end")(lambda event: self.screen.reset_view())
        return kb

    def toolbar(self):
        """The bar under the prompt.  With the banner pinned at the top it is one line of hints; otherwise
        it carries the logo with the model, effort, mode, context share and the hints."""
        if self.pinned:
            return [("class:bottom-toolbar", " ? shortcuts · ↑↓ history · / commands · PgUp/PgDn scroll · Esc interrupts a reply · /quit leaves")]
        ctx = f"ctx {self.context_pct:.0f}%" if self.context_pct is not None else "ctx 0%"
        effort = self.effort or "effort default"
        if self.effort:
            effort = f"effort {self.effort}"
        account = self.provider.status() if self.provider else "starting…"
        right = [
            [("class:bottom-toolbar.title", "BRG Terminal"), ("class:bottom-toolbar", f"  v{VERSION}  "), ("class:bottom-toolbar.idle", "● Idle")],
            [("class:bottom-toolbar.model", f"{self.model_label()} · {effort} · mode {self.mode} · {ctx}")],
            [("class:bottom-toolbar", account)],
            [("class:bottom-toolbar", "? shortcuts · ↑↓ history · / commands · Esc interrupts a reply · /quit leaves")],
        ]
        out: list[tuple[str, str]] = []
        for i, (logo_line, text_line) in enumerate(zip(banner.logo_fragments(), right)):
            if i:
                out.append(("", "\n"))
            out.append(("noreverse", " "))
            out.extend(logo_line)
            out.append(("noreverse", "   "))
            out.extend(text_line)
        return out

    # ------------------------------------------------------------------ output
    def print(self, *args, **kwargs) -> None:
        """Print, and with the banner pinned also remember the lines for paging back."""
        if self.pinned:
            self.screen.reset_view()
            try:
                lines = [""] if not args else [l for a in args for l in ansi_lines(self.console, a)]
            except Exception:                                          # noqa: BLE001
                lines = [""]
            self.screen.remember(lines)
        self.console.print(*args, **kwargs)

    def trimmed(self, renderable, width: int | None = None):
        """A renderable rendered now, without the padding to the full width: lines keep no trailing
        spaces, so a later narrowing of the window does not wrap them into blank lines."""
        width = min(width or TEXT_WIDTH, self.console.width - 1)      # never exactly the terminal width
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
            try:
                images.show(self.console, path, caption, mode=self.figures_mode)
            except Exception as exc:                                  # noqa: BLE001
                self.error(f"could not show {ref}: {exc}")

    def event(self, text: str) -> None:
        self.print(Text.assemble(("● ", "bold #3fb950"), (text, "#c9d1d9")))

    def error(self, text: str) -> None:
        self.print(Text.assemble(("● ", "bold #f85149"), (text, "#f85149")))

    def header_text(self) -> Text:
        """The four lines beside the logo in the pinned banner."""
        ctx = f"ctx {self.context_pct:.0f}%" if self.context_pct is not None else "ctx 0%"
        effort = f"effort {self.effort}" if self.effort else "effort default"
        state = ("● Working", "#d29922") if self.turn is not None else ("● Idle", "#3fb950")
        text = Text()
        text.append("BRG Terminal", style="bold #e6edf3")
        text.append(f"  v{VERSION}   ", style="#8b949e")
        text.append(state[0], style=state[1])
        text.append("\n")
        text.append(f"{self.model_label()} · {effort} · mode {self.mode} · {ctx}", style="#c9d1d9")
        text.append("\n")
        account = self.provider.status() if self.provider else "starting the BRG MCP server…"
        text.append(f"{account} · {len(self.bridge.tools)} BRG tools", style="#8b949e")
        text.append("\n")
        text.append(str(self.workdir if self.mode != "read" else self.data_root), style="#6e7681")
        return text

    def header(self) -> None:
        table = Table.grid(padding=(0, 3))
        table.add_row(banner.logo(), self.header_text())
        if self.pinned:
            self.screen.draw_header(ansi_lines(self.console, table))
            return
        self.print()
        self.print(table)
        self.print()

    def refresh_header(self) -> None:
        if self.pinned and self.screen.active:
            self.header()

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
        self.provider.terminal_width = self.console.width
        self.provider.mode = self.mode
        self.provider.effort = self.effort
        self.provider.workdir = str(self.workdir)
        self.provider.ask_permission = self.ask_permission
        if name == "codex":
            from brg_mcp.cli.providers.agent_cli import codex_account
            self.provider.account = await codex_account()
        self.provider_name = name
        self.set_title()
        self.refresh_header()
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
        self.refresh_header()

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
        self.refresh_header()

    async def ask_permission(self, tool: str, tool_input: dict) -> bool:
        """Asked by the engine before a file change or a command in edit mode: show what it wants,
        pause the status line, take y/n at the prompt."""
        if self.live is not None:
            self.live.stop()
        what = describe_action(tool, tool_input)
        self.print(Text.assemble(("? ", "bold #d29922"), (what, "#e6edf3")))
        try:
            answer = (await self.session.prompt_async([("class:caret", "  allow? [y/N] ")], completer=None)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"
        finally:
            if self.live is not None:
                self.live.start()
        allowed = answer in ("y", "yes")
        self.event(("allowed: " if allowed else "declined: ") + what.splitlines()[0])
        return allowed

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
        self.refresh_header()

    async def login(self, which: str) -> None:
        cls = PROVIDERS.get(which)
        command = getattr(cls, "login_command", None)
        if not command:
            self.error(f"/login works for claude and codex, not {which!r}")
            return
        if not shutil.which(command[0]):
            self.error(f"{command[0]} is not installed; see /help")
            return
        subprocess.run(command)                                        # interactive: browser or device code
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
            where = {"kitty": "this terminal shows images inline", "iterm2": "this terminal shows images inline",
                     "blocks": "this terminal cannot show images; figures are links"}[images.protocol()]
            self.event(f"figures: {self.figures_mode} · {where}")
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
            images.show(self.console, path, mode=self.figures_mode)
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
    def text_width(self) -> int:
        return min(TEXT_WIDTH, self.console.width - 1) - INDENT

    async def ask(self, line: str) -> None:
        """Run one reply.  Only a one-line status is redrawn while the model works; the step chain is
        printed when text follows it, each paragraph (or code block) when it is complete, so everything
        in the scrollback was printed exactly once and a resize cannot disturb a redraw."""
        trace = Trace()
        self.trace = trace
        started = time.monotonic()
        buffer: list[str] = []                       # the paragraph being received
        full: list[str] = []                         # the whole reply, for the figures
        spinner = Spinner("dots", style="#58a6ff")

        slow_noted = {"at": 0.0}

        def status() -> Spinner:
            label = "Writing…" if buffer else trace.running()
            elapsed = time.monotonic() - started
            text = Text.assemble((" BRG ", "bold #58a6ff"), (f"{self.model_label()} · ", "#8b949e"),
                                 (f"{label} ", "#c9d1d9"), (f"{elapsed:.0f}s", GREY))
            if trace.chain and not buffer:
                text.append("   ")
                text.append_text(trace.status_chain(max(10, self.console.width - text.cell_len - 6)))
            text.append("   Esc interrupts", style="#484f58")
            text.truncate(max(10, self.console.width - 4))
            spinner.update(text=text)
            step_s = trace.current_step_seconds()
            if step_s > 45 and elapsed - slow_noted["at"] > 45:          # a step is taking long: say so, once a while
                slow_noted["at"] = elapsed
                self.print(Text.assemble(("● ", "bold #d29922"),
                                         (f"still waiting on {label.rstrip('…')} ({step_s:.0f}s on this step, {elapsed:.0f}s in all); "
                                          "Esc interrupts, /trace shows the steps afterwards", "#8b949e")))
            return spinner

        self.refresh_header()
        with Live(get_renderable=status, console=self.console, refresh_per_second=10,
                  vertical_overflow="crop", transient=True) as live:
            self.live = live

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
                    try:
                        images.show(self.console, Path(image), drawing.get("title", "").split(":")[0], mode=self.figures_mode)
                    except Exception as exc:                              # noqa: BLE001
                        self.error(f"could not show {image}: {exc}")
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

            try:
                await self.provider.send(line, on_text, on_event)
                if not full and not trace.steps:
                    buffer.append("*(no text in the reply)*")
            except asyncio.CancelledError:
                buffer.append("\n\n*(interrupted)*")
            except Exception as exc:                                  # noqa: BLE001
                buffer.append(f"\n\n**{type(exc).__name__}**: {exc}")
            flush_chain()
            flush_text(final=True)
        self.live = None
        self.show_figures("".join(full))
        if self.provider is not None:
            usage = await self.provider.context_usage()
            if usage and usage.get("percentage") is not None:
                self.context_pct = float(usage["percentage"])
        self.set_title()
        self.print(self.trimmed(metrics_line(trace.usage, self.context_pct, time.monotonic() - started,
                                             show_cost=self.provider_name in ("anthropic", "openai"))))   # accounts: no $
        self.print()
        self.turn = None
        self.refresh_header()

    async def send(self, line: str) -> None:
        """Run a reply as a task; Esc or Ctrl+C while it runs cancels it (keys are read directly, the
        prompt is not active during a reply)."""
        self.turn = asyncio.create_task(self.ask(line))
        loop = asyncio.get_running_loop()
        turn = self.turn

        def on_keys() -> None:
            try:
                keys = self.session.input.read_keys()
                keys += self.session.input.flush_keys()                # a lone Esc waits in the parser otherwise
            except Exception:                                          # noqa: BLE001
                return
            if any(k.key in (Keys.Escape, Keys.ControlC) for k in keys) and not turn.done():
                turn.cancel()
            for k in keys:
                if k.key == Keys.PageUp:
                    self.screen.page(self.screen.view_rows - 2)
                elif k.key == Keys.PageDown:
                    self.screen.page(-(self.screen.view_rows - 2))

        try:
            loop.add_signal_handler(signal.SIGINT, turn.cancel)
        except (NotImplementedError, RuntimeError):
            pass
        try:
            with self.session.input.raw_mode(), self.session.input.attach(on_keys):
                await turn
        except Exception:                                              # noqa: BLE001 - attach can fail on odd inputs
            await turn
        finally:
            try:
                loop.remove_signal_handler(signal.SIGINT)
            except (NotImplementedError, RuntimeError):
                pass
            self.turn = None

    # ------------------------------------------------------------------ main loop
    def paint(self, on: bool) -> None:
        """Set (or restore) the terminal's background colour; most terminals honour OSC 11 / 111."""
        if not self.console.is_terminal or not BACKGROUND:
            return
        self.console.file.write(f"\x1b]11;{BACKGROUND}\x07" if on else "\x1b]111\x07")
        self.console.file.flush()

    def set_title(self) -> None:
        """The terminal's window/tab title: BRG and the model, always visible above the transcript."""
        if not self.console.is_terminal:
            return
        ctx = f" · ctx {self.context_pct:.0f}%" if self.context_pct is not None else ""
        self.console.file.write(f"\x1b]2;BRG · {self.model_label()}{ctx}\x07")
        self.console.file.flush()

    async def run(self) -> None:
        self.paint(True)
        self.set_title()
        loop = asyncio.get_running_loop()
        if self.pinned:
            self.screen.start()
            self.header()
            try:
                loop.add_signal_handler(signal.SIGWINCH, self.on_resize)
            except (NotImplementedError, RuntimeError, AttributeError):
                pass
        with Live(Spinner("dots", text=Text(" starting the BRG MCP server and your account…", style=GREY), style="#58a6ff"),
                  console=self.console, transient=True, refresh_per_second=10, vertical_overflow="crop"):
            try:
                await self.bridge.start()
            except Exception as exc:                                      # noqa: BLE001
                self.error(f"could not start the BRG MCP server: {exc}")
                return
            await self.set_provider(self.provider_name, self.requested_model, announce=False)
            if self.provider is not None and self.provider.ready()[0]:
                await self.load_models()
        self.header()                                                     # with the real model line
        self.set_title()
        self.event("Type a question, or /help. /legend explains the symbols.")
        self.first_run_check()
        if self.pinned:
            self.screen.fill_to_bottom()
        interrupts = 0
        try:
            while True:
                try:
                    with patch_stdout():
                        line = (await self.session.prompt_async()).strip()
                except KeyboardInterrupt:
                    interrupts += 1
                    if interrupts >= 2:
                        break
                    self.event("Ctrl+C again (or /quit) to leave")
                    continue
                except EOFError:
                    break
                interrupts = 0
                if self.pinned:                                       # the question stays in the paging memory
                    self.screen.reset_view()
                    self.screen.remember(ansi_lines(self.console, Text.assemble(("> ", "bold #58a6ff"), (line, "#e6edf3"))))
                if not line:
                    continue
                if line == "?" or line == "/":
                    self.print(commands.help_text())
                    continue
                command = commands.parse(line)
                if command:
                    if not await self.run_command(command):
                        break
                    continue
                if self.provider is None:
                    self.error("no provider; the MCP server did not start")
                    continue
                ok, todo = self.provider.ready()
                if not ok:
                    self.error(todo)
                    continue
                await self.send(line)
        finally:
            if self.provider is not None and hasattr(self.provider, "close"):
                await self.provider.close()
            await self.bridge.stop()
            if self.pinned:
                try:
                    loop.remove_signal_handler(signal.SIGWINCH)
                except (NotImplementedError, RuntimeError, AttributeError):
                    pass
                self.screen.stop()
            self.paint(False)

    def on_resize(self) -> None:
        self.screen.resize()
        self.header()


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
