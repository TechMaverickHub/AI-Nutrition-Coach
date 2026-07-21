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
environment. Domain models and the first migration are added in a later task.

```bash
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
```
