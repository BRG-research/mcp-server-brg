from mcp.server.fastmcp import FastMCP

from brg_mcp.catalog import Catalog


def register(server: FastMCP, catalog: Catalog) -> None:
    @server.resource("brg://knowledge/{document_id}", mime_type="text/markdown")
    def read_knowledge(document_id: str) -> str:
        """Read a registered knowledge document by ID."""
        return catalog.read(document_id)
