# Production image for the AI Nutrition Coach API.
FROM python:3.11-slim-bookworm

# uv is the project's package manager; copy its binary from the official image.
COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first so this layer is cached until the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Application source and migrations. Prompts live in app/services/ai/prompts.py,
# so no extra files are needed at runtime.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# Run as an unprivileged user.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Render injects $PORT; default to 8000 for local runs.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
