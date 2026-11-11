"""The BRG MCP server.

Every markdown file ``src/brg_mcp/<folder>/<page>.md`` is one command.
``readme.md`` is the command of the folder, every other page adds its name::

    fd/readme.md   ->   fd
    fd/algorithm.md     ->   fd_algorithm

A new command is a new markdown file; this file does not change.
Each command reaches the chatbot in two ways:

* through the tool ``command``: the user types ``mcp_brg_fd`` and the model calls the tool with it,
* as a prompt, which some chatbots show as a slash command (Claude Code: ``/mcp__brg__fd``).

``uv run brg-mcp`` runs the server. It waits for a chatbot on stdin and stdout; it is not a chat.

"""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from brg_mcp.teaching import link
from brg_mcp.teaching import notebooks_of
from brg_mcp.teaching import plain
from brg_mcp.teaching import title

HERE = Path(__file__).parent

# ==============================================================================
# Commands
# ==============================================================================


def command_name(path):
    """Name the command of a markdown file.

    Parameters
    ----------
    path : :class:`pathlib.Path`
        The file ``<folder>/<page>.md``.

    Returns
    -------
    str
        ``<folder>`` for ``readme.md``, ``<folder>_<page>`` otherwise.

    """
    folder, page = path.relative_to(HERE).with_suffix("").parts
    return folder if page == "readme" else "{}_{}".format(folder, plain(page))


# Finds the file names.
COMMANDS = {command_name(path): path for path in sorted(HERE.glob("*/*.md"))}


def reply(name):
    """The text of a command, with the instruction to repeat it as it is.

    The ``readme.md`` of a folder ends with the list of the other pages in that folder, in the order of their numbers.
    A page with a notebook folder of the same name, numbers aside, such as ``06_exercises.md`` and ``07_exercises/``, ends with a link
    to each notebook in it, which opens the notebook in the Jupyter of the teaching website.

    Parameters
    ----------
    name : str
        A key of ``COMMANDS``.

    Returns
    -------
    str

    """
    path = COMMANDS[name]
    text = path.read_text(encoding="utf-8").strip()
    if path.stem == "readme":
        pages = [other for other in COMMANDS if other != name and COMMANDS[other].parent == path.parent]
        text += "\n\nMore information:\n\n" + "\n".join("- {}: mcp_brg_{}".format(page.removeprefix(name + "_").capitalize(), page) for page in pages)
    notebooks = notebooks_of(path)
    if notebooks:
        text += "\n\nNotebooks:\n\n" + "\n".join("- {}: {}".format(title(notebook), link(notebook)) for notebook in notebooks)
    return "Reply with exactly this text, word for word, nothing added:\n\n" + text.strip()


# ==============================================================================
# Server
# ==============================================================================

RULE = (
    "When the user's message is mcp_brg or mcp_brg_<name>, with or without a leading /, "
    "call the tool `command` of this server with the message as `name` and repeat the result word for word. "
    "mcp_brg lists the commands: {}."
).format(", ".join("mcp_brg_{}".format(name) for name in COMMANDS))

mcp = FastMCP("brg", instructions=RULE)


def add_prompt(name):
    """Offer a command as a prompt, which chatbots show as a slash command.

    Parameters
    ----------
    name : str
        A key of ``COMMANDS``.

    """
    mcp.prompt(name=name, description="BRG {}".format(name))(lambda: reply(name))


for name in COMMANDS:
    add_prompt(name)


@mcp.tool(description=RULE)
def command(name: str):
    """Answer a command typed as text, for chatbots without slash commands.

    Parameters
    ----------
    name : str
        The command, for example ``mcp_brg_fd``, ``/mcp_brg_fd`` or ``fd``.
        The type hint stays: MCP reads it to tell the chatbot that ``name`` is text.

    Returns
    -------
    str

    """
    name = name.strip().lstrip("/").removeprefix("mcp__brg__").removeprefix("mcp_brg").lstrip("_")
    if name not in COMMANDS:
        return "Reply with exactly this list, nothing added:\n\n" + "\n".join("mcp_brg_{}".format(command) for command in COMMANDS)
    return reply(name)
