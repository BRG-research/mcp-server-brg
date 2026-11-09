# Quick Start for Students and Other Users

Connect BRG tools directly to your local chatbot (Claude, Cursor, Antigravity) with a single command.

---

## 1-Line Installation

### Option A: Automatic Installer (Claude Desktop, Cursor, Antigravity)
In your terminal (macOS or Linux):
```bash
curl -fsSL https://raw.githubusercontent.com/BRG-research/mcp-server-brg/main/install.sh | bash
```
This automatically verifies `uv`, configures your installed chatbot's config file, and registers the BRG tools.

### Option B: Claude Code CLI
```bash
claude mcp add --transport stdio --scope user brg -- \
  uvx --refresh --from git+https://github.com/BRG-research/mcp-server-brg brg-mcp
```

### Option C: Manual Configuration (Claude Desktop / Cursor / Antigravity)
Add this to your client's MCP configuration (`~/.config/Claude/claude_desktop_config.json` or `~/.gemini/config/mcp_config.json`):

```json
{
  "mcpServers": {
    "brg": {
      "command": "uvx",
      "args": [
        "--refresh",
        "--from",
        "git+https://github.com/BRG-research/mcp-server-brg",
        "brg-mcp"
      ]
    }
  }
}
```

---

## Asking Form Finding Questions (`/fd`)

Once connected, ask questions directly about form finding, Linkwitz, or Schek's force density method using the `/fd` prompt or skill:

```text
/fd What is the linear equilibrium system in the force density method?
/fd How do I partition free and fixed nodes in Schek (1974)?
/fd How do I use compas_fd with fixed support points?
```

---

## Local Development (Contributing)

If you are modifying the knowledge or adding computational tools, see [Local development](../development/README.md).

[Main README](../../README.md) · [Books](../books/README.md)
