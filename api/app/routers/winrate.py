"""Win Rate API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.models.winrate_schemas import SetWinRateTargetsRequest, WinRateTargets
from app.services.win_rate_service import WinRateService

router = APIRouter()


@router.get("/winrate/{user_id}/targets")
async def get_targets(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get user's win rate targets."""
    try:
        service = WinRateService(supabase)
        targets = service.get_targets(user_id)
        if not targets:
            return {"targets": None}
        return targets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get targets: {str(e)}")


@router.post("/winrate/{user_id}/targets")
async def set_targets(
    user_id: UUID,
    request: SetWinRateTargetsRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Create or update win rate targets."""
    try:
        service = WinRateService(supabase)
        targets = service.set_targets(user_id, request)
        return targets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set targets: {str(e)}")


@router.get("/winrate/{user_id}/stats")
async def get_stats(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get full win rate stats including targets, current rates, and trend."""
    try:
        service = WinRateService(supabase)
        return service.get_stats(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
