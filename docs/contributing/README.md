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

## Add a notebook skill (`/box`, …)

A notebook skill is an MCP tool whose name ends in `_notebook`. The CAS website (Jupyter + BRG) lists every
such tool as a slash command (`compas_box_notebook` → `/box`, `compas_frames_notebook` → `/frames`), shows it in
`/skills`, and runs it from the page; Claude uses the same tool when asked in words. No website change is needed.

1. Start from a course notebook that works in JupyterLite (`knowledge/02_computational_design/notebooks/`).
2. In `src/brg_mcp/tools/notebooks.py`, write a function like `box_notebook` that returns
   `{"name", "file", "cells"}`: first `INSTALL`, then the imports, short `## headings`, and a COMPAS scene at
   the end. Parameters are what a student would change (sizes, counts, colours); check them and raise
   `ValueError` with a plain message for bad input (the website shows it).
3. Register it in `register()` as `compas_<name>_notebook`. The docstring's first paragraph is the help text of
   the slash command; its parameters, in order, are the command's arguments (`/box 3 2 1` or `/box zsize=4`).
4. Add a test to `tests/test_notebooks.py`, and run the cells once (see `test_notebooks.py` for what to check).
5. Push to `main`: Render deploys it, and the command appears on the website the next time the page opens.

- Books stay in public R2; follow the [Books README](../books/README.md).
- Shared concepts belong in `knowledge/concepts/`.
- Check changes with `uv run pytest`.

[Main README](../../README.md) · [Architecture](../architecture.md)
