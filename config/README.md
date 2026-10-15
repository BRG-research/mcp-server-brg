# Catalogs

- `domains.yaml`: the seven domain IDs, labels, and directories.
- `knowledge.yaml`: the allowlist of Markdown documents exposed by MCP.
- `packages.yaml`: candidate packages, integration status, and tested versions.
- `sources.yaml`: bibliographic records; reserved for future citation resolution.

The first three catalogs are loaded at startup. Source metadata on knowledge
entries is passed through to search results; it is not independently verified.
There is no solver execution or permissions configuration in the starter.
