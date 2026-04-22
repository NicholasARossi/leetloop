"""Pydantic schemas for Language Learning feature."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============ Track Models ============


class LanguageTopicInfo(BaseModel):
    """A topic within a language track (e.g., a chapter from a textbook)."""

    name: str
    order: int
    difficulty: str  # "easy", "medium", "hard"
    key_concepts: list[str] = []


class LanguageRubricWeights(BaseModel):
    """Rubric dimension weights for language grading."""

    accuracy: int = Field(default=3, ge=1, le=5)
    grammar: int = Field(default=3, ge=1, le=5)
    vocabulary: int = Field(default=2, ge=1, le=5)
    naturalness: int = Field(default=2, ge=1, le=5)


class LanguageTrack(BaseModel):
    """A language learning track (e.g., French A1)."""

    id: UUID
    name: str
    description: Optional[str] = None
    language: str  # "french", "chinese", etc.
    level: str  # CEFR: "a1"-"c2"
    topics: list[LanguageTopicInfo] = []
    total_topics: int = 0
    rubric: LanguageRubricWeights = LanguageRubricWeights()
    source_book: Optional[str] = None
    created_at: Optional[datetime] = None


class LanguageTrackSummary(BaseModel):
    """Summary view of a language track (for listing)."""

    id: UUID
    name: str
    description: Optional[str] = None
    language: str
    level: str
    total_topics: int


# ============ Attempt Models ============


class CreateLanguageAttemptRequest(BaseModel):
    """Request to create a new language exercise attempt."""

    track_id: UUID
    topic: str
    exercise_type: str = "vocabulary"  # vocabulary, grammar, fill_blank, conjugation, sentence_construction, reading_comprehension, dictation


class SubmitLanguageAttemptRequest(BaseModel):
    """Request to submit response for a language attempt."""

    response_text: str


class LanguageAttemptGrade(BaseModel):
    """Grading result for a language attempt."""

    score: float = Field(ge=1, le=10)
    verdict: str  # "pass", "fail", "borderline"
    feedback: str
    corrections: Optional[str] = None
    missed_concepts: list[str] = []


class LanguageAttempt(BaseModel):
    """A language exercise attempt."""

    id: UUID
    user_id: UUID
    track_id: Optional[UUID] = None
    topic: str
    exercise_type: str
    question_text: str
    expected_answer: Optional[str] = None
    question_focus_area: Optional[str] = None
    question_key_concepts: list[str] = []
    response_text: Optional[str] = None
    word_count: int = 0
    score: Optional[float] = None
    verdict: Optional[str] = None
    feedback: Optional[str] = None
    corrections: Optional[str] = None
    missed_concepts: list[str] = []
    status: str = "pending"
    created_at: datetime
    graded_at: Optional[datetime] = None


class LanguageAttemptHistoryItem(BaseModel):
    """Summary of a past attempt for history view."""

    id: UUID
    topic: str
    exercise_type: str
    question_text: str
    score: Optional[float] = None
    verdict: Optional[str] = None
    status: str
    created_at: datetime
    graded_at: Optional[datetime] = None
    track_name: Optional[str] = None


class LanguageAttemptHistoryResponse(BaseModel):
    """List of past attempts with pagination."""

    attempts: list[LanguageAttemptHistoryItem]
    total: int
    has_more: bool


# ============ Review Queue Models ============


class LanguageReviewItem(BaseModel):
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
    source_attempt_id: Optional[UUID] = None
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


class LanguageTrackProgress(BaseModel):
    """User's progress on a language track."""

    id: UUID
    user_id: UUID
    track_id: UUID
    completed_topics: list[str] = []
    sessions_completed: int = 0
    average_score: float = 0.0
    started_at: datetime
    last_activity_at: datetime


class LanguageTrackProgressResponse(BaseModel):
    """Track details with user progress."""

    track: LanguageTrack
    progress: Optional[LanguageTrackProgress] = None
    completion_percentage: float = 0.0
    next_topic: Optional[str] = None


# ============ Dashboard Models ============


class LanguageNextTopicInfo(BaseModel):
    """Information about the next topic to practice."""

    track_id: UUID
    track_name: str
    language: str
    level: str
    topic_name: str
    topic_order: int
    topic_difficulty: str
    key_concepts: list[str] = []
    topics_completed: int
    total_topics: int


class LanguageDashboardExercise(BaseModel):
    """A preview exercise for dashboard display."""

    id: str
    exercise_type: str
    question_text: str
    topic: str
    track_id: UUID
    completed: bool = False


