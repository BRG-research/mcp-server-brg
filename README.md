# BRG MCP

The MCP server of the Block Research Group. A chatbot connects to it and gets short texts on structural design, one command per text. Write "mcp_brg" to know all the functions.

## Layout

```text
README.md  pyproject.toml  uv.lock
src/brg_mcp/server.py              the server
src/brg_mcp/fd/readme.md           the command fd (form finding, force density)
src/brg_mcp/fd/01_algorithm.md     the command fd_algorithm (also applications, keywords, references, presentations)
tests/test_server.py               starts the server and checks what it offers
```

## Connect a chatbot

Install [uv](https://docs.astral.sh/uv/) once. Replace `/path/to/mcp-server-brg` with the path of this folder.
The server is the same for every chatbot; only where each one stores the connection differs.

| Chatbot | Connect |
|---|---|
| Claude Code | `claude mcp add --transport stdio --scope user brg -- uv --directory /path/to/mcp-server-brg run brg-mcp` |
| Codex | `codex mcp add brg -- uv --directory /path/to/mcp-server-brg run brg-mcp` |
| Antigravity | add the block below to `~/.gemini/config/mcp_config.json` |

```json
{
  "mcpServers": {
    "brg": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-server-brg", "run", "brg-mcp"]
    }
  }
}
```

Check the connection with `claude mcp list`, `codex mcp list`, or `/mcp` inside Antigravity.
Restart the chatbot after every change to this folder: it starts the server again and sees the new state.

## Use a command

Type the command as a message, in any chatbot: `mcp_brg_fd`. Type `mcp_brg` for the list of all commands. The model calls the server's tool `command` with it
and repeats the text. Chatbots that show MCP prompts also offer it as a slash command, in their own format
(Claude Code: `/mcp__brg__fd`).

## Add a command

Every file `src/brg_mcp/<folder>/<page>.md` is a command. `readme.md` is the command `<folder>`,
every other page is `<folder>_<page>`, for example `fd/03_keywords.md` is `fd_keywords`; the number only orders the pages.
Write in it what the command should answer. The reply of `readme.md` ends with the list of the other pages
in its folder (`- Keywords: mcp_brg_fd_keywords`), made by the server.
A page with a folder of the same name (`08_answers.md` and `08_answers/`) ends with a Google Colab link to each notebook
in that folder. The links open once the notebooks are pushed to `main` on GitHub.
Restart the chatbot. `server.py` does not change.

## Test

The code follows the [COMPAS](https://github.com/compas-dev/compas) style: numpy docstrings, ruff with the same rules.

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format .
uv run pytest -q
```
