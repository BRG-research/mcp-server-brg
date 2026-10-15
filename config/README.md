# Catalogs

- `domains.yaml`: the seven domain IDs, labels, and directories.
- `knowledge.yaml`: the allowlist of Markdown documents exposed by MCP.
- `packages.yaml`: candidate packages, integration status, and tested versions.
- `sources.yaml`: public book collection URL and library-map path. Bibliographic
  details and original page references come from its `LIBRARY.md` and chapters.

The catalogs are loaded at startup; remote book text is fetched only when a book
tool is called. An empty sources list disables book tools. Source metadata on knowledge
entries is passed through to search results; it is not independently verified.
There is no solver execution or permissions configuration in the starter.
