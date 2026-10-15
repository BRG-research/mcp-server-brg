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

## First run, new user

1. Install the terminal: `uv sync --extra cli`, then `uv run brg`.
2. The header shows which account the current model uses. If nothing is signed in, the first
   lines of the transcript say so and what to do:
   - `/login claude` runs Claude Code's sign-in (`claude auth login`) inside the terminal: a
     browser opens, or a URL and a code are printed; the terminal resumes when it finishes.
   - `/login codex` runs `codex login` the same way for a ChatGPT account.
   - If the CLI itself is missing, the message gives the install command
     (`npm install -g @anthropic-ai/claude-code` or `npm install -g @openai/codex`).
3. `/models` lists the models your accounts offer, by name (Claude Fable 5.1, Claude Opus 5.5,
   Codex Astra, …); `/model fable` or `/model astra` switches. Nothing is sent to a model until its account is ready, so a new user never sees a raw
   CLI error.

Without any account, `api:<model>` with `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in the
environment is the fallback. You do not need a key for speed: the account path keeps one session
alive and answers short follow-ups in under two seconds.

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

Type `/` and the list of commands appears under the prompt, filtered as you type; `/model ` lists
the models the same way. Up and Down move in the list, Tab or Enter take the highlighted entry
(a command without argument runs at once), Esc closes it. With no list open, Up and Down walk
through the lines you typed before.

| command | effect |
|---|---|
| `/help` or `?` | list the commands |
| `/model <name>` | switch model by its name: `Claude Fable 5.1`, `Claude Opus 5.5`, `Codex Astra`, … or a word of it (`fable`, `sonnet`, `astra`); also any `claude-*` or `gpt-*` id, or `api:<model>` for the direct APIs |
| `/models` | the models your accounts offer (Claude Code's own list for your Claude account, Codex's config for your ChatGPT account) and which one is current |
| `/login claude` / `/login codex` | run the CLI's sign-in in this terminal |
| `/provider claude\|codex\|anthropic\|openai` | advanced: pick the engine directly |
| `/status` | provider, model, account, tool count |
| `/tools` | the MCP tools the model can call |
| `/search <words>` | query the knowledge notes directly (no model) |
| `/read <id>` | print a knowledge note, e.g. `/read form-finding-compas-fd` |
| `/books <words>` | search the public book library directly |
| `/clear` | forget the conversation |
| `/quit` | leave (also Ctrl+C); Escape cancels a running answer |

Switching to a model on the same engine keeps the conversation; switching engine (Claude account to ChatGPT account or back) starts a new one.

## How the backends work

- **claude**: one long-lived session through the Claude Agent SDK (`ClaudeSDKClient`), which runs
  the same Claude Code engine with your Claude login. The session and the BRG MCP server inside it
  start on your first message and stay alive, so later turns cost only the model call (measured:
  about 6 s for a first turn with a tool call, 1.6 s for a short follow-up; the per-turn
  `claude -p` path took about 4 s each). `/model opus` or `sonnet` switches the model inside the
  session. `/provider claude-cli` is the old one-process-per-turn fallback.
- **codex**: each turn runs `codex exec --json` with the server passed as inline config
  (`-c mcp_servers.brg.command=… -c mcp_servers.brg.args=…`), approvals off
  (`approval_policy="never"`, read-only sandbox) and the BRG tools auto-approved
  (`mcp_servers.brg.default_tools_approval_mode="approve"`, they only read); later turns use
  `codex exec resume --last`. `/model` takes Codex model names, e.g. `/model gpt-6-astra`.
- **anthropic** / **openai**: the terminal runs the tool loop itself over the MCP connection it
  holds. These are for people who prefer API billing; the account backends are the default.

Options: `--provider`, `--model`, `--data-root`, or the environment variables `BRG_PROVIDER`,
`BRG_MODEL`.

[Main README](../README.md) · [Local development](development/README.md)

## Look and feel

The terminal paints nothing of its own: it runs on your terminal's colours (Textual's ANSI mode),
so resizing, transparency and your theme behave as in any other terminal program. While a reply is
being prepared an animated indicator with the elapsed time is shown; it disappears with the first
streamed character.
