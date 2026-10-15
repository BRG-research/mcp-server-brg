"""The default backends: your own Claude or ChatGPT account through the installed `claude` / `codex` CLIs.

No API key is involved. Each turn runs the agent CLI non-interactively with the BRG MCP server
attached, streams its events into the terminal, and resumes the same agent session next turn.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path

from brg_mcp.cli.mcp_bridge import MCPBridge
from .base import OnEvent, OnText, Provider


def mcp_config_file(bridge: MCPBridge) -> Path:
    """A Claude Code --mcp-config file pointing at this checkout's server."""
    command, args = bridge.server_command()
    config = {"mcpServers": {"brg": {"command": command, "args": args}}}
    path = Path(tempfile.gettempdir()) / "brg-terminal-mcp.json"
    path.write_text(json.dumps(config, indent=2))
    return path


async def stream_lines(cmd: list[str], stdin_text: str | None, cwd: str, on_line) -> tuple[int, str]:
    """Run a command, call on_line for every stdout line as it arrives, return (exit code, stderr)."""
    process = await asyncio.create_subprocess_exec(
        *cmd, stdin=asyncio.subprocess.PIPE if stdin_text is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd,
        limit=64 * 1024 * 1024)          # a tool result can be one very long JSON line
    if stdin_text is not None:
        process.stdin.write(stdin_text.encode())
        await process.stdin.drain()
        process.stdin.close()
    async for raw in process.stdout:
        on_line(raw.decode(errors="replace").rstrip("\n"))
    err = (await process.stderr.read()).decode(errors="replace")
    return await process.wait(), err


INSTALL = {
    "claude": "install Claude Code:  npm install -g @anthropic-ai/claude-code   (or see https://code.claude.com)",
    "codex": "install Codex:  npm install -g @openai/codex   (or see https://github.com/openai/codex)",
}


def readiness(which: str, account: str) -> tuple[bool, str]:
    """(ready, what to do) for an account engine: installed and signed in, or the instruction to fix it."""
    if not shutil.which(which):
        return False, f"the `{which}` CLI is not installed. {INSTALL[which]}, then restart brg."
    if account.startswith("not signed in"):
        return False, f"{which} is installed but no account is signed in. Type /login {which} and follow the sign-in in this terminal."
    return True, ""


def claude_account() -> str:
    """The signed-in Claude account, read from Claude Code's own config file."""
    path = Path.home() / ".claude.json"
    try:
        account = json.loads(path.read_text()).get("oauthAccount") or {}
    except (OSError, json.JSONDecodeError):
        return "not signed in (run /login claude)"
    email = account.get("emailAddress")
    return email or "not signed in (run /login claude)"


async def codex_account() -> str:
    exe = shutil.which("codex")
    if not exe:
        return "codex not installed"
    process = await asyncio.create_subprocess_exec(exe, "login", "status", stdout=asyncio.subprocess.PIPE,
                                                   stderr=asyncio.subprocess.STDOUT)
    out, _ = await process.communicate()
    line = out.decode(errors="replace").strip().splitlines()[0] if out.strip() else ""
    return line if line.lower().startswith("logged in") else "not signed in (run /login codex)"


