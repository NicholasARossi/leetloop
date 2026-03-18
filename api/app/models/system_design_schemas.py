"""Pydantic schemas for System Design Review feature."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============ Track Models ============


class TopicInfo(BaseModel):
    """A topic within a system design track."""

    name: str
    order: int
    difficulty: str  # "easy", "medium", "hard"
    example_systems: list[str] = []


class RubricWeights(BaseModel):
    """Rubric dimension weights for grading."""

    depth: int = Field(default=3, ge=1, le=5)
    tradeoffs: int = Field(default=3, ge=1, le=5)
    clarity: int = Field(default=2, ge=1, le=5)
    scalability: int = Field(default=2, ge=1, le=5)


class SystemDesignTrack(BaseModel):
    """A system design interview prep track."""

    id: UUID
    name: str
    description: Optional[str] = None
    track_type: str  # "mle", "traditional", "infra", "data"
    topics: list[TopicInfo] = []
    total_topics: int = 0
    rubric: RubricWeights = RubricWeights()
    created_at: Optional[datetime] = None


class TrackSummary(BaseModel):
    """Summary view of a track (for listing)."""

    id: UUID
    name: str
    description: Optional[str] = None
    track_type: str
    total_topics: int


# ============ Review Queue Models ============


class SystemDesignReviewItem(BaseModel):
    """A topic in the spaced repetition review queue."""

    id: UUID
    user_id: UUID
    track_id: Optional[UUID] = None
    topic: str
    reason: Optional[str] = None
    priority: int = 0
    next_review: datetime
    interval_days: int = 1
    review_count: int = 0
    last_reviewed: Optional[datetime] = None
    source_session_id: Optional[UUID] = None
    created_at: datetime


class CompleteReviewRequest(BaseModel):
    """Request to mark a review as complete."""

    success: bool


class CompleteReviewResponse(BaseModel):
    """Response after completing a review."""

    id: UUID
    next_review: datetime
    new_interval_days: int


# ============ Progress Models ============


class UserTrackProgress(BaseModel):
    """User's progress on a system design track."""

    id: UUID
    user_id: UUID
    track_id: UUID
    completed_topics: list[str] = []
    sessions_completed: int = 0
    average_score: float = 0.0
    started_at: datetime
    last_activity_at: datetime


class TrackProgressResponse(BaseModel):
    """Track details with user progress."""

    track: SystemDesignTrack
    progress: Optional[UserTrackProgress] = None
    completion_percentage: float = 0.0
    next_topic: Optional[str] = None


# ============ Dashboard Integration Models ============


class SetActiveTrackRequest(BaseModel):
    """Request to set active system design track."""

    track_id: Optional[UUID] = None  # None to clear active track


class NextTopicInfo(BaseModel):
    """Information about the next topic to practice."""

    track_id: UUID
    track_name: str
    track_type: str
    topic_name: str
    topic_order: int
    topic_difficulty: str
    example_systems: list[str] = []
    topics_completed: int
    total_topics: int


class SystemDesignDashboardSummary(BaseModel):
    """Summary for dashboard display."""

    has_active_track: bool
    active_track: Optional[TrackSummary] = None
    next_topic: Optional[NextTopicInfo] = None
    oral_session: Optional["OralSession"] = None  # Today's oral session (auto-generated)
    reviews_due_count: int = 0
    reviews_due: list[SystemDesignReviewItem] = []
    recent_score: Optional[float] = None
    sessions_this_week: int = 0


# ============ Oral System Design Models ============


class OralSessionCreate(BaseModel):
    """Request to create a new oral practice session."""

    track_id: UUID
    topic: str


class OralSubQuestion(BaseModel):
    """A focused sub-question within an oral session."""

    id: str
    part_number: int
    question_text: str
    focus_area: str
    key_concepts: list[str] = []
    suggested_duration_minutes: int = 4
    status: str = "pending"
    # Grading fields (populated after audio submission)
    overall_score: Optional[float] = None
    verdict: Optional[str] = None
    transcript: Optional[str] = None
    feedback: Optional[str] = None
    dimension_scores: Optional[list["DimensionScore"]] = None
    missed_concepts: Optional[list[str]] = None
    strongest_moment: Optional[str] = None
    weakest_moment: Optional[str] = None
    follow_up_questions: Optional[list[str]] = None
    follow_up_responses: Optional[list["OralFollowUp"]] = None


class OralSession(BaseModel):
    """An oral system design practice session with 3 sub-questions."""

    id: str
    user_id: str
    track_id: str
    topic: str
    scenario: str
    status: str = "active"
    questions: list[OralSubQuestion] = []
    created_at: str


class DimensionEvidence(BaseModel):
    """A cited quote from the transcript with analysis."""

    quote: str
    analysis: str


class DimensionScore(BaseModel):
    """Score for a single rubric dimension with cited evidence."""

    name: str  # "technical_depth", "structure_and_approach", etc.
    score: int = Field(ge=1, le=10)
    evidence: list[DimensionEvidence] = []
    summary: str


class OralGradeResult(BaseModel):
    """Complete grading result for an oral response."""

    transcript: str
    dimensions: list[DimensionScore] = []
    overall_score: float
    verdict: str  # "pass", "borderline", "fail" — computed in code
    feedback: str
    missed_concepts: list[str] = []
    strongest_moment: str = ""
    weakest_moment: str = ""
    follow_up_questions: list[str] = []


class OralSessionSummary(BaseModel):
    """Aggregate results after completing an oral session."""

    session_id: str
    topic: str
    questions_graded: int
    dimension_averages: dict[str, float] = {}
    overall_score: float
    verdict: str
    review_topics_added: list[str] = []


# ============ Follow-Up Models ============


class FollowUpGradeResult(BaseModel):
    """Simplified grading result for a follow-up question response."""

    transcript: str
    score: int = Field(ge=1, le=10)
    feedback: str
    addressed_gap: bool


class OralFollowUp(BaseModel):
    """A follow-up question response within an oral session."""

    id: str
    question_id: str
    follow_up_index: int
    follow_up_text: str
    status: str = "pending"
    transcript: Optional[str] = None
    score: Optional[int] = None
    feedback: Optional[str] = None
    addressed_gap: Optional[bool] = None
    graded_at: Optional[str] = None


# Resolve forward references
OralSubQuestion.model_rebuild()
OralFollowUp.model_rebuild()
FollowUpGradeResult.model_rebuild()
SystemDesignDashboardSummary.model_rebuild()
