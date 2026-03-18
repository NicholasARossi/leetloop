"""System Design Review endpoints."""

import time
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from supabase import Client

from app.db.supabase import get_supabase
from app.models.system_design_schemas import (
    CompleteReviewRequest,
    CompleteReviewResponse,
    FollowUpGradeResult,
    NextTopicInfo,
    DimensionEvidence,
    DimensionScore,
    OralFollowUp,
    OralGradeResult,
    OralSession,
    OralSessionCreate,
    OralSessionSummary,
    OralSubQuestion,
    RubricWeights,
    SetActiveTrackRequest,
    SystemDesignDashboardSummary,
    SystemDesignReviewItem,
    SystemDesignTrack,
    TopicInfo,
    TrackProgressResponse,
    TrackSummary,
    UserTrackProgress,
)
from app.services.system_design_service import get_system_design_service

router = APIRouter()

# In-memory TTL cache for system-design dashboard: {user_id_str: (expiry_timestamp, response)}
_sd_dashboard_cache: dict[str, tuple[float, SystemDesignDashboardSummary]] = {}
_SD_DASHBOARD_CACHE_TTL = 300  # 5 minutes


def _build_oral_sub_question(
    q: dict,
    include_full_grade: bool = True,
    follow_ups: list[dict] | None = None,
) -> OralSubQuestion:
    """Build OralSubQuestion from a DB row. If include_full_grade, includes dimension_scores etc."""
    base = dict(
        id=q["id"],
        part_number=q["part_number"],
        question_text=q["question_text"],
        focus_area=q["focus_area"],
        key_concepts=q.get("key_concepts") or [],
        suggested_duration_minutes=q.get("suggested_duration_minutes", 4),
        status=q["status"],
        overall_score=q.get("overall_score"),
        verdict=q.get("verdict"),
        transcript=q.get("transcript"),
        feedback=q.get("feedback"),
    )
    if include_full_grade and q.get("status") == "graded":
        raw_dims = q.get("dimension_scores") or []
        base["dimension_scores"] = [
            DimensionScore(
                name=d.get("name", ""),
                score=d.get("score", 0),
                evidence=[
                    DimensionEvidence(quote=e.get("quote", ""), analysis=e.get("analysis", ""))
                    for e in (d.get("evidence") or [])
                ],
                summary=d.get("summary", ""),
            )
            for d in raw_dims
        ]
        base["missed_concepts"] = q.get("missed_concepts") or []
        base["strongest_moment"] = q.get("strongest_moment")
        base["weakest_moment"] = q.get("weakest_moment")
        base["follow_up_questions"] = q.get("follow_up_questions") or []

    # Attach follow-up responses if provided
    if follow_ups is not None:
        base["follow_up_responses"] = [
            OralFollowUp(
                id=fu["id"],
                question_id=fu["question_id"],
                follow_up_index=fu["follow_up_index"],
                follow_up_text=fu["follow_up_text"],
                status=fu["status"],
                transcript=fu.get("transcript"),
                score=fu.get("score"),
                feedback=fu.get("feedback"),
                addressed_gap=fu.get("addressed_gap"),
                graded_at=fu.get("graded_at"),
            )
            for fu in follow_ups
        ]

    return OralSubQuestion(**base)


# ============ Tracks ============


