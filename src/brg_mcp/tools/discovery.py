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
    def list_packages() -> list[dict]:
        """List candidate software integrations and their declared implementation status."""
        return catalog.packages
