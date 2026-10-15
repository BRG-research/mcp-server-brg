from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from brg_mcp.cli.mcp_bridge import MCPBridge

OnText = Callable[[str], None]            # called with each streamed text fragment
OnEvent = Callable[[str], None]           # called with one-line status events (tool calls, notes)


@dataclass
class ToolCallEvent:
    name: str
    arguments: dict
    result_preview: str


class Provider:
    """Base class. Subclasses keep their own conversation state."""

    name = "base"
    default_model = ""
    needs_api_key: str | None = None      # environment variable, if an API key is required

    def __init__(self, bridge: MCPBridge, model: str | None = None):
        self.bridge = bridge
        self.model = model or self.default_model

    def reset(self) -> None:
        """Forget the conversation."""

    async def send(self, user_text: str, on_text: OnText, on_event: OnEvent) -> str:
        """Stream the reply for `user_text`; return the full reply text."""
        raise NotImplementedError

    def status(self) -> str:
        return f"{self.name} · {self.model}"


SYSTEM_PROMPT = """You are the BRG terminal assistant for the Block Research Group (ETH Zurich): structural design,
graphic statics, form finding, thrust network analysis and the COMPAS packages.
You have tools from the BRG MCP server: search_knowledge and the brg://knowledge/{id} resources for the
group's own notes, and the book tools (get_book_guide, search_books, list_book_sections, read_book_section)
for the public library. Use them before answering factual questions about these topics, cite what you read
(note id, book section and printed page markers), and say plainly when a tool returned nothing relevant.
Answer concisely in Markdown; show equations as TeX in $...$ and code in fenced blocks."""
