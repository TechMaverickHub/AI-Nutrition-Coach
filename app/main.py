"""FastAPI application factory."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    ai,
    analytics,
    auth,
    coach,
    dashboard,
    goal,
    health,
    meal,
    user,
)
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.exceptions import AppError


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="AI Nutrition Coach API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(user.router)
    app.include_router(meal.router)
    app.include_router(dashboard.router)
    app.include_router(goal.router)
    app.include_router(ai.router)
    app.include_router(coach.router)
    app.include_router(analytics.router)
    return app


app = create_app()
