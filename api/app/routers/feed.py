"""Daily Feed API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.services.feed_generator import FeedGenerator

router = APIRouter()


@router.get("/feed/{user_id}")
async def get_daily_feed(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get today's problem feed. Generates on-demand if needed."""
    try:
        generator = FeedGenerator(supabase)
        return await generator.get_or_generate_feed(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feed: {str(e)}")


@router.post("/feed/{user_id}/regenerate")
async def regenerate_feed(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Regenerate pending feed items."""
    try:
        generator = FeedGenerator(supabase)
        return await generator.regenerate_feed(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate feed: {str(e)}")


@router.post("/feed/{user_id}/extend")
async def extend_feed(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Add more problems to today's feed."""
    try:
        generator = FeedGenerator(supabase)
        return await generator.extend_feed(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extend feed: {str(e)}")
