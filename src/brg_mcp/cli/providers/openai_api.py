"""OpenAI models (GPT, Codex) through the Responses API, with the MCP tools as function tools."""

from __future__ import annotations

import json
import time
import os

from brg_mcp.cli.mcp_bridge import MCPBridge
from .base import Event, preview, SYSTEM_PROMPT, OnEvent, OnText, Provider

MAX_TOOL_ROUNDS = 12
MODEL_ALIASES = {"codex": "gpt-5-codex", "gpt": "gpt-5"}


def openai_tools(bridge: MCPBridge) -> list[dict]:
    """MCP tool specs as Responses-API function tools."""
    return [{"type": "function", "name": t.name, "description": t.description,
             "parameters": t.input_schema} for t in bridge.tools]


class OpenAIProvider(Provider):
    name = "openai"
    default_model = os.environ.get("BRG_OPENAI_MODEL", "gpt-5")
    needs_api_key = "OPENAI_API_KEY"

    def __init__(self, bridge: MCPBridge, model: str | None = None):
        super().__init__(bridge, MODEL_ALIASES.get(model or "", model))
        self.previous_response_id: str | None = None
        self._client = None

    def reset(self) -> None:
        self.previous_response_id = None

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI()
        return self._client

    async def send(self, user_text: str, on_text: OnText, on_event: OnEvent) -> str:
        client = self._get_client()
        pending_input: list = [{"role": "user", "content": user_text}]
        reply = []
        totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "tools": 0}
        started_at = time.monotonic()
        for _ in range(MAX_TOOL_ROUNDS):
            stream = await client.responses.create(
                model=self.model,
                instructions=SYSTEM_PROMPT,
                input=pending_input,
                tools=openai_tools(self.bridge),
                previous_response_id=self.previous_response_id,
                stream=True,
            )
            response = None
            async for event in stream:
                if event.type == "response.output_text.delta":
                    on_text(event.delta)
                    reply.append(event.delta)
                elif event.type == "response.completed":
                    response = event.response
            if response is None:
                break
            self.previous_response_id = response.id
            u = getattr(response, "usage", None)
            if u is not None:
                totals["input"] += u.input_tokens or 0; totals["output"] += u.output_tokens or 0
                details = getattr(u, "input_tokens_details", None)
                totals["cache_read"] += getattr(details, "cached_tokens", 0) or 0
            if any(item.type == "reasoning" for item in response.output):
                on_event(Event("thinking"))
            calls = [item for item in response.output if item.type == "function_call"]
            totals["tools"] += len(calls)
            if not calls:
                break
            pending_input = []
            for call in calls:
                arguments = json.loads(call.arguments or "{}")
                on_event(Event("tool_call", call.name, json.dumps(arguments)))
                try:
                    text = await self.bridge.call_tool(call.name, arguments)
                    on_event(Event("tool_result", call.name, preview(text), ok=True))
                except Exception as exc:                      # noqa: BLE001
                    text = f"tool error: {exc}"
                    on_event(Event("tool_result", call.name, text, ok=False))
                pending_input.append({"type": "function_call_output", "call_id": call.call_id, "output": text[:40000]})
            if reply:
                on_text("\n\n")
                reply.append("\n\n")
        return "".join(reply)
