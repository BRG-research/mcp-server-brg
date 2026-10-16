# BRG terminal

`brg` is a chat terminal for the BRG MCP server: a pixel BRG logo on top, the transcript in the
middle, a `>` prompt at the bottom. It talks to **your own signed-in accounts**, not to API keys:
the default backend is the Claude Code CLI with your Claude login, the second one is the Codex CLI
with your ChatGPT login. Both get the BRG MCP server attached, so the model can search the
knowledge notes and the book library while it answers.

## Install and run

```bash
uv sync                      # everything, including the terminal
uv run brg                   # from the checkout, or: uv run brg --data-root /path/to/mcp-server-brg
```

Requirements for the account backends: the [Claude Code](https://code.claude.com) CLI (`claude`)
and/or the [Codex](https://github.com/openai/codex) CLI (`codex`) on your PATH, signed in. If you
are not signed in yet, type `/login claude` or `/login codex` inside the terminal: the CLI's own
login runs in the same window and the terminal resumes afterwards.

## First run, new user

1. Install: `uv sync`, then `uv run brg`.
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

## Modes: reading, editing, acting

By default (`read`) the model has the BRG tools only: it can search and read
notes and books, nothing on disk is touched. The engines underneath are the
same Claude Code and Codex, so the terminal can also work on files:

```
/mode edit     file and shell tools in the folder you started brg in;
               every change and every command is shown and you answer y/N
/mode auto     the same without questions (like claude --dangerously-skip-permissions)
/mode read     back to the BRG tools only
```

Start `brg` inside the project you want to work on: that directory is the
working directory of the file tools (the BRG notes are found on their own).
`--mode edit` or `BRG_MODE=edit` starts in that mode. Switching the mode
starts a new conversation, because the tool set is fixed when the engine
session opens. With the Codex engine `edit` maps to its workspace-write
sandbox and `auto` to full access; `codex exec` cannot ask questions, so
Codex does not confirm step by step.

## Reading a reply

A reply is laid out like a pipeline view. Between the text messages a
chain of badges shows the steps the model took, in order, joined by
chevrons:

| badge | meaning |
|---|---|
| `◐` blue | the model is thinking |
| `≣` | a read: a knowledge note, a book section, a search |
| `⚙` | any other tool (in Codex also a shell command) |
| amber / green / red | running / returned / failed |

Each badge is followed by a short dim label, the tool and its main
argument, so `≣ search_knowledge "force density"` reads at a glance. The
chain is as long as the number of steps between two messages. Each badge is
also a hyperlink whose target repeats the tool and its arguments, for
terminals that show link targets on hover. `/trace` prints every step of
the last reply with all arguments, duration and a preview of the result.
`/legend` (or `/symbols`) explains every symbol, in colour, inside the
terminal.

Under each reply a dim line gives the tokens read and written, the cached
part, the number of tools, the share of the context window in use and the
time. API-key engines also show the cost; account engines do not.

## Equations and figures

Display equations (`$$...$$`) are typeset in two dimensions, as SymPy
prints in a terminal: fractions over a rule, sums and integrals with their
limits, parentheses that grow with their content, accents on the line
above, matrices in brackets, marked with a bar at the left:

```
▌        sⱼ
▌   ∑   ──── (xₖ − xᵢ) + pᵢ = 0
▌   j    lⱼ
```

Inline math (`$...$`) is written the way an engineer writes it in a text
file, in the code colour: `C^T Q C x = p`, `α_max ≤ 30°`, `(w L²)/(8 f)`.
Anything the typesetter cannot parse falls back to that notation.

Figures referenced in a reply or a note (`![caption](path.png)`) are listed
under the text with their caption and path as a `file://` link; Ctrl+click
opens the image viewer. Kitty, Ghostty, WezTerm and iTerm2 show the image
itself inline. `/figures open` opens every figure in the system viewer as it
appears, `/figures link` keeps links only, `/figures blocks` draws a coarse
pixel rendering (not pretty; off by default); `BRG_FIGURES` sets the mode at
start. `/show <note id>` lists a note's figures, `/show <image path>` one
image, `/show open <path>` opens it.

## Where the model name is

The header printed at the start names the model, the account and the tool
count. Because the transcript is the terminal's own scrollback, that header
scrolls away like any other line; the model stays visible in two places
that do not scroll: the terminal's window or tab title (`BRG · Claude Fable
5.1 · ctx 9%`) and the bar under the prompt. A header pinned to the top of
the window is not offered: a terminal only saves scrolled-off lines into
its scrollback when the scrolling region starts at the top row, so a pinned
header would cost the scrollbar and the mouse-wheel history.

## Logs

The MCP server's log lines and the Claude subprocess's stderr never reach
the screen: they go to `~/.brg/brg.log` (`BRG_LOG` changes the path). If a
tool misbehaves, that file has the details.

## Look and feel

The terminal's background is painted dark blue while `brg` runs and
restored when you leave (set `BRG_BACKGROUND` to another colour, or empty
to keep your own). The scrollbar is not part of the terminal canvas: it is
a widget of the terminal application, coloured by the desktop theme, and no
program running inside the terminal can recolour it. If the mismatch
bothers you, keep your own background (`BRG_BACKGROUND=`) or set the
terminal profile's background to the same dark blue.

While a reply is produced only a one-line status is redrawn. The step chain,
each paragraph and each code block are printed once, when complete, so
nothing in the scrollback is ever rewritten and a resize cannot disturb it.

The terminal is the terminal: nothing is drawn full-screen. The banner, the
events and the replies are printed into the terminal's own scrollback, so the
terminal's scrollbar, mouse selection and copy work as usual, exactly as in
Claude Code. Only the prompt line at the bottom is live (prompt_toolkit): the
command menu opens under it as soon as you type `/`, `/model ` lists the model
names, Up/Down walk the history (kept in `~/.brg_history`, or `$BRG_HISTORY`).
While a reply is being prepared an animated indicator with the elapsed time is
shown; it is replaced by the reply as it streams in, rendered as Markdown.
Ctrl+C interrupts a running reply; at an empty prompt Ctrl+C twice, Ctrl+D or
`/quit` leaves.
