from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Awaitable, Callable

from brg_mcp.cli.mcp_bridge import MCPBridge

OnText = Callable[[str], None]            # called with each streamed text fragment


@dataclass
class Event:
    """One step of the agent loop, in the order it happens.  The terminal draws them as a chain of badges
    between the text messages, and keeps them for /trace.

    kind: "thinking"     the model is reasoning (no name)
          "tool_call"    a tool was called: name, detail = the arguments (JSON)
          "tool_result"  that tool returned: name, ok, detail = a preview of the result
          "note"         a one-line status to print (detail)
          "error"        a one-line error to print (detail)
          "usage"        end of turn: data = {input, output, cache_read, cache_write, duration_ms, tools, cost, ...}
    """

    kind: str
    name: str = ""
    detail: str = ""
    ok: bool | None = None
    data: dict | None = None

    @staticmethod
    def note(text: str) -> "Event":
        return Event("note", detail=text)

    @staticmethod
    def error(text: str) -> "Event":
        return Event("error", detail=text)


OnEvent = Callable[[Event], None]         # called with each Event

READ_TOOLS = {"search_knowledge", "read_knowledge", "list_domains", "get_book_guide", "search_books", "list_book_sections",
              "read_book_section", "ReadMcpResourceTool", "ListMcpResourcesTool"}


def tool_name(raw: str) -> str:
    return raw.removeprefix("mcp__brg__")


def preview(content, limit: int = 160) -> str:
    """A one-line preview of a tool result (string, or MCP content blocks)."""
    if isinstance(content, list):
        content = " ".join(str(b.get("text", "")) if isinstance(b, dict) else str(getattr(b, "text", b)) for b in content)
    text = " ".join(str(content or "").split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


class Provider:
    """Base class. Subclasses keep their own conversation state."""

    name = "base"
    default_model = ""
    needs_api_key: str | None = None      # environment variable, if an API key is required

    def __init__(self, bridge: MCPBridge, model: str | None = None):
        self.bridge = bridge
        self.model = model or self.default_model

    def reset(self):
        """Forget the conversation.  May be a coroutine (engines with a live session)."""

    async def send(self, user_text: str, on_text: OnText, on_event: OnEvent) -> str:
        """Stream the reply for `user_text`; return the full reply text."""
        raise NotImplementedError

    async def context_usage(self) -> dict | None:
        """{"percentage", "totalTokens", "maxTokens"} of the conversation's context window, if the engine knows."""
        return None

    def ready(self) -> tuple[bool, str]:
        """(True, "") when a message can be sent, else (False, what the user must do first)."""
        if self.needs_api_key and not os.environ.get(self.needs_api_key):
            return False, f"set {self.needs_api_key} in the environment, or use an account model (/models)"
        return True, ""

    def status(self) -> str:
        return f"{self.name} · {self.model}"


SYSTEM_PROMPT = """You are the BRG terminal assistant of the Block Research Group (ETH Zurich): structural design,
graphic statics, form finding, thrust network analysis, masonry and shell structures, and the COMPAS packages.

Tools. The `brg` MCP server gives you search_knowledge and read_knowledge (the group's own notes, by id) and the book tools (get_book_guide, search_books, list_book_sections, read_book_section) for the public
library. Use them for factual questions on these topics; for everything else answer directly without calling tools.

How to answer.
- Match the length to the question. A simple question gets one to three sentences. No padding, no restating the
  question, no summary at the end, no closing offer.
- Plain prose by default. A list or a table only for genuinely parallel items or numbers; headers only when the
  answer is long and the reader asked for a full treatment.
- Answer first, reason second, citation last (note id, book section, printed page) when a tool gave it.
- Never narrate your work ("Let me search…", "I found…", "Based on the tool results…"); the terminal shows the
  tool calls on its own.
- Equations in TeX between $...$ and code in fenced blocks, only when they carry the answer.
- If the tools returned nothing relevant, say so in one sentence and answer from general knowledge, marked as such.
- Quote at most one sentence from a source; do not reproduce passages.
- When a note you read has a figure that carries the answer, repeat its image line verbatim
  (![caption](path.png)) at the end of the answer: the terminal displays the figure."""
