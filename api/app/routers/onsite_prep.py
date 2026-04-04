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
    DesignPhase,
    DimensionScore,
    IdealResponse,
    OnsitePrepAttempt,
    OnsitePrepAttemptHistory,
    OnsitePrepDashboard,
    OnsitePrepFollowUp,
    OnsitePrepFollowUpResult,
    OnsitePrepGradeResult,
    OnsitePrepQuestion,
    RubricDimension,
    SubmitAudioResponse,
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
        structured_probes=q.get("structured_probes") or [],
    )


# Audio validation
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/mp4", "audio/x-m4a", "audio/mpeg", "audio/wav", "audio/x-wav"}

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
    """Get a full attempt with follow-ups."""
    try:
        result = supabase.table("onsite_prep_attempts").select("*").eq("id", str(attempt_id)).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Attempt not found")
        a = result.data[0]

        # Get follow-ups
        fu_result = supabase.table("onsite_prep_follow_ups").select("*").eq("attempt_id", str(attempt_id)).order("sort_order").execute()

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
            "id, question_id, overall_score, verdict, duration_seconds, created_at"
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
                overall_score=a.get("overall_score"),
                verdict=a.get("verdict"),
                duration_seconds=a.get("duration_seconds"),
                created_at=a.get("created_at"),
            )
            for a in result.data
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")
