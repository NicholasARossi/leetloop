"""Language Learning endpoints."""

import time
from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.models.language_schemas import (
    CompleteReviewRequest,
    CompleteReviewResponse,
    CreateLanguageAttemptRequest,
    LanguageAttempt,
    LanguageAttemptGrade,
    LanguageAttemptHistoryItem,
    LanguageAttemptHistoryResponse,
    LanguageDashboardExercise,
    LanguageDashboardSummary,
    LanguageNextTopicInfo,
    LanguageQuestionContext,
    LanguageReviewItem,
    LanguageRubricWeights,
    LanguageTopicInfo,
    LanguageTrack,
    LanguageTrackProgress,
    LanguageTrackProgressResponse,
    LanguageTrackSummary,
    SetActiveTrackRequest,
    SubmitLanguageAttemptRequest,
)
from app.services.language_service import BookContentContext, get_language_service

router = APIRouter()

# In-memory TTL cache for language dashboard
_lang_dashboard_cache: dict[str, tuple[float, LanguageDashboardSummary]] = {}
_LANG_DASHBOARD_CACHE_TTL = 300  # 5 minutes


# ============ Tracks ============


@router.get("/language/tracks", response_model=list[LanguageTrackSummary])
async def list_tracks(
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """List all available language tracks."""
    try:
        response = (
            supabase.table("language_tracks")
            .select("id, name, description, language, level, total_topics")
            .order("name")
            .execute()
        )
        return [LanguageTrackSummary(**t) for t in response.data] if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tracks: {str(e)}")


@router.get("/language/tracks/{track_id}", response_model=LanguageTrack)
async def get_track(
    track_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get track details with topics."""
    try:
        response = (
            supabase.table("language_tracks")
            .select("*")
            .eq("id", str(track_id))
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Track not found")

        data = response.data
        topics = [LanguageTopicInfo(**t) for t in data.get("topics", [])]
        rubric = LanguageRubricWeights(**data.get("rubric", {}))

        return LanguageTrack(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            language=data["language"],
            level=data["level"],
            topics=topics,
            total_topics=data.get("total_topics", 0),
            rubric=rubric,
            source_book=data.get("source_book"),
            created_at=data.get("created_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get track: {str(e)}")


@router.get("/language/tracks/{track_id}/progress/{user_id}", response_model=LanguageTrackProgressResponse)
async def get_track_progress(
    track_id: UUID,
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get user's progress on a specific language track."""
    try:
        # Get track
        track_response = (
            supabase.table("language_tracks")
            .select("*")
            .eq("id", str(track_id))
            .single()
            .execute()
        )

        if not track_response.data:
            raise HTTPException(status_code=404, detail="Track not found")

        track_data = track_response.data
        topics = [LanguageTopicInfo(**t) for t in track_data.get("topics", [])]
        rubric = LanguageRubricWeights(**track_data.get("rubric", {}))

        track = LanguageTrack(
            id=track_data["id"],
            name=track_data["name"],
            description=track_data.get("description"),
            language=track_data["language"],
            level=track_data["level"],
            topics=topics,
            total_topics=track_data.get("total_topics", 0),
            rubric=rubric,
            source_book=track_data.get("source_book"),
            created_at=track_data.get("created_at"),
        )

        # Get user progress
        progress_response = (
            supabase.table("language_track_progress")
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
            progress = LanguageTrackProgress(**progress_response.data[0])
            completed = len(progress.completed_topics)
            total = track.total_topics
            completion_percentage = (completed / total * 100) if total > 0 else 0.0

            for topic in topics:
                if topic.name not in progress.completed_topics:
                    next_topic = topic.name
                    break
        else:
            next_topic = topics[0].name if topics else None

        return LanguageTrackProgressResponse(
            track=track,
            progress=progress,
            completion_percentage=completion_percentage,
            next_topic=next_topic,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get track progress: {str(e)}")


# ============ Attempts ============


@router.post("/language/{user_id}/attempt", response_model=LanguageAttempt)
async def create_attempt(
    user_id: UUID,
    request: CreateLanguageAttemptRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Create a new language exercise attempt."""
    try:
        # Get track info
        track_response = (
            supabase.table("language_tracks")
            .select("*")
            .eq("id", str(request.track_id))
            .single()
            .execute()
        )

        if not track_response.data:
            raise HTTPException(status_code=404, detail="Track not found")

        track_data = track_response.data
        topics = track_data.get("topics", [])

        # Find topic info
        topic_info = next((t for t in topics if t["name"] == request.topic), None)
        key_concepts = topic_info.get("key_concepts", []) if topic_info else []

        # Get user's previous weak areas from recent attempts
        weak_areas = []
        try:
            recent_attempts = (
                supabase.table("language_attempts")
                .select("missed_concepts")
                .eq("user_id", str(user_id))
                .eq("status", "graded")
                .order("graded_at", desc=True)
                .limit(5)
                .execute()
            )
            if recent_attempts.data:
                for a in recent_attempts.data:
                    weak_areas.extend(a.get("missed_concepts") or [])
                weak_areas = list(set(weak_areas))[:5]
        except Exception:
            pass

        # Check for book content linked to this track/topic
        book_content = None
        try:
            book_response = (
                supabase.table("book_content")
                .select("chapter_title, summary, key_concepts, case_studies")
                .eq("language_track_id", str(request.track_id))
                .eq("chapter_title", request.topic)
                .limit(1)
                .execute()
            )
            if book_response.data:
                bc = book_response.data[0]
                book_content = BookContentContext(
                    chapter_title=bc.get("chapter_title", ""),
                    summary=bc.get("summary", ""),
                    key_concepts=bc.get("key_concepts", []),
                    case_studies=bc.get("case_studies", []),
                )
        except Exception:
            pass  # Book content is optional

        # Generate exercise via Gemini
        service = get_language_service()
        context = LanguageQuestionContext(
            language=track_data["language"],
            level=track_data["level"],
            topic=request.topic,
            exercise_type=request.exercise_type,
            key_concepts=key_concepts,
            user_weak_areas=weak_areas,
        )
        generated = await service.generate_exercise(context, book_content)

        # Create attempt
        attempt_data = {
            "user_id": str(user_id),
            "track_id": str(request.track_id),
            "topic": request.topic,
            "exercise_type": request.exercise_type,
            "question_text": generated.question_text,
            "expected_answer": generated.expected_answer,
            "question_focus_area": generated.focus_area,
            "question_key_concepts": generated.key_concepts,
            "status": "pending",
        }

        response = (
            supabase.table("language_attempts")
            .insert(attempt_data)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create attempt")

        attempt = response.data[0]
        return LanguageAttempt(
            id=attempt["id"],
            user_id=attempt["user_id"],
            track_id=attempt.get("track_id"),
            topic=attempt["topic"],
            exercise_type=attempt["exercise_type"],
            question_text=attempt["question_text"],
            expected_answer=attempt.get("expected_answer"),
            question_focus_area=attempt.get("question_focus_area"),
            question_key_concepts=attempt.get("question_key_concepts") or [],
            status=attempt["status"],
            created_at=attempt["created_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create attempt: {str(e)}")


@router.post("/language/attempts/{attempt_id}/submit", response_model=LanguageAttemptGrade)
async def submit_attempt(
    attempt_id: UUID,
    request: SubmitLanguageAttemptRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Submit response for a language attempt and get AI grading."""
    try:
        # Get attempt with track info
        attempt_response = (
            supabase.table("language_attempts")
            .select("*, language_tracks(*)")
            .eq("id", str(attempt_id))
            .single()
            .execute()
        )

        if not attempt_response.data:
            raise HTTPException(status_code=404, detail="Attempt not found")

        attempt = attempt_response.data

        if attempt["status"] == "graded":
            return LanguageAttemptGrade(
                score=attempt["score"],
                verdict=attempt["verdict"],
                feedback=attempt["feedback"],
                corrections=attempt.get("corrections"),
                missed_concepts=attempt.get("missed_concepts") or [],
            )

        word_count = len(request.response_text.split())

        # Grade via Gemini
        service = get_language_service()
        track_data = attempt.get("language_tracks", {})

        grading_result = await service.grade_exercise(
            language=track_data.get("language", "french"),
            level=track_data.get("level", "a1"),
            exercise_type=attempt["exercise_type"],
            question_text=attempt["question_text"],
            expected_answer=attempt.get("expected_answer"),
            focus_area=attempt.get("question_focus_area") or "general",
            key_concepts=attempt.get("question_key_concepts") or [],
            response_text=request.response_text,
        )

        # Update attempt with response and grade
        update_data = {
            "response_text": request.response_text,
            "word_count": word_count,
            "score": grading_result.score,
            "verdict": grading_result.verdict,
            "feedback": grading_result.feedback,
            "corrections": grading_result.corrections,
            "missed_concepts": grading_result.missed_concepts,
            "status": "graded",
            "graded_at": datetime.utcnow().isoformat(),
        }

        supabase.table("language_attempts").update(update_data).eq("id", str(attempt_id)).execute()

        # Add to review queue if score < 7
        if grading_result.score < 7:
            user_id = attempt["user_id"]
            track_id = attempt.get("track_id")
            try:
                supabase.table("language_review_queue").upsert({
                    "user_id": str(user_id),
                    "track_id": str(track_id) if track_id else None,
                    "topic": attempt["topic"],
                    "reason": f"Weak area from {attempt['exercise_type']} exercise on {attempt['topic']}",
                    "priority": 1,
                    "interval_days": 1,
                }, on_conflict="user_id,topic").execute()
            except Exception:
                pass

        # Update track progress
        track_id = attempt.get("track_id")
        if track_id:
            _update_language_track_progress(
                supabase, attempt["user_id"], track_id, attempt["topic"], grading_result.score
            )

        return LanguageAttemptGrade(
            score=grading_result.score,
            verdict=grading_result.verdict,
            feedback=grading_result.feedback,
            corrections=grading_result.corrections,
            missed_concepts=grading_result.missed_concepts,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit attempt: {str(e)}")


@router.get("/language/attempts/{attempt_id}", response_model=LanguageAttempt)
async def get_attempt(
    attempt_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get a specific language attempt."""
    try:
        response = (
            supabase.table("language_attempts")
            .select("*")
            .eq("id", str(attempt_id))
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Attempt not found")

        attempt = response.data
        return LanguageAttempt(
            id=attempt["id"],
            user_id=attempt["user_id"],
            track_id=attempt.get("track_id"),
            topic=attempt["topic"],
            exercise_type=attempt["exercise_type"],
            question_text=attempt["question_text"],
            expected_answer=attempt.get("expected_answer"),
            question_focus_area=attempt.get("question_focus_area"),
            question_key_concepts=attempt.get("question_key_concepts") or [],
            response_text=attempt.get("response_text"),
            word_count=attempt.get("word_count") or 0,
            score=attempt.get("score"),
            verdict=attempt.get("verdict"),
            feedback=attempt.get("feedback"),
            corrections=attempt.get("corrections"),
            missed_concepts=attempt.get("missed_concepts") or [],
            status=attempt["status"],
            created_at=attempt["created_at"],
            graded_at=attempt.get("graded_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attempt: {str(e)}")


@router.get("/language/{user_id}/attempts", response_model=LanguageAttemptHistoryResponse)
async def get_attempt_history(
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get user's language attempt history."""
    try:
        response = (
            supabase.table("language_attempts")
            .select("*, language_tracks(name)", count="exact")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        total = response.count or 0
        attempts = []

        for a in (response.data or []):
            track = a.get("language_tracks")
            attempts.append(LanguageAttemptHistoryItem(
                id=a["id"],
                topic=a["topic"],
                exercise_type=a["exercise_type"],
                question_text=a["question_text"],
                score=a.get("score"),
                verdict=a.get("verdict"),
                status=a["status"],
                created_at=a["created_at"],
                graded_at=a.get("graded_at"),
                track_name=track.get("name") if track else None,
            ))

        return LanguageAttemptHistoryResponse(
            attempts=attempts,
            total=total,
            has_more=offset + limit < total,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attempt history: {str(e)}")


# ============ Reviews ============


@router.get("/language/{user_id}/reviews", response_model=list[LanguageReviewItem])
async def get_due_reviews(
    user_id: UUID,
    limit: int = 10,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get language topics due for review."""
    try:
        response = supabase.rpc(
            "get_due_language_reviews",
            {"p_user_id": str(user_id), "p_limit": limit}
        ).execute()

        return [LanguageReviewItem(**r) for r in response.data] if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reviews: {str(e)}")


@router.post("/language/reviews/{review_id}/complete", response_model=CompleteReviewResponse)
async def complete_review(
    review_id: UUID,
    request: CompleteReviewRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Mark a language review as complete (pass/fail)."""
    try:
        supabase.rpc(
            "complete_language_review",
            {"p_review_id": str(review_id), "p_success": request.success}
        ).execute()

        updated = (
            supabase.table("language_review_queue")
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


# ============ Dashboard ============


@router.get("/language/{user_id}/dashboard", response_model=LanguageDashboardSummary)
async def get_dashboard_summary(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get language learning summary for dashboard display."""
    cache_key = str(user_id)
    cached = _lang_dashboard_cache.get(cache_key)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    try:
        # Get user settings
        settings_response = (
            supabase.table("user_language_settings")
            .select("*")
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )

        has_active_track = False
        active_track = None
        next_topic = None

        if settings_response.data and settings_response.data[0].get("active_track_id"):
            has_active_track = True
            active_track_id = settings_response.data[0]["active_track_id"]

            # Get active track details
            track_response = (
                supabase.table("language_tracks")
                .select("id, name, description, language, level, total_topics, topics")
                .eq("id", active_track_id)
                .single()
                .execute()
            )

            if track_response.data:
                track_data = track_response.data
                active_track = LanguageTrackSummary(
                    id=track_data["id"],
                    name=track_data["name"],
                    description=track_data.get("description"),
                    language=track_data["language"],
                    level=track_data["level"],
                    total_topics=track_data.get("total_topics", 0),
                )

                # Get user's progress to find next topic
                progress_response = (
                    supabase.table("language_track_progress")
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
                        next_topic = LanguageNextTopicInfo(
                            track_id=UUID(track_data["id"]),
                            track_name=track_data["name"],
                            language=track_data["language"],
                            level=track_data["level"],
                            topic_name=topic.get("name", ""),
                            topic_order=topic.get("order", 0),
                            topic_difficulty=topic.get("difficulty", "medium"),
                            key_concepts=topic.get("key_concepts", []),
                            topics_completed=len(completed_topics),
                            total_topics=track_data.get("total_topics", 0),
                        )
                        break

        # Get reviews due
        reviews_response = supabase.rpc(
            "get_due_language_reviews",
            {"p_user_id": str(user_id), "p_limit": 5}
        ).execute()

        reviews_due = []
        if reviews_response.data:
            reviews_due = [LanguageReviewItem(**r) for r in reviews_response.data]

        # Get exercises this week
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        exercises_response = (
            supabase.table("language_attempts")
            .select("id", count="exact")
            .eq("user_id", str(user_id))
            .gte("created_at", week_ago)
            .execute()
        )
        exercises_this_week = exercises_response.count or 0

        # Get most recent score
        recent_score = None
        recent_attempt_response = (
            supabase.table("language_attempts")
            .select("score")
            .eq("user_id", str(user_id))
            .eq("status", "graded")
            .order("graded_at", desc=True)
            .limit(1)
            .execute()
        )
        if recent_attempt_response.data:
            recent_score = recent_attempt_response.data[0].get("score")

        response = LanguageDashboardSummary(
            has_active_track=has_active_track,
            active_track=active_track,
            next_topic=next_topic,
            reviews_due_count=len(reviews_due),
            reviews_due=reviews_due,
            recent_score=recent_score,
            exercises_this_week=exercises_this_week,
        )
        _lang_dashboard_cache[cache_key] = (time.monotonic() + _LANG_DASHBOARD_CACHE_TTL, response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard summary: {str(e)}")


@router.put("/language/{user_id}/active-track")
async def set_active_track(
    user_id: UUID,
    request: SetActiveTrackRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Set user's active language track."""
    try:
        if request.track_id:
            track_response = (
                supabase.table("language_tracks")
                .select("id, name")
                .eq("id", str(request.track_id))
                .single()
                .execute()
            )
            if not track_response.data:
                raise HTTPException(status_code=404, detail="Track not found")

        settings_data = {
            "user_id": str(user_id),
            "active_track_id": str(request.track_id) if request.track_id else None,
            "updated_at": datetime.utcnow().isoformat(),
        }

        supabase.table("user_language_settings").upsert(
            settings_data, on_conflict="user_id"
        ).execute()

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


# ============ Helpers ============


def _update_language_track_progress(
    supabase: Client,
    user_id: str,
    track_id: str,
    topic: str,
    score: float,
):
    """Update user's language track progress after completing an exercise."""
    try:
        progress_response = (
            supabase.table("language_track_progress")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("track_id", str(track_id))
            .limit(1)
            .execute()
        )

        if progress_response.data:
            progress = progress_response.data[0]
            completed = set(progress.get("completed_topics", []))
            completed.add(topic)

            sessions = progress.get("sessions_completed", 0) + 1
            current_avg = progress.get("average_score", 0.0)
            new_avg = ((current_avg * (sessions - 1)) + score) / sessions

            supabase.table("language_track_progress").update({
                "completed_topics": list(completed),
                "sessions_completed": sessions,
                "average_score": new_avg,
                "last_activity_at": datetime.utcnow().isoformat(),
            }).eq("id", progress["id"]).execute()
        else:
            supabase.table("language_track_progress").insert({
                "user_id": str(user_id),
                "track_id": str(track_id),
                "completed_topics": [topic],
                "sessions_completed": 1,
                "average_score": score,
            }).execute()
    except Exception as e:
        print(f"Failed to update language track progress: {e}")
