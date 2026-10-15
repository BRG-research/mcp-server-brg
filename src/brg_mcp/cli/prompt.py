"""The prompt: an Input with history and an inline suggestion panel under it (commands after `/`,
models after `/model `), navigated with the arrow keys, like Claude Code's prompt."""

from __future__ import annotations

from rich.text import Text
from textual import events
from textual.message import Message
from textual.widgets import Input, Static

from brg_mcp.cli import commands, models


class PromptInput(Input):
    class Navigate(Message):
        def __init__(self, direction: int) -> None:
            super().__init__(); self.direction = direction

    class Accept(Message):
        pass

    class Dismiss(Message):
        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(placeholder="", **kwargs)
        self.history: list[str] = []
        self.history_pos: int | None = None
        self.draft = ""

    async def _on_key(self, event: events.Key) -> None:
        if event.key in ("up", "down"):
            event.stop(); event.prevent_default()
            self.post_message(self.Navigate(-1 if event.key == "up" else 1))
        elif event.key == "tab":
            event.stop(); event.prevent_default()
            self.post_message(self.Accept())
        elif event.key == "escape":
            event.stop(); event.prevent_default()
            self.post_message(self.Dismiss())
        else:
            await super()._on_key(event)

    def set_text(self, text: str) -> None:
        self.value = text
        self.cursor_position = len(text)

    def remember(self, line: str) -> None:
        if line and (not self.history or self.history[-1] != line):
            self.history.append(line)
        self.history_pos = None

    def recall(self, direction: int) -> None:
        """Up (-1) walks back through earlier lines, Down (+1) forward to the unsent draft."""
        if not self.history:
            return
        if self.history_pos is None:
            if direction > 0:
                return
            self.draft = self.value
            self.history_pos = len(self.history) - 1
        else:
            self.history_pos += direction
        if self.history_pos >= len(self.history):
            self.history_pos = None
            self.set_text(self.draft)
            return
        self.history_pos = max(self.history_pos, 0)
        self.set_text(self.history[self.history_pos])


class Suggestions(Static):
    """Matches for the current prompt text; `current` is the highlighted entry."""

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self.entries: list[tuple[str, str]] = []     # (completion, note)
        self.index = 0

    @property
    def is_open(self) -> bool:
        return self.has_class("visible")

    @property
    def current(self) -> str | None:
        return self.entries[self.index][0] if self.entries else None

    @property
    def current_takes_argument(self) -> bool:
        cur = self.current or ""
        if cur.startswith("/model ") or cur.startswith("/provider ") or cur.startswith("/login "):
            return False
        return cur in commands.COMMANDS and ("<" in commands.COMMANDS[cur] or cur in ("/model", "/provider", "/login"))

    def matches(self, text: str) -> list[tuple[str, str]]:
        if not text.startswith("/"):
            return []
        head, _, rest = text.partition(" ")
        if head == "/model" and (rest or text.endswith(" ")):
            return [(f"/model {e.name}", e.note) for e in models.catalog() if e.name.lower().startswith(rest.lower())]
        if head == "/provider" and (rest or text.endswith(" ")):
            return [(f"/provider {k}", "engine") for k in ("claude", "codex", "anthropic", "openai") if k.startswith(rest)]
        if head == "/login" and (rest or text.endswith(" ")):
            return [(f"/login {k}", "sign in") for k in ("claude", "codex") if k.startswith(rest)]
        if " " in text:
            return []
        return [(name, doc) for name, doc in commands.COMMANDS.items() if name.startswith(text.lower())]

    def refresh_for(self, text: str) -> None:
        self.entries = self.matches(text)
        self.index = 0
        self.render_entries()

    def move(self, direction: int) -> None:
        if self.entries:
            self.index = (self.index + direction) % len(self.entries)
            self.render_entries()

    def close(self) -> None:
        self.entries = []
        self.render_entries()

    def render_entries(self) -> None:
        if not self.entries:
            self.remove_class("visible"); self.update(""); return
        self.add_class("visible")
        width = max(len(c) for c, _ in self.entries)
        text = Text()
        for i, (completion, note) in enumerate(self.entries[:12]):
            marked = i == self.index
            text.append("❯ " if marked else "  ", style="bold #3fb950")
            text.append(f"{completion:<{width}}  ", style="bold #e6edf3" if marked else "#c9d1d9")
            text.append(note, style="#8b949e")
            if i < min(len(self.entries), 12) - 1:
                text.append("\n")
        self.update(text)
