# Remote server on Hugging Face

The CAS website's BRG terminal (`Teaching/CAS/website/library.html#/terminal`) cannot start a local
stdio server, so this one runs as a free Hugging Face Space. Claude reaches it through the Claude API's MCP
connector. It is the same server with the same tools as `uv run brg-mcp`. There is no second copy of the
tools on the website.

```
git push (main) ──▶ GitHub Action: tests, then upload ──▶ Space brghuggingface/brg-mcp (Docker)
                                                           https://brghuggingface-brg-mcp.hf.space/mcp
```

- `Dockerfile` (repository root) runs `brg-mcp --transport http` with `config/` and `knowledge/`.
  The server is stateless and read-only. Books are read live from the public R2 bucket, so a newly
  published book needs no deploy.
- `README.md` in this folder becomes the Space's README. Its header tells Hugging Face to build the
  Dockerfile and use port 8000.
- `.github/workflows/deploy-mcp.yml` deploys on every push to `main` that changes `src/`, `config/`,
  `knowledge/`, `skills/` or this folder. It can also be run by hand (Actions → Deploy MCP server → Run
  workflow). Hugging Face then rebuilds the Space, which takes a few minutes.
- A free Space sleeps after 48 hours without requests. The website wakes it when the library page opens.
  The first request after a sleep can take up to a minute.

## Set up once

1. huggingface.co → Settings → Access Tokens → Create new token → type **Write**. Copy it.
2. GitHub → BRG-research/mcp-server-brg → Settings → Secrets and variables → Actions → New repository
   secret: name `HF_TOKEN`, value the token.
3. Push to `main`, or run the workflow by hand. The first run creates the Space.
4. Check https://huggingface.co/spaces/brghuggingface/brg-mcp: the status should be **Running**.

## Try it locally

```bash
uv run brg-mcp --data-root . --transport http --port 8000    # http://127.0.0.1:8000/mcp
docker build -t brg-mcp . && docker run -p 8000:8000 brg-mcp  # the deployed image
npx @modelcontextprotocol/inspector                           # connect to the URL, call the tools
```

The Claude API cannot reach `localhost`. Only the deployed Space works from the website.
