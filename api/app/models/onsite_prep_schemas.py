"""Pydantic schemas for Amazon Onsite Prep."""

from pydantic import BaseModel


class RubricDimension(BaseModel):
    name: str
    label: str
    description: str


class DesignPhase(BaseModel):
    name: str
    prompt: str
    duration_seconds: int
    key_areas: list[str] = []


class OnsitePrepQuestion(BaseModel):
    id: str
    category: str  # lp, breadth, depth, design
    subcategory: str | None = None
    prompt_text: str
    context_hint: str | None = None
    rubric_dimensions: list[RubricDimension] = []
    target_duration_seconds: int = 120
    sort_order: int = 0
    ideal_answer: "IdealResponse | None" = None
    phases: list[DesignPhase] = []
    structured_probes: list[str] = []


class DimensionEvidence(BaseModel):
    quote: str
    analysis: str


class DimensionScore(BaseModel):
    name: str
    score: int
    evidence: list[DimensionEvidence] = []
    summary: str = ""


class OnsitePrepGradeResult(BaseModel):
    transcript: str
    dimensions: list[DimensionScore]
    overall_score: float
    verdict: str  # pass, borderline, fail
    feedback: str
    strongest_moment: str = ""
    weakest_moment: str = ""
    follow_up_questions: list[str] = []


class IdealResponse(BaseModel):
    summary: str
    outline: list[str]
    full_response: str


class SubmitAudioResponse(BaseModel):
    attempt_id: str
    grade: OnsitePrepGradeResult


class OnsitePrepFollowUpResult(BaseModel):
    transcript: str
    score: int
    feedback: str
    addressed_gap: bool


class ConversationalFollowUpResult(BaseModel):
    transcript: str
    score: int
    feedback: str
    addressed_gap: bool
    ideal_answer: str = ""
    next_follow_up: "OnsitePrepFollowUp | None" = None


class OnsitePrepFollowUp(BaseModel):
    id: str
    attempt_id: str
    question_text: str
    transcript: str | None = None
    score: float | None = None
    feedback: str | None = None
    ideal_answer: str | None = None
    addressed_gap: bool = False
    sort_order: int = 0
    parent_follow_up_id: str | None = None


class OnsitePrepAttempt(BaseModel):
    id: str
    user_id: str
    question_id: str
    transcript: str | None = None
    dimensions: list[DimensionScore] | None = None
    overall_score: float | None = None
    verdict: str | None = None
    feedback: str | None = None
    strongest_moment: str | None = None
    weakest_moment: str | None = None
    duration_seconds: int | None = None
    follow_up_questions: list[str] = []
    follow_ups: list[OnsitePrepFollowUp] = []
    ideal_response: IdealResponse | None = None
    audio_gcs_path: str | None = None
    created_at: str | None = None


class CategoryStats(BaseModel):
    category: str
    label: str
    total: int
    practiced: int
    avg_score: float | None = None


class OnsitePrepDashboard(BaseModel):
    total_questions: int
    practiced_count: int
    avg_score: float | None = None
    avg_duration: float | None = None
    categories: list[CategoryStats] = []


class OnsitePrepAttemptHistory(BaseModel):
    id: str
    question_id: str
    prompt_text: str
    category: str
    overall_score: float | None = None
    verdict: str | None = None
    duration_seconds: int | None = None
    created_at: str | None = None
