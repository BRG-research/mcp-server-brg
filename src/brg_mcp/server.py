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
from brg_mcp.tools.additions import register as register_additions
from brg_mcp.prompts.books import register as register_book_prompts
from brg_mcp.prompts.fd import register as register_fd_prompts


def find_data_root(start: Path | None = None) -> Path:
    """Find the directory containing config/ and knowledge/.

    Checks in order:
    1. Explicit start directory (if provided).
    2. Current working directory (if run from a repository root).
    3. Source checkout root (when run in development / editable mode).
    4. Bundled package directory (when installed as a wheel / via uvx).
    """
    candidates = [start] if start else []
    pkg_dir = Path(__file__).resolve().parent
    candidates += [
        Path.cwd(),
        pkg_dir.parent.parent,
        pkg_dir,
    ]
    for c in candidates:
        if c and (c / "config" / "knowledge.yaml").is_file():
            return c.resolve()
    from importlib.resources import files
    try:
        res = Path(str(files("brg_mcp")))
        if (res / "config" / "knowledge.yaml").is_file():
            return res.resolve()
    except Exception:
        pass
    raise SystemExit("Could not find BRG data directory containing config/knowledge.yaml; please pass --data-root")


def create_server(data_root: Path, **settings) -> FastMCP:
    catalog = Catalog(data_root)
    server = FastMCP("BRG MCP", instructions=SERVER_INSTRUCTIONS, **settings)
    register_tools(server, catalog)
    register_resources(server, catalog)
    register_book_prompts(server)
    register_fd_prompts(server, catalog)
    register_drawing(server)
    register_notebooks(server)
    register_additions(server)
    books = PublicBooks.from_config(data_root)
    if books is not None:
        register_books(server, books)
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="BRG MCP server")
    parser.add_argument("--data-root", required=False, default=None, type=Path,
                        help="Directory containing config/ and knowledge/ (default: auto-detected)")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                        help="stdio for a local client (default); http serves Streamable HTTP at /mcp")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP only: address to listen on")
    parser.add_argument("--port", type=int, default=8000, help="HTTP only: port to listen on")
    args = parser.parse_args()
    data_root = find_data_root(args.data_root)
    if args.transport == "stdio":
        create_server(data_root).run(transport="stdio")
    else:
        # Stateless JSON responses: every request stands alone, so any instance can answer it
        # (the Claude API's MCP connector, a container that sleeps and restarts).
        import uvicorn
        server = create_server(data_root, host=args.host, port=args.port,
                               stateless_http=True, json_response=True)
        uvicorn.run(http_app(server), host=args.host, port=args.port, log_level="info")


def http_app(server: FastMCP):
    """The Streamable HTTP app, callable from web pages too (CORS): the CAS website lists the notebook
    tools as slash commands and calls them directly. The server is read-only and holds no secrets."""
    from starlette.middleware.cors import CORSMiddleware
    return CORSMiddleware(server.streamable_http_app(), allow_origins=["*"], allow_methods=["GET", "POST", "OPTIONS"],
                          allow_headers=["*"], expose_headers=["mcp-session-id"])


if __name__ == "__main__":
    main()
