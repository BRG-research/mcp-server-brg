"""The model list the user switches between: real model names, taken from the accounts.

Claude models come from the running Claude Code session (its own list for this account);
Codex models come from the user's ~/.codex/config.toml.  No entry is called "default".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:                                   # Python < 3.11
    tomllib = None


@dataclass(frozen=True)
class ModelEntry:
    name: str                 # what is shown: "Claude Fable 5.1", "Codex Astra"
    provider: str             # engine key in PROVIDERS
    model: str                # what the engine receives (model id)
    note: str                 # one-line description with the account
    aliases: tuple[str, ...] = field(default_factory=tuple)   # other spellings that select it

    def matches(self, text: str) -> bool:
        t = text.strip().lower()
        return t in {self.name.lower(), self.model.lower(), *(a.lower() for a in self.aliases)}


def claude_entries(server_models: list[dict], account_note: str = "Claude") -> list[ModelEntry]:
    """From ClaudeSDKClient.get_server_info()['models']; the 'default' pseudo-entry is skipped."""
    out, seen = [], set()
    for m in server_models:
        value, resolved = m.get("value", ""), m.get("resolvedModel", "")
        if value == "default" or not resolved or resolved in seen:
            continue
        seen.add(resolved)
        display = m.get("displayName") or resolved
        aliases = tuple(a for a in {value, resolved} if a and a != display)
        out.append(ModelEntry(f"Claude {display}", "claude", resolved, f"{m.get('description', '')} · {account_note}", aliases))
    return out


def claude_default_model(server_models: list[dict]) -> str | None:
    """Opus when the account offers it (the user's choice), else the account's own default."""
    for m in server_models:
        if "opus" in str(m.get("resolvedModel", "")) and m.get("value") != "default":
            return m.get("resolvedModel")
    for m in server_models:
        if m.get("value") == "default":
            return m.get("resolvedModel")
    return None


def codex_display_name(model_id: str) -> str:
    """gpt-6-astra -> Codex Astra, gpt-6.1-sol -> Codex Sol, o3 -> Codex o3."""
    tail = model_id.split("-")[-1]
    return f"Codex {tail.capitalize()}" if tail.isalpha() and len(model_id.split('-')) > 1 else f"Codex {model_id}"


def codex_entries(path: Path | None = None, account_note: str = "ChatGPT") -> list[ModelEntry]:
    """Model ids that Codex itself has recorded in ~/.codex/config.toml (its current and offered models)."""
    path = path or Path.home() / ".codex" / "config.toml"
    if tomllib is None or not path.is_file():
        return []
    try:
        config = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return []
    ids = []
    if isinstance(config.get("model"), str):
        ids.append(config["model"])
    ids += list((config.get("tui") or {}).get("model_availability_nux") or {})
    out, seen = [], set()
    for model_id in ids:
        if model_id not in seen:
            seen.add(model_id)
            out.append(ModelEntry(codex_display_name(model_id), "codex", model_id, f"{model_id} · {account_note}", (model_id,)))
    return out


def resolve(text: str, entries: list[ModelEntry]) -> ModelEntry | None:
    """Exact name / alias / id first, then a unique word match ("fable", "astra"), then id shapes."""
    t = text.strip()
    if not t:
        return None
    for e in entries:
        if e.matches(t):
            return e
    words = t.lower().split()
    partial = [e for e in entries if all(w in e.name.lower() or w in e.model.lower() for w in words)]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:                                      # "fable" -> the newest, listed first by the engine
        return partial[0]
    if t.startswith("api:"):
        target = t[4:]
        provider = "anthropic" if target.startswith("claude") else "openai"
        return ModelEntry(t, provider, target, f"{provider} API with a key")
    if t.startswith("claude"):
        return ModelEntry(t, "claude", t, "Claude model by id, your Claude account")
    if re.match(r"^(gpt|o\d|codex)", t):
        return ModelEntry(codex_display_name(t), "codex", t, f"{t} · ChatGPT")
    return None


def listing(entries: list[ModelEntry], current: str | None = None) -> str:
    width = max((len(e.name) for e in entries), default=10)
    lines = ["Models (switch with /model <name>):", ""]
    for e in entries:
        mark = "● " if current and e.model == current else "  "
        lines.append(f"{mark}{e.name:<{width}}  {e.note}")
    lines += ["", "Also: any claude-* or gpt-*/o*/codex-* id, or api:<model> for the direct APIs with a key."]
    return "\n".join(lines)
