"""Composition root and local stdio entry point."""

import argparse
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from brg_mcp.catalog import Catalog
from brg_mcp.adapters.public_books import PublicBooks
from brg_mcp.book_guidance import SERVER_INSTRUCTIONS
from brg_mcp.resources.knowledge import register as register_resources
from brg_mcp.tools.discovery import register as register_tools
from brg_mcp.tools.books import register as register_books
from brg_mcp.tools.drawing import register as register_drawing
from brg_mcp.prompts.books import register as register_book_prompts


def create_server(data_root: Path) -> FastMCP:
    catalog = Catalog(data_root)
    server = FastMCP("BRG MCP", instructions=SERVER_INSTRUCTIONS)
    register_tools(server, catalog)
    register_resources(server, catalog)
    register_book_prompts(server)
    register_drawing(server)
    books = PublicBooks.from_config(data_root)
    if books is not None:
        register_books(server, books)
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="BRG MCP local stdio server")
    parser.add_argument("--data-root", required=True, type=Path,
                        help="Directory containing config/ and knowledge/")
    args = parser.parse_args()
    create_server(args.data_root).run(transport="stdio")


if __name__ == "__main__":
    main()
