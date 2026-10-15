# Agent workflows

- [`books-process`](books-process/SKILL.md): portable processing workflow for a local PDF or HTTPS URL.
- MCP prompt: `books_process(source, workspace?, language?)`; no client-specific skill installation required.
- Claude shortcut: [`.claude/skills/books-process/`](../.claude/skills/books-process/SKILL.md), a thin adapter.
- For availability in other projects, follow the [personal installation steps](../docs/books/README.md#process).

`research-methodology/SKILL.md` provides an initial research workflow. Skills are
instructions for a compatible agent client. MCP exposes book-processing instructions
through its prompt and guide tool; the client executes the workflow using its own tools.

`structural-library/SKILL.md` covers querying and processing books and routes to
the server's shared `src/brg_mcp/book_guidance.md`. MCP clients can retrieve that
guide with `get_book_guide` without installing the skill.

Add graphic-statics, form-finding, thrust-network-analysis, or constructability
skills once each has a concrete repeatable workflow. Keep the name and description
in YAML frontmatter and describe inputs, method-specific checks, and outputs.
