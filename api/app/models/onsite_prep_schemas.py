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
    rubric_dimensions: list[RubricDimension] = []


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
    breakdown_phases: list[DesignPhase] = []
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


class PhaseSubmissionResult(BaseModel):
    """Result from grading a single breakdown phase."""
    transcript: str
    dimensions: list[DimensionScore]
    overall_score: float
    verdict: str  # pass, borderline, fail
    feedback: str
    strongest_moment: str = ""
    weakest_moment: str = ""


class SubmitPhaseAudioResponse(BaseModel):
    """Response from submitting a breakdown phase audio."""
    phase_submission_id: str
    phase_number: int
    result: PhaseSubmissionResult
    gate_passed: bool
    next_phase: int | None = None
    attempt_complete: bool = False
    overall_score: float | None = None  # Set when attempt_complete=True
    overall_verdict: str | None = None


class OnsitePrepPhaseSubmission(BaseModel):
    """A single phase submission in a breakdown attempt."""
    id: str
    attempt_id: str
    phase_number: int
    transcript: str | None = None
    dimensions: list[DimensionScore] | None = None
    overall_score: float | None = None
    verdict: str | None = None
    feedback: str | None = None
    strongest_moment: str | None = None
    weakest_moment: str | None = None
    audio_gcs_path: str | None = None
    duration_seconds: int | None = None
    created_at: str | None = None


class OnsitePrepImage(BaseModel):
    """An image attached to an attempt or phase submission."""
    id: str
    attempt_id: str | None = None
    phase_submission_id: str | None = None
    gcs_path: str
    filename: str
    include_in_grading: bool = False
    sort_order: int = 0
    created_at: str | None = None


class CreateBreakdownAttemptResponse(BaseModel):
    attempt_id: str
    mode: str
    current_phase: int


class ImageUploadResponse(BaseModel):
    image_id: str
    gcs_path: str


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
    mode: str = "stand_and_deliver"
    current_phase: int = 0
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
    phase_submissions: list[OnsitePrepPhaseSubmission] = []
    images: list[OnsitePrepImage] = []
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
    mode: str = "stand_and_deliver"
    phases_completed: int = 0
    overall_score: float | None = None
    verdict: str | None = None
    duration_seconds: int | None = None
    created_at: str | None = None
