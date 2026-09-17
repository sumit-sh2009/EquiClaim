# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

# uv is statically linked; copying the published binary is faster and more
# reproducible than `pip install uv` inside the image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install dependencies first (separate layer) so app-code edits don't bust
# the dependency cache.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

RUN useradd --create-home --uid 1000 equiclaim \
    && mkdir -p /app/data/uploads \
    && chown -R equiclaim:equiclaim /app
USER equiclaim

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

# Migrations run inside the FastAPI lifespan on startup (see app/main.py),
# so no separate migrate-then-serve entrypoint is required.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
