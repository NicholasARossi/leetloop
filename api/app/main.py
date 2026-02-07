"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, coaching, health, mastery, mission, objectives, onboarding, paths, progress, recommendations, reviews, submissions, system_design, today


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name} in {settings.environment} mode")
    yield
    # Shutdown
    print("Shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Backend API for LeetLoop - A systematic LeetCode learning coach",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(recommendations.router, prefix="/api", tags=["recommendations"])
    app.include_router(progress.router, prefix="/api", tags=["progress"])
    app.include_router(reviews.router, prefix="/api", tags=["reviews"])
    app.include_router(coaching.router, prefix="/api", tags=["coaching"])
    app.include_router(paths.router, prefix="/api", tags=["paths"])
    app.include_router(today.router, prefix="/api", tags=["today"])
    app.include_router(mastery.router, prefix="/api", tags=["mastery"])
    app.include_router(mission.router, prefix="/api", tags=["mission"])
    app.include_router(submissions.router, prefix="/api", tags=["submissions"])
    app.include_router(objectives.router, prefix="/api", tags=["objectives"])
    app.include_router(onboarding.router, prefix="/api", tags=["onboarding"])
    app.include_router(system_design.router, prefix="/api", tags=["system-design"])

    return app


app = create_app()
