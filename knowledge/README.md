# Knowledge collection

The numbered folders follow the seven CAS course chapters. Shared concepts belong
in `concepts/` and can link to multiple domains without duplicating explanations.

- This folder includes theory, practical package/API usage, assumptions, limitations,
  troubleshooting, and links to runnable examples. It is not theory-only.
- Executable examples belong in `examples/`; reusable computation in `src/brg_mcp/adapters/`.
- Start with the [Form Finding walkthrough](04_form_finding/README.md).

Write formulas as in [the formula style](FORMULA_STYLE.md) (formula, plain reading, symbol table,
worked numbers). Use [the note template](../docs/templates/knowledge-note.md). The authoritative
lookup catalog is `config/knowledge.yaml`: each entry needs a unique, stable `id`,
`title`, a domain from `config/domains.yaml`, a repository-relative Markdown `path`,
and a `sources` list. Keep IDs unchanged when moving files. Use simple lowercase
hyphenated IDs so they work in `brg://knowledge/{id}` URIs.

Only cataloged notes are served and searched. Frontmatter is retained in resource
text but is not parsed by the starter. Restart the server after catalog edits.
A source reference should record `source_id`, `pages`, and verification status;
register the corresponding bibliographic record in `config/sources.yaml`.

Keep BRG-authored explanations and topic overviews here. Books, extracted text,
figures, and their page/provenance metadata live in public Cloudflare R2 storage,
referenced by `config/sources.yaml`; do not mirror their folder trees here.
Book tools search the hosted library map and read selected Markdown over HTTPS.
Local knowledge tools continue to search only registered notes in this repository.
