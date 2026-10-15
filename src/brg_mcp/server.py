"""Composition root and local stdio entry point."""

import argparse
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from brg_mcp.catalog import Catalog
from brg_mcp.resources.knowledge import register as register_resources
from brg_mcp.tools.discovery import register as register_tools


def create_server(data_root: Path) -> FastMCP:
    catalog = Catalog(data_root)
    server = FastMCP("BRG MCP")
    register_tools(server, catalog)
    register_resources(server, catalog)
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="BRG MCP local stdio server")
    parser.add_argument("--data-root", required=True, type=Path,
                        help="Directory containing config/ and knowledge/")
    args = parser.parse_args()
    create_server(args.data_root).run(transport="stdio")


if __name__ == "__main__":
    main()
