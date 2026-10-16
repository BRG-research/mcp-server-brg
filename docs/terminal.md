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

The terminal is a full-screen application built on prompt_toolkit, the
same library that draws its input line. From top to bottom:

- the banner: the BRG logo, and beside it the model, effort, mode and
  context share, the account and tool count, the directory, and whether the
  terminal is idle or working;
- the transcript, which scrolls: the mouse wheel, PageUp / PageDown,
  Shift+Up / Shift+Down (three lines) and End (back to the newest line);
  while you are scrolled back, the status line says how far;
- the status line: while a reply runs, a spinner with the elapsed time and
  the chain of steps so far;
- the input line; Up and Down walk your history, `/` opens the command menu;
- one line of key hints.

The application uses the terminal's own colours for text and background
(`BRG_BACKGROUND=#0b1220` paints one, if you want it); the terminal's
scrollbar is unused. With the wheel in use the terminal
reports the mouse to `brg`, so selecting text needs Shift held while
dragging (as in vim or tmux); `/mouse off` (or `BRG_MOUSE=off`) gives plain
selection back and leaves PageUp / PageDown for scrolling. On exit the
terminal shows your shell again as it was.

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

## Answer style

`/style caveman` (default): the fewest words that still answer, short
sentences, no preamble or summary, numbers and equations over prose; a
simple question gets one to three sentences. `/style plain` is short prose,
`/style full` a complete treatment with headings and derivations.
`BRG_STYLE` sets it at start. With the Claude engine a change starts a new
conversation.

## Speed: where the time goes

The terminal adds about 0.3 s to a reply; the rest is the model. Measured
with the same simple question (no tool calls):

| engine | first text after | total |
|---|---|---|
| Opus 5.5, caveman | 6.5 s | 9.6 s |
| Opus 5.5, plain | 3.5 s | 7.7 s |
| Sonnet 5.5, caveman | 5.7 s | 6.8 s |

The time before the first word is the model thinking and reading the
context; every tool call adds a round trip of a few seconds; every output
token costs time at roughly 60 to 80 tokens per second on Opus. So: the
caveman style cuts the output, `/model sonnet` answers faster for simple
questions, `/effort low` reduces thinking, and the prompt tells the model to
answer general knowledge without tools and to search at most once for a
simple question.

## Effort

`/effort low | medium | high | xhigh | max` sets how hard the model thinks:
`low` answers fastest, `high` is the model's own default, `max` thinks
longest. `/effort` alone shows the current setting; `/effort default` goes
back to the engine's own setting (Claude Code's `effortLevel` in
`~/.claude/settings.json`, Codex's `model_reasoning_effort`). With the
Claude engine a change starts a new conversation. `--effort` and
`BRG_EFFORT` set it at start.

## Drawings: computed, not hand-drawn

The model never draws with text itself. Two server tools compute and draw,
and the terminal prints each drawing the moment the tool returns, between
the steps of the chain, with a green bar at the left:

- `funicular_cable(span, loads, pole_distance, support_heights)` solves the
  funicular polygon of a hanging cable (mirrored, an arch) under point loads
  exactly and returns the construction step by step in the graphic statics
  way: form diagram with Bow's notation, load line, pole and rays, the
  funicular polygon, the forces read off the rays.
- `draw_diagram(lines, arrows, dashed, points, labels, title)` draws any
  line construction from coordinates the model computes: form and force
  diagrams, trusses, reciprocal figures.

Lines are drawn with Braille dots (two by four per character cell, so
proportions are true), labels in plain characters. A construction that took
two minutes of hand-drawn text art now takes one tool call; the model
explains the drawings instead of producing them.

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

## Look and feel

Replies sit two columns from the left edge, wrap at 110 columns at most,
and are printed block by block as they complete: the chain, each paragraph,
each code block, each drawing. Nothing on screen is ever rewritten by hand,
the application lays the screen out again itself on every change and on
resize.

