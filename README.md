# AI-Nutrition-Coach

AI-powered calorie tracker that estimates nutrition from food images and
natural language using OpenAI models. This repository currently contains the
**backend** (FastAPI). The frontend will be added later.

## Tech Stack (Backend)

FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL · Alembic · Pydantic v2 · uv

## Architecture

Layered: **API → Service → Repository → Database**. Routers only validate input,
call services, and return responses. Business logic lives in services; database
access is confined to repositories.

```
app/
  core/          # config, logging, database engine + session
  api/routes/    # HTTP routers
  services/      # business logic (added per feature)
  repositories/  # database access (added per feature)
  models/        # SQLAlchemy ORM models (added per feature)
  schemas/       # Pydantic DTOs (added per feature)
```

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- A running PostgreSQL instance with the target database created

## Setup

```bash
# 1. Install dependencies (creates .venv and resolves the lockfile)
uv sync

# 2. Configure environment
cp .env.example .env
# then edit .env and set DATABASE_URL to your PostgreSQL instance
```

## Running

```bash
# Start the API with autoreload
uv run uvicorn app.main:app --reload

# Health check (verifies DB connectivity)
# GET http://127.0.0.1:8000/health -> {"status":"ok","db":"ok"}
```

## Development

```bash
uv run pytest        # run tests
uv run ruff check .  # lint
uv run ruff format . # format
uv run mypy app      # type-check
```

## Database Migrations

Alembic is configured against the async engine and reads `DATABASE_URL` from the
environment.

```bash
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
```

## Docker

The production image is built with `uv` and honours `uv.lock` exactly.

```bash
# Build
docker build -t ai-nutrition-coach .

# Run against a PostgreSQL instance on the host
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgresql://postgres:root@host.docker.internal:5432/ai-nutrition-coach" \
  -e JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')" \
  -e APP_ENV=production \
  ai-nutrition-coach
```

## Deployment (Render)

`render.yaml` is a Blueprint describing the web service and a managed PostgreSQL
database.

1. Push this repository to GitHub.
2. Render Dashboard → **New → Blueprint** → select the repository. Render reads
   `render.yaml`, creates the web service and the database, and wires `DATABASE_URL`
   automatically.
3. Set the secrets marked `sync: false` in the service's **Environment** tab:
   - `JWT_SECRET_KEY` — generate a fresh one, **do not reuse the development value**:
     `python -c "import secrets; print(secrets.token_urlsafe(48))"`
   - `CORS_ORIGINS` — the frontend origin, e.g. `https://your-app.vercel.app`
   - `OPENAI_API_KEY` — optional; without it the AI endpoints return 503 and the rest
     of the API works normally.
4. Deploy. `alembic upgrade head` runs as the pre-deploy command, and Render probes
   `/health` (which verifies database connectivity) before shifting traffic.

Notes:

- Render's `DATABASE_URL` uses the `postgres://` scheme; the app rewrites it to
  `postgresql+asyncpg://` automatically.
- If your plan does not support `preDeployCommand`, remove it from `render.yaml` and
  run `alembic upgrade head` once from the Render shell after the first deploy.
- If the managed database requires TLS, append `?ssl=require` to `DATABASE_URL`.
