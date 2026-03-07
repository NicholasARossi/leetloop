"""Daily Feed API endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.models.schemas import FocusNotesRequest, FocusNotesResponse
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


@router.get("/feed/{user_id}/notes")
async def get_focus_notes(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get user's focus notes for feed steering."""
    try:
        user_id_str = str(user_id)
        resp = (
            supabase.table("user_settings")
            .select("focus_notes, updated_at")
            .eq("user_id", user_id_str)
            .limit(1)
            .execute()
        )
        row = resp.data[0] if resp.data else {}
        return FocusNotesResponse(
            user_id=user_id,
            focus_notes=row.get("focus_notes"),
            updated_at=row.get("updated_at"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get focus notes: {str(e)}")


@router.put("/feed/{user_id}/notes")
async def update_focus_notes(
    user_id: UUID,
    request: FocusNotesRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Update user's focus notes for feed steering."""
    try:
        user_id_str = str(user_id)
        now = datetime.utcnow().isoformat()

        # Upsert into user_settings
        supabase.table("user_settings").upsert(
            {
                "user_id": user_id_str,
                "focus_notes": request.focus_notes,
                "updated_at": now,
            },
            on_conflict="user_id",
        ).execute()

        return FocusNotesResponse(
            user_id=user_id,
            focus_notes=request.focus_notes,
            updated_at=now,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update focus notes: {str(e)}")
