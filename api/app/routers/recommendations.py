"""Recommendation endpoints for personalized problem suggestions."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.models.schemas import RecommendationResponse, RecommendedProblem
from app.services.recommendation_engine import RecommendationEngine

router = APIRouter()


@router.get("/recommendations/{user_id}", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: UUID,
    limit: int = 5,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Get personalized problem recommendations for a user.

    Recommendations are based on:
    1. Problems in the spaced repetition review queue (highest priority)
    2. Problems targeting weak skill areas
    3. Natural difficulty progression
    """
    engine = RecommendationEngine(supabase)

    try:
        recommendations = await engine.get_recommendations(user_id, limit=limit)
        weak_areas = await engine.get_weak_areas(user_id)

        return RecommendationResponse(
            user_id=user_id,
            recommendations=recommendations,
            weak_areas=weak_areas,
            generated_at=datetime.utcnow(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")


@router.get("/recommendations/{user_id}/next", response_model=RecommendedProblem)
async def get_next_problem(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get the single highest priority problem for the user to work on next."""
    engine = RecommendationEngine(supabase)

    try:
        recommendations = await engine.get_recommendations(user_id, limit=1)
        if not recommendations:
            raise HTTPException(status_code=404, detail="No recommendations available")
        return recommendations[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get next problem: {str(e)}")
