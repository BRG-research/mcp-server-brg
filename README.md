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
- [Remote server](deploy/README.md) — the same server over HTTP, used by the CAS website's BRG terminal.

## Available now

- Course domains, local knowledge search, and package discovery.
- Public book search over chapter summaries (historical books first), chapter reads, and figures as images.
- Book-processing guidance; conversion runs through your agent's local tools.
- Notebook skills: `compas_box_notebook` (`/box` on the CAS website) writes a runnable COMPAS notebook.
- Computational solvers and full-text book search are not implemented.

## Add a notebook skill (`/box`, `/primitives`, …)

Every MCP tool named `compas_<name>_notebook` becomes the slash command `/<name>` on the
[CAS website](https://brg-teaching.github.io/Teaching/CAS/website/library.html#/notebook) (Jupyter + BRG).
`/skills` lists them; each writes a runnable notebook into JupyterLite. The website never needs changing.

Example: turn [`02-geometry/01-primitives.ipynb`](knowledge/02_computational_design/notebooks/02-geometry/01-primitives.ipynb)
into `/primitives`.

1. **Open** [`src/brg_mcp/tools/notebooks.py`](src/brg_mcp/tools/notebooks.py).
2. **Copy** the `box_notebook` function, rename it `primitives_notebook`, and replace its code cells with the
   code from the tutorial. Keep `INSTALL` first and `viewer.show()` last.
3. **Name the file:** set `"file": "primitives.ipynb"`.
4. **Register it:** in `register()`, copy the `compas_box_notebook` block and rename it
   `compas_primitives_notebook`. Its first docstring paragraph is the help text; its parameters are the
   arguments (`/primitives 3`, `/primitives size=3`).
5. **Test:** copy the test in [`tests/test_notebooks.py`](tests/test_notebooks.py), then run the tests.
6. **Push** to `main`; Render deploys it in a few minutes.
7. **Use it:** reload the website, type `/skills`, then `/primitives`.

```bash
uv run --extra dev pytest -q
git commit -am "Add /primitives"
git push
```

More detail: [Contributing → Add a notebook skill](docs/contributing/README.md#add-a-notebook-skill-box-).
