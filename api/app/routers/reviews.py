"""Review queue endpoints for spaced repetition."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.models.schemas import ReviewCompleteRequest, ReviewCompleteResponse, ReviewItem

router = APIRouter()


@router.get("/reviews/{user_id}", response_model=list[ReviewItem])
async def get_due_reviews(
    user_id: UUID,
    limit: int = 10,
    include_future: bool = False,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Get problems due for review.

    By default, only returns items where next_review <= now.
    Set include_future=True to get all queued items.
    """
    try:
        # Use RPC function for due reviews
        if not include_future:
            response = supabase.rpc(
                "get_due_reviews",
                {"p_user_id": str(user_id), "p_limit": limit}
            ).execute()
        else:
            response = (
                supabase.table("review_queue")
                .select("*")
                .eq("user_id", str(user_id))
                .order("priority", desc=True)
                .order("next_review")
                .limit(limit)
                .execute()
            )

        return [ReviewItem(**r) for r in response.data] if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reviews: {str(e)}")


@router.get("/reviews/{user_id}/count")
async def get_review_count(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get count of reviews due now."""
    try:
        response = (
            supabase.table("review_queue")
            .select("id", count="exact")
            .eq("user_id", str(user_id))
            .lte("next_review", datetime.utcnow().isoformat())
            .execute()
        )
        return {"count": response.count or 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get review count: {str(e)}")


@router.post("/reviews/{review_id}/complete", response_model=ReviewCompleteResponse)
async def complete_review(
    review_id: UUID,
    request: ReviewCompleteRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Mark a review as complete.

    If success=True, the interval doubles (up to 30 days).
    If success=False, the interval resets to 1 day.
    """
    try:
        # Use the RPC function
        response = supabase.rpc(
            "complete_review",
            {"p_review_id": str(review_id), "p_success": request.success}
        ).execute()

        # Get updated review item
        updated = (
            supabase.table("review_queue")
            .select("*")
            .eq("id", str(review_id))
            .single()
            .execute()
        )

        if not updated.data:
            raise HTTPException(status_code=404, detail="Review not found")

        return ReviewCompleteResponse(
            id=review_id,
            next_review=updated.data["next_review"],
            new_interval_days=updated.data["interval_days"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete review: {str(e)}")


@router.delete("/reviews/{review_id}")
async def delete_review(
    review_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Remove a problem from the review queue."""
    try:
        response = (
            supabase.table("review_queue")
            .delete()
            .eq("id", str(review_id))
            .execute()
        )
        return {"success": True, "deleted_id": str(review_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete review: {str(e)}")


@router.post("/reviews/{user_id}/add")
async def add_to_review_queue(
    user_id: UUID,
    problem_slug: str,
    problem_title: str = None,
    reason: str = "Manual addition",
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Manually add a problem to the review queue."""
    try:
        response = (
            supabase.table("review_queue")
            .insert({
                "user_id": str(user_id),
                "problem_slug": problem_slug,
                "problem_title": problem_title,
                "reason": reason,
                "next_review": datetime.utcnow().isoformat(),
                "interval_days": 1,
            })
            .execute()
        )

        if response.data:
            return ReviewItem(**response.data[0])
        raise HTTPException(status_code=500, detail="Failed to add to review queue")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add review: {str(e)}")
