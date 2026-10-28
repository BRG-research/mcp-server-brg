# The BRG MCP server over Streamable HTTP, for clients that cannot start it locally (the CAS website's
# BRG terminal, through the Claude API's MCP connector). Deployed as a Hugging Face Space (deploy/huggingface).
#   docker build -t brg-mcp . && docker run -p 8000:8000 brg-mcp   # then http://localhost:8000/mcp
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock README.md ./
COPY src src
COPY skills skills
RUN uv sync --locked --no-dev
# content last: a change to the knowledge rebuilds only this layer
COPY config config
COPY knowledge knowledge
EXPOSE 8000
CMD ["/app/.venv/bin/brg-mcp", "--data-root", "/app", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
