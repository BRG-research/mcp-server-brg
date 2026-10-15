# Contributing

For a complete chapter example, follow the [Form Finding walkthrough](../../knowledge/04_form_finding/README.md).

## Add knowledge

1. Copy the [note template](../templates/knowledge-note.md) into the relevant `knowledge/` chapter.
2. Add assumptions, units, verification, source IDs, and page references.
3. Register it in `config/knowledge.yaml`; restart MCP and search for it.

## Add computation

1. Verify package APIs and versions; add an optional dependency if needed.
2. Put computation in `src/brg_mcp/adapters/` and its MCP wrapper in `tools/`.
3. Register the tool in `server.py`.
4. Add a benchmark and example; only then mark it supported in `config/packages.yaml`.

- Books stay in public R2; follow the [Books README](../books/README.md).
- Shared concepts belong in `knowledge/concepts/`.
- Check changes with `uv run pytest`.

[Main README](../../README.md) · [Architecture](../architecture.md)
