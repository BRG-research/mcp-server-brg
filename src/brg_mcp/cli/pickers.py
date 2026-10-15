"""Pop-up lists: pick a model after `/model`, pick a command after `/`."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option


class Picker(ModalScreen[str | None]):
    """A titled list; Enter returns the chosen id, Escape returns None."""

    CSS = """
    Picker { align: center middle; }
    #box { width: 84; max-height: 80%; background: #161b22; border: round #30363d; padding: 1 2; }
    #title { color: #e6edf3; text-style: bold; margin-bottom: 1; }
    OptionList { background: #161b22; border: none; height: auto; max-height: 20; }
    #hint { color: #6e7681; margin-top: 1; }
    """
    BINDINGS = [("escape", "cancel", "cancel")]

    def __init__(self, title: str, entries: list[tuple[str, str, str]], current: str | None = None) -> None:
        """entries: (id, label, note)."""
        super().__init__()
        self.title_text = title
        self.entries = entries
        self.current = current

    def compose(self) -> ComposeResult:
        with Static(id="box"):
            yield Static(self.title_text, id="title")
            width = max(len(label) for _, label, _ in self.entries)
            options = []
            for key, label, note in self.entries:
                mark = "● " if key == self.current else "  "
                options.append(Option(Text.assemble((mark, "#3fb950"), (f"{label:<{width}}  ", "bold #e6edf3"), (note, "#8b949e")), id=key))
            yield OptionList(*options, id="options")
            yield Static("↑↓ to move · Enter to choose · Esc to cancel", id="hint")

    def on_mount(self) -> None:
        options = self.query_one(OptionList)
        options.focus()
        if self.current:
            for i, (key, _, _) in enumerate(self.entries):
                if key == self.current:
                    options.highlighted = i

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option.id))

    def action_cancel(self) -> None:
        self.dismiss(None)
