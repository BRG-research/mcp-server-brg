"""The BRG terminal, built on the terminal itself: the transcript is printed into the terminal's own
scrollback (its scrollbar, selection and copy work as usual) and only the prompt line is live, as in
Claude Code.  prompt_toolkit draws the prompt, the completion menu under it and the history;
rich prints the banner, the streamed Markdown replies and the events."""

from __future__ import annotations

import argparse
import asyncio
import inspect
import os
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
from brg_mcp.cli.mathtext import mathify
from brg_mcp.cli.providers.base import Event
from brg_mcp.cli.trace import GREY, Trace, legend, metrics_line

TEXT_WIDTH = 110                   # replies wrap at this width at most: easier to read, fewer reflow problems
INDENT = 2                         # replies, chains and metrics sit this far from the left edge

BACKGROUND = os.environ.get("BRG_BACKGROUND", "#0b1220")      # the terminal's background while brg runs (OSC 11)

try:
    VERSION = package_version("brg-mcp")
except PackageNotFoundError:
    VERSION = "0.1.0"

PROMPT_STYLE = Style.from_dict({
    "caret": "bold #58a6ff",
    "bottom-toolbar": "#6e7681 noreverse",
    "bottom-toolbar.model": "#8b949e noreverse",
    "bottom-toolbar.idle": "#3fb950 noreverse",
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


class Terminal:
    def __init__(self, data_root: Path, provider: str = "claude", model: str | None = None,
                 console: Console | None = None, session: PromptSession | None = None) -> None:
        self.data_root = data_root
        self.console = console or Console(highlight=False)
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
        history_path = Path(os.environ.get("BRG_HISTORY", Path.home() / ".brg_history"))
        self.session = session or PromptSession(
            message=[("class:caret", "> ")],
            completer=SlashCompleter(self),
            complete_while_typing=True,
            history=FileHistory(str(history_path)),
            style=PROMPT_STYLE,
            bottom_toolbar=self.toolbar,
        )

    def toolbar(self):
        ctx = f" · ctx {self.context_pct:.0f}%" if self.context_pct is not None else ""
        return [("class:bottom-toolbar.idle", " ● Idle"), ("class:bottom-toolbar.model", f" · {self.model_label()}{ctx}"),
                ("class:bottom-toolbar", " · ? for shortcuts · ↑↓ history · / commands · Ctrl+C interrupts")]

    # ------------------------------------------------------------------ output
    def print(self, *args, **kwargs) -> None:
        self.console.print(*args, **kwargs)

    def trimmed(self, renderable, width: int | None = None):
        """A renderable rendered now, without the padding to the full width: lines keep no trailing
        spaces, so a later narrowing of the window does not wrap them into blank lines."""
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
        return Segments(out)

    def reply_markdown(self, text: str) -> Markdown:
        """The reply as Markdown: TeX as Unicode, image lines removed (the figures are shown below the text)."""
        return Markdown(mathify(images.IMAGE_LINK.sub("", text)))

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

    def header(self) -> None:
        table = Table.grid(padding=(0, 3))
        table.add_row(banner.logo(), banner.header_lines(VERSION, self.model_line(), str(self.data_root)))
        self.print()
        self.print(table)
        self.print()

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
        return f"{self.model_label()} · {self.provider.status()} · {len(self.bridge.tools)} BRG tools"

    # ------------------------------------------------------------------ engines
    async def set_provider(self, name: str, model: str | None = None, announce: bool = True) -> None:
        cls = PROVIDERS.get(name)
        if cls is None:
            self.error(f"unknown provider {name!r}; choose from {', '.join(PROVIDERS)}")
            return
        if self.provider is not None and hasattr(self.provider, "close"):
            await self.provider.close()
        self.provider = cls(self.bridge, model)
        if name == "codex":
            from brg_mcp.cli.providers.agent_cli import codex_account
            self.provider.account = await codex_account()
        self.provider_name = name
        self.set_title()
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
    async def ask(self, line: str) -> None:
        """Stream the reply below the prompt.  Steps (thinking, tool calls) are drawn as a chain of badges;
        the chain is printed for good when text follows it, finished paragraphs are printed as they complete,
        so only the current chain or paragraph is redrawn and everything else lives in the scrollback."""
        trace = Trace()
        self.trace = trace
        started = time.monotonic()
        buffer: list[str] = []                       # the paragraph being streamed
        full: list[str] = []                         # the whole reply, for the figures

        def spinner():
            return Spinner("dots", text=Text.assemble((f" {trace.running()} ", "#c9d1d9"),
                                                      (f"{time.monotonic() - started:.0f}s", GREY),
                                                      ("   (Ctrl+C to interrupt)", "#484f58")), style="#58a6ff")

        def renderable():
            parts = []
            if trace.chain:
                parts.append(self.trimmed(trace.chain_text()))
            if buffer:
                parts.append(self.trimmed(self.reply_markdown("".join(buffer))))
            else:
                parts.append(spinner())
            return Group(*parts)

        with Live(get_renderable=renderable, console=self.console, refresh_per_second=12,
                  vertical_overflow="visible", transient=True) as live:
            def flush_chain() -> None:
                if trace.chain:
                    live.console.print(self.trimmed(trace.chain_text()))
                    trace.text_started()

            def flush_text(final: bool = False) -> None:
                """Print the finished paragraphs (never inside an open code fence)."""
                text = "".join(buffer)
                if final:
                    done, rest = text, ""
                else:
                    cut = -1
                    for i in range(len(text) - 2, -1, -1):
                        if text.startswith("\n\n", i) and text[:i].count("```") % 2 == 0:
                            cut = i
                            break
                    if cut < 0:
                        return
                    done, rest = text[:cut], text[cut + 2:]
                if done.strip():
                    live.console.print(self.trimmed(self.reply_markdown(done)))
                buffer[:] = [rest] if rest else []

            def on_text(fragment: str) -> None:
                if not fragment:
                    return
                if not buffer:
                    flush_chain()
                buffer.append(fragment)
                full.append(fragment)
                flush_text()

            def on_event(event: Event) -> None:
                if event.kind in ("note", "error"):
                    style = "#c9d1d9" if event.kind == "note" else "#f85149"
                    live.console.print(Text.assemble(("● ", f"bold {style}"), (event.detail, style)))
                    return
                if event.kind in ("thinking", "tool_call") and buffer:
                    flush_text(final=True)
                trace.add(event)

            try:
                await self.provider.send(line, on_text, on_event)
                if not buffer and not trace.steps:
                    buffer.append("*(no text in the reply)*")
            except asyncio.CancelledError:
                buffer.append("\n\n*(interrupted)*")
            except Exception as exc:                                  # noqa: BLE001
                buffer.append(f"\n\n**{type(exc).__name__}**: {exc}")
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
        self.turn = asyncio.create_task(self.ask(line))
        loop = asyncio.get_running_loop()
        try:
            loop.add_signal_handler(signal.SIGINT, self.turn.cancel)
        except (NotImplementedError, RuntimeError):
            pass
        try:
            await self.turn
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
        with Live(Spinner("dots", text=Text(" starting the BRG MCP server and your account…", style=GREY), style="#58a6ff"),
                  console=self.console, transient=True, refresh_per_second=12):
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
            self.paint(False)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="brg", description="BRG terminal: chat with your own Claude or ChatGPT account over the BRG MCP server")
    parser.add_argument("--data-root", type=Path, default=None, help="checkout with config/ and knowledge/ (default: auto-detect)")
    parser.add_argument("--provider", default=os.environ.get("BRG_PROVIDER", "claude"), choices=list(PROVIDERS))
    parser.add_argument("--model", default=os.environ.get("BRG_MODEL"), help="model name (default: the account's)")
    args = parser.parse_args(argv)
    provider, model = args.provider, args.model
    entry = models.resolve(model, []) if model else None
    if entry is not None:
        provider, model = entry.provider, entry.model
    asyncio.run(Terminal(find_data_root(args.data_root), provider, model).run())


if __name__ == "__main__":
    main()
