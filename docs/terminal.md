# BRG terminal

`brg` is a chat terminal for the BRG MCP server: a pixel BRG logo on top, the transcript in the
middle, a `>` prompt at the bottom. It talks to **your own signed-in accounts**, not to API keys:
the default backend is the Claude Code CLI with your Claude login, the second one is the Codex CLI
with your ChatGPT login. Both get the BRG MCP server attached, so the model can search the
knowledge notes and the book library while it answers.

## Install and run

```bash
uv sync --extra cli          # textual, anthropic, openai
uv run brg                   # from the checkout, or: uv run brg --data-root /path/to/mcp-server-brg
```

Requirements for the account backends: the [Claude Code](https://code.claude.com) CLI (`claude`)
and/or the [Codex](https://github.com/openai/codex) CLI (`codex`) on your PATH, signed in. If you
are not signed in yet, type `/login claude` or `/login codex` inside the terminal: the CLI's own
login runs in the same window and the terminal resumes afterwards.

## The screen

```
▀▀▀▀▀  ▀▀▀▀▀   ▀▀▀▀    BRG Terminal  v0.1.0
█   █  █   █  █        Claude Code default · claude account · you@example.com · 8 BRG tools
▀▀▀▀▀  ▀▀▀▀   ▀▀▀▀▀    /home/you/mcp-server-brg

> how does compas_fd compute reactions?
● search_knowledge({"query": "reactions compas_fd"})
● In compas_fd the residual at a fixed node is p - C^t Q C x ...

──────────────────────────────────────────────────────────────
>
──────────────────────────────────────────────────────────────
? for shortcuts
```

The header always stays on top. Lines starting with `>` are yours, green bullets are tool calls
and notes, the model's reply renders as Markdown below them.

## Commands

Type `/` and Tab to complete.

| command | effect |
|---|---|
| `/help` or `?` | list the commands |
| `/provider claude` | Claude Code CLI with your Claude account (default) |
| `/provider codex` | Codex CLI with your ChatGPT account |
| `/provider anthropic` | Anthropic API directly; needs `ANTHROPIC_API_KEY` or an SDK login profile |
| `/provider openai` | OpenAI Responses API directly; needs `OPENAI_API_KEY` |
| `/login claude` / `/login codex` | run the CLI's sign-in in this terminal |
| `/model <name>` | pick a model: `opus`, `sonnet`, `claude-opus-5-5`, `gpt-5-codex`, …; `/model default` restores the provider's own |
| `/status` | provider, model, account, tool count |
| `/tools` | the MCP tools the model can call |
| `/search <words>` | query the knowledge notes directly (no model) |
| `/read <id>` | print a knowledge note, e.g. `/read form-finding-compas-fd` |
| `/books <words>` | search the public book library directly |
| `/clear` | forget the conversation |
| `/quit` | leave (also Ctrl+C); Escape cancels a running answer |

Switching provider or model starts a new conversation.

## How the backends work

- **claude**: each turn runs `claude -p --output-format stream-json --include-partial-messages
  --mcp-config <generated file> --allowedTools "mcp__brg__*"` with your message on stdin, streams
  the text and tool calls as they happen, and remembers the session id so the next turn resumes it
  (`--resume`). The generated config points at this checkout's server
  (`python -m brg_mcp.server --data-root …`).
- **codex**: each turn runs `codex exec --json` with the server passed as inline config
  (`-c mcp_servers.brg.command=… -c mcp_servers.brg.args=…`); later turns use `codex exec resume --last`.
- **anthropic** / **openai**: the terminal runs the tool loop itself over the MCP connection it
  holds. These are for people who prefer API billing; the account backends are the default.

Options: `--provider`, `--model`, `--data-root`, or the environment variables `BRG_PROVIDER`,
`BRG_MODEL`.

[Main README](../README.md) · [Local development](development/README.md)
