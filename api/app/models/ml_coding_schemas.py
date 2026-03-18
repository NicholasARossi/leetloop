"""Pydantic schemas for ML Coding Drills feature."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============ Problem Models ============


class MLCodingProblem(BaseModel):
    """A static ML coding problem from the bank."""

    id: UUID
    slug: str
    title: str
    description: str
    difficulty: str  # "easy", "medium", "hard"
    category: str
    key_concepts: list[str] = []
    math_concepts: list[str] = []
    estimated_minutes: int = 30
    sort_order: int = 0


# ============ Daily Exercise Models ============


class MLCodingDailyExercise(BaseModel):
    """A daily ML coding exercise instance."""

    id: UUID
    problem_id: Optional[UUID] = None
    problem_slug: Optional[str] = None
    problem_title: Optional[str] = None
    prompt_text: str
    starter_code: Optional[str] = None
    status: str = "pending"
    is_review: bool = False
    sort_order: int = 0
    # Grading fields (populated after submission)
    submitted_code: Optional[str] = None
    score: Optional[float] = None
    verdict: Optional[str] = None
    feedback: Optional[str] = None
    correctness_score: Optional[float] = None
    code_quality_score: Optional[float] = None
    math_understanding_score: Optional[float] = None
    missed_concepts: list[str] = []
    suggested_improvements: list[str] = []
    completed_at: Optional[str] = None


class MLCodingDailyBatch(BaseModel):
    """A batch of daily ML coding exercises."""

    generated_date: str
    exercises: list[MLCodingDailyExercise] = []
    completed_count: int = 0
    total_count: int = 0
    average_score: Optional[float] = None


class SubmitMLCodingExerciseRequest(BaseModel):
    """Request to submit code for an ML coding exercise."""

    submitted_code: str


class MLCodingExerciseGrade(BaseModel):
    """Grading result for an ML coding exercise."""

    score: float = Field(ge=0, le=10)
    verdict: str  # "pass", "borderline", "fail"
    feedback: str
    correctness_score: float = Field(ge=0, le=10)
    code_quality_score: float = Field(ge=0, le=10)
    math_understanding_score: float = Field(ge=0, le=10)
    missed_concepts: list[str] = []
    suggested_improvements: list[str] = []


# ============ Review Models ============


class MLCodingReviewItem(BaseModel):
    """An ML coding problem in the spaced repetition review queue."""

    id: UUID
    user_id: UUID
    problem_slug: str
    reason: Optional[str] = None
    priority: int = 0
    next_review: datetime
    interval_days: int = 1
    review_count: int = 0
    last_reviewed: Optional[datetime] = None
    created_at: datetime


class CompleteMLCodingReviewRequest(BaseModel):
    """Request to mark a review as complete."""

    success: bool


class CompleteMLCodingReviewResponse(BaseModel):
    """Response after completing a review."""

    id: UUID
    next_review: datetime
    new_interval_days: int


# ============ Dashboard Models ============


class MLCodingDashboardSummary(BaseModel):
    """Summary for dashboard display."""

    problems_attempted: int = 0
    problems_total: int = 10
    today_exercise_count: int = 0
    today_completed_count: int = 0
    average_score: Optional[float] = None
    reviews_due_count: int = 0
    recent_scores: list[float] = []