class ClaudeCliProvider(Provider):
    """`claude -p --output-format stream-json` with the BRG server attached; turns resume by session id."""

    name = "claude"
    default_model = ""                  # Claude Code's own default unless /model sets one
    login_command = ["claude", "auth", "login"]

    def __init__(self, bridge: MCPBridge, model: str | None = None):
        super().__init__(bridge, model)
        self.session_id: str | None = None
        self.account = claude_account()

    def reset(self) -> None:
        self.session_id = None

    async def send(self, user_text: str, on_text: OnText, on_event: OnEvent) -> str:
        exe = shutil.which("claude")
        if not exe:
            raise RuntimeError("the `claude` CLI is not installed or not on PATH")
        cmd = [exe, "-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
               "--mcp-config", str(mcp_config_file(self.bridge)), "--allowedTools", "mcp__brg__*"]
        if self.model:
            cmd += ["--model", self.model]
        if self.session_id:
            cmd += ["--resume", self.session_id]
        reply: list[str] = []
        streamed_any = False

        def on_line(line: str) -> None:
            nonlocal streamed_any
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                return
            kind = event.get("type")
            if kind == "stream_event":
                inner = event.get("event") or {}
                delta = inner.get("delta") or {}
                if inner.get("type") == "content_block_delta" and delta.get("type") == "text_delta":
                    on_text(delta.get("text", "")); reply.append(delta.get("text", "")); streamed_any = True
            elif kind == "assistant":
                for block in (event.get("message") or {}).get("content") or []:
                    if block.get("type") == "tool_use":
                        name = str(block.get("name", ""))
                        if name == "ToolSearch":                      # Claude Code's internal tool lookup
                            continue
                        name = name.removeprefix("mcp__brg__")
                        on_event(f"{name}({json.dumps(block.get('input', {}))[:140]})")
            elif kind == "result":
                self.session_id = event.get("session_id", self.session_id)
                if not streamed_any and event.get("result"):
                    on_text(event["result"]); reply.append(event["result"])
                if event.get("is_error"):
                    on_event(f"claude reported an error: {str(event.get('result'))[:300]}")

        code, err = await stream_lines(cmd, user_text, str(self.bridge.data_root), on_line)
        if code != 0 and not reply:
            raise RuntimeError(f"claude exited with {code}: {err.strip()[:500] or 'no output'}")
        return "".join(reply)

    def ready(self) -> tuple[bool, str]:
        return readiness("claude", self.account)

    def status(self) -> str:
        return f"Claude account {self.account}"


class CodexCliProvider(Provider):
    """`codex exec --json` with the BRG server passed as inline config; later turns `codex exec resume --last`."""

    name = "codex"
    default_model = ""
    login_command = ["codex", "login"]

    def __init__(self, bridge: MCPBridge, model: str | None = None):
        super().__init__(bridge, model)
        self.started = False
        self.account = "ChatGPT account"

    def reset(self) -> None:
        self.started = False

    def _config_args(self) -> list[str]:
        command, args = self.bridge.server_command()
        return ["-c", f'mcp_servers.brg.command="{command}"', "-c", "mcp_servers.brg.args=" + json.dumps(args),
                "-c", 'mcp_servers.brg.default_tools_approval_mode="approve"']   # the BRG tools only read

    async def send(self, user_text: str, on_text: OnText, on_event: OnEvent) -> str:
        exe = shutil.which("codex")
        if not exe:
            raise RuntimeError("the `codex` CLI is not installed or not on PATH")
        # never ask for approvals (there is nobody to answer in exec mode) but keep a read-only sandbox:
        # the BRG tools only read notes and books
        cmd = [exe, "exec", "--json", "--skip-git-repo-check", "-c", "approval_policy=\"never\"", "--sandbox", "read-only"] + self._config_args()
        if self.model:
            cmd += ["-m", self.model]
        if self.started:
            cmd += ["resume", "--last"]
        cmd.append(user_text)
        reply: list[str] = []

        def on_line(line: str) -> None:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                return
            item = event.get("item") or {}
            kind, itype = event.get("type"), item.get("type")
            if kind == "item.completed" and itype == "agent_message":
                text = item.get("text", "")
                on_text(("\n\n" if reply else "") + text); reply.append(text)
            elif kind == "item.started" and itype in ("mcp_tool_call", "command_execution"):
                label = item.get("tool") or item.get("command") or itype
                on_event(f"{label}")
            elif kind == "error":
                on_event(f"codex error: {event.get('message', '')[:300]}")

        code, err = await stream_lines(cmd, None, str(self.bridge.data_root), on_line)
        self.started = True
        if code != 0 and not reply:
            raise RuntimeError(f"codex exited with {code}: {err.strip()[:500] or 'no output'}")
        return "\n\n".join(reply)

    def ready(self) -> tuple[bool, str]:
        return readiness("codex", self.account)

    def status(self) -> str:
        return self.account
