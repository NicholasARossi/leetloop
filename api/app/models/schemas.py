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


class DailyObjective(BaseModel):
    """The daily focus objective generated by LLM."""

    title: str
    description: str
    skill_tags: list[str] = []
    target_count: int = 5  # Number of problems to complete
    completed_count: int = 0


class MissionResponse(BaseModel):
    """Complete daily mission data for Mission Control dashboard."""

    user_id: UUID
    mission_date: str  # ISO date string
    objective: DailyObjective
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


# ============ Meta Objective Models ============


class ObjectiveTemplate(BaseModel):
    """Pre-built objective template for common interview targets."""

    id: UUID
    name: str
    company: str
    role: str
    level: Optional[str] = None
    description: Optional[str] = None
    required_skills: dict[str, float] = {}
    recommended_path_ids: list[UUID] = []
    difficulty_distribution: dict[str, float] = {}
    estimated_weeks: int = 12
    created_at: Optional[datetime] = None


class ObjectiveTemplateSummary(BaseModel):
    """Summary view of an objective template."""

    id: UUID
    name: str
    company: str
    role: str
    level: Optional[str] = None
    description: Optional[str] = None
    estimated_weeks: int = 12


class CreateObjectiveRequest(BaseModel):
    """Request to create a new objective from a template."""

    template_id: Optional[UUID] = None
    title: str
    target_company: str
    target_role: str
    target_level: Optional[str] = None
    target_deadline: date
    weekly_problem_target: int = Field(default=25, ge=10, le=50)
    daily_problem_minimum: int = Field(default=4, ge=1, le=10)
    required_skills: dict[str, float] = {}
    path_ids: list[UUID] = []


class UpdateObjectiveRequest(BaseModel):
    """Request to update an existing objective."""

    title: Optional[str] = None
    target_deadline: Optional[date] = None
    weekly_problem_target: Optional[int] = Field(default=None, ge=10, le=50)
    daily_problem_minimum: Optional[int] = Field(default=None, ge=1, le=10)
    required_skills: Optional[dict[str, float]] = None
    path_ids: Optional[list[UUID]] = None
    status: Optional[str] = None


class PaceStatus(BaseModel):
    """Current pace status for an objective."""

    status: str  # "ahead", "on_track", "behind", "critical"
    problems_this_week: int = 0
    weekly_target: int = 25
    problems_behind: int = 0
    pace_percentage: float = 100.0
    projected_completion_date: Optional[date] = None
    daily_rate_needed: float = 0.0


class SkillGap(BaseModel):
    """Gap between current and target skill level."""

    domain: str
    current_score: float = 0.0
    target_score: float = 0.0
    gap: float = 0.0
    priority: int = 0


class MetaObjective(BaseModel):
    """User's meta objective (career goal)."""

    id: UUID
    user_id: UUID
    title: str
    target_company: str
    target_role: str
    target_level: Optional[str] = None
    target_deadline: date
    started_at: datetime
    weekly_problem_target: int = 25
    daily_problem_minimum: int = 4
    required_skills: dict[str, float] = {}
    path_ids: list[UUID] = []
    template_id: Optional[UUID] = None
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ObjectiveProgress(BaseModel):
    """Daily progress record for an objective."""

    id: UUID
    user_id: UUID
    objective_id: UUID
    progress_date: date
    problems_completed: int = 0
    problems_attempted: int = 0
    cumulative_problems: int = 0
    target_cumulative: int = 0
    pace_status: str = "on_track"


class MetaObjectiveResponse(BaseModel):
    """Complete objective data with pace and skill gaps."""

    objective: MetaObjective
    pace_status: PaceStatus
    skill_gaps: list[SkillGap] = []
    days_remaining: int = 0
    total_days: int = 0
    problems_solved: int = 0
    total_problems_target: int = 0
    readiness_percentage: float = 0.0


# ============ Onboarding Models ============


class OnboardingStatus(BaseModel):
    """User's onboarding progress."""

    user_id: UUID
    has_objective: bool = False
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

    step: str  # "objective", "extension", "history", "path"
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

    # Goal
    target_company: Optional[str] = None
    target_role: Optional[str] = None
    target_deadline: Optional[date] = None
    weekly_commitment: int = 25
    days_until_deadline: Optional[int] = None

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
