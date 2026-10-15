# BRG MCP

A starter MCP server for Block Research Group knowledge and computational design
workflows.

## Run it

Install [uv](https://docs.astral.sh/uv/), then from this checkout:

```bash
uv sync --python 3.12 --extra dev
uv run pytest
uv run brg-mcp --data-root "$PWD"
```

The last command starts a stdio server waiting for an MCP client, so it does not
show an interactive prompt. To connect your client, adapt
[examples/mcp-client.json](examples/mcp-client.json), replacing both absolute
paths and using an absolute path to `uv` if your client cannot find it.

Available now: `list_domains`, `search_knowledge`, `list_packages`, and Markdown
resources at `brg://knowledge/{document_id}`. Try searching for `equilibrium`, then
read `brg://knowledge/equilibrium`. Software entries are planned integrations;
computational solvers, PDF search, and figure retrieval are not implemented yet.

## Where things go

```text
knowledge/                 Course content and shared concepts
  01_history/
  02_computational_design/
  03_graphic_statics/
  04_form_finding/
  05_thrust_network_analysis/
  06_constructability/
  07_research_projects/
  concepts/
src/brg_mcp/                Server, tools, resources, adapters, indexing
config/                    Domain, document, software, and source catalogs
skills/                    Agent research workflows (loaded separately)
examples/                  Client configuration and future worked examples
tests/                     Catalog and MCP protocol checks
docs/                      Architecture and reusable note template
data/                      Local originals and generated artifacts
```

## Fill it gradually

1. **Add one note.** Copy the [template](docs/templates/knowledge-note.md) into a
   chapter, fill its assumptions and references, and register it in
   `config/knowledge.yaml`. Restart the server and search for it.
2. **Build a small collection.** Add reviewed explanations and worked examples.
   Record source IDs and page references; keep shared concepts in `knowledge/concepts/`.
3. **Connect one computation.** Add a verified package wrapper in `adapters/`,
   expose it in `tools/`, and register it in `server.py`. Add a benchmark and example
   before marking the integration supported.
4. **Expand from use.** Add other solvers, figures, extraction/indexing, and domain
   skills when the first workflows need them.

See [architecture and contribution details](docs/architecture.md) for conventions.
The Python package and content are separate: `--data-root` must point to a directory
containing `config/` and `knowledge/`, including when installing a built wheel.
