"""Claude through the Anthropic API, with the MCP tools exposed as client tools (manual streaming loop)."""

from __future__ import annotations

import json
import time
import os

from brg_mcp.cli.mcp_bridge import MCPBridge
from .base import Event, preview, result_text, SYSTEM_PROMPT, OnEvent, OnText, Provider

MAX_TOOL_ROUNDS = 12


def anthropic_tools(bridge: MCPBridge) -> list[dict]:
    """MCP tool specs as Anthropic tool definitions."""
    return [{"name": t.name, "description": t.description, "input_schema": t.input_schema,
             "eager_input_streaming": True} for t in bridge.tools]


class AnthropicProvider(Provider):
    name = "anthropic"
    default_model = "claude-opus-5-5"
    needs_api_key = "ANTHROPIC_API_KEY"

    def __init__(self, bridge: MCPBridge, model: str | None = None):
        super().__init__(bridge, model)
        self.messages: list[dict] = []
        self._client = None

    def reset(self) -> None:
        self.messages = []

    def _get_client(self):
        if self._client is None:
            import anthropic
            # resolves ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or an `ant auth login` profile
            self._client = anthropic.AsyncAnthropic()
        return self._client

    async def send(self, user_text: str, on_text: OnText, on_event: OnEvent) -> str:
        client = self._get_client()
        self.messages.append({"role": "user", "content": user_text})
        tools = anthropic_tools(self.bridge)
        reply = []
        totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "tools": 0}
        started_at = time.monotonic()
        for _ in range(MAX_TOOL_ROUNDS):
            kwargs = dict(
                model=self.model,
                max_tokens=16000,
                system=[{"type": "text", "text": self.system_prompt(), "cache_control": {"type": "ephemeral"}}],
                tools=tools,
                messages=self.messages,
            )
            if self.effort:
                kwargs["output_config"] = {"effort": self.effort}
            if self.model.startswith(("claude-opus-5", "claude-sonnet-5", "claude-fable-5")):
                # server-side refusal fallback, as recommended for these models
                kwargs["betas"] = ["server-side-fallback-2026-07-01"]
                kwargs["fallbacks"] = "default"
            async with client.beta.messages.stream(**kwargs) as stream:
                async for event in stream:
                    if event.type == "text":
                        on_text(event.text)
                        reply.append(event.text)
                response = await stream.get_final_message()
            self.messages.append({"role": "assistant", "content": response.content})
            u = response.usage
            totals["input"] += u.input_tokens; totals["output"] += u.output_tokens
            totals["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
            totals["cache_write"] += getattr(u, "cache_creation_input_tokens", 0) or 0
            for block in response.content:
                if block.type == "thinking":
                    on_event(Event("thinking"))
            if response.stop_reason == "refusal":
                on_event(Event.note("the model declined this request" + (
                    f" ({response.stop_details.category})" if getattr(response, "stop_details", None) else "")))
                break
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses or response.stop_reason == "max_tokens":
                break
            results = []
            totals["tools"] += len(tool_uses)
            for tool in tool_uses:
                arguments = tool.input if isinstance(tool.input, dict) else json.loads(tool.input or "{}")
                on_event(Event("tool_call", tool.name, json.dumps(arguments)))
                try:
                    text = await self.bridge.call_tool(tool.name, arguments)
                    results.append({"type": "tool_result", "tool_use_id": tool.id, "content": text[:40000]})
                    on_event(Event("tool_result", tool.name, preview(text), ok=True, data={"text": text}))
                except Exception as exc:                      # noqa: BLE001 - reported to the model
                    results.append({"type": "tool_result", "tool_use_id": tool.id,
                                    "content": f"tool error: {exc}", "is_error": True})
                    on_event(Event("tool_result", tool.name, f"tool error: {exc}", ok=False))
            self.messages.append({"role": "user", "content": results})
            if reply:
                on_text("\n\n")
                reply.append("\n\n")
        on_event(Event("usage", data={**totals, "duration_ms": int((time.monotonic() - started_at) * 1000), "api_ms": 0,
                                      "turns": 0, "cost": 0.0, "context_window": 0}))
        return "".join(reply)

    def status(self) -> str:
        key = "key: env" if os.environ.get("ANTHROPIC_API_KEY") else "key: profile/env"
        return f"Anthropic API ({key})"
