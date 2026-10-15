# Architecture and growth

The course organizes knowledge. Python modules organize responsibilities.

```text
knowledge/                 Seven chapters plus shared concepts
config/                    Domain, document, package, and source catalogs
skills/                    Agent workflow instructions
src/brg_mcp/
  server.py                Compose registrations; run local stdio
  catalog.py               Resolve IDs, read Markdown, lexical search
  tools/discovery.py       list_domains, search_knowledge, list_packages
  resources/knowledge.py   brg://knowledge/{document_id}
  adapters/                Future optional computational wrappers
  indexing/                Future document extraction and indexing
examples/                  Client connection example
tests/                     Catalog and MCP protocol checks
```

The CLI requires an explicit data root containing `config/` and `knowledge/`.
Content lives outside the Python wheel; use a checkout or a separately maintained
content directory. This makes behavior independent of the client's working directory.
The MCP SDK is bounded to its documented v1 FastMCP API (`mcp<2`); reassess v2 in a
separate migration. See the [official SDK documentation](https://py.sdk.modelcontextprotocol.io/v1/).

## Add content

1. Copy `docs/templates/knowledge-note.md` into a chapter folder.
2. Fill assumptions, notation, units, verification, and source/page provenance.
3. Add the note to `config/knowledge.yaml`; register bibliographic metadata in
   `config/sources.yaml`. Mark unreviewed content as draft.
4. Restart and use `search_knowledge`, then read the returned resource URI.

Search currently checks all query words against each registered Markdown document
and title, without ranking, embeddings, PDF extraction, or mathematical parsing.
It returns catalog metadata and source references, not generated answers.

## Add the first computation

Choose one small method (for example a force-density example). Verify the package
API and compatible versions before adding an optional dependency group. Put its
Python wrapper in `adapters/`, then expose a typed function in `tools/` and register
it in `server.py`. Import optional packages only when their integration is used.

Define geometry, units, supports, loads, sign conventions, solver settings, and
failure behavior. Return structured geometry/results, residuals, convergence, and
package/version metadata. Add a small analytical benchmark and a reproducible
example before marking the package supported in `config/packages.yaml`.

## Later extensions

Add method-specific skills when workflows exist. Add MCP prompts only when a client
needs a reusable prompt; skills and prompts have different discovery mechanisms.
Introduce PDF ingestion, figure resources, and an index when the curated collection
needs them. Keep originals, extractions, and reviewed notes distinguishable.

The server exposes only registered Markdown under the knowledge root; paths are
resolved before reading, including symlinks. Future computation and remote hosting
need their own explicit execution and access design. Log to stderr under stdio.
