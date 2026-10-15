"""One model list across all engines, so the user switches models, not providers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:                                   # Python < 3.11
    tomllib = None


@dataclass(frozen=True)
class ModelEntry:
    name: str          # what the user types
    provider: str      # engine key in PROVIDERS
    model: str         # what the engine receives ("" = the engine's own default)
    note: str


CLAUDE_MODELS = [
    ModelEntry("claude", "claude", "", "Claude Code's default model, your Claude account"),
    ModelEntry("opus", "claude", "opus", "Claude Opus, your Claude account"),
    ModelEntry("sonnet", "claude", "sonnet", "Claude Sonnet, your Claude account"),
    ModelEntry("haiku", "claude", "haiku", "Claude Haiku, your Claude account"),
]
CODEX_MODELS = [
    ModelEntry("codex", "codex", "", "Codex's default model, your ChatGPT account"),
]


def codex_models_from_config(path: Path | None = None) -> list[ModelEntry]:
    """Model names that Codex itself has recorded in ~/.codex/config.toml."""
    path = path or Path.home() / ".codex" / "config.toml"
    if tomllib is None or not path.is_file():
        return []
    try:
        config = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return []
    names = []
    if isinstance(config.get("model"), str):
        names.append(config["model"])
    names += list((config.get("tui") or {}).get("model_availability_nux") or {})
    seen, out = set(), []
    for n in names:
        if n not in seen:
            seen.add(n); out.append(ModelEntry(n, "codex", n, "Codex model, your ChatGPT account"))
    return out


def catalog() -> list[ModelEntry]:
    return CLAUDE_MODELS + CODEX_MODELS + codex_models_from_config()


def resolve(name: str) -> ModelEntry | None:
    """Map what the user typed to an engine and a model id.

    Known names come from the catalog; otherwise the name's shape decides:
    `api:<model>` goes to the Anthropic or OpenAI API, `claude-*` to the Claude engine,
    `gpt-*`, `o*` and `codex-*` to the Codex engine."""
    name = name.strip()
    if not name or name == "default":
        return None
    for entry in catalog():
        if entry.name.lower() == name.lower():
            return entry
    if name.startswith("api:"):
        target = name[4:]
        provider = "anthropic" if target.startswith("claude") else "openai"
        return ModelEntry(name, provider, target, f"{provider} API with a key")
    if name.startswith("claude"):
        return ModelEntry(name, "claude", name, "Claude model by id, your Claude account")
    if re.match(r"^(gpt|o\d|codex)", name):
        return ModelEntry(name, "codex", name, "Codex model by id, your ChatGPT account")
    return None


def listing() -> str:
    width = max(len(e.name) for e in catalog())
    lines = ["Models (switch with /model <name>):", ""]
    for e in catalog():
        lines.append(f"  {e.name:<{width}}  {e.note}")
    lines += ["", "Any claude-* id, any gpt-*/o*/codex-* id, or api:<model> for the direct APIs also works."]
    return "\n".join(lines)
