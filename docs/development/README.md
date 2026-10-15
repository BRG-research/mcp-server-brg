# Local development

Run from the repository root (Bash/Zsh):

```bash
uv sync --python 3.12 --extra dev
uv run pytest
claude mcp add --transport stdio --scope local brg -- \
  uv --directory "$PWD" run --locked brg-mcp --data-root "$PWD"
claude
```

- Install [uv](https://docs.astral.sh/uv/) and sign in to your AI client first.
- In Claude Code, use `/mcp` to check the connection.
- Ask: “Use BRG to list domains and find equilibrium.”
- Other clients: adapt [mcp-client.json](../../examples/mcp-client.json) with absolute local paths.
- Restart MCP after code/catalog changes. Run `uv sync` after dependency changes.
- Manual startup: `uv run brg-mcp --data-root "$PWD"`; it waits for MCP input, not chat.
- Claude Code automatically discovers the project's `/books-process` skill when opened here.

[Main README](../../README.md) · [Books](../books/README.md) · [Claude MCP setup](https://code.claude.com/docs/en/mcp)
