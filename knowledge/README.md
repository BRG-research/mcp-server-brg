# Knowledge collection

The numbered folders follow the seven CAS course chapters. Shared concepts belong
in `concepts/` and can link to multiple domains without duplicating explanations.

Use [the note template](../docs/templates/knowledge-note.md). The authoritative
lookup catalog is `config/knowledge.yaml`: each entry needs a unique, stable `id`,
`title`, a domain from `config/domains.yaml`, a repository-relative Markdown `path`,
and a `sources` list. Keep IDs unchanged when moving files. Use simple lowercase
hyphenated IDs so they work in `brg://knowledge/{id}` URIs.

Only cataloged notes are served and searched. Frontmatter is retained in resource
text but is not parsed by the starter. Restart the server after catalog edits.
A source reference should record `source_id`, `pages`, and verification status;
register the corresponding bibliographic record in `config/sources.yaml`.

Store original PDFs locally in `data/private/`. Add figures with source/page and
rights metadata when needed; PDF ingestion and image resources are future work.
