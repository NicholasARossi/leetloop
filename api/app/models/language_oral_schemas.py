"""Pydantic schemas for Language Oral Practice."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============ Prompt Models ============


class OralPrompt(BaseModel):
    """A pre-generated oral monologue prompt."""

    id: UUID
    track_id: UUID
    chapter_ref: str
    chapter_order: int
    prompt_text: str
    theme: Optional[str] = None
    grammar_targets: list[str] = []
    vocab_targets: list[str] = []
    suggested_duration_seconds: int = 120
    sort_order: int = 0


# ============ Grading Models ============


class OralDimensionEvidence(BaseModel):
    """A cited quote from the transcript with analysis."""

    quote: str
    analysis: str


class OralDimensionScore(BaseModel):
    """Score for a single rubric dimension with cited evidence."""

    name: str  # "grammar", "lexical", "discourse", "task"
    score: float = Field(ge=1, le=10)
    evidence: list[OralDimensionEvidence] = []
    summary: str = ""


class OralGrading(BaseModel):
    """Full grading result for an oral session."""

    transcript: str
    scores: dict[str, OralDimensionScore]  # keyed by dimension name
    overall_score: float
    verdict: str  # "strong", "developing", "needs_work"
    feedback: str  # in target language
    strongest_moment: str = ""
    weakest_moment: str = ""


# ============ Session Models ============


class OralSessionCreate(BaseModel):
    """Request to create an oral session from a prompt."""

    prompt_id: UUID


class OralSession(BaseModel):
    """An oral recording session."""

    id: UUID
    user_id: UUID
    prompt_id: UUID
    track_id: UUID
    chapter_ref: str
    prompt: Optional[OralPrompt] = None
    grading: Optional[OralGrading] = None
    audio_duration_seconds: Optional[int] = None
    status: str = "prompted"  # prompted, recorded, grading, graded, failed
    created_at: Optional[datetime] = None
    graded_at: Optional[datetime] = None


# ============ Dashboard Models ============


class StreakInfo(BaseModel):
    """User's practice streak information."""

    current_streak: int = 0
    longest_streak: int = 0
    last_practice_date: Optional[str] = None


class ChapterInfo(BaseModel):
    """Current chapter info for dashboard display."""

    name: str
    order: int
    total_chapters: int
    completion_percentage: float = 0.0


class OralDashboard(BaseModel):
    """Dashboard summary for oral practice."""

    chapter: Optional[ChapterInfo] = None
    streak: StreakInfo = StreakInfo()
    todays_prompts: list[OralPrompt] = []
    pending_sessions: list[OralSession] = []  # status = grading
    recent_sessions: list[OralSession] = []  # status = graded, with gradings
