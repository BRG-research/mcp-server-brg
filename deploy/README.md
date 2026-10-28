# Remote server

The CAS website's BRG terminal (`Teaching/CAS/website/library.html#/terminal`) cannot start a local
stdio server, so this one runs on Render's free plan. Claude reaches it through the Claude API's MCP
connector. It is the same server with the same tools as `uv run brg-mcp`. There is no second copy of the
tools on the website.

```
git push (main) ──▶ GitHub Action: tests ──pass──▶ calls Render's deploy hook ──▶ Render builds the Dockerfile
                                                      https://brg-mcp.onrender.com/mcp
```

- `Dockerfile` (repository root) runs `brg-mcp --transport http` with `config/` and `knowledge/`.
  The server is stateless and read-only. Books are read live from the public R2 bucket, so a newly
  published book needs no deploy.
- `render.yaml` (repository root) describes the service: Docker, free plan, no deploy of its own.
- `.github/workflows/tests.yml` runs the tests on every push; on `main`, when they pass, it calls Render's
  deploy hook (repository secret `RENDER_DEPLOY_HOOK`), so every push to `main` is deployed.
- A free service sleeps after 15 minutes without requests. The next request wakes it in about a minute.
  The website pings the server when the library page opens, so it is usually awake before the first
  question.

## Set up once

1. render.com → sign in with GitHub, and give Render access to `BRG-research/mcp-server-brg`.
2. New → Blueprint → choose the repository → Apply. Render reads `render.yaml` and builds the server.
3. Render → brg-mcp → Settings → Deploy: set **Auto-Deploy** to **Off**, and copy the **Deploy Hook** link.
   GitHub → mcp-server-brg → Settings → Secrets and variables → Actions → New repository secret:
   name `RENDER_DEPLOY_HOOK`, value the link. Keep it private: anyone with it can start a deploy.
4. The service page shows its address. If it is not `https://brg-mcp.onrender.com`, put that address
   plus `/mcp` into `Teaching/CAS/website/library-config.js` (`mcpEndpoint`) and
   `Teaching/CAS/brg-terminal-ai/wrangler.toml` (`MCP_URL`).

## Try it locally

```bash
uv run brg-mcp --data-root . --transport http --port 8000    # http://127.0.0.1:8000/mcp
docker build -t brg-mcp . && docker run -p 8000:8000 brg-mcp  # the deployed image
npx @modelcontextprotocol/inspector                           # connect to the URL, call the tools
```

The Claude API cannot reach `localhost`. Only the deployed server works from the website.
