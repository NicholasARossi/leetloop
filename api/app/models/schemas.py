"""Pydantic schemas for API request/response models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SubmissionStatus(str, Enum):
    """Possible submission statuses from LeetCode."""

    ACCEPTED = "Accepted"
    WRONG_ANSWER = "Wrong Answer"
    TIME_LIMIT_EXCEEDED = "Time Limit Exceeded"
    MEMORY_LIMIT_EXCEEDED = "Memory Limit Exceeded"
    RUNTIME_ERROR = "Runtime Error"
    COMPILE_ERROR = "Compile Error"


class Difficulty(str, Enum):
    """Problem difficulty levels."""

    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


# ============ Submission Models ============


class Submission(BaseModel):
    """A single submission record."""

    id: UUID
    user_id: UUID
    problem_slug: str
    problem_title: str
    problem_id: Optional[int] = None
    difficulty: Optional[Difficulty] = None
    tags: Optional[list[str]] = None
    status: SubmissionStatus
    runtime_ms: Optional[int] = None
    runtime_percentile: Optional[float] = None
    memory_mb: Optional[float] = None
    memory_percentile: Optional[float] = None
    attempt_number: Optional[int] = None
    time_elapsed_seconds: Optional[int] = None
    language: Optional[str] = None
    code: Optional[str] = None
    code_length: Optional[int] = None
    session_id: Optional[UUID] = None
    submitted_at: datetime
    created_at: datetime


# ============ Skill Score Models ============


class SkillScore(BaseModel):
    """User's skill level for a specific tag/topic."""

    user_id: UUID
    tag: str
    score: float = Field(ge=0, le=100, default=50.0)
    total_attempts: int = 0
    success_rate: float = Field(ge=0, le=1, default=0.0)
    avg_time_seconds: Optional[float] = None
    last_practiced: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============ Review Queue Models ============


class ReviewItem(BaseModel):
    """An item in the spaced repetition review queue."""

    id: UUID
    user_id: UUID
    problem_slug: str
    problem_title: Optional[str] = None
    reason: Optional[str] = None
    priority: int = 0
    next_review: datetime
    interval_days: int = 1
    review_count: int = 0
    last_reviewed: Optional[datetime] = None
    created_at: datetime


class ReviewCompleteRequest(BaseModel):
    """Request to mark a review as complete."""

    success: bool


class ReviewCompleteResponse(BaseModel):
    """Response after completing a review."""

    id: UUID
    next_review: datetime
    new_interval_days: int


# ============ Progress/Stats Models ============


class UserStats(BaseModel):
    """Aggregated statistics for a user."""

    total_submissions: int = 0
    accepted_count: int = 0
    failed_count: int = 0
    success_rate: float = 0.0
    problems_solved: int = 0
    problems_attempted: int = 0
    streak_days: int = 0
    reviews_due: int = 0


class ProgressTrend(BaseModel):
    """Progress data point for trend charts."""

    date: str
    submissions: int
    accepted: int
    success_rate: float


class UserProgress(BaseModel):
    """Complete progress data for a user."""

    stats: UserStats
    skill_scores: list[SkillScore] = []
    trends: list[ProgressTrend] = []
    recent_submissions: list[Submission] = []


# ============ Recommendation Models ============


class RecommendedProblem(BaseModel):
    """A problem recommended for the user to attempt."""

    problem_slug: str
    problem_title: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    tags: list[str] = []
    reason: str  # Why this problem is recommended
    priority: float  # Higher = more urgent
    source: str  # "review_queue", "weak_skill", "progression"


class RecommendationResponse(BaseModel):
    """Response containing personalized recommendations."""

    user_id: UUID
    recommendations: list[RecommendedProblem]
    weak_areas: list[str] = []
    generated_at: datetime


# ============ Coaching Models ============


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Request for coaching chat."""

    user_id: UUID
    message: str
    context: Optional[dict] = None  # Current problem, recent submissions, etc.
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    """Response from coaching chat."""

    message: str
    suggestions: list[str] = []  # Follow-up suggestions


class CodeAnalysisRequest(BaseModel):
    """Request to analyze submitted code."""

    user_id: UUID
    submission_id: UUID
    code: str
    language: str
    problem_slug: str
    status: SubmissionStatus


class CodeAnalysisResponse(BaseModel):
    """Response from code analysis."""

    summary: str
    issues: list[str] = []
    suggestions: list[str] = []
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None


# ============ Learning Path Models ============


class PathProblem(BaseModel):
    """A problem within a learning path category."""

    slug: str
    title: str
    difficulty: Difficulty
    order: int


class PathCategory(BaseModel):
    """A category/pattern group within a learning path."""

    name: str
    order: int
    problems: list[PathProblem]


class LearningPath(BaseModel):
    """A structured learning path (e.g., NeetCode 150, Blind 75)."""

    id: UUID
    name: str
    description: Optional[str] = None
    total_problems: int
    categories: list[PathCategory]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LearningPathSummary(BaseModel):
    """Summary view of a learning path (without full problem details)."""

    id: UUID
    name: str
    description: Optional[str] = None
    total_problems: int


class UserPathProgress(BaseModel):
    """User's progress on a specific learning path."""

    id: UUID
    user_id: UUID
    path_id: UUID
    completed_problems: list[str] = []
    current_category: Optional[str] = None
    started_at: datetime
    last_activity_at: Optional[datetime] = None


class PathProgressResponse(BaseModel):
    """Complete path progress with path details."""

    path: LearningPath
    progress: Optional[UserPathProgress] = None
    completed_count: int = 0
    completion_percentage: float = 0.0
    categories_progress: dict[str, dict] = {}  # {category_name: {total, completed, problems}}


class CompleteProblemRequest(BaseModel):
    """Request to mark a problem as completed in a path."""

    problem_slug: str


class SetCurrentPathRequest(BaseModel):
    """Request to set user's current learning path."""

    path_id: UUID


# ============ Today's Focus Models ============


class DailyFocusProblem(BaseModel):
    """A problem recommended for today's focus."""

    slug: str
    title: str
    difficulty: Optional[Difficulty] = None
    category: str
    reason: str
    priority: int  # 1 = highest priority


class TodaysFocus(BaseModel):
    """Daily mission data for Today's Focus page."""

    user_id: UUID
    streak: int = 0
    daily_goal: int = 5
    completed_today: int = 0
    reviews_due: list[DailyFocusProblem] = []
    path_problems: list[DailyFocusProblem] = []
    skill_builders: list[DailyFocusProblem] = []
    llm_insight: Optional[str] = None
    generated_at: datetime


# ============ Mastery Models ============


class DomainScore(BaseModel):
    """Score for a specific DSA domain."""

    name: str
    score: float = Field(ge=0, le=100, default=0.0)
    status: str  # "WEAK", "FAIR", "GOOD", "STRONG"
    problems_attempted: int = 0
    problems_solved: int = 0
    sub_patterns: list[dict] = []  # [{name, score, attempted}]


class MasteryResponse(BaseModel):
    """Complete mastery/readiness data for a user."""

    user_id: UUID
    readiness_score: float = Field(ge=0, le=100, default=0.0)
    readiness_summary: str = ""
    domains: list[DomainScore] = []
    weak_areas: list[str] = []
    strong_areas: list[str] = []
    generated_at: datetime


class DomainDetailResponse(BaseModel):
    """Detailed breakdown of a specific domain."""

    domain: DomainScore
    failure_analysis: Optional[str] = None
    recommended_path: list[PathProblem] = []
    recent_submissions: list[Submission] = []
