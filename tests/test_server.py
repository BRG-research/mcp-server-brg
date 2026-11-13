import asyncio
import re
import sys
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from brg_mcp.server import COMMANDS
from brg_mcp.server import mcp
from brg_mcp.teaching import link
from brg_mcp.teaching import notebooks_of


def ask(question):
    """Start the server the way a chatbot does and ask it ``question(client)``."""

    async def run():
        transport = StdioTransport(command=str(Path(sys.executable).parent / "brg-mcp"), args=[], keep_alive=False)
        async with Client(transport) as client:
            return await question(client)

    return asyncio.run(asyncio.wait_for(run(), timeout=20))


def test_instructions_name_every_command():
    assert all("mcp_brg_{}".format(name) in mcp.instructions for name in COMMANDS)


def test_readme_lists_the_pages_of_its_folder():
    text = ask(lambda client: client.call_tool("command", {"name": "mcp_brg_fd"})).content[0].text
    assert all("mcp_brg_{}".format(name) in text for name in COMMANDS if name.startswith("fd_"))


@pytest.mark.parametrize("name", ["fd_exercises", "fd_answers", "fd_extensions"])
def test_page_lists_the_notebooks_of_its_folder(name):
    text = ask(lambda client: client.call_tool("command", {"name": name})).content[0].text
    notebooks = notebooks_of(COMMANDS[name])
    assert notebooks and all(link(notebook) in text for notebook in notebooks)


def test_server_offers_every_command():
    prompts = ask(lambda client: client.list_prompts())
    tools = ask(lambda client: client.list_tools())
    assert {prompt.name for prompt in prompts} == set(COMMANDS)
    assert "fd" in COMMANDS
    assert {tool.name for tool in tools} == {"command", "greet"}


@pytest.mark.parametrize("typed", ["mcp_brg_fd", "/mcp_brg_fd", "fd", "/mcp__brg__fd"])
def test_prompt_and_tool_reply_the_same(typed):
    prompt = ask(lambda client: client.get_prompt("fd"))
    tool = ask(lambda client: client.call_tool("command", {"name": typed}))
    assert prompt.messages[0].content.text == tool.content[0].text


@pytest.mark.parametrize("typed", ["mcp_brg", "/mcp_brg", "nothing"])
def test_mcp_brg_lists_the_commands(typed):
    tool = ask(lambda client: client.call_tool("command", {"name": typed}))
    assert all("mcp_brg_{}".format(name) in tool.content[0].text for name in COMMANDS)


@pytest.mark.parametrize("name", sorted(COMMANDS))
def test_every_command_named_in_a_text_exists(name):
    for named in re.findall(r"mcp_brg_([a-z_]+)", COMMANDS[name].read_text(encoding="utf-8")):
        assert named in COMMANDS


@pytest.mark.parametrize("name", ["compas_fd_hypar", "compas_fd_selfweight"])
@pytest.mark.parametrize("editor", [None, "vscode"])
def test_code_is_shown_in_a_terminal_and_written_in_an_editor(monkeypatch, editor, name):
    from brg_mcp.server import reply

    monkeypatch.delenv("CLAUDE_CODE_ENTRYPOINT", raising=False)
    monkeypatch.delenv("TERMINAL_EMULATOR", raising=False)
    if editor:
        monkeypatch.setenv("TERM_PROGRAM", editor)
    else:
        monkeypatch.delenv("TERM_PROGRAM", raising=False)
    text = reply(name)
    assert "{}.py".format(name.replace("compas_", "")) in text
    assert text.startswith("Write each Python example") == bool(editor)
