"""Pydantic schemas for win rate targeting system."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WinRateTargets(BaseModel):
    id: UUID
    user_id: UUID
    easy_target: float = 0.90
    medium_target: float = 0.70
    hard_target: float = 0.50
    optimality_threshold: float = 70.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SetWinRateTargetsRequest(BaseModel):
    easy_target: float = Field(default=0.90, ge=0.0, le=1.0)
    medium_target: float = Field(default=0.70, ge=0.0, le=1.0)
    hard_target: float = Field(default=0.50, ge=0.0, le=1.0)
    optimality_threshold: float = Field(default=70.0, ge=0.0, le=100.0)


class DifficultyWinRate(BaseModel):
    rate: float = 0.0
    attempts: int = 0
    optimal: int = 0
    target: float = 0.0


class WinRateStats(BaseModel):
    targets: WinRateTargets
    current_30d: dict = {}
    current_alltime: dict = {}
    trend: list[dict] = []


class FeedItem(BaseModel):
    id: UUID
    problem_slug: str
    problem_title: Optional[str] = None
    difficulty: Optional[str] = None
    tags: list[str] = []
    feed_type: str
    practice_source: Optional[str] = None
    practice_reason: Optional[str] = None
    metric_rationale: Optional[str] = None
    sort_order: int = 0
    status: str = "pending"
    was_accepted: Optional[bool] = None
    was_optimal: Optional[bool] = None
    runtime_percentile: Optional[float] = None


class DailyFeedResponse(BaseModel):
    user_id: UUID
    feed_date: str
    items: list[FeedItem] = []
    completed_count: int = 0
    total_count: int = 0
    practice_count: int = 0
    metric_count: int = 0
