# The BRG MCP server over Streamable HTTP, for clients that cannot start it locally (the CAS website's
# BRG terminal, through the Claude API's MCP connector). Deployed on Render (render.yaml, deploy/README.md).
#   docker build -t brg-mcp . && docker run -p 8000:8000 brg-mcp   # then http://localhost:8000/mcp
# Only the server's packages: the terminal's (`uv run brg`, a default dependency group) stay out, and so do
# uv and its download cache, which are needed to build the environment, not to run it.
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_CACHE=1
COPY pyproject.toml uv.lock README.md ./
COPY src src
COPY skills skills
RUN uv sync --locked --no-dev --no-default-groups --no-editable

FROM python:3.12-slim
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
# content last: a change to the knowledge rebuilds only this layer
COPY config config
COPY knowledge knowledge
EXPOSE 8000
CMD ["/app/.venv/bin/brg-mcp", "--data-root", "/app", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