@router.get("/system-design/tracks", response_model=list[TrackSummary])
async def list_tracks(
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """List all available system design tracks."""
    try:
        response = (
            supabase.table("system_design_tracks")
            .select("id, name, description, track_type, total_topics")
            .order("name")
            .execute()
        )
        return [TrackSummary(**t) for t in response.data] if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tracks: {str(e)}")


@router.get("/system-design/tracks/{track_id}", response_model=SystemDesignTrack)
async def get_track(
    track_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get track details with topics."""
    try:
        response = (
            supabase.table("system_design_tracks")
            .select("*")
            .eq("id", str(track_id))
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Track not found")

        data = response.data
        topics = [TopicInfo(**t) for t in data.get("topics", [])]
        rubric = RubricWeights(**data.get("rubric", {}))

        return SystemDesignTrack(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            track_type=data["track_type"],
            topics=topics,
            total_topics=data.get("total_topics", 0),
            rubric=rubric,
            created_at=data.get("created_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get track: {str(e)}")


@router.get("/system-design/tracks/{track_id}/progress/{user_id}", response_model=TrackProgressResponse)
async def get_track_progress(
    track_id: UUID,
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get user's progress on a specific track."""
    try:
        # Get track
        track_response = (
            supabase.table("system_design_tracks")
            .select("*")
            .eq("id", str(track_id))
            .single()
            .execute()
        )

        if not track_response.data:
            raise HTTPException(status_code=404, detail="Track not found")

        track_data = track_response.data
        topics = [TopicInfo(**t) for t in track_data.get("topics", [])]
        rubric = RubricWeights(**track_data.get("rubric", {}))

        track = SystemDesignTrack(
            id=track_data["id"],
            name=track_data["name"],
            description=track_data.get("description"),
            track_type=track_data["track_type"],
            topics=topics,
            total_topics=track_data.get("total_topics", 0),
            rubric=rubric,
            created_at=track_data.get("created_at"),
        )

        # Get user progress (use limit(1) instead of maybe_single to avoid None response)
        progress_response = (
            supabase.table("user_track_progress")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("track_id", str(track_id))
            .limit(1)
            .execute()
        )

        progress = None
        completion_percentage = 0.0
        next_topic = None

        if progress_response.data:
            progress = UserTrackProgress(**progress_response.data[0])
            completed = len(progress.completed_topics)
            total = track.total_topics
            completion_percentage = (completed / total * 100) if total > 0 else 0.0

            # Find next uncompleted topic
            for topic in topics:
                if topic.name not in progress.completed_topics:
                    next_topic = topic.name
                    break
        else:
            # No progress yet, first topic is next
            next_topic = topics[0].name if topics else None

        return TrackProgressResponse(
            track=track,
            progress=progress,
            completion_percentage=completion_percentage,
            next_topic=next_topic,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get track progress: {str(e)}")


# ============ Reviews ============


@router.get("/system-design/{user_id}/reviews", response_model=list[SystemDesignReviewItem])
async def get_due_reviews(
    user_id: UUID,
    limit: int = 10,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get system design topics due for review."""
    try:
        response = supabase.rpc(
            "get_due_system_design_reviews",
            {"p_user_id": str(user_id), "p_limit": limit}
        ).execute()

        return [SystemDesignReviewItem(**r) for r in response.data] if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reviews: {str(e)}")


@router.post("/system-design/reviews/{review_id}/complete", response_model=CompleteReviewResponse)
async def complete_review(
    review_id: UUID,
    request: CompleteReviewRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Mark a review as complete (pass/fail)."""
    try:
        # Use RPC function for spaced repetition update
        supabase.rpc(
            "complete_system_design_review",
            {"p_review_id": str(review_id), "p_success": request.success}
        ).execute()

        # Get updated review
        updated = (
            supabase.table("system_design_review_queue")
            .select("*")
            .eq("id", str(review_id))
            .single()
            .execute()
        )

        if not updated.data:
            raise HTTPException(status_code=404, detail="Review not found")

        return CompleteReviewResponse(
            id=review_id,
            next_review=updated.data["next_review"],
            new_interval_days=updated.data["interval_days"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete review: {str(e)}")


def _update_track_progress(
    supabase: Client,
    user_id: str,
    track_id: str,
    topic: str,
    score: float,
):
    """Update user's track progress after completing a session."""
    try:
        # Get existing progress (use limit(1) instead of maybe_single)
        progress_response = (
            supabase.table("user_track_progress")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("track_id", str(track_id))
            .limit(1)
            .execute()
        )

        if progress_response.data:
            # Update existing
            progress = progress_response.data[0]
            completed = set(progress.get("completed_topics", []))
            completed.add(topic)

            sessions = progress.get("sessions_completed", 0) + 1
            current_avg = progress.get("average_score", 0.0)
            new_avg = ((current_avg * (sessions - 1)) + score) / sessions

            supabase.table("user_track_progress").update({
                "completed_topics": list(completed),
                "sessions_completed": sessions,
                "average_score": new_avg,
                "last_activity_at": datetime.utcnow().isoformat(),
            }).eq("id", progress["id"]).execute()
        else:
            # Create new
            supabase.table("user_track_progress").insert({
                "user_id": str(user_id),
                "track_id": str(track_id),
                "completed_topics": [topic],
                "sessions_completed": 1,
                "average_score": score,
            }).execute()
    except Exception as e:
        print(f"Failed to update track progress: {e}")


# ============ Dashboard Integration ============


@router.get("/system-design/{user_id}/dashboard", response_model=SystemDesignDashboardSummary)
async def get_dashboard_summary(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get system design summary for dashboard display."""
    from datetime import timedelta

    cache_key = str(user_id)
    cached = _sd_dashboard_cache.get(cache_key)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    try:
        # Get user settings
        settings_response = (
            supabase.table("user_system_design_settings")
            .select("*")
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )

        has_active_track = False
        active_track = None
        next_topic = None
        track_data = None

        if settings_response.data and settings_response.data[0].get("active_track_id"):
            has_active_track = True
            active_track_id = settings_response.data[0]["active_track_id"]

            # Get active track details
            track_response = (
                supabase.table("system_design_tracks")
                .select("id, name, description, track_type, total_topics, topics")
                .eq("id", active_track_id)
                .single()
                .execute()
            )

            if track_response.data:
                track_data = track_response.data
                active_track = TrackSummary(
                    id=track_data["id"],
                    name=track_data["name"],
                    description=track_data.get("description"),
                    track_type=track_data["track_type"],
                    total_topics=track_data.get("total_topics", 0),
                )

                # Get user's progress to find next topic
                progress_response = (
                    supabase.table("user_track_progress")
                    .select("completed_topics")
                    .eq("user_id", str(user_id))
                    .eq("track_id", active_track_id)
                    .limit(1)
                    .execute()
                )

                completed_topics = []
                if progress_response.data:
                    completed_topics = progress_response.data[0].get("completed_topics", [])

                # Find next uncompleted topic
                topics = track_data.get("topics", [])
                for topic in sorted(topics, key=lambda t: t.get("order", 0)):
                    if topic.get("name") not in completed_topics:
                        next_topic = NextTopicInfo(
                            track_id=UUID(track_data["id"]),
                            track_name=track_data["name"],
                            track_type=track_data["track_type"],
                            topic_name=topic.get("name", ""),
                            topic_order=topic.get("order", 0),
                            topic_difficulty=topic.get("difficulty", "medium"),
                            example_systems=topic.get("example_systems", []),
                            topics_completed=len(completed_topics),
                            total_topics=track_data.get("total_topics", 0),
                        )
                        break

        # Get or create today's oral session
        oral_session_model = None
        if has_active_track and next_topic:
            try:
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                existing_oral = (
                    supabase.table("system_design_oral_sessions")
                    .select("*")
                    .eq("user_id", str(user_id))
                    .gte("created_at", today_start)
                    .in_("status", ["active", "completed"])
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )

                if existing_oral.data:
                    os_data = existing_oral.data[0]
                    oq_response = (
                        supabase.table("system_design_oral_questions")
                        .select("*")
                        .eq("session_id", os_data["id"])
                        .order("part_number")
                        .execute()
                    )
                    oral_session_model = OralSession(
                        id=os_data["id"],
                        user_id=os_data["user_id"],
                        track_id=os_data["track_id"],
                        topic=os_data["topic"],
                        scenario=os_data.get("scenario", ""),
                        status=os_data["status"],
                        questions=[_build_oral_sub_question(q) for q in (oq_response.data or [])],
                        created_at=os_data["created_at"],
                    )
                else:
                    # Auto-generate a new oral session for today
                    import uuid as _uuid
                    service = get_system_design_service()
                    track_type = track_data.get("track_type", "mle") if track_data else "mle"
                    scenario, sub_questions = await service.generate_oral_questions(
                        next_topic.topic_name, track_type
                    )

                    session_data = {
                        "user_id": str(user_id),
                        "track_id": str(next_topic.track_id),
                        "topic": next_topic.topic_name,
                        "scenario": scenario,
                        "status": "active",
                    }
                    new_session = supabase.table("system_design_oral_sessions").insert(session_data).execute()

                    if new_session.data:
                        ns = new_session.data[0]
                        q_models = []
                        for sq in sub_questions:
                            q_data = {
                                "session_id": ns["id"],
                                "part_number": sq["part_number"],
                                "question_text": sq["question_text"],
                                "focus_area": sq["focus_area"],
                                "key_concepts": sq["key_concepts"],
                                "suggested_duration_minutes": sq.get("suggested_duration_minutes", 4),
                                "status": "pending",
                            }
                            q_resp = supabase.table("system_design_oral_questions").insert(q_data).execute()
                            if q_resp.data:
                                q_models.append(_build_oral_sub_question(q_resp.data[0], include_full_grade=False))

                        oral_session_model = OralSession(
                            id=ns["id"],
                            user_id=ns["user_id"],
                            track_id=ns["track_id"],
                            topic=ns["topic"],
                            scenario=ns.get("scenario", ""),
                            status=ns["status"],
                            questions=q_models,
                            created_at=ns["created_at"],
                        )
            except Exception:
                # Don't fail the whole dashboard if oral session creation fails
                pass

        # Get reviews due
        reviews_response = supabase.rpc(
            "get_due_system_design_reviews",
            {"p_user_id": str(user_id), "p_limit": 5}
        ).execute()

        reviews_due = []
        if reviews_response.data:
            reviews_due = [SystemDesignReviewItem(**r) for r in reviews_response.data]

        # Get recent oral sessions this week
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        oral_sessions_response = (
            supabase.table("system_design_oral_sessions")
            .select("id", count="exact")
            .eq("user_id", str(user_id))
            .gte("created_at", week_ago)
            .execute()
        )
        sessions_this_week = oral_sessions_response.count or 0

        # Get most recent oral score
        recent_score = None
        recent_oral_response = (
            supabase.table("system_design_oral_questions")
            .select("overall_score, graded_at, session_id")
            .eq("status", "graded")
            .order("graded_at", desc=True)
            .limit(1)
            .execute()
        )
        if recent_oral_response.data:
            oral_q = recent_oral_response.data[0]
            oral_session_check = (
                supabase.table("system_design_oral_sessions")
                .select("user_id")
                .eq("id", oral_q["session_id"])
                .eq("user_id", str(user_id))
                .limit(1)
                .execute()
            )
            if oral_session_check.data:
                recent_score = oral_q["overall_score"]

        response = SystemDesignDashboardSummary(
            has_active_track=has_active_track,
            active_track=active_track,
            next_topic=next_topic,
            oral_session=oral_session_model,
            reviews_due_count=len(reviews_due),
            reviews_due=reviews_due,
            recent_score=recent_score,
            sessions_this_week=sessions_this_week,
        )
        _sd_dashboard_cache[cache_key] = (time.monotonic() + _SD_DASHBOARD_CACHE_TTL, response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard summary: {str(e)}")


@router.put("/system-design/{user_id}/active-track")
async def set_active_track(
    user_id: UUID,
    request: SetActiveTrackRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Set user's active system design track."""
    try:
        # Check if track exists (if setting one)
        if request.track_id:
            track_response = (
                supabase.table("system_design_tracks")
                .select("id, name")
                .eq("id", str(request.track_id))
                .single()
                .execute()
            )
            if not track_response.data:
                raise HTTPException(status_code=404, detail="Track not found")

        # Upsert settings
        settings_data = {
            "user_id": str(user_id),
            "active_track_id": str(request.track_id) if request.track_id else None,
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = (
            supabase.table("user_system_design_settings")
            .upsert(settings_data, on_conflict="user_id")
            .execute()
        )

        track_name = None
        if request.track_id and track_response.data:
            track_name = track_response.data.get("name")

        return {
            "success": True,
            "active_track_id": str(request.track_id) if request.track_id else None,
            "track_name": track_name,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set active track: {str(e)}")


@router.get("/system-design/{user_id}/active-track")
async def get_active_track(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get user's active system design track."""
    try:
        settings_response = (
            supabase.table("user_system_design_settings")
            .select("active_track_id")
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )

        if not settings_response.data or not settings_response.data[0].get("active_track_id"):
            return {"active_track_id": None, "track": None}

        active_track_id = settings_response.data[0]["active_track_id"]

        # Get track details
        track_response = (
            supabase.table("system_design_tracks")
            .select("*")
            .eq("id", active_track_id)
            .single()
            .execute()
        )

        if not track_response.data:
            return {"active_track_id": None, "track": None}

        track_data = track_response.data
        return {
            "active_track_id": active_track_id,
            "track": TrackSummary(
                id=track_data["id"],
                name=track_data["name"],
                description=track_data.get("description"),
                track_type=track_data["track_type"],
                total_topics=track_data.get("total_topics", 0),
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active track: {str(e)}")


# ============ Oral System Design Sessions ============

ALLOWED_AUDIO_TYPES = {
    "audio/webm", "audio/mp4", "audio/x-m4a", "audio/mpeg",
    "audio/wav", "audio/x-wav", "audio/ogg", "audio/m4a",
}
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB


@router.post("/system-design/{user_id}/oral-session", response_model=OralSession)
async def create_oral_session(
    user_id: UUID,
    request: OralSessionCreate,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Create a new oral practice session with 3 focused sub-questions."""
    try:
        # Get track info
        track_response = (
            supabase.table("system_design_tracks")
            .select("*")
            .eq("id", str(request.track_id))
            .single()
            .execute()
        )

        if not track_response.data:
            raise HTTPException(status_code=404, detail="Track not found")

        track_data = track_response.data

        # Generate oral questions via Gemini
        service = get_system_design_service()
        scenario, sub_questions = await service.generate_oral_questions(
            topic=request.topic,
            track_type=track_data["track_type"],
        )

        # Insert session
        session_data = {
            "user_id": str(user_id),
            "track_id": str(request.track_id),
            "topic": request.topic,
            "scenario": scenario,
            "status": "active",
        }

        session_response = (
            supabase.table("system_design_oral_sessions")
            .insert(session_data)
            .execute()
        )

        if not session_response.data:
            raise HTTPException(status_code=500, detail="Failed to create oral session")

        session = session_response.data[0]

        # Insert sub-questions
        question_models = []
        for sq in sub_questions:
            q_data = {
                "session_id": session["id"],
                "part_number": sq["part_number"],
                "question_text": sq["question_text"],
                "focus_area": sq["focus_area"],
                "key_concepts": sq["key_concepts"],
                "suggested_duration_minutes": sq.get("suggested_duration_minutes", 4),
                "status": "pending",
            }

            q_response = (
                supabase.table("system_design_oral_questions")
                .insert(q_data)
                .execute()
            )

            if q_response.data:
                q = q_response.data[0]
                question_models.append(OralSubQuestion(
                    id=q["id"],
                    part_number=q["part_number"],
                    question_text=q["question_text"],
                    focus_area=q["focus_area"],
                    key_concepts=q.get("key_concepts") or [],
                    suggested_duration_minutes=q.get("suggested_duration_minutes", 4),
                    status=q["status"],
                ))

        return OralSession(
            id=session["id"],
            user_id=session["user_id"],
            track_id=session["track_id"],
            topic=session["topic"],
            scenario=session.get("scenario", ""),
            status=session["status"],
            questions=question_models,
            created_at=session["created_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create oral session: {str(e)}")


@router.get("/system-design/oral-sessions/{session_id}", response_model=OralSession)
async def get_oral_session(
    session_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get oral session with all questions and their grades."""
    try:
        session_response = (
            supabase.table("system_design_oral_sessions")
            .select("*")
            .eq("id", str(session_id))
            .single()
            .execute()
        )

        if not session_response.data:
            raise HTTPException(status_code=404, detail="Oral session not found")

        session = session_response.data

        # Get questions
        questions_response = (
            supabase.table("system_design_oral_questions")
            .select("*")
            .eq("session_id", str(session_id))
            .order("part_number")
            .execute()
        )

        questions_data = questions_response.data or []

        # Batch-fetch all follow-ups for this session's questions
        question_ids = [q["id"] for q in questions_data]
        follow_ups_by_question: dict[str, list[dict]] = {qid: [] for qid in question_ids}

        if question_ids:
            follow_ups_response = (
                supabase.table("system_design_oral_follow_ups")
                .select("*")
                .in_("question_id", question_ids)
                .order("follow_up_index")
                .execute()
            )
            for fu in (follow_ups_response.data or []):
                follow_ups_by_question[fu["question_id"]].append(fu)

        question_models = [
            _build_oral_sub_question(
                q,
                include_full_grade=True,
                follow_ups=follow_ups_by_question.get(q["id"]),
            )
            for q in questions_data
        ]

        return OralSession(
            id=session["id"],
            user_id=session["user_id"],
            track_id=session["track_id"],
            topic=session["topic"],
            scenario=session.get("scenario", ""),
            status=session["status"],
            questions=question_models,
            created_at=session["created_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get oral session: {str(e)}")


@router.post("/system-design/oral-questions/{question_id}/submit-audio", response_model=OralGradeResult)
async def submit_oral_audio(
    question_id: UUID,
    audio: UploadFile = File(...),
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Submit audio for an oral question and get Gemini multimodal grading."""
    from app.services.oral_grading_service import get_oral_grading_service

    try:
        # Validate content type
        content_type = audio.content_type or "audio/webm"
        if content_type not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio type: {content_type}. Allowed: {', '.join(ALLOWED_AUDIO_TYPES)}"
            )

        # Read audio bytes and validate size
        audio_bytes = await audio.read()
        if len(audio_bytes) > MAX_AUDIO_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Audio file too large: {len(audio_bytes) / 1024 / 1024:.1f}MB. Max: 25MB"
            )

        # Get question with session info
        question_response = (
            supabase.table("system_design_oral_questions")
            .select("*, system_design_oral_sessions(track_id, topic, system_design_tracks(track_type))")
            .eq("id", str(question_id))
            .single()
            .execute()
        )

        if not question_response.data:
            raise HTTPException(status_code=404, detail="Question not found")

        question = question_response.data
        session = question.get("system_design_oral_sessions", {})
        track = session.get("system_design_tracks", {})
        track_type = track.get("track_type", "traditional")

        # Grade via Gemini multimodal
        grading_service = get_oral_grading_service()
        result = await grading_service.transcribe_and_grade(
            audio_bytes=audio_bytes,
            mime_type=content_type,
            question_text=question["question_text"],
            focus_area=question["focus_area"],
            key_concepts=question.get("key_concepts") or [],
            track_type=track_type,
            suggested_duration=question.get("suggested_duration_minutes", 4),
        )

        # Update question row with grade data
        update_data = {
            "transcript": result.transcript,
            "dimension_scores": [
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
            "missed_concepts": result.missed_concepts,
            "strongest_moment": result.strongest_moment,
            "weakest_moment": result.weakest_moment,
            "follow_up_questions": result.follow_up_questions,
            "status": "graded",
            "graded_at": datetime.utcnow().isoformat(),
        }

        supabase.table("system_design_oral_questions").update(update_data).eq("id", str(question_id)).execute()

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to grade audio: {str(e)}")


@router.post(
    "/system-design/oral-questions/{question_id}/follow-ups/{follow_up_index}/submit-audio",
    response_model=FollowUpGradeResult,
)
async def submit_follow_up_audio(
    question_id: UUID,
    follow_up_index: int,
    audio: UploadFile = File(...),
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Submit audio for a follow-up question and get simplified grading."""
    from app.services.oral_grading_service import get_oral_grading_service

    try:
        # Validate content type
        content_type = audio.content_type or "audio/webm"
        if content_type not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio type: {content_type}. Allowed: {', '.join(ALLOWED_AUDIO_TYPES)}"
            )

        # Read audio bytes and validate size
        audio_bytes = await audio.read()
        if len(audio_bytes) > MAX_AUDIO_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Audio file too large: {len(audio_bytes) / 1024 / 1024:.1f}MB. Max: 25MB"
            )

        # Fetch parent question — must be graded
        question_response = (
            supabase.table("system_design_oral_questions")
            .select("*")
            .eq("id", str(question_id))
            .single()
            .execute()
        )

        if not question_response.data:
            raise HTTPException(status_code=404, detail="Question not found")

        question = question_response.data

        if question["status"] != "graded":
            raise HTTPException(status_code=400, detail="Question must be graded before answering follow-ups")

        # Validate follow-up index is in bounds
        follow_up_questions = question.get("follow_up_questions") or []
        if follow_up_index < 0 or follow_up_index >= len(follow_up_questions):
            raise HTTPException(
                status_code=400,
                detail=f"Follow-up index {follow_up_index} out of range (0-{len(follow_up_questions) - 1})"
            )

        follow_up_text = follow_up_questions[follow_up_index]

        # Grade via Gemini multimodal
        grading_service = get_oral_grading_service()
        result = await grading_service.transcribe_and_grade_follow_up(
            audio_bytes=audio_bytes,
            mime_type=content_type,
            original_question_text=question["question_text"],
            original_transcript=question.get("transcript") or "",
            follow_up_question=follow_up_text,
        )

        # Upsert row into system_design_oral_follow_ups
        follow_up_data = {
            "question_id": str(question_id),
            "follow_up_index": follow_up_index,
            "follow_up_text": follow_up_text,
            "transcript": result.transcript,
            "score": result.score,
            "feedback": result.feedback,
            "addressed_gap": result.addressed_gap,
            "status": "graded",
            "graded_at": datetime.utcnow().isoformat(),
        }

        supabase.table("system_design_oral_follow_ups").upsert(
            follow_up_data,
            on_conflict="question_id,follow_up_index",
        ).execute()

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to grade follow-up audio: {str(e)}")


@router.post("/system-design/oral-sessions/{session_id}/complete", response_model=OralSessionSummary)
async def complete_oral_session(
    session_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Complete an oral session, compute aggregates, and update review queue."""
    try:
        # Get session
        session_response = (
            supabase.table("system_design_oral_sessions")
            .select("*")
            .eq("id", str(session_id))
            .single()
            .execute()
        )

        if not session_response.data:
            raise HTTPException(status_code=404, detail="Oral session not found")

        session = session_response.data

        if session["status"] == "completed":
            raise HTTPException(status_code=400, detail="Session already completed")

        # Get all graded questions
        questions_response = (
            supabase.table("system_design_oral_questions")
            .select("*")
            .eq("session_id", str(session_id))
            .eq("status", "graded")
            .order("part_number")
            .execute()
        )

        graded_questions = questions_response.data or []

        if not graded_questions:
            raise HTTPException(status_code=400, detail="No graded questions in this session")

        # Compute dimension averages across all graded questions
        dimension_totals: dict[str, list[float]] = {}
        for q in graded_questions:
            for dim in (q.get("dimension_scores") or []):
                name = dim.get("name", "")
                score = dim.get("score", 0)
                if name not in dimension_totals:
                    dimension_totals[name] = []
                dimension_totals[name].append(float(score))

        dimension_averages = {
            name: round(sum(scores) / len(scores), 1)
            for name, scores in dimension_totals.items()
        }

        # Compute overall score from dimension averages
        from app.services.oral_grading_service import DIMENSION_WEIGHTS
        weighted_sum = 0.0
        total_weight = 0.0
        for name, avg in dimension_averages.items():
            weight = DIMENSION_WEIGHTS.get(name, 1.0)
            weighted_sum += avg * weight
            total_weight += weight

        overall_score = round(weighted_sum / total_weight, 1) if total_weight > 0 else 0.0

        if overall_score >= 7:
            verdict = "pass"
        elif overall_score >= 5:
            verdict = "borderline"
        else:
            verdict = "fail"

        # Update session status
        supabase.table("system_design_oral_sessions").update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", str(session_id)).execute()

        # Add weak areas to review queue
        review_topics_added = []
        user_id = session["user_id"]
        track_id = session.get("track_id")

        for name, avg in dimension_averages.items():
            if avg < 7:
                topic_label = f"{session['topic']} - {name.replace('_', ' ').title()}"
                try:
                    supabase.table("system_design_review_queue").upsert({
                        "user_id": str(user_id),
                        "track_id": str(track_id) if track_id else None,
                        "topic": topic_label,
                        "reason": f"Weak area from oral session on {session['topic']} (avg score: {avg}/10)",
                        "priority": 1,
                        "interval_days": 1,
                    }, on_conflict="user_id,topic").execute()
                    review_topics_added.append(topic_label)
                except Exception:
                    pass

        # Update track progress
        if track_id:
            _update_track_progress(
                supabase, user_id, track_id, session["topic"], overall_score
            )

        return OralSessionSummary(
            session_id=str(session_id),
            topic=session["topic"],
            questions_graded=len(graded_questions),
            dimension_averages=dimension_averages,
            overall_score=overall_score,
            verdict=verdict,
            review_topics_added=review_topics_added,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete oral session: {str(e)}")


@router.get("/system-design/{user_id}/oral-sessions", response_model=list[OralSession])
async def list_oral_sessions(
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """List user's oral sessions with pagination."""
    try:
        response = (
            supabase.table("system_design_oral_sessions")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        sessions = []
        for s in (response.data or []):
            # Get questions for each session (summary only for listing)
            questions_response = (
                supabase.table("system_design_oral_questions")
                .select("*")
                .eq("session_id", s["id"])
                .order("part_number")
                .execute()
            )

            question_models = [
                _build_oral_sub_question(q, include_full_grade=False)
                for q in (questions_response.data or [])
            ]

            sessions.append(OralSession(
                id=s["id"],
                user_id=s["user_id"],
                track_id=s["track_id"],
                topic=s["topic"],
                scenario=s.get("scenario", ""),
                status=s["status"],
                questions=question_models,
                created_at=s["created_at"],
            ))

        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list oral sessions: {str(e)}")
