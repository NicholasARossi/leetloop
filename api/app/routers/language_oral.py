"""Language Oral Practice endpoints — dashboard, recording sessions, async grading."""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File
from supabase import Client

from app.db.supabase import get_supabase
from app.models.language_oral_schemas import (
    ChapterInfo,
    OralDashboard,
    OralDimensionEvidence,
    OralDimensionScore,
    OralGrading,
    OralPrompt,
    OralSession,
    OralSessionCreate,
    StreakInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Audio validation
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/mp4", "audio/x-m4a", "audio/mpeg", "audio/wav", "audio/x-wav", "audio/ogg"}

# Dashboard cache
_dashboard_cache: dict[str, tuple[float, OralDashboard]] = {}
_DASHBOARD_CACHE_TTL = 120  # 2 minutes

# Chapter advancement threshold
CHAPTER_ADVANCE_THRESHOLD = 5  # recordings from current chapter before auto-advance

# Default user (single-user app)
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


def _build_prompt(row: dict) -> OralPrompt:
    """Build OralPrompt from a DB row."""
    return OralPrompt(
        id=row["id"],
        track_id=row["track_id"],
        chapter_ref=row["chapter_ref"],
        chapter_order=row["chapter_order"],
        prompt_text=row["prompt_text"],
        theme=row.get("theme"),
        grammar_targets=row.get("grammar_targets") or [],
        vocab_targets=row.get("vocab_targets") or [],
        suggested_duration_seconds=row.get("suggested_duration_seconds", 120),
        sort_order=row.get("sort_order", 0),
    )


def _build_session(row: dict, prompt: OralPrompt | None = None, grading: OralGrading | None = None) -> OralSession:
    """Build OralSession from a DB row."""
    return OralSession(
        id=row["id"],
        user_id=row["user_id"],
        prompt_id=row["prompt_id"],
        track_id=row["track_id"],
        chapter_ref=row["chapter_ref"],
        prompt=prompt,
        grading=grading,
        audio_duration_seconds=row.get("audio_duration_seconds"),
        status=row["status"],
        created_at=row.get("created_at"),
        graded_at=row.get("graded_at"),
    )


def _build_grading(row: dict) -> OralGrading:
    """Build OralGrading from a DB row."""
    scores_raw = row.get("scores") or {}
    scores = {}
    for dim_name, dim_data in scores_raw.items():
        if isinstance(dim_data, dict):
            evidence = [
                OralDimensionEvidence(quote=e.get("quote", ""), analysis=e.get("analysis", ""))
                for e in dim_data.get("evidence", [])
                if isinstance(e, dict)
            ]
            scores[dim_name] = OralDimensionScore(
                name=dim_name,
                score=float(dim_data.get("score", 5)),
                evidence=evidence,
                summary=dim_data.get("summary", ""),
            )
    return OralGrading(
        transcript=row.get("transcript") or "",
        scores=scores,
        overall_score=float(row.get("overall_score", 0)),
        verdict=row.get("verdict") or "needs_work",
        feedback=row.get("feedback") or "",
        strongest_moment=row.get("strongest_moment") or "",
        weakest_moment=row.get("weakest_moment") or "",
    )


def _get_user_settings(supabase: Client, user_id: str) -> dict:
    """Get or create user_language_settings row."""
    resp = (
        supabase.table("user_language_settings")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if resp.data:
        return resp.data[0]
    # Create default settings
    supabase.table("user_language_settings").upsert(
        {"user_id": user_id, "current_chapter_order": 1, "current_streak": 0, "longest_streak": 0},
        on_conflict="user_id",
    ).execute()
    return {"user_id": user_id, "current_chapter_order": 1, "current_streak": 0, "longest_streak": 0, "last_practice_date": None, "active_track_id": None}


# ============ Dashboard ============


@router.get("/language/oral/{user_id}/dashboard", response_model=OralDashboard)
async def get_oral_dashboard(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Oral practice dashboard: chapter progress, streak, today's prompts, recent sessions."""
    cache_key = str(user_id)
    now = time.monotonic()

    if cache_key in _dashboard_cache:
        expiry, cached = _dashboard_cache[cache_key]
        if now < expiry:
            return cached

    try:
        settings = _get_user_settings(supabase, str(user_id))
        active_track_id = settings.get("active_track_id")
        current_chapter_order = settings.get("current_chapter_order", 1) or 1

        if not active_track_id:
            return OralDashboard()

        # Get track info
        track_resp = (
            supabase.table("language_tracks")
            .select("id, name, topics, total_topics")
            .eq("id", active_track_id)
            .limit(1)
            .execute()
        )
        if not track_resp.data:
            return OralDashboard()

        track = track_resp.data[0]
        topics = sorted(track.get("topics", []), key=lambda t: t.get("order", 0))
        total_chapters = len(topics)

        # Find current chapter
        current_topic = None
        for t in topics:
            if t.get("order") == current_chapter_order:
                current_topic = t
                break
        if not current_topic and topics:
            current_topic = topics[min(current_chapter_order - 1, len(topics) - 1)]

        chapter_info = None
        if current_topic:
            # Completion: how many prompts from current chapter have been recorded
            recorded_count_resp = (
                supabase.table("language_oral_sessions")
                .select("id", count="exact")
                .eq("user_id", str(user_id))
                .eq("track_id", active_track_id)
                .eq("chapter_ref", current_topic["name"])
                .in_("status", ["grading", "graded"])
                .execute()
            )
            total_prompts_resp = (
                supabase.table("language_oral_prompts")
                .select("id", count="exact")
                .eq("track_id", active_track_id)
                .eq("chapter_ref", current_topic["name"])
                .execute()
            )
            recorded = recorded_count_resp.count or 0
            total_prompts = total_prompts_resp.count or 0
            pct = (recorded / total_prompts * 100) if total_prompts > 0 else 0.0

            chapter_info = ChapterInfo(
                name=current_topic["name"],
                order=current_chapter_order,
                total_chapters=total_chapters,
                completion_percentage=round(min(pct, 100.0), 1),
            )

        # Streak info
        streak_info = StreakInfo(
            current_streak=settings.get("current_streak", 0) or 0,
            longest_streak=settings.get("longest_streak", 0) or 0,
            last_practice_date=str(settings["last_practice_date"]) if settings.get("last_practice_date") else None,
        )

        # Today's available prompts: unrecorded prompts from current chapter
        todays_prompts = []
        if current_topic:
            # Get prompt IDs already used in sessions for this user + chapter
            used_resp = (
                supabase.table("language_oral_sessions")
                .select("prompt_id")
                .eq("user_id", str(user_id))
                .eq("track_id", active_track_id)
                .eq("chapter_ref", current_topic["name"])
                .execute()
            )
            used_prompt_ids = {s["prompt_id"] for s in (used_resp.data or [])}

            # Get all prompts for current chapter
            prompts_resp = (
                supabase.table("language_oral_prompts")
                .select("*")
                .eq("track_id", active_track_id)
                .eq("chapter_ref", current_topic["name"])
                .order("sort_order")
                .execute()
            )

            available = [p for p in (prompts_resp.data or []) if p["id"] not in used_prompt_ids]
            todays_prompts = [_build_prompt(p) for p in available[:3]]

        # Pending sessions (status = grading)
        pending_resp = (
            supabase.table("language_oral_sessions")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("status", "grading")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        pending_sessions = [_build_session(s) for s in (pending_resp.data or [])]

        # Recent graded sessions (last 10 with gradings)
        recent_resp = (
            supabase.table("language_oral_sessions")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("status", "graded")
            .order("graded_at", desc=True)
            .limit(10)
            .execute()
        )
        recent_sessions = []
        if recent_resp.data:
            session_ids = [s["id"] for s in recent_resp.data]
            gradings_resp = (
                supabase.table("language_oral_gradings")
                .select("*")
                .in_("session_id", session_ids)
                .execute()
            )
            grading_map = {g["session_id"]: g for g in (gradings_resp.data or [])}

            # Also fetch prompt details for recent sessions
            prompt_ids = list(set(s["prompt_id"] for s in recent_resp.data))
            prompts_for_recent = (
                supabase.table("language_oral_prompts")
                .select("*")
                .in_("id", prompt_ids)
                .execute()
            )
            prompt_map = {p["id"]: p for p in (prompts_for_recent.data or [])}

            for s in recent_resp.data:
                grading_row = grading_map.get(s["id"])
                grading = _build_grading(grading_row) if grading_row else None
                prompt_row = prompt_map.get(s["prompt_id"])
                prompt = _build_prompt(prompt_row) if prompt_row else None
                recent_sessions.append(_build_session(s, prompt=prompt, grading=grading))

        dashboard = OralDashboard(
            chapter=chapter_info,
            streak=streak_info,
            todays_prompts=todays_prompts,
            pending_sessions=pending_sessions,
            recent_sessions=recent_sessions,
        )

        _dashboard_cache[cache_key] = (now + _DASHBOARD_CACHE_TTL, dashboard)
        return dashboard

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get oral dashboard for user %s", user_id)
        raise HTTPException(status_code=500, detail=f"Failed to get oral dashboard: {str(e)}")


# ============ Sessions ============


@router.post("/language/oral/{user_id}/sessions", response_model=OralSession)
async def create_oral_session(
    user_id: UUID,
    request: OralSessionCreate,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Create a new oral session from a prompt."""
    try:
        # Validate prompt exists
        prompt_resp = (
            supabase.table("language_oral_prompts")
            .select("*")
            .eq("id", str(request.prompt_id))
            .limit(1)
            .execute()
        )
        if not prompt_resp.data:
            raise HTTPException(status_code=404, detail="Prompt not found")

        prompt_row = prompt_resp.data[0]

        # Create session
        session_data = {
            "user_id": str(user_id),
            "prompt_id": str(request.prompt_id),
            "track_id": prompt_row["track_id"],
            "chapter_ref": prompt_row["chapter_ref"],
            "status": "prompted",
        }
        result = supabase.table("language_oral_sessions").insert(session_data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create session")

        session_row = result.data[0]
        prompt = _build_prompt(prompt_row)
        return _build_session(session_row, prompt=prompt)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create oral session")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.post("/language/oral/sessions/{session_id}/upload-audio")
async def upload_oral_audio(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Upload audio for an oral session. Triggers async transcription + grading."""
    try:
        # Validate audio
        content_type = audio.content_type or "audio/webm"
        if content_type not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported audio type: {content_type}")

        audio_bytes = await audio.read()
        if len(audio_bytes) > MAX_AUDIO_SIZE:
            raise HTTPException(status_code=400, detail=f"Audio too large: {len(audio_bytes) / 1024 / 1024:.1f}MB. Max: 25MB")

        if len(audio_bytes) < 1000:
            raise HTTPException(status_code=400, detail="Audio too short")

        # Get session
        session_resp = (
            supabase.table("language_oral_sessions")
            .select("*")
            .eq("id", str(session_id))
            .limit(1)
            .execute()
        )
        if not session_resp.data:
            raise HTTPException(status_code=404, detail="Session not found")

        session = session_resp.data[0]
        if session["status"] not in ("prompted", "failed"):
            raise HTTPException(status_code=400, detail=f"Session already has status '{session['status']}', cannot upload audio")

        # Update status to grading
        supabase.table("language_oral_sessions").update(
            {"status": "grading"}
        ).eq("id", str(session_id)).execute()

        # Fire background task for transcription + grading
        background_tasks.add_task(
            _async_transcribe_and_grade,
            session_id=str(session_id),
            user_id=session["user_id"],
            prompt_id=session["prompt_id"],
            track_id=session["track_id"],
            chapter_ref=session["chapter_ref"],
            audio_bytes=audio_bytes,
            mime_type=content_type,
        )

        # Update streak
        _update_streak(supabase, session["user_id"])

        # Invalidate dashboard cache
        _dashboard_cache.pop(session["user_id"], None)

        return {"session_id": str(session_id), "status": "grading"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to upload audio for session %s", session_id)
        raise HTTPException(status_code=500, detail=f"Failed to upload audio: {str(e)}")


@router.get("/language/oral/sessions/{session_id}", response_model=OralSession)
async def get_oral_session(
    session_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get a session with its prompt and grading (if available)."""
    try:
        session_resp = (
            supabase.table("language_oral_sessions")
            .select("*")
            .eq("id", str(session_id))
            .limit(1)
            .execute()
        )
        if not session_resp.data:
            raise HTTPException(status_code=404, detail="Session not found")

        session_row = session_resp.data[0]

        # Get prompt
        prompt_resp = (
            supabase.table("language_oral_prompts")
            .select("*")
            .eq("id", session_row["prompt_id"])
            .limit(1)
            .execute()
        )
        prompt = _build_prompt(prompt_resp.data[0]) if prompt_resp.data else None

        # Get grading if exists
        grading = None
        if session_row["status"] == "graded":
            grading_resp = (
                supabase.table("language_oral_gradings")
                .select("*")
                .eq("session_id", str(session_id))
                .limit(1)
                .execute()
            )
            if grading_resp.data:
                grading = _build_grading(grading_resp.data[0])

        return _build_session(session_row, prompt=prompt, grading=grading)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.get("/language/oral/{user_id}/sessions", response_model=list[OralSession])
async def list_oral_sessions(
    user_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """List user's oral sessions (most recent first)."""
    try:
        sessions_resp = (
            supabase.table("language_oral_sessions")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        if not sessions_resp.data:
            return []

        # Batch-fetch prompts and gradings
        prompt_ids = list(set(s["prompt_id"] for s in sessions_resp.data))
        session_ids = [s["id"] for s in sessions_resp.data]

        prompts_resp = (
            supabase.table("language_oral_prompts")
            .select("*")
            .in_("id", prompt_ids)
            .execute()
        )
        prompt_map = {p["id"]: p for p in (prompts_resp.data or [])}

        graded_ids = [s["id"] for s in sessions_resp.data if s["status"] == "graded"]
        grading_map = {}
        if graded_ids:
            gradings_resp = (
                supabase.table("language_oral_gradings")
                .select("*")
                .in_("session_id", graded_ids)
                .execute()
            )
            grading_map = {g["session_id"]: g for g in (gradings_resp.data or [])}

        results = []
        for s in sessions_resp.data:
            prompt_row = prompt_map.get(s["prompt_id"])
            prompt = _build_prompt(prompt_row) if prompt_row else None
            grading_row = grading_map.get(s["id"])
            grading = _build_grading(grading_row) if grading_row else None
            results.append(_build_session(s, prompt=prompt, grading=grading))

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


# ============ Streak ============


@router.get("/language/oral/{user_id}/streak", response_model=StreakInfo)
async def get_streak(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get user's oral practice streak."""
    try:
        settings = _get_user_settings(supabase, str(user_id))
        return StreakInfo(
            current_streak=settings.get("current_streak", 0) or 0,
            longest_streak=settings.get("longest_streak", 0) or 0,
            last_practice_date=str(settings["last_practice_date"]) if settings.get("last_practice_date") else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get streak: {str(e)}")


# ============ Background Task ============


async def _async_transcribe_and_grade(
    session_id: str,
    user_id: str,
    prompt_id: str,
    track_id: str,
    chapter_ref: str,
    audio_bytes: bytes,
    mime_type: str,
):
    """Background task: transcribe audio, grade, store results, check chapter advancement."""
    from app.db.supabase import get_supabase_client
    from app.services.language_oral_service import get_language_oral_service

    sb = get_supabase_client()
    service = get_language_oral_service()

    try:
        # 1. Transcribe
        transcript = await service.transcribe_french(audio_bytes, mime_type)

        if not transcript or len(transcript.strip()) < 10:
            sb.table("language_oral_sessions").update(
                {"status": "failed"}
            ).eq("id", session_id).execute()
            logger.warning("Transcription too short for session %s", session_id)
            return

        # 2. Get prompt details for grading context
        prompt_resp = (
            sb.table("language_oral_prompts")
            .select("prompt_text, grammar_targets, vocab_targets, chapter_ref")
            .eq("id", prompt_id)
            .limit(1)
            .execute()
        )
        prompt_data = prompt_resp.data[0] if prompt_resp.data else {}

        # 3. Grade
        grading = await service.grade_monologue(
            transcript=transcript,
            prompt_text=prompt_data.get("prompt_text", ""),
            grammar_targets=prompt_data.get("grammar_targets") or [],
            vocab_targets=prompt_data.get("vocab_targets") or [],
            chapter_context=chapter_ref,
        )

        # 4. Store grading
        scores_json = {}
        for dim_name, dim_score in grading.scores.items():
            scores_json[dim_name] = {
                "score": dim_score.score,
                "evidence": [{"quote": e.quote, "analysis": e.analysis} for e in dim_score.evidence],
                "summary": dim_score.summary,
            }

        grading_data = {
            "session_id": session_id,
            "transcript": grading.transcript,
            "scores": scores_json,
            "overall_score": grading.overall_score,
            "verdict": grading.verdict,
            "feedback": grading.feedback,
            "strongest_moment": grading.strongest_moment,
            "weakest_moment": grading.weakest_moment,
        }
        sb.table("language_oral_gradings").insert(grading_data).execute()

        # 5. Update session status
        sb.table("language_oral_sessions").update(
            {"status": "graded", "graded_at": datetime.utcnow().isoformat()}
        ).eq("id", session_id).execute()

        # 6. Archive audio (best-effort)
        try:
            gcs_path = await service.archive_audio(audio_bytes, mime_type, user_id, session_id)
            if gcs_path:
                sb.table("language_oral_sessions").update(
                    {"audio_gcs_path": gcs_path}
                ).eq("id", session_id).execute()
        except Exception:
            logger.warning("Failed to archive audio for session %s", session_id)

        # 7. Check chapter advancement
        _check_chapter_advancement(sb, user_id, track_id, chapter_ref)

        # 8. Invalidate dashboard cache
        _dashboard_cache.pop(user_id, None)

        logger.info("Graded oral session %s: overall=%.1f verdict=%s", session_id, grading.overall_score, grading.verdict)

    except Exception as e:
        logger.exception("Background grading failed for session %s", session_id)
        try:
            sb.table("language_oral_sessions").update(
                {"status": "failed"}
            ).eq("id", session_id).execute()
        except Exception:
            pass


# ============ Helpers ============


def _update_streak(supabase: Client, user_id: str):
    """Update user's practice streak after a recording."""
    try:
        settings = _get_user_settings(supabase, user_id)
        today = date.today()
        last_practice = settings.get("last_practice_date")

        current_streak = settings.get("current_streak", 0) or 0
        longest_streak = settings.get("longest_streak", 0) or 0

        if last_practice:
            if isinstance(last_practice, str):
                last_practice = date.fromisoformat(last_practice)

            if last_practice == today:
                # Already practiced today, no change
                return
            elif last_practice == today - timedelta(days=1):
                # Consecutive day
                current_streak += 1
            else:
                # Streak broken
                current_streak = 1
        else:
            # First practice ever
            current_streak = 1

        longest_streak = max(longest_streak, current_streak)

        supabase.table("user_language_settings").update({
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "last_practice_date": today.isoformat(),
        }).eq("user_id", user_id).execute()

    except Exception as e:
        logger.warning("Failed to update streak for user %s: %s", user_id, e)


def _check_chapter_advancement(supabase: Client, user_id: str, track_id: str, chapter_ref: str):
    """Check if user should advance to next chapter."""
    try:
        settings = _get_user_settings(supabase, user_id)
        current_chapter_order = settings.get("current_chapter_order", 1) or 1

        # Count recordings from this chapter
        count_resp = (
            supabase.table("language_oral_sessions")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("track_id", track_id)
            .eq("chapter_ref", chapter_ref)
            .in_("status", ["grading", "graded"])
            .execute()
        )
        recorded = count_resp.count or 0

        if recorded < CHAPTER_ADVANCE_THRESHOLD:
            return

        # Get track to find the chapter order for this chapter_ref
        track_resp = (
            supabase.table("language_tracks")
            .select("topics")
            .eq("id", track_id)
            .limit(1)
            .execute()
        )
        if not track_resp.data:
            return

        topics = track_resp.data[0].get("topics", [])
        chapter_order_for_ref = None
        for t in topics:
            if t.get("name") == chapter_ref:
                chapter_order_for_ref = t.get("order")
                break

        if chapter_order_for_ref is None:
            return

        # Only advance if user is currently on this chapter (don't regress)
        if chapter_order_for_ref != current_chapter_order:
            return

        next_order = current_chapter_order + 1
        max_order = max((t.get("order", 0) for t in topics), default=0)
        if next_order > max_order:
            # Book complete — keep at max
            return

        supabase.table("user_language_settings").update({
            "current_chapter_order": next_order,
        }).eq("user_id", user_id).execute()

        logger.info("User %s advanced to chapter %d", user_id, next_order)

    except Exception as e:
        logger.warning("Failed to check chapter advancement: %s", e)
