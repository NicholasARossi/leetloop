"""Mission Control API endpoints - Daily mission generation and tracking."""

import time
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from supabase import Client

from app.config import get_settings
from app.db.supabase import get_supabase
from app.models.schemas import (
    DailyMissionResponseV2,
    MissionProblem,
    Difficulty,
)
from app.services.mission_generator import MissionGenerator
from app.services.gemini_gateway import GeminiGateway
from app.utils import parse_iso_datetime

router = APIRouter()

# In-memory TTL cache for missions: {user_id_str: (expiry_timestamp, response)}
_mission_cache: dict[str, tuple[float, DailyMissionResponseV2]] = {}
_MISSION_CACHE_TTL = 300  # 5 minutes


def _parse_difficulty(diff: str | None) -> Difficulty | None:
    """Parse difficulty string to Difficulty enum."""
    if not diff:
        return None
    diff_lower = diff.lower()
    if diff_lower == "easy":
        return Difficulty.EASY
    elif diff_lower == "medium":
        return Difficulty.MEDIUM
    elif diff_lower == "hard":
        return Difficulty.HARD
    return None


def _build_mission_response(mission_data: dict) -> DailyMissionResponseV2:
    """Build DailyMissionResponseV2 from generator output."""
    problems = [
        MissionProblem(
            problem_id=p.get("problem_id", ""),
            problem_title=p.get("problem_title"),
            difficulty=_parse_difficulty(p.get("difficulty")),
            source=p.get("source", "path"),
            reasoning=p.get("reasoning", ""),
            priority=p.get("priority", 0),
            skills=p.get("skills", []),
            estimated_difficulty=p.get("estimated_difficulty"),
            completed=p.get("completed", False),
        )
        for p in mission_data.get("problems", [])
    ]

    generated_at = mission_data.get("generated_at", datetime.utcnow().isoformat())
    if isinstance(generated_at, str):
        generated_at = parse_iso_datetime(generated_at)

    return DailyMissionResponseV2(
        user_id=UUID(mission_data["user_id"]),
        mission_date=mission_data["mission_date"],
        daily_objective=mission_data.get("daily_objective") or mission_data.get("objective", {}).get("title", ""),
        problems=problems,
        balance_explanation=mission_data.get("balance_explanation"),
        pacing_status=mission_data.get("pacing_status"),
        pacing_note=mission_data.get("pacing_note"),
        streak=mission_data.get("streak", 0),
        total_completed_today=mission_data.get("total_completed_today", 0),
        can_regenerate=mission_data.get("can_regenerate", True),
        generated_at=generated_at,
    )


@router.get("/mission/{user_id}", response_model=DailyMissionResponseV2)
async def get_daily_mission(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Get today's daily mission for a user.

    If no mission exists for today, generates one on-demand.

    Returns:
        DailyMissionResponseV2 with problems and Gemini reasoning
    """
    cache_key = str(user_id)
    cached = _mission_cache.get(cache_key)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    try:
        gemini = GeminiGateway()
        generator = MissionGenerator(supabase, gemini)

        mission_data = await generator.generate_mission(user_id)
        response = _build_mission_response(mission_data)
        _mission_cache[cache_key] = (time.monotonic() + _MISSION_CACHE_TTL, response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get mission: {str(e)}")


@router.post("/mission/{user_id}/regenerate", response_model=DailyMissionResponseV2)
async def regenerate_mission(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Regenerate today's mission for a user.

    Limited to 3 regenerations per day.

    Returns:
        DailyMissionResponseV2 with new problems and reasoning
    """
    cache_key = str(user_id)
    _mission_cache.pop(cache_key, None)

    try:
        gemini = GeminiGateway()
        generator = MissionGenerator(supabase, gemini)

        mission_data = await generator.generate_mission(user_id, force_regenerate=True)
        response = _build_mission_response(mission_data)
        _mission_cache[cache_key] = (time.monotonic() + _MISSION_CACHE_TTL, response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate mission: {str(e)}")


@router.delete("/mission/{user_id}/reset")
async def reset_daily_mission(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Delete today's mission to allow fresh generation.

    Useful when a mission is in a bad state.
    """
    _mission_cache.pop(str(user_id), None)

    try:
        # Use RPC function to bypass RLS
        result = supabase.rpc(
            "reset_daily_mission",
            {"p_user_id": str(user_id)}
        ).execute()

        # RPC returns the JSONB result directly
        if result.data:
            return dict(result.data)

        return {"success": True, "message": "Mission reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset mission: {str(e)}")


@router.post("/mission/generate-all")
async def generate_all_missions(
    supabase: Annotated[Client, Depends(get_supabase)] = None,
    x_cron_secret: Annotated[str | None, Header()] = None,
):
    """
    Generate missions for all active users.

    This endpoint is intended to be called by a cron job.
    Requires X-Cron-Secret header for authentication.

    Returns:
        Summary of generation results
    """
    settings = get_settings()

    # Validate cron secret if configured
    if settings.cron_secret:
        if not x_cron_secret or x_cron_secret != settings.cron_secret:
            raise HTTPException(status_code=401, detail="Invalid or missing cron secret")

    try:
        gemini = GeminiGateway()
        generator = MissionGenerator(supabase, gemini)

        results = await generator.generate_all_missions()

        return {
            "success": True,
            "generated": results["generated"],
            "skipped": results["skipped"],
            "failed": results["failed"],
            "total_users": results.get("total_users", 0),
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate missions: {str(e)}")
