"""Submissions router for receiving submission data from the Chrome extension."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.supabase import get_supabase_client

router = APIRouter()


class SubmissionCreate(BaseModel):
    """Submission data from the Chrome extension."""

    id: UUID
    user_id: UUID
    problem_slug: str
    problem_title: str
    problem_id: Optional[int] = None
    difficulty: Optional[str] = None
    tags: Optional[list[str]] = None
    status: str
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


class SubmissionResponse(BaseModel):
    """Response after creating a submission."""

    id: UUID
    success: bool
    message: str


@router.post("/submissions", response_model=SubmissionResponse)
async def create_submission(submission: SubmissionCreate) -> SubmissionResponse:
    """
    Receive a submission from the Chrome extension and store it in Supabase.

    This endpoint replaces direct Supabase calls from the extension,
    allowing centralized submission processing and validation.
    """
    supabase = get_supabase_client()

    try:
        # Convert to dict and prepare for insert
        data = {
            "id": str(submission.id),
            "user_id": str(submission.user_id),
            "problem_slug": submission.problem_slug,
            "problem_title": submission.problem_title,
            "problem_id": submission.problem_id,
            "difficulty": submission.difficulty,
            "tags": submission.tags,
            "status": submission.status,
            "runtime_ms": submission.runtime_ms,
            "runtime_percentile": submission.runtime_percentile,
            "memory_mb": submission.memory_mb,
            "memory_percentile": submission.memory_percentile,
            "attempt_number": submission.attempt_number,
            "time_elapsed_seconds": submission.time_elapsed_seconds,
            "language": submission.language,
            "code": submission.code,
            "code_length": submission.code_length,
            "session_id": str(submission.session_id) if submission.session_id else None,
            "submitted_at": submission.submitted_at.isoformat(),
        }

        # Upsert to handle potential duplicates
        result = supabase.table("submissions").upsert(data).execute()

        if result.data:
            return SubmissionResponse(
                id=submission.id,
                success=True,
                message="Submission stored successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to store submission")

    except Exception as e:
        # Log the error but don't expose internal details
        print(f"[Submissions] Error storing submission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store submission: {str(e)}")


@router.post("/submissions/batch", response_model=list[SubmissionResponse])
async def create_submissions_batch(submissions: list[SubmissionCreate]) -> list[SubmissionResponse]:
    """
    Receive multiple submissions from the Chrome extension.
    Useful for syncing backlog of unsynced submissions.
    """
    results = []

    for submission in submissions:
        try:
            result = await create_submission(submission)
            results.append(result)
        except HTTPException as e:
            results.append(SubmissionResponse(
                id=submission.id,
                success=False,
                message=str(e.detail)
            ))

    return results
