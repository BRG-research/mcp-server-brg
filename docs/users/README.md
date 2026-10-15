# Other users

Install [uv](https://docs.astral.sh/uv/), then:

```bash
git clone https://github.com/BRG-research/mcp-server-brg.git
cd mcp-server-brg
uv sync --python 3.12 --locked
claude mcp add --transport stdio --scope user brg -- \
  uv --directory "$PWD" run --locked brg-mcp --data-root "$PWD"
```

- Open Claude Code, sign in with your account, and check `/mcp`.
- Other clients: adapt [mcp-client.json](../../examples/mcp-client.json) with your checkout's absolute paths.
- If `uv` is not found, use its absolute executable path in the client configuration.
- Public book reading needs no R2 keys. Your AI client handles model access and billing.
- The client starts the local server; keep the checkout for its catalogs and local knowledge.
- Updates: `git pull --ff-only`, then `uv sync --locked`, then restart MCP.
- This setup requires a client supporting local stdio MCP, not only remote URLs.
- Skills are installed separately from MCP; see [Books](../books/README.md#process).

[Main README](../../README.md) · [Books](../books/README.md)
