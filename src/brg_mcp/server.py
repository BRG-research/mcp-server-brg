"""Composition root and entry point: local stdio, or Streamable HTTP for remote clients."""

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
from brg_mcp.tools.notebooks import register as register_notebooks
from brg_mcp.prompts.books import register as register_book_prompts


def create_server(data_root: Path, **settings) -> FastMCP:
    catalog = Catalog(data_root)
    server = FastMCP("BRG MCP", instructions=SERVER_INSTRUCTIONS, **settings)
    register_tools(server, catalog)
    register_resources(server, catalog)
    register_book_prompts(server)
    register_drawing(server)
    register_notebooks(server)
    books = PublicBooks.from_config(data_root)
    if books is not None:
        register_books(server, books)
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="BRG MCP server")
    parser.add_argument("--data-root", required=True, type=Path,
                        help="Directory containing config/ and knowledge/")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                        help="stdio for a local client (default); http serves Streamable HTTP at /mcp")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP only: address to listen on")
    parser.add_argument("--port", type=int, default=8000, help="HTTP only: port to listen on")
    args = parser.parse_args()
    if args.transport == "stdio":
        create_server(args.data_root).run(transport="stdio")
    else:
        # Stateless JSON responses: every request stands alone, so any instance can answer it
        # (the Claude API's MCP connector, a container that sleeps and restarts).
        create_server(args.data_root, host=args.host, port=args.port,
                      stateless_http=True, json_response=True).run(transport="streamable-http")


if __name__ == "__main__":
    main()
