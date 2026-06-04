# syntax=docker/dockerfile:1.7

FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

COPY pyproject.toml uv.lock ./
COPY src ./src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH=/app/.venv/bin:$PATH \
    RAG_MCP_HOST=0.0.0.0 \
    RAG_MCP_PORT=8010

WORKDIR /app

RUN groupadd --system app && \
    useradd --system --gid app --home-dir /app app && \
    mkdir -p /app/workspace /app/input /app/output /app/cache && \
    chown -R app:app /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app src ./src

USER app

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/health', timeout=3).read()"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8010"]
