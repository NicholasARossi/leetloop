"""Language Learning endpoints."""

import time
from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.models.language_schemas import (
    BookContentSection,
    BookProgressResponse,
    ChapterProgressItem,
    CompleteReviewRequest,
    CompleteReviewResponse,
    CreateLanguageAttemptRequest,
    DailyExercise,
    DailyExerciseBatch,
    DailyExerciseGrade,
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
    SubmitDailyExerciseRequest,
    SubmitLanguageAttemptRequest,
    WrittenGrading,
)
from app.services.language_service import (
    BookContentContext,
    get_language_service,
    get_response_format,
    get_word_target,
)

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


# ============ Book Progress ============


@router.get("/language/tracks/{track_id}/book-progress/{user_id}", response_model=BookProgressResponse)
async def get_book_progress(
    track_id: UUID,
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get chapter-by-chapter book progress for a track."""
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
        topics = sorted(track_data.get("topics", []), key=lambda t: t.get("order", 0))

        # Get user progress
        progress_response = (
            supabase.table("language_track_progress")
            .select("completed_topics, average_score")
            .eq("user_id", str(user_id))
            .eq("track_id", str(track_id))
            .limit(1)
            .execute()
        )

        completed_topics = set()
        average_score = 0.0
        if progress_response.data:
            completed_topics = set(progress_response.data[0].get("completed_topics", []))
            average_score = progress_response.data[0].get("average_score", 0.0)

        # Get book content for all chapters in this track
        book_content_map: dict[str, dict] = {}
        try:
            book_response = (
                supabase.table("book_content")
                .select("chapter_title, summary, sections, key_concepts")
                .eq("language_track_id", str(track_id))
                .execute()
            )
            if book_response.data:
                for bc in book_response.data:
                    book_content_map[bc["chapter_title"]] = bc
        except Exception:
            pass

        # Get due reviews for this user + track
        review_topics_map: dict[str, str] = {}
        try:
            reviews_response = (
                supabase.table("language_review_queue")
                .select("topic, reason")
                .eq("user_id", str(user_id))
                .eq("track_id", str(track_id))
                .lte("next_review", datetime.utcnow().isoformat())
                .execute()
            )
            if reviews_response.data:
                for r in reviews_response.data:
                    review_topics_map[r["topic"]] = r.get("reason", "Due for review")
        except Exception:
            pass

        # Build chapter list
        chapters = []
        found_current = False
        for topic in topics:
            name = topic.get("name", "")
            is_completed = name in completed_topics
            is_current = False
            if not is_completed and not found_current:
                is_current = True
                found_current = True

            # Book content
            bc = book_content_map.get(name, {})
            book_sections = []
            for section in (bc.get("sections") or []):
                book_sections.append(BookContentSection(
                    title=section.get("title", ""),
                    summary=section.get("summary", ""),
                    key_points=section.get("key_points", []),
                ))

            chapters.append(ChapterProgressItem(
                name=name,
                order=topic.get("order", 0),
                difficulty=topic.get("difficulty", "medium"),
                key_concepts=topic.get("key_concepts", []),
                is_completed=is_completed,
                is_current=is_current,
                has_review_due=name in review_topics_map,
                review_reason=review_topics_map.get(name),
                book_summary=bc.get("summary"),
                book_sections=book_sections,
            ))

        completed_count = len(completed_topics)
        total_count = len(topics)
        completion_pct = (completed_count / total_count * 100) if total_count > 0 else 0.0

        return BookProgressResponse(
            track_name=track_data["name"],
            language=track_data["language"],
            level=track_data["level"],
            source_book=track_data.get("source_book"),
            total_chapters=total_count,
            completed_chapters=completed_count,
            completion_percentage=round(completion_pct, 1),
            average_score=round(average_score, 1),
            chapters=chapters,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get book progress: {str(e)}")


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

        grading_result, _ = await service.grade_exercise(
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
        book_total_chapters = 0
        book_completed_chapters = 0

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

                # Book progress stats
                topics = track_data.get("topics", [])
                book_total_chapters = len(topics)
                book_completed_chapters = len(completed_topics)

                # Find next uncompleted topic
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

        book_pct = (book_completed_chapters / book_total_chapters * 100) if book_total_chapters > 0 else 0.0

        response = LanguageDashboardSummary(
            has_active_track=has_active_track,
            active_track=active_track,
            next_topic=next_topic,
            reviews_due_count=len(reviews_due),
            reviews_due=reviews_due,
            recent_score=recent_score,
            exercises_this_week=exercises_this_week,
            book_total_chapters=book_total_chapters,
            book_completed_chapters=book_completed_chapters,
            book_completion_percentage=round(book_pct, 1),
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


# ============ Daily Exercises ============

# In-memory TTL cache for daily exercises (short TTL, just for dedup on rapid refreshes)
_daily_exercises_cache: dict[str, tuple[float, DailyExerciseBatch]] = {}
_DAILY_EXERCISES_CACHE_TTL = 60  # 1 minute

# Exercise type mix for new topics (tier-aware: 3 quick, 2 short, 2 extended, 1 free-form)
_EXERCISE_TYPE_SEQUENCE = [
    "conjugation", "fill_blank", "vocabulary",           # 3 quick
    "sentence_construction", "error_correction",          # 2 short
    "situational", "reading_comprehension",               # 2 extended
    "journal_entry",                                      # 1 free-form
]


@router.get("/language/{user_id}/daily-exercises", response_model=DailyExerciseBatch)
async def get_daily_exercises(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get today's daily exercise batch. Generates if not exists."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cache_key = f"{user_id}:{today}"

    # Check cache
    cached = _daily_exercises_cache.get(cache_key)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    try:
        # Check if exercises already exist for today
        existing = (
            supabase.table("language_daily_exercises")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("generated_date", today)
            .order("sort_order")
            .execute()
        )

        if existing.data:
            batch = _build_batch_response(existing.data, today)
            _daily_exercises_cache[cache_key] = (time.monotonic() + _DAILY_EXERCISES_CACHE_TTL, batch)
            return batch

        # No exercises for today - generate a new batch
        batch = await _generate_daily_batch(supabase, user_id, today)
        _daily_exercises_cache[cache_key] = (time.monotonic() + _DAILY_EXERCISES_CACHE_TTL, batch)
        return batch

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get daily exercises: {str(e)}")


@router.post("/language/daily-exercises/{exercise_id}/submit", response_model=DailyExerciseGrade)
async def submit_daily_exercise(
    exercise_id: UUID,
    request: SubmitDailyExerciseRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Submit an answer for a daily exercise and get inline grading."""
    try:
        # Get the exercise
        exercise_response = (
            supabase.table("language_daily_exercises")
            .select("*, language_tracks(*)")
            .eq("id", str(exercise_id))
            .single()
            .execute()
        )

        if not exercise_response.data:
            raise HTTPException(status_code=404, detail="Exercise not found")

        exercise = exercise_response.data

        # Already completed - return existing grade
        if exercise["status"] == "completed":
            return DailyExerciseGrade(
                score=exercise["score"],
                verdict=exercise["verdict"],
                feedback=exercise["feedback"],
                corrections=exercise.get("corrections"),
                missed_concepts=exercise.get("missed_concepts") or [],
            )

        word_count = len(request.response_text.split())

        # Grade via Gemini
        service = get_language_service()
        track_data = exercise.get("language_tracks") or {}

        grading_result, written_grading = await service.grade_exercise(
            language=track_data.get("language", "french"),
            level=track_data.get("level", "a1"),
            exercise_type=exercise["exercise_type"],
            question_text=exercise["question_text"],
            expected_answer=exercise.get("expected_answer"),
            focus_area=exercise.get("focus_area") or "general",
            key_concepts=exercise.get("key_concepts") or [],
            response_text=request.response_text,
            vocab_targets=exercise.get("vocab_targets") or [],
        )

        # Update exercise record
        update_data = {
            "response_text": request.response_text,
            "word_count": word_count,
            "score": grading_result.score,
            "verdict": grading_result.verdict,
            "feedback": grading_result.feedback,
            "corrections": grading_result.corrections,
            "missed_concepts": grading_result.missed_concepts,
            "written_grading": written_grading.model_dump() if written_grading else None,
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
        }

        supabase.table("language_daily_exercises").update(update_data).eq(
            "id", str(exercise_id)
        ).execute()

        # Also create a language_attempts record for history tracking
        attempt_data = {
            "user_id": exercise["user_id"],
            "track_id": exercise.get("track_id"),
            "topic": exercise["topic"],
            "exercise_type": exercise["exercise_type"],
            "question_text": exercise["question_text"],
            "expected_answer": exercise.get("expected_answer"),
            "question_focus_area": exercise.get("focus_area"),
            "question_key_concepts": exercise.get("key_concepts") or [],
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
        try:
            supabase.table("language_attempts").insert(attempt_data).execute()
        except Exception:
            pass  # Attempt logging is best-effort

        # Add to review queue if score < 7
        if grading_result.score < 7:
            try:
                supabase.table("language_review_queue").upsert(
                    {
                        "user_id": exercise["user_id"],
                        "track_id": exercise.get("track_id"),
                        "topic": exercise["topic"],
                        "reason": f"Weak area from daily {exercise['exercise_type']} exercise on {exercise['topic']}",
                        "priority": 1,
                        "interval_days": 1,
                    },
                    on_conflict="user_id,topic",
                ).execute()
            except Exception:
                pass

        # Update track progress
        track_id = exercise.get("track_id")
        if track_id:
            _update_language_track_progress(
                supabase, exercise["user_id"], track_id,
                exercise["topic"], grading_result.score,
            )

        # Invalidate cache for this user's daily exercises
        today = datetime.utcnow().strftime("%Y-%m-%d")
        cache_key = f"{exercise['user_id']}:{today}"
        _daily_exercises_cache.pop(cache_key, None)

        return DailyExerciseGrade(
            score=grading_result.score,
            verdict=grading_result.verdict,
            feedback=grading_result.feedback,
            corrections=grading_result.corrections,
            missed_concepts=grading_result.missed_concepts,
            written_grading=written_grading,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit daily exercise: {str(e)}")


@router.post("/language/{user_id}/daily-exercises/regenerate", response_model=DailyExerciseBatch)
async def regenerate_daily_exercises(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Delete pending exercises for today, keep completed ones, generate new ones for remaining slots."""
    today = datetime.utcnow().strftime("%Y-%m-%d")

    try:
        # Delete pending exercises for today
        supabase.table("language_daily_exercises").delete().eq(
            "user_id", str(user_id)
        ).eq("generated_date", today).eq("status", "pending").execute()

        # Get remaining completed exercises
        remaining = (
            supabase.table("language_daily_exercises")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("generated_date", today)
            .order("sort_order")
            .execute()
        )

        completed_exercises = remaining.data or []
        completed_count = len(completed_exercises)
        target_total = 8
        slots_to_fill = max(0, target_total - completed_count)

        if slots_to_fill == 0:
            batch = _build_batch_response(completed_exercises, today)
            cache_key = f"{user_id}:{today}"
            _daily_exercises_cache.pop(cache_key, None)
            return batch

        # Generate new exercises for remaining slots
        batch = await _generate_daily_batch(
            supabase, user_id, today,
            existing_exercises=completed_exercises,
            target_count=slots_to_fill,
        )

        # Invalidate cache
        cache_key = f"{user_id}:{today}"
        _daily_exercises_cache.pop(cache_key, None)

        return batch

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate daily exercises: {str(e)}")


async def _generate_daily_batch(
    supabase: Client,
    user_id: UUID,
    today: str,
    existing_exercises: list[dict] = None,
    target_count: int = 8,
) -> DailyExerciseBatch:
    """Generate a batch of daily exercises."""
    existing_exercises = existing_exercises or []
    start_order = len(existing_exercises)

    # 1. Get user's active track
    settings_response = (
        supabase.table("user_language_settings")
        .select("active_track_id")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )

    if not settings_response.data or not settings_response.data[0].get("active_track_id"):
        raise HTTPException(status_code=400, detail="No active language track set")

    active_track_id = settings_response.data[0]["active_track_id"]

    # 2. Get track details
    track_response = (
        supabase.table("language_tracks")
        .select("*")
        .eq("id", active_track_id)
        .single()
        .execute()
    )

    if not track_response.data:
        raise HTTPException(status_code=404, detail="Active track not found")

    track_data = track_response.data
    language = track_data["language"]
    level = track_data["level"]
    topics = sorted(track_data.get("topics", []), key=lambda t: t.get("order", 0))

    # 3. Get user's track progress (completed topics)
    progress_response = (
        supabase.table("language_track_progress")
        .select("completed_topics")
        .eq("user_id", str(user_id))
        .eq("track_id", active_track_id)
        .limit(1)
        .execute()
    )

    completed_topics = set()
    if progress_response.data:
        completed_topics = set(progress_response.data[0].get("completed_topics", []))

    # 4. Get due reviews from language_review_queue (limit 3)
    review_limit = min(3, target_count)
    reviews_response = (
        supabase.rpc(
            "get_due_language_reviews",
            {"p_user_id": str(user_id), "p_limit": review_limit},
        ).execute()
    )

    review_topics = []
    if reviews_response.data:
        for r in reviews_response.data:
            # Find key_concepts from track topics
            topic_info = next((t for t in topics if t.get("name") == r["topic"]), None)
            review_topics.append({
                "topic": r["topic"],
                "reason": r.get("reason", "Due for review"),
                "key_concepts": topic_info.get("key_concepts", []) if topic_info else [],
                "exercise_type": "vocabulary",  # Will be varied by Gemini
            })

    # 5. Select next uncompleted topics for new exercises
    # Exclude topics already covered by reviews
    review_topic_names = {rt["topic"] for rt in review_topics}
    # Also exclude topics from existing completed exercises in this regeneration
    existing_topic_names = {e["topic"] for e in existing_exercises}

    new_topic_count = target_count - len(review_topics)
    new_topics = []
    type_idx = 0

    for topic in topics:
        if len(new_topics) >= new_topic_count:
            break
        topic_name = topic.get("name", "")
        if topic_name in review_topic_names or topic_name in existing_topic_names:
            continue
        # Include both completed and uncompleted topics, but prefer uncompleted
        if topic_name not in completed_topics:
            exercise_type = _EXERCISE_TYPE_SEQUENCE[type_idx % len(_EXERCISE_TYPE_SEQUENCE)]
            type_idx += 1
            new_topics.append({
                "topic": topic_name,
                "exercise_type": exercise_type,
                "key_concepts": topic.get("key_concepts", []),
            })

    # If we still need more, pull from completed topics for extra review
    if len(new_topics) < new_topic_count:
        for topic in topics:
            if len(new_topics) >= new_topic_count:
                break
            topic_name = topic.get("name", "")
            if topic_name in review_topic_names or topic_name in existing_topic_names:
                continue
            if topic_name in completed_topics:
                exercise_type = _EXERCISE_TYPE_SEQUENCE[type_idx % len(_EXERCISE_TYPE_SEQUENCE)]
                type_idx += 1
                new_topics.append({
                    "topic": topic_name,
                    "exercise_type": exercise_type,
                    "key_concepts": topic.get("key_concepts", []),
                })

    # 6. Get user's weak areas from recent attempts
    user_weak_areas = []
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
                user_weak_areas.extend(a.get("missed_concepts") or [])
            user_weak_areas = list(set(user_weak_areas))[:5]
    except Exception:
        pass

    # 7. Get book_content for relevant topics
    all_topic_names = [rt["topic"] for rt in review_topics] + [nt["topic"] for nt in new_topics]
    book_contexts: dict[str, BookContentContext] = {}

    if all_topic_names:
        try:
            book_response = (
                supabase.table("book_content")
                .select("chapter_title, summary, key_concepts, case_studies")
                .eq("language_track_id", active_track_id)
                .in_("chapter_title", all_topic_names)
                .execute()
            )
            if book_response.data:
                for bc in book_response.data:
                    book_contexts[bc["chapter_title"]] = BookContentContext(
                        chapter_title=bc.get("chapter_title", ""),
                        summary=bc.get("summary", ""),
                        key_concepts=bc.get("key_concepts", []),
                        case_studies=bc.get("case_studies", []),
                    )
        except Exception:
            pass  # Book content is optional

    # 8. Call generate_batch_exercises
    service = get_language_service()
    generated = await service.generate_batch_exercises(
        language=language,
        level=level,
        new_topics=new_topics,
        review_topics=review_topics,
        user_weak_areas=user_weak_areas,
        book_contexts=book_contexts,
    )

    # 9. Insert into language_daily_exercises table
    rows = []
    for i, ex in enumerate(generated):
        # Find matching review topic for reason
        review_reason = None
        is_review = ex.get("is_review", False)
        if is_review:
            matching = next((rt for rt in review_topics if rt["topic"] == ex["topic"]), None)
            review_reason = matching["reason"] if matching else None

        rows.append({
            "user_id": str(user_id),
            "track_id": active_track_id,
            "generated_date": today,
            "sort_order": start_order + i,
            "topic": ex["topic"],
            "exercise_type": ex["exercise_type"],
            "question_text": ex["question_text"],
            "expected_answer": ex.get("expected_answer"),
            "focus_area": ex.get("focus_area"),
            "key_concepts": ex.get("key_concepts", []),
            "is_review": is_review,
            "review_topic_reason": review_reason,
            "status": "pending",
        })

    if rows:
        supabase.table("language_daily_exercises").insert(rows).execute()

    # 10. Fetch all exercises for today (including previously completed) and return
    all_exercises_response = (
        supabase.table("language_daily_exercises")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("generated_date", today)
        .order("sort_order")
        .execute()
    )

    return _build_batch_response(all_exercises_response.data or [], today)


def _build_batch_response(exercises_data: list[dict], today: str) -> DailyExerciseBatch:
    """Build a DailyExerciseBatch from raw exercise rows."""
    exercises = []
    completed_count = 0
    scores = []
    track_id = None

    for ex in exercises_data:
        if track_id is None and ex.get("track_id"):
            track_id = ex["track_id"]
        etype = ex["exercise_type"]
        # grammar_targets = key_concepts (renamed at API boundary)
        key_concepts = ex.get("key_concepts") or []
        # vocab_targets from dedicated JSONB column
        vocab_targets_raw = ex.get("vocab_targets") or []
        vocab_targets = vocab_targets_raw if isinstance(vocab_targets_raw, list) else []
        # written_grading from JSONB column (populated after grading)
        wg_raw = ex.get("written_grading")
        written_grading = None
        if isinstance(wg_raw, dict):
            try:
                written_grading = WrittenGrading(**wg_raw)
            except Exception:
                pass

        exercises.append(DailyExercise(
            id=ex["id"],
            topic=ex["topic"],
            exercise_type=etype,
            question_text=ex["question_text"],
            expected_answer=ex.get("expected_answer"),
            focus_area=ex.get("focus_area"),
            key_concepts=key_concepts,
            grammar_targets=key_concepts,
            vocab_targets=vocab_targets,
            is_review=ex.get("is_review", False),
            review_topic_reason=ex.get("review_topic_reason"),
            status=ex["status"],
            sort_order=ex.get("sort_order", 0),
            response_format=get_response_format(etype),
            word_target=get_word_target(etype),
            response_text=ex.get("response_text"),
            score=ex.get("score"),
            verdict=ex.get("verdict"),
            feedback=ex.get("feedback"),
            corrections=ex.get("corrections"),
            missed_concepts=ex.get("missed_concepts") or [],
            written_grading=written_grading,
            completed_at=ex.get("completed_at"),
        ))
        if ex["status"] == "completed":
            completed_count += 1
            if ex.get("score") is not None:
                scores.append(float(ex["score"]))

    average_score = sum(scores) / len(scores) if scores else None

    return DailyExerciseBatch(
        generated_date=today,
        track_id=track_id,
        exercises=exercises,
        completed_count=completed_count,
        total_count=len(exercises),
        average_score=round(average_score, 1) if average_score is not None else None,
    )


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

            # Only mark topic completed if score >= 7 (proficiency threshold)
            if score >= 7:
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
                "completed_topics": [topic] if score >= 7 else [],
                "sessions_completed": 1,
                "average_score": score,
            }).execute()
    except Exception as e:
        print(f"Failed to update language track progress: {e}")