class LanguageDashboardSummary(BaseModel):
    """Summary for dashboard display."""

    has_active_track: bool
    active_track: Optional[LanguageTrackSummary] = None
    next_topic: Optional[LanguageNextTopicInfo] = None
    daily_exercise: Optional[LanguageDashboardExercise] = None
    reviews_due_count: int = 0
    reviews_due: list[LanguageReviewItem] = []
    recent_score: Optional[float] = None
    exercises_this_week: int = 0
    book_total_chapters: int = 0
    book_completed_chapters: int = 0
    book_completion_percentage: float = 0.0


class SetActiveTrackRequest(BaseModel):
    """Request to set active language track."""

    track_id: Optional[UUID] = None


# ============ Gemini Context Models ============


class LanguageQuestionContext(BaseModel):
    """Context sent to Gemini for question generation."""

    language: str
    level: str
    topic: str
    exercise_type: str
    key_concepts: list[str] = []
    user_weak_areas: list[str] = []


class LanguageGradingResponse(BaseModel):
    """Gemini's grading response for a language exercise."""

    score: float = Field(ge=1, le=10)
    verdict: str  # "pass", "fail", "borderline"
    feedback: str
    corrections: Optional[str] = None
    missed_concepts: list[str] = []


class LanguageQuestionResponse(BaseModel):
    """Gemini's generated question for a language exercise."""

    question_text: str
    expected_answer: Optional[str] = None
    focus_area: str
    key_concepts: list[str] = []


# ============ Written Grading Models ============


class EvidenceItem(BaseModel):
    """A quote + analysis pair from the student's response."""

    quote: str
    analysis: str


class DimensionScore(BaseModel):
    """Score for a single grading dimension."""

    score: float
    evidence: list[EvidenceItem] = []
    summary: str = ""


class GrammarTargetHit(BaseModel):
    """Whether a specific grammar target was used correctly."""

    target: str
    used: bool = False
    correct: bool = False
    evidence: str = ""


class WrittenGrading(BaseModel):
    """Full 4-dimension rubric grading for written exercises."""

    scores: dict[str, DimensionScore] = {}  # grammar, lexical, discourse, task
    overall_score: float
    verdict: str  # strong, developing, needs_work
    feedback: str
    grammar_target_hits: list[GrammarTargetHit] = []
    vocab_target_hits: list[str] = []


# ============ Daily Exercise Models ============


class DailyExercise(BaseModel):
    """A single daily exercise."""

    id: UUID
    topic: str
    exercise_type: str
    question_text: str
    expected_answer: Optional[str] = None
    focus_area: Optional[str] = None
    key_concepts: list[str] = []
    grammar_targets: list[str] = []
    vocab_targets: list[str] = []
    is_review: bool = False
    review_topic_reason: Optional[str] = None
    status: str = "pending"
    sort_order: int = 0
    response_format: str = "long_text"
    word_target: int = 100
    # Response/grading (filled after submission)
    response_text: Optional[str] = None
    score: Optional[float] = None
    verdict: Optional[str] = None
    feedback: Optional[str] = None
    corrections: Optional[str] = None
    missed_concepts: list[str] = []
    written_grading: Optional[WrittenGrading] = None
    completed_at: Optional[datetime] = None


class DailyExerciseBatch(BaseModel):
    """Today's exercise batch."""

    generated_date: str  # "2026-02-18"
    track_id: Optional[UUID] = None
    exercises: list[DailyExercise]
    completed_count: int = 0
    total_count: int = 0
    average_score: Optional[float] = None


class SubmitDailyExerciseRequest(BaseModel):
    """Submit an answer for a daily exercise."""

    response_text: str


class DailyExerciseGrade(BaseModel):
    """Grade result for a daily exercise."""

    score: float
    verdict: str
    feedback: str
    corrections: Optional[str] = None
    missed_concepts: list[str] = []
    written_grading: Optional[WrittenGrading] = None


# ============ Book Progress Models ============


class BookContentSection(BaseModel):
    """A section within a book chapter."""

    title: str
    summary: str = ""
    key_points: list[str] = []


class ChapterProgressItem(BaseModel):
    """Progress info for a single chapter in the book."""

    name: str
    order: int
    difficulty: str
    key_concepts: list[str] = []
    is_completed: bool = False
    is_current: bool = False
    has_review_due: bool = False
    review_reason: Optional[str] = None
    book_summary: Optional[str] = None
    book_sections: list[BookContentSection] = []


class BookProgressResponse(BaseModel):
    """Full book progress with per-chapter details."""

    track_name: str
    language: str
    level: str
    source_book: Optional[str] = None
    total_chapters: int
    completed_chapters: int
    completion_percentage: float
    average_score: float = 0.0
    chapters: list[ChapterProgressItem]
