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
  tools/books.py           Public library discovery, summary search, chapter reads
  prompts/books.py         Client-independent books_process workflow
  book_guidance.md         Shared reading/processing conventions adapted from Books/CLAUDE.md
  book_guidance.py         Load the packaged guide; MCP initialization instructions
  adapters/public_books.py HTTPS retrieval, index parsing, bounded in-memory cache
  adapters/                Future optional computational wrappers
examples/                  Client connection example
tests/                     Catalog and MCP protocol checks
```

The server entry point requires an explicit data root containing `config/` and `knowledge/`.
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
Books, extracted text, figures, and page/provenance metadata live in public R2
storage. `config/sources.yaml` sets the HTTPS base URL and `LIBRARY.md` path.
`PublicBooks` parses the existing library-map headings and chapter summaries.
Search checks those summaries; it does not claim full-text or semantic retrieval.
Only listed chapters and known book indexes can be read by MCP. Fetches are lazy,
limited to 2 MB of decoded bytes per document, and cached for the server process
(32 entries). Restart after uploads to refresh. No R2 keys are needed by readers.
Keep BRG-authored notes in `knowledge/`, without mirroring hosted book folders.

- `book_guidance.md`: shared reading/processing rules, exposed through `get_book_guide`
  and `brg://books/guide`. Initialization instructions point clients to it.
- `skills/structural-library/SKILL.md`: optional agent entry point to the same guide.
- `skills/books-process/SKILL.md`: canonical processing workflow, included in the
  package and exposed by the `books_process` prompt and `get_book_guide` tool.
- `.claude/skills/books-process/SKILL.md`: thin slash-command adapter to that workflow.
- Authoring, review, and conversion are documented workflows, not MCP execution tools.

For full-text search later, publish a compact passage index alongside the collection
instead of downloading every chapter for each query.

The server exposes only registered Markdown under the knowledge root; paths are
resolved before reading, including symlinks. Future computation and remote hosting
need their own explicit execution and access design. Log to stderr under stdio.
