"""Slash commands of the BRG terminal."""

from __future__ import annotations

from dataclasses import dataclass

COMMANDS: dict[str, str] = {
    "/help": "list the commands",
    "/model": "/model  opens the model list; /model <name> switches directly (opus, sonnet, codex, gpt-6-astra, ...)",
    "/models": "list the models you can switch to and which account each one uses",
    "/login": "/login claude | codex  sign in with your own account (opens the CLI's login in this terminal)",
    "/provider": "/provider claude | codex | anthropic | openai  (advanced: pick the engine directly)",
    "/status": "current provider, model and tool count",
    "/tools": "list the MCP tools the model can call",
    "/search": "/search <words>  search the knowledge notes directly",
    "/read": "/read <note id>  read a knowledge note (e.g. form-finding-compas-fd)",
    "/books": "/books <words>  search the public book library",
    "/clear": "forget the conversation",
    "/quit": "leave the terminal",
}
ALIASES = {"/exit": "/quit", "/q": "/quit", "/h": "/help", "/?": "/help", "/reset": "/clear"}


@dataclass
class Command:
    name: str
    argument: str


def parse(line: str) -> Command | None:
    """Return the command if `line` starts with a slash, else None."""
    if not line.startswith("/"):
        return None
    head, _, rest = line.strip().partition(" ")
    name = ALIASES.get(head, head)
    return Command(name, rest.strip())


def help_text() -> str:
    width = max(len(k) for k in COMMANDS)
    lines = ["Commands (type / alone for a list, or / and Tab to complete):", ""]
    for name, doc in COMMANDS.items():
        lines.append(f"  {name:<{width}}  {doc}")
    lines += ["", "Anything else is sent to the model, which can call the BRG tools while answering."]
    return "\n".join(lines)
