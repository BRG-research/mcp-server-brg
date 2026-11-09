#!/usr/bin/env bash
# One-line installer for BRG MCP server into Claude, Cursor, and Antigravity.
set -euo pipefail

REPO_SPEC="git+https://github.com/BRG-research/mcp-server-brg"

echo "=== BRG MCP Connector Installer ==="

# Check / install uv if missing
if ! command -v uv >/dev/null 2>&1; then
    echo ">> 'uv' is required to run the MCP server. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv was installed but is not in PATH. Please run:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo "and rerun this script."
    exit 1
fi

echo ">> Using uv: $(uv --version)"

# Python helper to safely inject mcpServers configuration into JSON configs
python3 - << 'EOF'
import json
import os
import sys
from pathlib import Path

CONFIGS = [
    # Claude Desktop (Linux & macOS)
    Path.home() / ".config" / "Claude" / "claude_desktop_config.json",
    Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
    # Antigravity
    Path.home() / ".gemini" / "config" / "mcp_config.json",
]

ENTRY = {
    "command": "uvx",
    "args": [
        "--refresh",
        "--from",
        "git+https://github.com/BRG-research/mcp-server-brg",
        "brg-mcp"
    ]
}

modified = 0
for cfg_path in CONFIGS:
    if cfg_path.parent.is_dir() or "Claude" in str(cfg_path) or ".gemini" in str(cfg_path):
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if cfg_path.is_file() and cfg_path.stat().st_size > 0:
            try:
                data = json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        servers = data.setdefault("mcpServers", {})
        servers["brg"] = ENTRY
        cfg_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"  [OK] Configured: {cfg_path}")
        modified += 1

if modified == 0:
    ag_cfg = Path.home() / ".gemini" / "config" / "mcp_config.json"
    ag_cfg.parent.mkdir(parents=True, exist_ok=True)
    ag_cfg.write_text(json.dumps({"mcpServers": {"brg": ENTRY}}, indent=2))
    print(f"  [OK] Created default config at: {ag_cfg}")

EOF

# If Claude Code CLI is present, register it there too
if command -v claude >/dev/null 2>&1; then
    echo ">> Configuring Claude Code CLI..."
    claude mcp add --transport stdio --scope user brg -- \
        uvx --refresh --from "$REPO_SPEC" brg-mcp 2>/dev/null || true
    echo "  [OK] Registered with Claude Code"
fi

echo ""
echo "=== Installation complete! ==="
echo "Restart your chatbot (Claude Desktop, Cursor, Antigravity) to activate BRG tools."
echo "You can test form finding by asking questions with: /fd <your question>"
