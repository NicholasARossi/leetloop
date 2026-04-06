"""Onsite Prep endpoints — questions, audio grading, follow-ups, dashboard."""

import logging
import time
from datetime import datetime
from typing import Annotated
from uuid import UUID

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from supabase import Client

from app.db.supabase import get_supabase
from app.models.onsite_prep_schemas import (
    CategoryStats,
    ConversationalFollowUpResult,
    CreateBreakdownAttemptResponse,
    DesignPhase,
    DimensionScore,
    IdealResponse,
    ImageUploadResponse,
    OnsitePrepAttempt,
    OnsitePrepAttemptHistory,
    OnsitePrepDashboard,
    OnsitePrepFollowUp,
    OnsitePrepFollowUpResult,
    OnsitePrepGradeResult,
    OnsitePrepImage,
    OnsitePrepPhaseSubmission,
    OnsitePrepQuestion,
    RubricDimension,
    SubmitAudioResponse,
    SubmitPhaseAudioResponse,
)

router = APIRouter()


def _build_question(q: dict) -> OnsitePrepQuestion:
    """Build OnsitePrepQuestion from a DB row dict."""
    return OnsitePrepQuestion(
        id=q["id"],
        category=q["category"],
        subcategory=q.get("subcategory"),
        prompt_text=q["prompt_text"],
        context_hint=q.get("context_hint"),
        rubric_dimensions=[RubricDimension(**d) for d in (q.get("rubric_dimensions") or [])],
        target_duration_seconds=q.get("target_duration_seconds", 120),
        sort_order=q.get("sort_order", 0),
        ideal_answer=IdealResponse(**q["ideal_answer"]) if q.get("ideal_answer") else None,
        phases=[DesignPhase(**p) for p in (q.get("phases") or [])],
        breakdown_phases=[DesignPhase(**p) for p in (q.get("breakdown_phases") or [])],
        structured_probes=q.get("structured_probes") or [],
    )


# Audio validation
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/mp4", "audio/x-m4a", "audio/mpeg", "audio/wav", "audio/x-wav"}

# Image validation
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# Dashboard cache
_dashboard_cache: dict[str, tuple[float, OnsitePrepDashboard]] = {}
_DASHBOARD_CACHE_TTL = 300  # 5 minutes


