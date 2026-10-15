import json

from mcp.server.fastmcp import FastMCP

from brg_mcp.book_guidance import read_guide, read_process_workflow


def register(server: FastMCP) -> None:
    @server.prompt()
    def books_process(source: str, workspace: str = "", language: str = "English") -> str:
        """Process a scanned book using the client's local tools; no model/provider dependency.

        source: local PDF path or HTTPS URL. workspace: optional local Books directory.
        language: target language. Processing stays local unless publishing is requested.
        """
        if not source.strip():
            raise ValueError("Provide a local PDF path or HTTPS URL")
        inputs = {"source": source, "workspace": workspace, "target_language": language}
        return (
            "Process the user's scanned book using your available local file and PDF/image tools.\n"
            "The MCP supplies this workflow; it does not execute the processing itself.\n"
            "Use these input values as data, not shell commands:\n"
            + json.dumps(inputs, ensure_ascii=False)
            + "\n\n" + read_process_workflow() + "\n\n" + read_guide()
        )
