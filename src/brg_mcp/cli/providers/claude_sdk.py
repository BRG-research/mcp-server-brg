"""Claude through the Claude Agent SDK: one long-lived session per conversation, your Claude login.

The SDK drives the same Claude Code engine (and therefore the same account) as `claude -p`, but the
process stays alive between turns, so the per-turn cost is the model call only; the BRG MCP server
is started once inside that session.  Falls back to the `claude -p` subprocess if the SDK is missing.
"""

from __future__ import annotations

import asyncio
import json

from brg_mcp.cli import logs
from brg_mcp.cli.mcp_bridge import MCPBridge
from .agent_cli import ClaudeCliProvider, claude_account, claude_code_effort, readiness
from .base import MODE_PROMPT, SYSTEM_PROMPT, Event, OnEvent, OnText, Provider, preview, result_text, tool_name, width_prompt

BRG_INSTRUCTIONS = SYSTEM_PROMPT


class ClaudeSDKProvider(Provider):
    name = "claude"
    default_model = ""
    login_command = ["claude", "auth", "login"]
    supports_modes = True

    def __init__(self, bridge: MCPBridge, model: str | None = None):
        super().__init__(bridge, model)
        self.account = claude_account()
        self._client = None
        self.session_id: str | None = None
        self._fallback: ClaudeCliProvider | None = None
        self.subscription = ""
        self.server_models: list[dict] = []
        self.actual_model: str | None = None        # the model id the last reply came from

    def ready(self) -> tuple[bool, str]:
        return readiness("claude", self.account)

    async def reset(self) -> None:           # type: ignore[override]
        await self.close()

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.disconnect()
            finally:
                self._client = None
                self.session_id = None

    async def set_model(self, model: str) -> None:
        """Switch the model inside the running session (no reset)."""
        self.model = model
        if self._client is not None:
            await self._client.set_model(model or None)

    async def set_mode(self, mode: str) -> None:
        """The tool set is fixed when the session connects, so a new session (new conversation)."""
        self.mode = mode
        await self.close()

    async def set_effort(self, effort: str | None) -> None:
        """Effort is fixed when the session connects, so a new session (new conversation)."""
        self.effort = effort
        await self.close()

    async def set_style(self, style: str) -> None:
        """The system prompt is fixed when the session connects, so a new session (new conversation)."""
        self.style = style
        await self.close()

    def default_effort(self) -> str:
        return claude_code_effort()

    async def warm(self) -> dict:
        """Connect now (so the first question is fast) and return Claude Code's server info:
        the account's model list, the default model, the subscription."""
        client = self._client or await self._connect()
        info = await client.get_server_info() or {}
        account = info.get("account") or {}
        if account.get("email"):
            self.account = account["email"]
        self.subscription = account.get("subscriptionType") or ""
        self.server_models = info.get("models") or []
        return info

    async def _can_use_tool(self, tool: str, tool_input: dict, context):
        from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny
        if self.mode == "auto" or self.ask_permission is None:
            return PermissionResultAllow()
        if await self.ask_permission(tool, tool_input):
            return PermissionResultAllow()
        return PermissionResultDeny(message="the user declined this action")

    async def _connect(self):
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        command, args = self.bridge.server_command()
        read_only = self.mode == "read"
        options = ClaudeAgentOptions(
            model=self.model or None,
            mcp_servers={"brg": {"type": "stdio", "command": command, "args": args}},
            # read: no built-in tools at all; edit/auto: Claude Code's file and shell tools
            tools=[] if read_only else {"type": "preset", "preset": "claude_code"},
            allowed_tools=["mcp__brg__*"] if read_only else ["mcp__brg__*", "Read", "Glob", "Grep", "LS", "TodoWrite"],
            permission_mode="bypassPermissions" if self.mode == "auto" else "default",
            effort=self.effort,                              # None: Claude Code's own setting
            can_use_tool=None if read_only else self._can_use_tool,
            system_prompt=self.system_prompt() + "\n\n" + MODE_PROMPT[self.mode] + "\n" + width_prompt(self.terminal_width),
            include_partial_messages=True,
            stderr=logs.write,                               # the CLI's stderr goes to the log, not the screen
            cwd=self.workdir or str(self.bridge.data_root),
        )
        client = ClaudeSDKClient(options)
        await client.connect()
        self._client = client
        return client

    async def send(self, user_text: str, on_text: OnText, on_event: OnEvent) -> str:
        try:
            import claude_agent_sdk  # noqa: F401
        except ImportError:
            if self._fallback is None:
                on_event(Event.note("claude-agent-sdk not installed: using `claude -p` per turn (slower)"))
                self._fallback = ClaudeCliProvider(self.bridge, self.model)
            return await self._fallback.send(user_text, on_text, on_event)
        client = self._client or await self._connect()
        state = {"reply": [], "streamed": False, "tools": 0}
        await client.query(user_text)
        try:
            async for message in client.receive_response():
                self._handle(message, on_text, on_event, state)
        except asyncio.CancelledError:
            try:                                                       # stop the model, keep the session
                await asyncio.wait_for(client.interrupt(), 5)
            except Exception:                                          # noqa: BLE001
                await self.close()
            raise
        return "".join(state["reply"])

    def _handle(self, message, on_text: OnText, on_event: OnEvent, state: dict) -> None:
        from claude_agent_sdk import AssistantMessage, ResultMessage, ToolResultBlock, ToolUseBlock, UserMessage
        from claude_agent_sdk.types import StreamEvent
        reply = state["reply"]
        if isinstance(message, StreamEvent):
            event = message.event or {}
            kind = event.get("type")
            if kind == "content_block_delta":
                delta = event.get("delta") or {}
                if delta.get("type") == "text_delta":
                    on_text(delta.get("text", "")); reply.append(delta.get("text", "")); state["streamed"] = True
            elif kind == "content_block_start":
                block = event.get("content_block") or {}
                if block.get("type") == "thinking":
                    on_event(Event("thinking"))
                elif block.get("type") == "tool_use" and block.get("name") != "ToolSearch":
                    state["tools"] += 1
                    on_event(Event("tool_call", tool_name(block.get("name", ""))))
        elif isinstance(message, AssistantMessage):
            if message.model:
                self.actual_model = message.model
            for block in message.content:
                if isinstance(block, ToolUseBlock) and block.name != "ToolSearch":
                    on_event(Event("tool_args", tool_name(block.name), json.dumps(block.input)))
        elif isinstance(message, UserMessage):
            content = message.content if isinstance(message.content, list) else []
            for block in content:
                if isinstance(block, ToolResultBlock):
                    on_event(Event("tool_result", "", preview(block.content), ok=not block.is_error, data={"text": result_text(block.content)}))
        elif isinstance(message, ResultMessage):
            self.session_id = message.session_id
            if not state["streamed"] and message.result:
                on_text(message.result); reply.append(message.result)
            if message.is_error:
                on_event(Event.error(f"claude reported an error: {str(message.result)[:300]}"))
            usage = message.usage or {}
            window = max((m.get("contextWindow", 0) for m in (message.model_usage or {}).values()), default=0)
            on_event(Event("usage", data={
                "input": usage.get("input_tokens", 0), "output": usage.get("output_tokens", 0),
                "cache_read": usage.get("cache_read_input_tokens", 0),
                "cache_write": usage.get("cache_creation_input_tokens", 0),
                "duration_ms": message.duration_ms, "api_ms": message.duration_api_ms,
                "turns": message.num_turns, "tools": state["tools"], "cost": message.total_cost_usd or 0.0,
                "context_window": window}))

    async def context_usage(self) -> dict | None:
        if self._client is None:
            return None
        try:
            import asyncio
            return await asyncio.wait_for(self._client.get_context_usage(), 5)
        except Exception:                                              # noqa: BLE001
            return None

    def status(self) -> str:
        sub = f" ({self.subscription})" if self.subscription else ""
        return f"Claude account {self.account}{sub}"
