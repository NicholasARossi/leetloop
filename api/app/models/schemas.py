"""Pydantic schemas for API request/response models."""

from datetime import date, datetime
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
    next_review: Optional[datetime] = None
    new_interval_days: Optional[int] = None
    graduated: bool = False


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
    code_output: Optional[str] = None
    expected_output: Optional[str] = None
    status_msg: Optional[str] = None
    total_correct: Optional[int] = None
    total_testcases: Optional[int] = None


class CodeAnalysisResponse(BaseModel):
    """Response from code analysis."""

    summary: str
    issues: list[str] = []
    suggestions: list[str] = []
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None
    root_cause: Optional[str] = None
    the_fix: Optional[str] = None
    pattern_type: Optional[str] = None
    concept_gap: Optional[str] = None


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


# ============ Daily Mission Models ============


class QuestStatus(str, Enum):
    """Status of a quest in the daily mission."""

    COMPLETED = "completed"
    CURRENT = "current"
    UPCOMING = "upcoming"


class MainQuest(BaseModel):
    """A problem in the main quest lineup (from learning path)."""

    slug: str
    title: str
    difficulty: Optional[Difficulty] = None
    category: str
    order: int
    status: QuestStatus = QuestStatus.UPCOMING


class SideQuest(BaseModel):
    """A side quest problem targeting a weakness."""

    slug: str
    title: str
    difficulty: Optional[Difficulty] = None
    reason: str  # Why this problem is recommended
    source_problem_slug: Optional[str] = None  # Problem that revealed the weakness
    target_weakness: str  # Skill/pattern being reinforced
    quest_type: str = "skill_gap"  # "review_due", "skill_gap", "slow_solve"
    completed: bool = False


class MissionResponse(BaseModel):
    """Complete daily mission data for Mission Control dashboard."""

    user_id: UUID
    mission_date: str  # ISO date string
    objective: Optional[dict] = None
    main_quests: list[MainQuest] = []
    side_quests: list[SideQuest] = []
    streak: int = 0
    total_completed_today: int = 0
    can_regenerate: bool = True  # False if regenerated 3+ times
    generated_at: datetime


class MissionGenerateRequest(BaseModel):
    """Request to generate or regenerate a mission."""

    force_regenerate: bool = False


class ProblemAttemptStats(BaseModel):
    """Stats about a user's attempts on a specific problem."""

    user_id: UUID
    problem_slug: str
    problem_title: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    first_attempt_at: Optional[datetime] = None
    first_success_at: Optional[datetime] = None
    last_attempt_at: Optional[datetime] = None
    time_to_first_success_seconds: Optional[int] = None
    is_slow_solve: bool = False
    is_struggle: bool = False


# ============ Onboarding Models ============


class OnboardingStatus(BaseModel):
    """User's onboarding progress."""

    user_id: UUID
    has_win_rate_target: bool = False
    extension_installed: bool = False
    history_imported: bool = False
    first_path_selected: bool = False
    onboarding_complete: bool = False
    current_step: int = Field(ge=1, le=4, default=1)
    extension_verified_at: Optional[datetime] = None
    history_imported_at: Optional[datetime] = None
    problems_imported_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OnboardingStepUpdate(BaseModel):
    """Request to update an onboarding step."""

    step: str  # "winrate", "extension", "history", "path"
    completed: bool = True
    metadata: Optional[dict] = None  # Extra data like problems_imported_count


# ============ Gemini Mission v2 Models ============


class SkillScoreContext(BaseModel):
    """Skill score context for Gemini mission generation."""

    domain: str
    score: float = Field(ge=0, le=100)
    status: str  # "weak", "developing", "proficient", "mastered"
    recent_failures: int = 0
    average_solve_time: Optional[float] = None


class ReviewItemContext(BaseModel):
    """Review queue item context for Gemini."""

    problem_id: str
    last_attempt: datetime
    failure_reason: Optional[str] = None
    interval: int  # Current spaced repetition interval


class PathContext(BaseModel):
    """Current learning path context for Gemini."""

    id: str
    name: str
    total_problems: int
    completed_count: int
    next_uncompleted_index: int
    current_category: Optional[str] = None


class GeminiMissionContext(BaseModel):
    """Complete context sent to Gemini for mission generation."""

    # Win rate targets
    win_rate_targets: Optional[dict] = None
    win_rate_current: Optional[dict] = None

    # Current path
    current_path: Optional[PathContext] = None

    # Skill state
    skill_scores: list[SkillScoreContext] = []

    # Review queue
    review_queue: list[ReviewItemContext] = []

    # History
    problems_attempted_total: int = 0
    problems_solved_total: int = 0
    current_streak: int = 0

    # Recent patterns (for Gemini to analyze)
    recent_failure_patterns: list[str] = []  # Common tags in failures
    recent_slow_solves: list[str] = []  # Problem slugs


class MissionProblem(BaseModel):
    """A problem in the Gemini-generated mission with reasoning."""

    problem_id: str
    problem_title: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    source: str  # "path", "gap_fill", "review", "reinforcement"
    reasoning: str  # WHY this problem was chosen
    priority: int  # 1 = most important
    skills: list[str] = []
    estimated_difficulty: Optional[str] = None  # "easy", "medium", "hard"
    completed: bool = False
    completed_at: Optional[datetime] = None


class GeminiMissionResponse(BaseModel):
    """Gemini's response for daily mission generation."""

    daily_objective: str  # "Build pattern recognition in DP"
    problems: list[MissionProblem]
    balance_explanation: str  # "Today is 60% path, 40% gap-filling"
    pacing_status: str  # "ahead", "on_track", "behind", "critical"
    pacing_note: str  # "You're 2 days ahead of schedule"


class DailyMissionResponseV2(BaseModel):
    """Complete daily mission response (v2 with Gemini reasoning)."""

    user_id: UUID
    mission_date: str  # ISO date string
    daily_objective: str
    problems: list[MissionProblem]
    balance_explanation: Optional[str] = None
    pacing_status: Optional[str] = None
    pacing_note: Optional[str] = None
    streak: int = 0
    total_completed_today: int = 0
    can_regenerate: bool = True
    generated_at: datetime


# ============ Pattern Analysis Models ============


class FocusNotesRequest(BaseModel):
    """Request to update user's focus notes for feed steering."""

    focus_notes: Optional[str] = Field(None, max_length=500)


class FocusNotesResponse(BaseModel):
    """Response containing user's focus notes."""

    user_id: UUID
    focus_notes: Optional[str] = None
    updated_at: Optional[datetime] = None


class PatternInsight(BaseModel):
    """A recurring mistake pattern detected across submissions."""

    pattern: str
    frequency: int
    example_problems: list[str] = []


class UserPatterns(BaseModel):
    """Result of analyzing a user's submission patterns."""

    recurring_mistakes: list[PatternInsight] = []
    error_distribution: dict[str, float] = {}
    learning_velocity: str = "unknown"  # improving | plateauing | regressing
    velocity_details: str = ""
    blind_spots: list[str] = []
    strategic_recommendations: list[str] = []
    analyzed_at: datetime
