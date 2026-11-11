# BRG MCP

The MCP server of the Block Research Group. A chatbot connects to it and gets short texts on structural design, one command per text. Write "mcp_brg" to know all the functions.

## Layout

```text
README.md  pyproject.toml  uv.lock
src/brg_mcp/server.py              the server
src/brg_mcp/teaching.py            copies the notebooks to the teaching website (brg-publish)
src/brg_mcp/fd/readme.md           the command fd (form finding, force density)
src/brg_mcp/fd/01_algorithm.md     the command fd_algorithm (also applications, keywords, references, ...)
src/brg_mcp/fd/07_exercises/       the notebooks of fd_exercises (08_answers/: of fd_answers)
.github/workflows/teaching.yml     publishes the notebooks on every push
tests/                             start the server, check what it offers and what it publishes
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

## Notebooks

A page with a notebook folder of the same name, numbers aside (`06_exercises.md` and `07_exercises/`), ends with a link
to each notebook. The link opens the notebook in the Jupyter of the
[teaching website](https://brg-teaching.github.io/Teaching/CAS/website/library.html#/notebook), in the browser.

On every push to `main`, the GitHub Action `.github/workflows/teaching.yml` copies the notebooks to
`BRG-teaching/Teaching` (`CAS/website/notebooks/<folder>/`, for example `notebooks/fd/`), always overwriting copies of the same name, and the
teaching website deploys them. The Action needs the repository secret `TEACHING_TOKEN`: a GitHub token that may write
the contents of `BRG-teaching/Teaching`. By hand: `uv run brg-publish /path/to/Teaching/CAS/website`.
Restart the chatbot. `server.py` does not change.

## Test

The code follows the [COMPAS](https://github.com/compas-dev/compas) style: numpy docstrings, ruff with the same rules.

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format .
uv run pytest -q
```
