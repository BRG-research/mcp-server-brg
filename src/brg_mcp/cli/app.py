"""The BRG terminal: pixel logo on top, a transcript, a `>` prompt with slash commands at the bottom."""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path

from rich.markdown import Markdown as RichMarkdown
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Input, Static
from textual import events

from brg_mcp.cli import banner, commands, models
from brg_mcp.cli.prompt import PromptInput, Suggestions
import inspect
from brg_mcp.cli.mcp_bridge import MCPBridge
from brg_mcp.cli.providers import PROVIDERS, Provider

try:
    VERSION = package_version("brg-mcp")
except PackageNotFoundError:
    VERSION = "0.1.0"


def find_data_root(start: Path | None = None) -> Path:
    """The checkout that holds config/ and knowledge/: the given path, the cwd, or the package's own repo."""
    candidates = [start] if start else []
    candidates += [Path.cwd(), Path(__file__).resolve().parents[3]]
    for c in candidates:
        if c and (c / "config" / "knowledge.yaml").is_file():
            return c.resolve()
    raise SystemExit("could not find a BRG checkout (config/knowledge.yaml); pass --data-root")


class Message(Static):
    """One transcript entry: a user line, an assistant reply, an event or an error."""

    def __init__(self, kind: str, text: str = "") -> None:
        super().__init__(classes=f"msg {kind}")
        self.kind = kind
        self.text = text
        self.render_now()

    def render_now(self) -> None:
        if self.kind == "user":
            self.update(Text.assemble(("> ", "bold #8b949e"), (self.text, "#e6edf3")))
        elif self.kind == "assistant":
            body = RichMarkdown(self.text or "…", code_theme="monokai")
            self.update(body)
        elif self.kind == "event":
            self.update(Text.assemble(("● ", "bold #3fb950"), (self.text, "#c9d1d9")))
        else:
            self.update(Text.assemble(("● ", "bold #f85149"), (self.text, "#f85149")))

    def append(self, fragment: str) -> None:
        self.text += fragment
        self.render_now()


