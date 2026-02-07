"""Progress and statistics endpoints."""

from datetime import datetime, timedelta
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.auth import AuthenticatedUser, get_current_user
from app.db.supabase import get_supabase
from app.models.schemas import (
    ProgressTrend,
    SkillScore,
    Submission,
    UserProgress,
    UserStats,
)

router = APIRouter()


@router.get("/progress/me/stats", response_model=UserStats)
async def get_my_stats(
    user: AuthenticatedUser = Depends(get_current_user),
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get stats for the authenticated user (from JWT)."""
    user_id = UUID(user.id)
    return await get_user_stats(user_id, supabase)


@router.get("/progress/{user_id}", response_model=UserProgress)
async def get_user_progress(
    user_id: UUID,
    days: int = Query(default=30, ge=1, le=365, description="Number of days for trend data"),
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Get comprehensive progress data for a user.

    Includes:
    - Aggregated statistics
    - Skill scores by tag
    - Submission trends over time
    - Recent submissions
    """
    try:
        # Get user stats from RPC function
        stats_response = supabase.rpc("get_user_stats", {"p_user_id": str(user_id)}).execute()
        stats_data = stats_response.data[0] if stats_response.data else {}

        # Get reviews due count
        reviews_response = (
            supabase.table("review_queue")
            .select("id", count="exact")
            .eq("user_id", str(user_id))
            .lte("next_review", datetime.utcnow().isoformat())
            .execute()
        )
        reviews_due = reviews_response.count or 0

        stats = UserStats(
            total_submissions=stats_data.get("total_submissions") or 0,
            accepted_count=stats_data.get("accepted_count") or 0,
            failed_count=stats_data.get("failed_count") or 0,
            success_rate=stats_data.get("success_rate") or 0.0,
            problems_solved=stats_data.get("problems_solved") or 0,
            problems_attempted=stats_data.get("problems_attempted") or 0,
            streak_days=stats_data.get("streak_days") or 0,
            reviews_due=reviews_due,
        )

        # Get skill scores
        skill_response = (
            supabase.table("skill_scores")
            .select("*")
            .eq("user_id", str(user_id))
            .order("score", desc=False)
            .execute()
        )
        skill_scores = [SkillScore(**s) for s in skill_response.data] if skill_response.data else []

        # Get submission trends
        start_date = datetime.utcnow() - timedelta(days=days)
        trends = await _get_submission_trends(supabase, user_id, start_date)

        # Get recent submissions
        recent_response = (
            supabase.table("submissions")
            .select("*")
            .eq("user_id", str(user_id))
            .order("submitted_at", desc=True)
            .limit(10)
            .execute()
        )
        recent_submissions = [Submission(**s) for s in recent_response.data] if recent_response.data else []

        return UserProgress(
            stats=stats,
            skill_scores=skill_scores,
            trends=trends,
            recent_submissions=recent_submissions,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@router.get("/progress/{user_id}/stats", response_model=UserStats)
async def get_user_stats(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get just the aggregated statistics for a user."""
    try:
        stats_response = supabase.rpc("get_user_stats", {"p_user_id": str(user_id)}).execute()
        stats_data = stats_response.data[0] if stats_response.data else {}

        # Get reviews due count
        reviews_response = (
            supabase.table("review_queue")
            .select("id", count="exact")
            .eq("user_id", str(user_id))
            .lte("next_review", datetime.utcnow().isoformat())
            .execute()
        )
        reviews_due = reviews_response.count or 0

        return UserStats(
            total_submissions=stats_data.get("total_submissions") or 0,
            accepted_count=stats_data.get("accepted_count") or 0,
            failed_count=stats_data.get("failed_count") or 0,
            success_rate=stats_data.get("success_rate") or 0.0,
            problems_solved=stats_data.get("problems_solved") or 0,
            problems_attempted=stats_data.get("problems_attempted") or 0,
            streak_days=stats_data.get("streak_days") or 0,
            reviews_due=reviews_due,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/progress/{user_id}/skills", response_model=list[SkillScore])
async def get_skill_scores(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get skill scores for all tags the user has attempted."""
    try:
        response = (
            supabase.table("skill_scores")
            .select("*")
            .eq("user_id", str(user_id))
            .order("score", desc=False)
            .execute()
        )
        return [SkillScore(**s) for s in response.data] if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get skill scores: {str(e)}")


@router.get("/submissions/{user_id}", response_model=list[Submission])
async def get_submissions(
    user_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = None,
    difficulty: Optional[str] = None,
    tag: Optional[str] = None,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get paginated submission history with optional filters."""
    try:
        query = (
            supabase.table("submissions")
            .select("*")
            .eq("user_id", str(user_id))
        )

        if status:
            query = query.eq("status", status)
        if difficulty:
            query = query.eq("difficulty", difficulty)
        if tag:
            query = query.contains("tags", [tag])

        response = (
            query
            .order("submitted_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return [Submission(**s) for s in response.data] if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get submissions: {str(e)}")


async def _get_submission_trends(
    supabase: Client,
    user_id: UUID,
    start_date: datetime,
) -> list[ProgressTrend]:
    """Calculate daily submission trends from start_date to now."""
    try:
        response = (
            supabase.table("submissions")
            .select("submitted_at, status")
            .eq("user_id", str(user_id))
            .gte("submitted_at", start_date.isoformat())
            .order("submitted_at")
            .execute()
        )

        if not response.data:
            return []

        # Aggregate by day
        daily_data: dict[str, dict] = {}
        for sub in response.data:
            date = sub["submitted_at"][:10]  # YYYY-MM-DD
            if date not in daily_data:
                daily_data[date] = {"submissions": 0, "accepted": 0}
            daily_data[date]["submissions"] += 1
            if sub["status"] == "Accepted":
                daily_data[date]["accepted"] += 1

        trends = []
        for date, data in sorted(daily_data.items()):
            success_rate = data["accepted"] / data["submissions"] if data["submissions"] > 0 else 0
            trends.append(
                ProgressTrend(
                    date=date,
                    submissions=data["submissions"],
                    accepted=data["accepted"],
                    success_rate=round(success_rate, 2),
                )
            )

        return trends
    except Exception:
        return []
