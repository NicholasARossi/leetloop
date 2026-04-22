"""Pydantic schemas for Life Ops feature."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============ Category Models ============


class CreateCategoryRequest(BaseModel):
    """Request to create a new category."""

    name: str
    color: str = "#6B7280"
    sort_order: int = 0


class UpdateCategoryRequest(BaseModel):
    """Request to update a category."""

    name: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None


class LifeOpsCategory(BaseModel):
    """A task category (e.g., Fitness, Chores, Quality Time)."""

    id: UUID
    user_id: UUID
    name: str
    color: str = "#6B7280"
    sort_order: int = 0
    created_at: Optional[datetime] = None


# ============ Task Models ============


class CreateTaskRequest(BaseModel):
    """Request to create a new task definition."""

    category_id: UUID
    title: str
    description: Optional[str] = None
    recurrence_days: int = Field(default=127, ge=0, le=127)  # bitmask Mon-Sun
    sort_order: int = 0


class UpdateTaskRequest(BaseModel):
    """Request to update a task definition."""

    category_id: Optional[UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    recurrence_days: Optional[int] = Field(default=None, ge=0, le=127)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class LifeOpsTask(BaseModel):
    """A recurring task definition."""

    id: UUID
    user_id: UUID
    category_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    recurrence_days: int = 127
    sort_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None


# ============ Daily Item Models ============


class LifeOpsDailyItem(BaseModel):
    """A materialized daily checklist item."""

    id: UUID
    user_id: UUID
    task_id: Optional[UUID] = None
    checklist_date: date
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    sort_order: int = 0
    task_title: str
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None


class ToggleItemResponse(BaseModel):
    """Response after toggling a checklist item."""

    id: UUID
    is_completed: bool
    completed_at: Optional[datetime] = None


# ============ Checklist Models ============


class ChecklistResponse(BaseModel):
    """Today's (or a date's) checklist grouped by category."""

    user_id: UUID
    checklist_date: date
    items: list[LifeOpsDailyItem] = []
    completed_count: int = 0
    total_count: int = 0


# ============ Streak Models ============


class LifeOpsStreak(BaseModel):
    """User streak data."""

    current_streak: int = 0
    longest_streak: int = 0
    last_completed_date: Optional[date] = None
    total_perfect_days: int = 0


# ============ Stats Models ============


class CompletionRate(BaseModel):
    """Completion rate for a time period."""

    period: str  # "week" or "month"
    completed: int = 0
    total: int = 0
    rate: float = 0.0


class LifeOpsStats(BaseModel):
    """Aggregated stats for the stats page."""

    streak: LifeOpsStreak = LifeOpsStreak()
    weekly_rates: list[CompletionRate] = []
    monthly_rates: list[CompletionRate] = []
    today_completed: int = 0
    today_total: int = 0