class BRGTerminal(App):
    CSS = """
    Screen { background: #0d1117; }
    #header { height: auto; padding: 1 2 0 2; }
    #logo { width: auto; margin-right: 3; }
    #title { width: 1fr; }
    #transcript { height: 1fr; padding: 1 2; }
    .msg { margin-bottom: 1; }
    .user { background: #161b22; padding: 0 1; }
    .assistant { padding: 0 1 0 1; }
    .event { padding: 0 1; }
    .error { padding: 0 1; }
    #rule-top, #rule-bottom { height: 1; color: #30363d; }
    #prompt-row { height: 1; padding: 0 1; }
    #caret { width: 2; }
    #prompt { border: none; background: #0d1117; padding: 0; height: 1; }
    #prompt:focus { border: none; }
    #suggest { display: none; height: auto; max-height: 12; padding: 0 3; color: #c9d1d9; background: #0d1117; }
    #suggest.visible { display: block; }
    #hint { height: 1; color: #6e7681; padding: 0 2; }
    """
    BINDINGS = [("ctrl+c", "quit", "quit"), ("escape", "cancel", "cancel")]

    def __init__(self, data_root: Path, provider: str = "claude", model: str | None = None) -> None:
        super().__init__()
        self.data_root = data_root
        self.bridge = MCPBridge(data_root)
        self.provider_name = provider
        self.requested_model = model
        self.provider: Provider | None = None
        self.busy = False

    # ------------------------------------------------------------------ layout
    def compose(self) -> ComposeResult:
        with Horizontal(id="header"):
            yield Static(banner.logo(), id="logo")
            yield Static(self._header_text("starting the BRG MCP server…"), id="title")
        yield VerticalScroll(id="transcript")
        yield Static(Text("─" * 200, style="#30363d"), id="rule-top")
        with Horizontal(id="prompt-row"):
            yield Static(Text("> ", style="bold #8b949e"), id="caret")
            yield PromptInput(id="prompt")
        yield Suggestions(id="suggest")
        yield Static(Text("─" * 200, style="#30363d"), id="rule-bottom")
        yield Static("? for shortcuts · ↑↓ history · / commands", id="hint")

    def _header_text(self, model_line: str) -> Text:
        return banner.header_lines(VERSION, model_line, str(self.data_root))

    def refresh_header(self) -> None:
        line = self.provider.status() if self.provider else "no model"
        self.query_one("#title", Static).update(self._header_text(f"{line} · {len(self.bridge.tools)} BRG tools"))

    async def on_mount(self) -> None:
        self.query_one("#prompt", Input).focus()
        try:
            await self.bridge.start()
        except Exception as exc:                                  # noqa: BLE001
            self.post("error", f"could not start the BRG MCP server: {exc}")
            return
        await self.set_provider(self.provider_name, self.requested_model, announce=False)
        self.post("event", f"BRG MCP connected: {len(self.bridge.tools)} tools. Type a question, or /help.")
        self.first_run_check()

    async def on_unmount(self) -> None:
        if self.provider is not None and hasattr(self.provider, "close"):
            await self.provider.close()
        await self.bridge.stop()

    async def reset_provider(self) -> None:
        result = self.provider.reset()
        if inspect.isawaitable(result):
            await result

    def first_run_check(self) -> None:
        """Tell a new user what is missing before they type anything."""
        if self.provider is None:
            return
        ok, todo = self.provider.ready()
        if ok:
            return
        self.post("error", todo)
        other = "codex" if self.provider_name == "claude" else "claude"
        self.post("event", f"Accounts: /login claude (Claude account), /login codex (ChatGPT account). "
                           f"/models lists the models; /model {other} switches engine. "
                           f"No account at all? api:<model> with ANTHROPIC_API_KEY or OPENAI_API_KEY also works.")

    # ------------------------------------------------------------------ transcript
    def post(self, kind: str, text: str) -> Message:
        message = Message(kind, text)
        transcript = self.query_one("#transcript", VerticalScroll)
        transcript.mount(message)
        transcript.scroll_end(animate=False)
        return message

    # ------------------------------------------------------------------ providers
    async def set_provider(self, name: str, model: str | None = None, announce: bool = True) -> None:
        cls = PROVIDERS.get(name)
        if cls is None:
            self.post("error", f"unknown provider {name!r}; choose from {', '.join(PROVIDERS)}")
            return
        if self.provider is not None and hasattr(self.provider, "close"):
            await self.provider.close()
        self.provider = cls(self.bridge, model)
        if name == "codex":
            from brg_mcp.cli.providers.agent_cli import codex_account
            self.provider.account = await codex_account()
        self.provider_name = name
        self.refresh_header()
        if announce:
            self.post("event", f"provider {name}: {self.provider.status()} (conversation reset)")

    # ------------------------------------------------------------------ input
    def on_input_changed(self, event: Input.Changed) -> None:
        self.query_one("#suggest", Suggestions).refresh_for(event.value)

    async def on_prompt_input_navigate(self, message: PromptInput.Navigate) -> None:
        """Up/Down: move in the suggestion panel when it is open, else walk the prompt history."""
        panel = self.query_one("#suggest", Suggestions)
        prompt = self.query_one("#prompt", PromptInput)
        if panel.is_open:
            panel.move(message.direction)
        else:
            prompt.recall(message.direction)

    async def on_prompt_input_accept(self, message: PromptInput.Accept) -> None:
        """Tab: take the highlighted suggestion into the prompt."""
        panel = self.query_one("#suggest", Suggestions)
        prompt = self.query_one("#prompt", PromptInput)
        if panel.is_open and panel.current:
            prompt.set_text(panel.current + (" " if panel.current_takes_argument else ""))

    async def on_prompt_input_dismiss(self, message: PromptInput.Dismiss) -> None:
        self.query_one("#suggest", Suggestions).close()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        panel = self.query_one("#suggest", Suggestions)
        prompt = self.query_one("#prompt", PromptInput)
        if panel.is_open and panel.current and panel.current != event.value.strip():
            # Enter on a highlighted suggestion: complete it; run it at once if it takes no argument
            if panel.current_takes_argument:
                prompt.set_text(panel.current + " ")
                return
            prompt.set_text(panel.current)
        line = prompt.value.strip()
        prompt.remember(line)
        prompt.value = ""
        panel.close()
        if not line:
            return
        if line == "?":
            self.post("event", commands.help_text())
            return
        if line == "/":
            prompt.set_text("/")                    # the panel lists every command
            return
        command = commands.parse(line)
        if command:
            await self.run_command(command)
            return
        if self.busy:
            self.post("error", "still answering; press Escape to cancel")
            return
        if self.provider is None:
            self.post("error", "no provider; the MCP server did not start")
            return
        ok, todo = self.provider.ready()
        if not ok:
            self.post("error", todo)
            return
        self.post("user", line)
        self.ask(line)

    async def run_command(self, command: commands.Command) -> None:
        name, arg = command.name, command.argument
        if name == "/help":
            self.post("event", commands.help_text())
        elif name == "/quit":
            self.exit()
        elif name == "/status":
            self.post("event", f"{self.provider.status() if self.provider else 'no provider'} · data root {self.data_root}")
        elif name == "/provider":
            await self.set_provider(arg or self.provider_name)
        elif name == "/model":
            if arg:
                await self.switch_model(arg)
            else:
                self.query_one("#prompt", PromptInput).set_text("/model ")   # the panel lists the models
        elif name == "/models":
            self.post("event", models.listing())
        elif name == "/login":
            await self.login(arg or self.provider_name)
        elif name == "/tools":
            lines = [f"{t.name}: {t.description.strip().splitlines()[0] if t.description else ''}" for t in self.bridge.tools]
            self.post("event", "\n".join(lines) or "no tools")
        elif name == "/search":
            self.post("event", await self.bridge.call_tool("search_knowledge", {"query": arg}))
        elif name == "/read":
            self.post("assistant", await self.bridge.read_resource(f"brg://knowledge/{arg}"))
        elif name == "/books":
            self.post("event", await self.bridge.call_tool("search_books", {"query": arg}))
        elif name == "/clear":
            if self.provider:
                await self.reset_provider()
            for child in list(self.query_one("#transcript").children):
                child.remove()
            self.post("event", "conversation cleared")
        else:
            self.post("error", f"unknown command {name}; type /help")

    async def switch_model(self, name: str) -> None:
        """One command for every engine: the registry says which account the model lives on."""
        if self.provider is None:
            return
        if name in ("", "default"):
            self.provider.model = ""
            self.refresh_header()
            self.post("event", f"model: {self.provider.name} default")
            return
        entry = models.resolve(name)
        if entry is None:
            self.post("error", f"unknown model {name!r}; /models lists them")
            return
        if entry.provider != self.provider_name:
            await self.set_provider(entry.provider, entry.model, announce=False)
            self.post("event", f"model: {entry.name} ({entry.note}); new engine, so a new conversation")
        else:
            if hasattr(self.provider, "set_model"):
                await self.provider.set_model(entry.model)   # inside the live session, no reset
            else:
                self.provider.model = entry.model
            self.refresh_header()
            self.post("event", f"model: {entry.name} ({entry.note})")

    async def login(self, which: str) -> None:
        """Run the CLI's own login flow in this terminal (the app is suspended while it runs)."""
        cls = PROVIDERS.get(which)
        command = getattr(cls, "login_command", None)
        if not command:
            self.post("error", f"/login works for claude and codex, not {which!r}")
            return
        if not shutil.which(command[0]):
            self.post("error", f"{command[0]} is not installed; see /help")
            return
        with self.suspend():
            subprocess.run(command)                                # interactive: browser or device code
        await self.set_provider(which, self.provider.model if self.provider else None, announce=False)
        ok, todo = self.provider.ready()
        self.post("event" if ok else "error", f"signed in: {self.provider.status()}" if ok else todo)

    # ------------------------------------------------------------------ the model turn
    @work(exclusive=True, group="ask")
    async def ask(self, line: str) -> None:
        self.busy = True
        reply = self.post("assistant", "")
        transcript = self.query_one("#transcript", VerticalScroll)

        def on_text(fragment: str) -> None:
            reply.append(fragment)
            transcript.scroll_end(animate=False)

        def on_event(note: str) -> None:
            transcript.mount(Message("event", note), before=reply)   # events go above the growing reply
            transcript.scroll_end(animate=False)

        try:
            await self.provider.send(line, on_text, on_event)
            if not reply.text:
                reply.append("(no text in the reply)")
        except asyncio.CancelledError:
            self.post("event", "cancelled")
            raise
        except Exception as exc:                                  # noqa: BLE001
            self.post("error", f"{type(exc).__name__}: {exc}")
        finally:
            self.busy = False

    def action_cancel(self) -> None:
        self.workers.cancel_group(self, "ask")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="brg", description="BRG terminal: chat with your own Claude or ChatGPT account over the BRG MCP server")
    parser.add_argument("--data-root", type=Path, default=None, help="checkout with config/ and knowledge/ (default: auto-detect)")
    parser.add_argument("--provider", default=os.environ.get("BRG_PROVIDER", "claude"), choices=list(PROVIDERS))
    parser.add_argument("--model", default=os.environ.get("BRG_MODEL"), help="model name for the provider (default: the provider's own)")
    args = parser.parse_args(argv)
    provider, model = args.provider, args.model
    entry = models.resolve(model) if model else None
    if entry is not None:
        provider, model = entry.provider, entry.model
    BRGTerminal(find_data_root(args.data_root), provider, model).run()


if __name__ == "__main__":
    main()
