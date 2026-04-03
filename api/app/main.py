"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, coaching, feed, health, language, mastery, mission, ml_coding, onboarding, onsite_prep, paths, progress, recommendations, reviews, submissions, system_design, today, winrate


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name} in {settings.environment} mode")

    # Initialize Telegram bot if configured
    bot_app = None
    if settings.telegram_bot_token:
        try:
            from app.services.telegram_bot import get_bot_application
            bot_app = get_bot_application()
            if bot_app:
                await bot_app.initialize()
                print("Telegram bot initialized")
        except Exception as e:
            print(f"Telegram bot init failed (non-fatal): {e}")

    yield

    # Shutdown
    if bot_app:
        try:
            await bot_app.shutdown()
        except Exception:
            pass
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
    app.include_router(winrate.router, prefix="/api", tags=["winrate"])
    app.include_router(feed.router, prefix="/api", tags=["feed"])
    app.include_router(onboarding.router, prefix="/api", tags=["onboarding"])
    app.include_router(system_design.router, prefix="/api", tags=["system-design"])
    app.include_router(language.router, prefix="/api", tags=["language"])
    app.include_router(ml_coding.router, prefix="/api", tags=["ml-coding"])
    app.include_router(onsite_prep.router, prefix="/api", tags=["onsite-prep"])

    return app


app = create_app()
