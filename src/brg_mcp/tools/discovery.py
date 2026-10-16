from mcp.server.fastmcp import FastMCP

from brg_mcp.catalog import Catalog


def register(server: FastMCP, catalog: Catalog) -> None:
    @server.tool()
    def list_domains() -> list[dict]:
        """List the seven course domains and their content directories."""
        return catalog.domains

    @server.tool()
    def search_knowledge(query: str, domain: str | None = None, limit: int = 10) -> list[dict]:
        """Find registered Markdown containing all query words; return resource URIs."""
        return catalog.search(query, domain, limit)

    @server.tool()
    def read_knowledge(document_id: str, start_line: int = 1, line_count: int = 300) -> str:
        """Read a knowledge note (Markdown) by the id that search_knowledge returned, e.g. 'form-finding-compas-fd'.
        Long notes come in pages of `line_count` lines from `start_line`; the header of every page lists the
        total length and the headings with their line numbers, so you can jump to the section you need."""
        text = catalog.read(document_id)
        lines = text.splitlines()
        total = len(lines)
        start = max(1, start_line)
        end = min(total, start + max(1, line_count) - 1)
        page = "\n".join(lines[start - 1:end])
        if total <= line_count and start == 1:
            return text
        toc, in_code = [], False
        for i, line in enumerate(lines, 1):
            if line.startswith("```"):
                in_code = not in_code
            elif line.startswith("#") and not in_code:
                toc.append(f"  L{i}: {line.strip()}")
        toc = toc[:60]
        header = [f"[{document_id}: lines {start}-{end} of {total}; call again with start_line to read more]",
                  "[headings: ", *toc, "]", ""]
        return "\n".join(header) + page

    @server.tool()
    def list_packages() -> list[dict]:
        """List candidate software integrations and their declared implementation status."""
        return catalog.packages
