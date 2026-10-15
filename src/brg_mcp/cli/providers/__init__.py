"""Model backends.  The account-based ones (`claude`, `codex`) are the default: they use the login of
the installed agent CLIs.  The API ones (`anthropic`, `openai`) need a key or an SDK profile."""

from __future__ import annotations

from .base import Provider
from .agent_cli import ClaudeCliProvider, CodexCliProvider
from .claude_sdk import ClaudeSDKProvider
from .anthropic_api import AnthropicProvider
from .openai_api import OpenAIProvider

PROVIDERS: dict[str, type[Provider]] = {
    "claude": ClaudeSDKProvider,          # persistent session (Agent SDK)
    "claude-cli": ClaudeCliProvider,      # one `claude -p` per turn, fallback
    "codex": CodexCliProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
}

__all__ = ["Provider", "PROVIDERS", "ClaudeSDKProvider", "ClaudeCliProvider", "CodexCliProvider", "AnthropicProvider", "OpenAIProvider"]
