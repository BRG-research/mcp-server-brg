"""Claude through the Claude Agent SDK: one long-lived session per conversation, your Claude login.

The SDK drives the same Claude Code engine (and therefore the same account) as `claude -p`, but the
process stays alive between turns, so the per-turn cost is the model call only; the BRG MCP server
is started once inside that session.  Falls back to the `claude -p` subprocess if the SDK is missing.
"""

from __future__ import annotations

import json

from brg_mcp.cli.mcp_bridge import MCPBridge
from .agent_cli import ClaudeCliProvider, claude_account, readiness
from .base import OnEvent, OnText, Provider

BRG_INSTRUCTIONS = """You are running inside the BRG terminal (Block Research Group, ETH Zurich). The `brg` MCP server gives
you search_knowledge and brg://knowledge/{id} resources for the group's notes and the book tools for the public
library. Use them before answering factual questions on structural design, graphic statics, form finding,
thrust network analysis or COMPAS; cite what you read (note id, book section, printed page). Answer concisely in
Markdown; TeX in $...$ for equations."""


class ClaudeSDKProvider(Provider):
    name = "claude"
    default_model = ""
    login_command = ["claude", "auth", "login"]

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

    async def _connect(self):
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        command, args = self.bridge.server_command()
        options = ClaudeAgentOptions(
            model=self.model or None,
            mcp_servers={"brg": {"type": "stdio", "command": command, "args": args}},
            allowed_tools=["mcp__brg__*"],
            system_prompt={"type": "preset", "preset": "claude_code", "append": BRG_INSTRUCTIONS},
            include_partial_messages=True,
            cwd=str(self.bridge.data_root),
        )
        client = ClaudeSDKClient(options)
        await client.connect()
        self._client = client
        return client

    async def send(self, user_text: str, on_text: OnText, on_event: OnEvent) -> str:
        try:
            from claude_agent_sdk import AssistantMessage, ResultMessage, ToolUseBlock
            from claude_agent_sdk.types import StreamEvent
        except ImportError:
            if self._fallback is None:
                on_event("claude-agent-sdk not installed: using `claude -p` per turn (slower)")
                self._fallback = ClaudeCliProvider(self.bridge, self.model)
            return await self._fallback.send(user_text, on_text, on_event)
        client = self._client or await self._connect()
        reply: list[str] = []
        streamed = False
        await client.query(user_text)
        async for message in client.receive_response():
            if isinstance(message, StreamEvent):
                event = message.event or {}
                delta = event.get("delta") or {}
                if event.get("type") == "content_block_delta" and delta.get("type") == "text_delta":
                    on_text(delta.get("text", "")); reply.append(delta.get("text", "")); streamed = True
            elif isinstance(message, AssistantMessage):
                if message.model:
                    self.actual_model = message.model
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        name = block.name
                        if name == "ToolSearch":
                            continue
                        on_event(f"{name.removeprefix('mcp__brg__')}({json.dumps(block.input)[:140]})")
            elif isinstance(message, ResultMessage):
                self.session_id = message.session_id
                if not streamed and message.result:
                    on_text(message.result); reply.append(message.result)
                if message.is_error:
                    on_event(f"claude reported an error: {str(message.result)[:300]}")
        return "".join(reply)

    def status(self) -> str:
        sub = f" ({self.subscription})" if self.subscription else ""
        return f"Claude account {self.account}{sub}"
