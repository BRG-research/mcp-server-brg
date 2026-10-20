# BRG MCP

Knowledge and computational tools for your existing AI client.
The client handles login, models, and usage; BRG MCP connects it to BRG content.

## How to fill a chapter

`knowledge/` contains explanations for people and agents: theory, package usage,
inputs/outputs, examples, limitations, and troubleshooting. It is not theory-only.

| Folder | What you put there |
|---|---|
| `knowledge/<chapter>/` | Explain a method and link to its code and sources |
| `examples/<method>/` | A runnable Python example and its input data |
| `src/brg_mcp/adapters/` | Reusable code calling the computational package |
| `src/brg_mcp/tools/` | A thin MCP interface to that code |
| `tests/` | Checks against known results |
| `config/` | Register searchable notes and tested package capabilities |

Work one method at a time: **inspect package → explain → run example → verify →
add adapter → expose through MCP**. A chapter connects these files; they do not
all live inside its knowledge folder.

Follow the [Form Finding walkthrough](knowledge/04_form_finding/README.md) for
the NumPy force density derivation, runnable examples, and planned `compas_fd`
integration.

## Start here

- [BRG terminal](docs/terminal.md) — `uv run brg`: chat with your own Claude or ChatGPT account over the BRG tools.
- [Local development](docs/development/README.md) — run, test, and connect your checkout.
- [Other users](docs/users/README.md) — install and connect on another computer.
- [Books](docs/books/README.md) — read, upload, process, and publish books.
- [Contributing](docs/contributing/README.md) — add knowledge or computational tools.
- [Architecture](docs/architecture.md) — file structure and implementation details.
- [Skills](skills/README.md) — portable workflows and optional client shortcuts.

## Available now

- Course domains, local knowledge search, and package discovery.
- Public book search over chapter summaries and selected chapter reads.
- Book-processing guidance; conversion runs through your agent's local tools.
- Computational solvers and full-text book search are not implemented.