@router.get("/onsite-prep/questions", response_model=list[OnsitePrepQuestion])
async def get_questions(
    category: str | None = Query(None),
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """List all onsite prep questions, optionally filtered by category."""
    try:
        query = supabase.table("onsite_prep_questions").select("*").order("sort_order")
        if category:
            query = query.eq("category", category)
        result = query.execute()

        return [_build_question(q) for q in result.data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get questions: {str(e)}")


@router.get("/onsite-prep/questions/{question_id}", response_model=OnsitePrepQuestion)
async def get_question(
    question_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get a single question by ID."""
    try:
        result = supabase.table("onsite_prep_questions").select("*").eq("id", str(question_id)).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Question not found")
        return _build_question(result.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get question: {str(e)}")


@router.post("/onsite-prep/questions/{question_id}/submit-audio", response_model=SubmitAudioResponse)
async def submit_audio(
    question_id: UUID,
    audio: UploadFile = File(...),
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Submit audio for a question, transcribe + grade with category-specific rubric."""
    from app.services.onsite_prep_service import get_onsite_prep_grading_service

    try:
        # Validate audio
        content_type = audio.content_type or "audio/webm"
        if content_type not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported audio type: {content_type}")

        audio_bytes = await audio.read()
        if len(audio_bytes) > MAX_AUDIO_SIZE:
            raise HTTPException(status_code=400, detail=f"Audio too large: {len(audio_bytes) / 1024 / 1024:.1f}MB. Max: 25MB")

        # Get question
        q_result = supabase.table("onsite_prep_questions").select("*").eq("id", str(question_id)).execute()
        if not q_result.data:
            raise HTTPException(status_code=404, detail="Question not found")
        question = q_result.data[0]

        # Grade
        service = get_onsite_prep_grading_service()
        result = await service.transcribe_and_grade(
            audio_bytes=audio_bytes,
            mime_type=content_type,
            question_text=question["prompt_text"],
            category=question["category"],
            subcategory=question.get("subcategory"),
            context_hint=question.get("context_hint"),
            target_duration_seconds=question.get("target_duration_seconds", 120),
        )

        # Save attempt
        attempt_data = {
            "user_id": "00000000-0000-0000-0000-000000000001",  # Default user for now
            "question_id": str(question_id),
            "transcript": result.transcript,
            "dimensions": [
                {
                    "name": d.name,
                    "score": d.score,
                    "evidence": [{"quote": e.quote, "analysis": e.analysis} for e in d.evidence],
                    "summary": d.summary,
                }
                for d in result.dimensions
            ],
            "overall_score": result.overall_score,
            "verdict": result.verdict,
            "feedback": result.feedback,
            "strongest_moment": result.strongest_moment,
            "weakest_moment": result.weakest_moment,
            "follow_up_questions": result.follow_up_questions,
            "created_at": datetime.utcnow().isoformat(),
        }
        insert_result = supabase.table("onsite_prep_attempts").insert(attempt_data).execute()
        attempt_id = insert_result.data[0]["id"]

        # Best-effort audio archival. Grading should still succeed if the helper
        # is absent or the upload path is misconfigured in local/dev environments.
        try:
            from app.services.gcs_upload import upload_audio_to_gcs
        except ImportError:
            logger.warning("GCS upload helper unavailable; skipping audio archival for attempt %s", attempt_id)
        else:
            try:
                gcs_path = await upload_audio_to_gcs(
                    audio_bytes=audio_bytes,
                    user_id="00000000-0000-0000-0000-000000000001",
                    question_id=str(question_id),
                    attempt_id=attempt_id,
                    mime_type=content_type,
                )
                if gcs_path:
                    supabase.table("onsite_prep_attempts").update(
                        {"audio_gcs_path": gcs_path}
                    ).eq("id", attempt_id).execute()
            except Exception:
                logger.exception("Failed to upload onsite prep audio for attempt %s", attempt_id)

        # Invalidate dashboard cache
        _dashboard_cache.clear()

        return SubmitAudioResponse(attempt_id=attempt_id, grade=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to grade audio for question %s", question_id)
        raise HTTPException(status_code=500, detail=f"Failed to grade audio: {str(e)}")


@router.get("/onsite-prep/attempts/{attempt_id}", response_model=OnsitePrepAttempt)
async def get_attempt(
    attempt_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get a full attempt with follow-ups, phase submissions, and images."""
    try:
        result = supabase.table("onsite_prep_attempts").select("*").eq("id", str(attempt_id)).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Attempt not found")
        a = result.data[0]

        # Get follow-ups
        fu_result = supabase.table("onsite_prep_follow_ups").select("*").eq("attempt_id", str(attempt_id)).order("sort_order").execute()

        # Get phase submissions
        ps_result = supabase.table("onsite_prep_phase_submissions").select("*").eq("attempt_id", str(attempt_id)).order("phase_number").execute()

        # Get images
        img_result = supabase.table("onsite_prep_images").select("*").eq("attempt_id", str(attempt_id)).order("sort_order").execute()

        dimensions = None
        if a.get("dimensions"):
            dimensions = [
                DimensionScore(
                    name=d["name"],
                    score=d["score"],
                    evidence=[],
                    summary=d.get("summary", ""),
                )
                for d in a["dimensions"]
            ]

        follow_ups = [
            OnsitePrepFollowUp(
                id=fu["id"],
                attempt_id=fu["attempt_id"],
                question_text=fu["question_text"],
                transcript=fu.get("transcript"),
                score=fu.get("score"),
                feedback=fu.get("feedback"),
                ideal_answer=fu.get("ideal_answer"),
                addressed_gap=fu.get("addressed_gap", False),
                sort_order=fu.get("sort_order", 0),
                parent_follow_up_id=fu.get("parent_follow_up_id"),
            )
            for fu in fu_result.data
        ]

        phase_submissions = [
            OnsitePrepPhaseSubmission(
                id=ps["id"],
                attempt_id=ps["attempt_id"],
                phase_number=ps["phase_number"],
                transcript=ps.get("transcript"),
                dimensions=[DimensionScore(**d) for d in (ps.get("dimensions") or [])] if ps.get("dimensions") else None,
                overall_score=ps.get("overall_score"),
                verdict=ps.get("verdict"),
                feedback=ps.get("feedback"),
                strongest_moment=ps.get("strongest_moment"),
                weakest_moment=ps.get("weakest_moment"),
                audio_gcs_path=ps.get("audio_gcs_path"),
                duration_seconds=ps.get("duration_seconds"),
                created_at=ps.get("created_at"),
            )
            for ps in ps_result.data
        ]

        images = [
            OnsitePrepImage(
                id=img["id"],
                attempt_id=img.get("attempt_id"),
                phase_submission_id=img.get("phase_submission_id"),
                gcs_path=img["gcs_path"],
                filename=img["filename"],
                include_in_grading=img.get("include_in_grading", False),
                sort_order=img.get("sort_order", 0),
                created_at=img.get("created_at"),
            )
            for img in img_result.data
        ]

        # Parse ideal_response if present
        ideal_response = None
        if a.get("ideal_response"):
            ir = a["ideal_response"]
            from app.models.onsite_prep_schemas import IdealResponse as IR
            ideal_response = IR(
                summary=ir.get("summary", ""),
                outline=ir.get("outline", []),
                full_response=ir.get("full_response", ""),
            )

        return OnsitePrepAttempt(
            id=a["id"],
            user_id=a["user_id"],
            question_id=a["question_id"],
            mode=a.get("mode", "stand_and_deliver"),
            current_phase=a.get("current_phase", 0),
            transcript=a.get("transcript"),
            dimensions=dimensions,
            overall_score=a.get("overall_score"),
            verdict=a.get("verdict"),
            feedback=a.get("feedback"),
            strongest_moment=a.get("strongest_moment"),
            weakest_moment=a.get("weakest_moment"),
            duration_seconds=a.get("duration_seconds"),
            follow_up_questions=a.get("follow_up_questions", []),
            follow_ups=follow_ups,
            phase_submissions=phase_submissions,
            images=images,
            ideal_response=ideal_response,
            audio_gcs_path=a.get("audio_gcs_path"),
            created_at=a.get("created_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attempt: {str(e)}")


@router.post("/onsite-prep/attempts/{attempt_id}/ideal-response", response_model=IdealResponse)
async def generate_ideal_response(
    attempt_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Generate (or return cached) ideal L6 response for an attempt."""
    from app.services.onsite_prep_service import get_onsite_prep_grading_service

    try:
        # Get attempt
        a_result = supabase.table("onsite_prep_attempts").select("*").eq("id", str(attempt_id)).execute()
        if not a_result.data:
            raise HTTPException(status_code=404, detail="Attempt not found")
        attempt = a_result.data[0]

        # Return cached if already generated on the attempt
        if attempt.get("ideal_response"):
            data = attempt["ideal_response"]
            return IdealResponse(
                summary=data.get("summary", ""),
                outline=data.get("outline", []),
                full_response=data.get("full_response", ""),
            )

        # Get question for context (and pre-stored ideal_answer)
        q_result = supabase.table("onsite_prep_questions").select("*").eq("id", attempt["question_id"]).execute()
        if not q_result.data:
            raise HTTPException(status_code=404, detail="Question not found")
        question = q_result.data[0]

        # If question has a validated ideal_answer, return it directly
        if question.get("ideal_answer"):
            ia = question["ideal_answer"]
            ideal = IdealResponse(
                summary=ia.get("summary", ""),
                outline=ia.get("outline", []),
                full_response=ia.get("full_response", ""),
            )
            # Cache on the attempt for future lookups
            supabase.table("onsite_prep_attempts").update({
                "ideal_response": {
                    "summary": ideal.summary,
                    "outline": ideal.outline,
                    "full_response": ideal.full_response,
                }
            }).eq("id", str(attempt_id)).execute()
            return ideal

        if not attempt.get("transcript"):
            raise HTTPException(status_code=400, detail="Attempt has no transcript")

        # Generate via Gemini for non-LP questions
        service = get_onsite_prep_grading_service()
        ideal = await service.generate_ideal_response(
            question_text=question["prompt_text"],
            category=question["category"],
            subcategory=question.get("subcategory"),
            context_hint=question.get("context_hint"),
            transcript=attempt["transcript"],
            feedback=attempt.get("feedback", ""),
        )

        # Save to DB for caching
        supabase.table("onsite_prep_attempts").update({
            "ideal_response": {
                "summary": ideal.summary,
                "outline": ideal.outline,
                "full_response": ideal.full_response,
            }
        }).eq("id", str(attempt_id)).execute()

        return ideal
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate ideal response: {str(e)}")


@router.post("/onsite-prep/attempts/{attempt_id}/generate-follow-ups", response_model=list[OnsitePrepFollowUp])
async def generate_follow_ups(
    attempt_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Generate follow-up probes from an attempt's transcript and save them."""
    from app.services.onsite_prep_service import get_onsite_prep_grading_service

    try:
        # Get attempt
        a_result = supabase.table("onsite_prep_attempts").select("*").eq("id", str(attempt_id)).execute()
        if not a_result.data:
            raise HTTPException(status_code=404, detail="Attempt not found")
        attempt = a_result.data[0]

        if not attempt.get("transcript"):
            raise HTTPException(status_code=400, detail="Attempt has no transcript")

        # Get question for category info
        q_result = supabase.table("onsite_prep_questions").select("*").eq("id", attempt["question_id"]).execute()
        if not q_result.data:
            raise HTTPException(status_code=404, detail="Question not found")
        question = q_result.data[0]

        dimensions = [
            DimensionScore(
                name=d["name"],
                score=d["score"],
                evidence=[],
                summary=d.get("summary", ""),
            )
            for d in (attempt.get("dimensions") or [])
        ]
        service = get_onsite_prep_grading_service()
        probes = await service.generate_follow_up_probes(
            question_text=question["prompt_text"],
            transcript=attempt["transcript"],
            category=question["category"],
            dimensions=dimensions,
            feedback=attempt.get("feedback", ""),
            subcategory=question.get("subcategory"),
            context_hint=question.get("context_hint"),
            structured_probes=question.get("structured_probes") or [],
        )

        # Delete existing follow-ups for this attempt (idempotent)
        supabase.table("onsite_prep_follow_ups").delete().eq("attempt_id", str(attempt_id)).execute()

        # Save follow-ups
        follow_ups = []
        for i, probe_text in enumerate(probes):
            fu_data = {
                "attempt_id": str(attempt_id),
                "question_text": probe_text,
                "sort_order": i,
            }
            result = supabase.table("onsite_prep_follow_ups").insert(fu_data).execute()
            fu = result.data[0]
            follow_ups.append(OnsitePrepFollowUp(
                id=fu["id"],
                attempt_id=fu["attempt_id"],
                question_text=fu["question_text"],
                sort_order=fu.get("sort_order", 0),
            ))

        return follow_ups
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate follow-ups: {str(e)}")


@router.post("/onsite-prep/follow-ups/{follow_up_id}/submit-audio", response_model=ConversationalFollowUpResult)
async def submit_follow_up_audio(
    follow_up_id: UUID,
    audio: UploadFile = File(...),
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Submit audio for a follow-up probe, transcribe + grade, and optionally generate next probe."""
    from app.services.onsite_prep_service import get_onsite_prep_grading_service

    try:
        # Validate audio
        content_type = audio.content_type or "audio/webm"
        if content_type not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported audio type: {content_type}")

        audio_bytes = await audio.read()
        if len(audio_bytes) > MAX_AUDIO_SIZE:
            raise HTTPException(status_code=400, detail="Audio too large")

        # Get follow-up
        fu_result = supabase.table("onsite_prep_follow_ups").select("*").eq("id", str(follow_up_id)).execute()
        if not fu_result.data:
            raise HTTPException(status_code=404, detail="Follow-up not found")
        follow_up = fu_result.data[0]

        # Get attempt
        attempt_id = follow_up["attempt_id"]
        a_result = supabase.table("onsite_prep_attempts").select("*").eq("id", attempt_id).execute()
        if not a_result.data:
            raise HTTPException(status_code=404, detail="Attempt not found")
        attempt = a_result.data[0]

        # Get question
        q_result = supabase.table("onsite_prep_questions").select("*").eq("id", attempt["question_id"]).execute()
        question = q_result.data[0] if q_result.data else {"prompt_text": "", "category": "lp"}

        # Get all previous follow-ups for conversation context
        all_fus = supabase.table("onsite_prep_follow_ups").select("*").eq(
            "attempt_id", attempt_id
        ).order("sort_order").execute()
        previous_follow_ups = [
            fu for fu in all_fus.data if fu["id"] != str(follow_up_id) and fu.get("transcript")
        ]

        # Grade with conversational context
        service = get_onsite_prep_grading_service()
        result = await service.transcribe_and_grade_follow_up_conversational(
            audio_bytes=audio_bytes,
            mime_type=content_type,
            original_question=question["prompt_text"],
            original_transcript=attempt.get("transcript", ""),
            follow_up_question=follow_up["question_text"],
            category=question["category"],
            previous_follow_ups=previous_follow_ups,
        )

        # Update follow-up record
        update_data = {
            "transcript": result["transcript"],
            "score": result["score"],
            "feedback": result["feedback"],
            "addressed_gap": result["addressed_gap"],
        }
        # ideal_answer column may not exist yet if migration hasn't been applied
        try:
            supabase.table("onsite_prep_follow_ups").update({
                **update_data,
                "ideal_answer": result.get("ideal_answer", ""),
            }).eq("id", str(follow_up_id)).execute()
        except Exception:
            supabase.table("onsite_prep_follow_ups").update(update_data).eq("id", str(follow_up_id)).execute()

        # If next_probe returned and under cap, insert new follow-up
        next_follow_up = None
        if result.get("next_probe") and len(all_fus.data) < 8:
            max_sort = max((fu.get("sort_order", 0) for fu in all_fus.data), default=0)
            new_fu_data = {
                "attempt_id": attempt_id,
                "question_text": result["next_probe"],
                "sort_order": max_sort + 1,
                "parent_follow_up_id": str(follow_up_id),
            }
            new_fu_result = supabase.table("onsite_prep_follow_ups").insert(new_fu_data).execute()
            nfu = new_fu_result.data[0]
            next_follow_up = OnsitePrepFollowUp(
                id=nfu["id"],
                attempt_id=nfu["attempt_id"],
                question_text=nfu["question_text"],
                sort_order=nfu.get("sort_order", 0),
                parent_follow_up_id=str(follow_up_id),
            )

        return ConversationalFollowUpResult(
            transcript=result["transcript"],
            score=result["score"],
            feedback=result["feedback"],
            addressed_gap=result["addressed_gap"],
            ideal_answer=result.get("ideal_answer", ""),
            next_follow_up=next_follow_up,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to grade follow-up: {str(e)}")


@router.get("/onsite-prep/dashboard/{user_id}", response_model=OnsitePrepDashboard)
async def get_dashboard(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Dashboard stats: practiced count, avg score per category."""
    cache_key = str(user_id)
    now = time.monotonic()

    if cache_key in _dashboard_cache:
        expiry, cached = _dashboard_cache[cache_key]
        if now < expiry:
            return cached

    try:
        # Count all questions
        q_result = supabase.table("onsite_prep_questions").select("id, category", count="exact").execute()
        all_questions = q_result.data

        # Get all attempts for this user
        a_result = supabase.table("onsite_prep_attempts").select(
            "question_id, overall_score, duration_seconds"
        ).eq("user_id", str(user_id)).execute()
        attempts = a_result.data

        # Build practiced set and stats
        practiced_questions = set()
        scores = []
        durations = []
        cat_attempts: dict[str, list[float]] = {}

        # Map question_id to category
        q_cat_map = {q["id"]: q["category"] for q in all_questions}

        for a in attempts:
            practiced_questions.add(a["question_id"])
            if a.get("overall_score") is not None:
                scores.append(a["overall_score"])
                cat = q_cat_map.get(a["question_id"], "unknown")
                if cat not in cat_attempts:
                    cat_attempts[cat] = []
                cat_attempts[cat].append(a["overall_score"])
            if a.get("duration_seconds") is not None:
                durations.append(a["duration_seconds"])

        # Count questions per category
        cat_counts: dict[str, int] = {}
        for q in all_questions:
            cat = q["category"]
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        # Category labels
        cat_labels = {"lp": "LP Stories", "breadth": "ML Breadth", "depth": "ML Depth", "design": "System Design"}

        # Build category stats
        categories = []
        for cat in ["lp", "breadth", "depth", "design"]:
            cat_practiced = sum(1 for qid in practiced_questions if q_cat_map.get(qid) == cat)
            cat_scores = cat_attempts.get(cat, [])
            categories.append(CategoryStats(
                category=cat,
                label=cat_labels.get(cat, cat),
                total=cat_counts.get(cat, 0),
                practiced=cat_practiced,
                avg_score=round(sum(cat_scores) / len(cat_scores), 1) if cat_scores else None,
            ))

        dashboard = OnsitePrepDashboard(
            total_questions=len(all_questions),
            practiced_count=len(practiced_questions),
            avg_score=round(sum(scores) / len(scores), 1) if scores else None,
            avg_duration=round(sum(durations) / len(durations)) if durations else None,
            categories=categories,
        )

        _dashboard_cache[cache_key] = (now + _DASHBOARD_CACHE_TTL, dashboard)
        return dashboard
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")


@router.get("/onsite-prep/history/{user_id}", response_model=list[OnsitePrepAttemptHistory])
async def get_history(
    user_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get recent practice history for a user."""
    try:
        result = supabase.table("onsite_prep_attempts").select(
            "id, question_id, overall_score, verdict, duration_seconds, created_at, mode, current_phase"
        ).eq("user_id", str(user_id)).order("created_at", desc=True).limit(limit).execute()

        if not result.data:
            return []

        # Get question details for these attempts
        question_ids = list(set(a["question_id"] for a in result.data))
        q_result = supabase.table("onsite_prep_questions").select("id, prompt_text, category").in_("id", question_ids).execute()
        q_map = {q["id"]: q for q in q_result.data}

        return [
            OnsitePrepAttemptHistory(
                id=a["id"],
                question_id=a["question_id"],
                prompt_text=q_map.get(a["question_id"], {}).get("prompt_text", ""),
                category=q_map.get(a["question_id"], {}).get("category", ""),
                mode=a.get("mode", "stand_and_deliver"),
                phases_completed=max(0, (a.get("current_phase", 1) or 1) - 1) if a.get("mode") == "breakdown" else 0,
                overall_score=a.get("overall_score"),
                verdict=a.get("verdict"),
                duration_seconds=a.get("duration_seconds"),
                created_at=a.get("created_at"),
            )
            for a in result.data
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


# ─── Breakdown Mode Endpoints ───────────────────────────────────────────────


@router.post("/onsite-prep/questions/{question_id}/start-breakdown", response_model=CreateBreakdownAttemptResponse)
async def start_breakdown(
    question_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Create a new breakdown attempt for a design question."""
    try:
        q_result = supabase.table("onsite_prep_questions").select("category").eq("id", str(question_id)).execute()
        if not q_result.data:
            raise HTTPException(status_code=404, detail="Question not found")
        if q_result.data[0]["category"] != "design":
            raise HTTPException(status_code=400, detail="Breakdown mode is only available for design questions")

        attempt_data = {
            "user_id": "00000000-0000-0000-0000-000000000001",
            "question_id": str(question_id),
            "mode": "breakdown",
            "current_phase": 1,
            "created_at": datetime.utcnow().isoformat(),
        }
        insert_result = supabase.table("onsite_prep_attempts").insert(attempt_data).execute()
        attempt = insert_result.data[0]

        return CreateBreakdownAttemptResponse(
            attempt_id=attempt["id"],
            mode="breakdown",
            current_phase=1,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start breakdown: {str(e)}")


@router.post("/onsite-prep/attempts/{attempt_id}/phases/{phase_number}/submit-audio", response_model=SubmitPhaseAudioResponse)
async def submit_phase_audio(
    attempt_id: UUID,
    phase_number: int,
    audio: UploadFile = File(...),
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Submit audio for a breakdown phase. Validates phase ordering and gate."""
    from app.services.onsite_prep_service import get_onsite_prep_grading_service, OnsitePrepGradingService

    try:
        if phase_number < 1 or phase_number > 7:
            raise HTTPException(status_code=400, detail="Phase number must be 1-7")

        content_type = audio.content_type or "audio/webm"
        if content_type not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported audio type: {content_type}")

        audio_bytes = await audio.read()
        if len(audio_bytes) > MAX_AUDIO_SIZE:
            raise HTTPException(status_code=400, detail="Audio too large")

        # Get attempt
        a_result = supabase.table("onsite_prep_attempts").select("*").eq("id", str(attempt_id)).execute()
        if not a_result.data:
            raise HTTPException(status_code=404, detail="Attempt not found")
        attempt = a_result.data[0]

        if attempt.get("mode") != "breakdown":
            raise HTTPException(status_code=400, detail="This attempt is not in breakdown mode")

        current_phase = attempt.get("current_phase", 1)
        # Allow re-recording any phase up to and including current_phase
        # (re-record of a passed phase, or retry of current gated phase)
        if phase_number > current_phase:
            raise HTTPException(status_code=400, detail=f"Expected phase {current_phase} or earlier, got {phase_number}")

        # Get question for breakdown phases
        q_result = supabase.table("onsite_prep_questions").select("*").eq("id", attempt["question_id"]).execute()
        if not q_result.data:
            raise HTTPException(status_code=404, detail="Question not found")
        question = q_result.data[0]

        breakdown_phases = question.get("breakdown_phases") or []
        if phase_number > len(breakdown_phases):
            raise HTTPException(status_code=400, detail=f"Phase {phase_number} not defined for this question")

        phase_def = breakdown_phases[phase_number - 1]

        # Get previous phase summaries for context
        prev_result = supabase.table("onsite_prep_phase_submissions").select(
            "phase_number, overall_score, feedback"
        ).eq("attempt_id", str(attempt_id)).order("phase_number").execute()
        previous_summaries = [
            {
                "phase_number": ps["phase_number"],
                "phase_name": breakdown_phases[ps["phase_number"] - 1]["name"] if ps["phase_number"] <= len(breakdown_phases) else f"Phase {ps['phase_number']}",
                "score": ps.get("overall_score", 0),
                "feedback": ps.get("feedback", ""),
            }
            for ps in prev_result.data
        ]

        # Get images marked for grading on this phase
        image_contents = []
        image_mime_types = []
        # Will be linked after phase submission is created

        # Grade
        service = get_onsite_prep_grading_service()
        result = await service.transcribe_and_grade_phase(
            audio_bytes=audio_bytes,
            mime_type=content_type,
            question_text=question["prompt_text"],
            phase_number=phase_number,
            phase_name=phase_def["name"],
            phase_prompt=phase_def["prompt"],
            phase_rubric_dimensions=phase_def.get("rubric_dimensions", []),
            previous_phase_summaries=previous_summaries,
            image_contents=image_contents if image_contents else None,
            image_mime_types=image_mime_types if image_mime_types else None,
        )

        # Save phase submission (upsert in case of re-record)
        ps_data = {
            "attempt_id": str(attempt_id),
            "phase_number": phase_number,
            "transcript": result.transcript,
            "dimensions": [
                {"name": d.name, "score": d.score, "evidence": [{"quote": e.quote, "analysis": e.analysis} for e in d.evidence], "summary": d.summary}
                for d in result.dimensions
            ],
            "overall_score": result.overall_score,
            "verdict": result.verdict,
            "feedback": result.feedback,
            "strongest_moment": result.strongest_moment,
            "weakest_moment": result.weakest_moment,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Delete existing submission for this phase (re-record)
        supabase.table("onsite_prep_phase_submissions").delete().eq(
            "attempt_id", str(attempt_id)
        ).eq("phase_number", phase_number).execute()

        insert_result = supabase.table("onsite_prep_phase_submissions").insert(ps_data).execute()
        phase_sub_id = insert_result.data[0]["id"]

        # Gate check: >= 3.0 to proceed
        gate_passed = result.overall_score >= 3.0
        next_phase = None
        attempt_complete = False
        overall_score = None
        overall_verdict = None

        # Re-fetch current_phase in case it was already advanced past this phase
        a_refresh = supabase.table("onsite_prep_attempts").select("current_phase").eq("id", str(attempt_id)).execute()
        current_phase = a_refresh.data[0]["current_phase"] if a_refresh.data else phase_number

        if gate_passed:
            if phase_number < 7:
                next_phase = phase_number + 1
                # Only advance current_phase forward, never regress
                if next_phase > current_phase:
                    supabase.table("onsite_prep_attempts").update(
                        {"current_phase": next_phase}
                    ).eq("id", str(attempt_id)).execute()
            else:
                # All 7 phases done — compute overall
                all_ps = supabase.table("onsite_prep_phase_submissions").select(
                    "phase_number, overall_score"
                ).eq("attempt_id", str(attempt_id)).execute()
                phase_scores = {ps["phase_number"]: ps["overall_score"] for ps in all_ps.data if ps.get("overall_score") is not None}
                overall_score = OnsitePrepGradingService.compute_breakdown_overall_score(phase_scores)
                overall_verdict = OnsitePrepGradingService._compute_verdict(overall_score)
                attempt_complete = True

                supabase.table("onsite_prep_attempts").update({
                    "current_phase": 8,  # Signals complete
                    "overall_score": overall_score,
                    "verdict": overall_verdict,
                }).eq("id", str(attempt_id)).execute()

                _dashboard_cache.clear()

        # Best-effort audio archival
        try:
            from app.services.gcs_upload import upload_audio_to_gcs
            gcs_path = await upload_audio_to_gcs(
                audio_bytes=audio_bytes,
                user_id="00000000-0000-0000-0000-000000000001",
                question_id=attempt["question_id"],
                attempt_id=str(attempt_id),
                mime_type=content_type,
            )
            if gcs_path:
                supabase.table("onsite_prep_phase_submissions").update(
                    {"audio_gcs_path": gcs_path}
                ).eq("id", phase_sub_id).execute()
        except Exception:
            logger.exception("Failed to upload phase audio for attempt %s phase %d", attempt_id, phase_number)

        return SubmitPhaseAudioResponse(
            phase_submission_id=phase_sub_id,
            phase_number=phase_number,
            result=result,
            gate_passed=gate_passed,
            next_phase=next_phase,
            attempt_complete=attempt_complete,
            overall_score=overall_score,
            overall_verdict=overall_verdict,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to grade phase audio for attempt %s phase %d", attempt_id, phase_number)
        raise HTTPException(status_code=500, detail=f"Failed to grade phase audio: {str(e)}")


@router.get("/onsite-prep/attempts/{attempt_id}/phases", response_model=list[OnsitePrepPhaseSubmission])
async def get_phase_submissions(
    attempt_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get all phase submissions for a breakdown attempt."""
    try:
        result = supabase.table("onsite_prep_phase_submissions").select("*").eq(
            "attempt_id", str(attempt_id)
        ).order("phase_number").execute()

        return [
            OnsitePrepPhaseSubmission(
                id=ps["id"],
                attempt_id=ps["attempt_id"],
                phase_number=ps["phase_number"],
                transcript=ps.get("transcript"),
                dimensions=[DimensionScore(**d) for d in (ps.get("dimensions") or [])] if ps.get("dimensions") else None,
                overall_score=ps.get("overall_score"),
                verdict=ps.get("verdict"),
                feedback=ps.get("feedback"),
                strongest_moment=ps.get("strongest_moment"),
                weakest_moment=ps.get("weakest_moment"),
                audio_gcs_path=ps.get("audio_gcs_path"),
                duration_seconds=ps.get("duration_seconds"),
                created_at=ps.get("created_at"),
            )
            for ps in result.data
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get phase submissions: {str(e)}")


# ─── Image Endpoints ────────────────────────────────────────────────────────


@router.post("/onsite-prep/attempts/{attempt_id}/upload-image", response_model=ImageUploadResponse)
async def upload_attempt_image(
    attempt_id: UUID,
    image: UploadFile = File(...),
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Upload an image for a Stand & Deliver attempt."""
    try:
        content_type = image.content_type or "image/jpeg"
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported image type: {content_type}")

        image_bytes = await image.read()
        if len(image_bytes) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

        # Verify attempt exists
        a_result = supabase.table("onsite_prep_attempts").select("id").eq("id", str(attempt_id)).execute()
        if not a_result.data:
            raise HTTPException(status_code=404, detail="Attempt not found")

        from app.services.gcs_upload import upload_image_to_gcs
        gcs_path = await upload_image_to_gcs(
            image_bytes=image_bytes,
            user_id="00000000-0000-0000-0000-000000000001",
            attempt_id=str(attempt_id),
            filename=image.filename or "image.jpg",
            mime_type=content_type,
        )

        # Count existing images for sort order
        existing = supabase.table("onsite_prep_images").select("id", count="exact").eq("attempt_id", str(attempt_id)).execute()
        sort_order = existing.count or 0

        img_data = {
            "attempt_id": str(attempt_id),
            "gcs_path": gcs_path or "",
            "filename": image.filename or "image.jpg",
            "include_in_grading": False,
            "sort_order": sort_order,
        }
        insert_result = supabase.table("onsite_prep_images").insert(img_data).execute()

        return ImageUploadResponse(
            image_id=insert_result.data[0]["id"],
            gcs_path=gcs_path or "",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to upload image for attempt %s", attempt_id)
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@router.post("/onsite-prep/attempts/{attempt_id}/phases/{phase_number}/upload-image", response_model=ImageUploadResponse)
async def upload_phase_image(
    attempt_id: UUID,
    phase_number: int,
    image: UploadFile = File(...),
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Upload an image for a specific breakdown phase."""
    try:
        content_type = image.content_type or "image/jpeg"
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported image type: {content_type}")

        image_bytes = await image.read()
        if len(image_bytes) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

        # Get phase submission
        ps_result = supabase.table("onsite_prep_phase_submissions").select("id").eq(
            "attempt_id", str(attempt_id)
        ).eq("phase_number", phase_number).execute()

        phase_sub_id = ps_result.data[0]["id"] if ps_result.data else None

        from app.services.gcs_upload import upload_image_to_gcs
        gcs_path = await upload_image_to_gcs(
            image_bytes=image_bytes,
            user_id="00000000-0000-0000-0000-000000000001",
            attempt_id=str(attempt_id),
            filename=image.filename or "image.jpg",
            mime_type=content_type,
            phase_number=phase_number,
        )

        img_data = {
            "attempt_id": str(attempt_id),
            "phase_submission_id": phase_sub_id,
            "gcs_path": gcs_path or "",
            "filename": image.filename or "image.jpg",
            "include_in_grading": False,
            "sort_order": 0,
        }
        insert_result = supabase.table("onsite_prep_images").insert(img_data).execute()

        return ImageUploadResponse(
            image_id=insert_result.data[0]["id"],
            gcs_path=gcs_path or "",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to upload phase image for attempt %s phase %d", attempt_id, phase_number)
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@router.patch("/onsite-prep/images/{image_id}")
async def toggle_image_grading(
    image_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Toggle include_in_grading for an image."""
    try:
        result = supabase.table("onsite_prep_images").select("id, include_in_grading").eq("id", str(image_id)).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Image not found")

        current = result.data[0]["include_in_grading"]
        supabase.table("onsite_prep_images").update(
            {"include_in_grading": not current}
        ).eq("id", str(image_id)).execute()

        return {"id": str(image_id), "include_in_grading": not current}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle image grading: {str(e)}")
