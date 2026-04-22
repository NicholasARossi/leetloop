"""Life Ops endpoints — daily checklist tracking with categories, recurrence, and streaks."""

import time
from datetime import date, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.models.lifeops_schemas import (
    ChecklistResponse,
    CompletionRate,
    CreateCategoryRequest,
    CreateTaskRequest,
    LifeOpsCategory,
    LifeOpsDailyItem,
    LifeOpsStats,
    LifeOpsStreak,
    LifeOpsTask,
    ToggleItemResponse,
    UpdateCategoryRequest,
    UpdateTaskRequest,
)
from app.services.lifeops_service import (
    compute_completion_rates,
    compute_streak,
    generate_daily_items,
)

router = APIRouter()

# In-memory TTL cache for stats
_stats_cache: dict[str, tuple[float, LifeOpsStats]] = {}
_STATS_CACHE_TTL = 300  # 5 minutes


# ============ Categories ============


@router.get("/life-ops/{user_id}/categories", response_model=list[LifeOpsCategory])
async def list_categories(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """List all categories for a user."""
    try:
        response = (
            supabase.table("lifeops_categories")
            .select("*")
            .eq("user_id", str(user_id))
            .order("sort_order")
            .order("name")
            .execute()
        )
        return [LifeOpsCategory(**c) for c in response.data] if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list categories: {str(e)}")


@router.post("/life-ops/{user_id}/categories", response_model=LifeOpsCategory)
async def create_category(
    user_id: UUID,
    request: CreateCategoryRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Create a new category."""
    try:
        response = (
            supabase.table("lifeops_categories")
            .insert({
                "user_id": str(user_id),
                "name": request.name,
                "color": request.color,
                "sort_order": request.sort_order,
            })
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create category")
        return LifeOpsCategory(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create category: {str(e)}")


@router.put("/life-ops/categories/{category_id}", response_model=LifeOpsCategory)
async def update_category(
    category_id: UUID,
    request: UpdateCategoryRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Update an existing category."""
    try:
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        response = (
            supabase.table("lifeops_categories")
            .update(updates)
            .eq("id", str(category_id))
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Category not found")
        return LifeOpsCategory(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update category: {str(e)}")


@router.delete("/life-ops/categories/{category_id}")
async def delete_category(
    category_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Delete a category (cascades to tasks and daily items)."""
    try:
        supabase.table("lifeops_categories").delete().eq("id", str(category_id)).execute()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete category: {str(e)}")


# ============ Tasks ============


@router.get("/life-ops/{user_id}/tasks", response_model=list[LifeOpsTask])
async def list_tasks(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """List all task definitions for a user."""
    try:
        response = (
            supabase.table("lifeops_tasks")
            .select("*")
            .eq("user_id", str(user_id))
            .order("sort_order")
            .order("title")
            .execute()
        )
        return [LifeOpsTask(**t) for t in response.data] if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@router.post("/life-ops/{user_id}/tasks", response_model=LifeOpsTask)
async def create_task(
    user_id: UUID,
    request: CreateTaskRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Create a new task definition."""
    try:
        response = (
            supabase.table("lifeops_tasks")
            .insert({
                "user_id": str(user_id),
                "category_id": str(request.category_id),
                "title": request.title,
                "description": request.description,
                "recurrence_days": request.recurrence_days,
                "sort_order": request.sort_order,
            })
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create task")
        return LifeOpsTask(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.put("/life-ops/tasks/{task_id}", response_model=LifeOpsTask)
async def update_task(
    task_id: UUID,
    request: UpdateTaskRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Update an existing task definition."""
    try:
        updates = {}
        for k, v in request.model_dump().items():
            if v is not None:
                if k == "category_id":
                    updates[k] = str(v)
                else:
                    updates[k] = v
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        response = (
            supabase.table("lifeops_tasks")
            .update(updates)
            .eq("id", str(task_id))
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Task not found")
        return LifeOpsTask(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")


@router.delete("/life-ops/tasks/{task_id}")
async def delete_task(
    task_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Delete a task definition (cascades to daily items)."""
    try:
        supabase.table("lifeops_tasks").delete().eq("id", str(task_id)).execute()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")


# ============ Checklist ============


@router.get("/life-ops/{user_id}/checklist", response_model=ChecklistResponse)
async def get_checklist(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get today's checklist, generating items if needed."""
    return await _get_or_generate_checklist(user_id, date.today(), supabase)


@router.get("/life-ops/{user_id}/checklist/{checklist_date}", response_model=ChecklistResponse)
async def get_checklist_for_date(
    user_id: UUID,
    checklist_date: date,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get checklist for a specific date, generating items if needed."""
    return await _get_or_generate_checklist(user_id, checklist_date, supabase)


async def _get_or_generate_checklist(
    user_id: UUID,
    target_date: date,
    supabase: Client,
) -> ChecklistResponse:
    """Get existing daily items or generate them for the target date."""
    uid = str(user_id)

    try:
        # Check for existing items
        existing = (
            supabase.table("lifeops_daily_items")
            .select("*")
            .eq("user_id", uid)
            .eq("checklist_date", target_date.isoformat())
            .order("sort_order")
            .execute()
        )

        if existing.data:
            items = [LifeOpsDailyItem(**item) for item in existing.data]
            completed = sum(1 for item in items if item.is_completed)
            return ChecklistResponse(
                user_id=user_id,
                checklist_date=target_date,
                items=items,
                completed_count=completed,
                total_count=len(items),
            )

        # Generate items from task definitions
        tasks_resp = (
            supabase.table("lifeops_tasks")
            .select("*")
            .eq("user_id", uid)
            .eq("is_active", True)
            .execute()
        )
        tasks = tasks_resp.data or []

        cats_resp = (
            supabase.table("lifeops_categories")
            .select("*")
            .eq("user_id", uid)
            .execute()
        )
        categories = {c["id"]: c for c in (cats_resp.data or [])}

        new_items = generate_daily_items(tasks, categories, uid, target_date)

        if not new_items:
            return ChecklistResponse(
                user_id=user_id,
                checklist_date=target_date,
                items=[],
                completed_count=0,
                total_count=0,
            )

        # Insert in batch
        inserted = (
            supabase.table("lifeops_daily_items")
            .insert(new_items)
            .execute()
        )

        items = [LifeOpsDailyItem(**item) for item in (inserted.data or [])]
        return ChecklistResponse(
            user_id=user_id,
            checklist_date=target_date,
            items=items,
            completed_count=0,
            total_count=len(items),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get checklist: {str(e)}")


# ============ Toggle ============


@router.post("/life-ops/items/{item_id}/toggle", response_model=ToggleItemResponse)
async def toggle_item(
    item_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Toggle a checklist item's completion status."""
    try:
        # Fetch current state
        current = (
            supabase.table("lifeops_daily_items")
            .select("id, is_completed, user_id, checklist_date")
            .eq("id", str(item_id))
            .limit(1)
            .execute()
        )

        if not current.data:
            raise HTTPException(status_code=404, detail="Item not found")

        item = current.data[0]
        new_completed = not item["is_completed"]
        now = datetime.utcnow().isoformat() if new_completed else None

        updated = (
            supabase.table("lifeops_daily_items")
            .update({
                "is_completed": new_completed,
                "completed_at": now,
            })
            .eq("id", str(item_id))
            .execute()
        )

        if not updated.data:
            raise HTTPException(status_code=500, detail="Failed to toggle item")

        result = updated.data[0]

        # Update streak in background (best-effort)
        try:
            await _update_streak(item["user_id"], supabase)
        except Exception:
            pass  # Non-critical

        # Invalidate stats cache
        _stats_cache.pop(item["user_id"], None)

        return ToggleItemResponse(
            id=result["id"],
            is_completed=result["is_completed"],
            completed_at=result.get("completed_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle item: {str(e)}")


async def _update_streak(user_id: str, supabase: Client) -> None:
    """Update streak data after a toggle."""
    today = date.today()
    # Fetch last 30 days of items for streak calculation
    start_date = (today - timedelta(days=30)).isoformat()

    items_resp = (
        supabase.table("lifeops_daily_items")
        .select("checklist_date, is_completed")
        .eq("user_id", user_id)
        .gte("checklist_date", start_date)
        .execute()
    )

    items_by_date: dict[str, list[dict]] = {}
    for item in (items_resp.data or []):
        d = item["checklist_date"]
        items_by_date.setdefault(d, []).append(item)

    # Get existing streak
    streak_resp = (
        supabase.table("lifeops_streaks")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    existing_streak = streak_resp.data[0] if streak_resp.data else None

    new_streak = compute_streak(items_by_date, existing_streak)

    # Count perfect days from fetched data
    perfect_days = 0
    for d_items in items_by_date.values():
        if d_items and all(item.get("is_completed", False) for item in d_items):
            perfect_days += 1
    new_streak["total_perfect_days"] = perfect_days

    last_date = new_streak.get("last_completed_date")
    streak_data = {
        "user_id": user_id,
        "current_streak": new_streak["current_streak"],
        "longest_streak": new_streak["longest_streak"],
        "last_completed_date": last_date.isoformat() if isinstance(last_date, date) else last_date,
        "total_perfect_days": new_streak["total_perfect_days"],
        "updated_at": datetime.utcnow().isoformat(),
    }

    if existing_streak:
        supabase.table("lifeops_streaks").update(streak_data).eq("user_id", user_id).execute()
    else:
        supabase.table("lifeops_streaks").insert(streak_data).execute()


# ============ Stats ============


@router.get("/life-ops/{user_id}/stats", response_model=LifeOpsStats)
async def get_stats(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get streak, weekly/monthly completion rates."""
    uid = str(user_id)

    # Check cache
    cached = _stats_cache.get(uid)
    if cached:
        timestamp, stats = cached
        if time.monotonic() - timestamp < _STATS_CACHE_TTL:
            return stats

    try:
        # Fetch last 90 days of items
        today = date.today()
        start_date = (today - timedelta(days=90)).isoformat()

        items_resp = (
            supabase.table("lifeops_daily_items")
            .select("checklist_date, is_completed")
            .eq("user_id", uid)
            .gte("checklist_date", start_date)
            .execute()
        )

        items_by_date: dict[str, list[dict]] = {}
        for item in (items_resp.data or []):
            d = item["checklist_date"]
            items_by_date.setdefault(d, []).append(item)

        # Streak
        streak_resp = (
            supabase.table("lifeops_streaks")
            .select("*")
            .eq("user_id", uid)
            .limit(1)
            .execute()
        )
        existing_streak = streak_resp.data[0] if streak_resp.data else None
        streak_data = compute_streak(items_by_date, existing_streak)

        # Completion rates
        weekly_rates, monthly_rates = compute_completion_rates(items_by_date)

        # Today
        today_items = items_by_date.get(today.isoformat(), [])
        today_completed = sum(1 for item in today_items if item.get("is_completed", False))
        today_total = len(today_items)

        stats = LifeOpsStats(
            streak=LifeOpsStreak(**streak_data),
            weekly_rates=[CompletionRate(**r) for r in weekly_rates],
            monthly_rates=[CompletionRate(**r) for r in monthly_rates],
            today_completed=today_completed,
            today_total=today_total,
        )

        _stats_cache[uid] = (time.monotonic(), stats)
        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
