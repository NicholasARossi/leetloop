"""System Design Review endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.models.system_design_schemas import (
    AttemptGrade,
    AttemptHistoryItem,
    AttemptHistoryResponse,
    CompleteReviewRequest,
    CompleteReviewResponse,
    CreateAttemptRequest,
    CreateSessionRequest,
    DashboardQuestion,
    GeminiGradingContext,
    GeminiQuestionContext,
    NextTopicInfo,
    QuestionGrade,
    RubricWeights,
    SessionGrade,
    SessionHistoryItem,
    SessionHistoryResponse,
    SessionQuestion,
    SetActiveTrackRequest,
    SubmitAttemptRequest,
    SubmitResponseRequest,
    SystemDesignAttempt,
    SystemDesignDashboardSummary,
    SystemDesignReviewItem,
    SystemDesignSession,
    SystemDesignTrack,
    TopicInfo,
    TrackProgressResponse,
    TrackSummary,
    UserTrackProgress,
)
from app.services.system_design_service import BookContentContext, get_system_design_service

router = APIRouter()


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


# ============ Sessions ============


@router.post("/system-design/{user_id}/sessions", response_model=SystemDesignSession)
async def create_session(
    user_id: UUID,
    request: CreateSessionRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Start a new system design session and generate questions."""
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
        topics = track_data.get("topics", [])

        # Find topic info
        topic_info = next((t for t in topics if t["name"] == request.topic), None)
        example_systems = topic_info.get("example_systems", []) if topic_info else []

        # Get user's previous weak areas from grades
        weak_areas = []
        grades_response = (
            supabase.table("system_design_grades")
            .select("gaps")
            .eq("session_id", supabase.table("system_design_sessions")
                .select("id")
                .eq("user_id", str(user_id))
                .order("completed_at", desc=True)
                .limit(3))
            .execute()
        )
        # Flatten gaps from recent sessions
        if grades_response.data:
            for g in grades_response.data:
                weak_areas.extend(g.get("gaps", []))
        weak_areas = list(set(weak_areas))[:5]  # Dedupe and limit

        # Check for book content linked to this track/topic
        book_content = None
        try:
            book_response = (
                supabase.table("book_content")
                .select("chapter_title, summary, key_concepts, case_studies")
                .eq("track_id", str(request.track_id))
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
            pass  # Book content is optional enhancement

        # Generate questions via Gemini
        service = get_system_design_service()
        context = GeminiQuestionContext(
            track_type=track_data["track_type"],
            topic=request.topic,
            example_systems=example_systems,
            user_weak_areas=weak_areas,
        )
        generated = await service.generate_questions(context, book_content)

        # Convert to storage format
        questions_json = [
            {
                "id": q.id,
                "text": q.text,
                "focus_area": q.focus_area,
                "key_concepts": q.key_concepts,
            }
            for q in generated
        ]

        # Create session
        session_data = {
            "user_id": str(user_id),
            "track_id": str(request.track_id),
            "topic": request.topic,
            "questions": questions_json,
            "session_type": request.session_type,
            "status": "in_progress",
        }

        response = (
            supabase.table("system_design_sessions")
            .insert(session_data)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create session")

        session = response.data[0]
        questions = [
            SessionQuestion(
                id=q["id"],
                text=q["text"],
                focus_area=q["focus_area"],
                key_concepts=q.get("key_concepts", []),
            )
            for q in session.get("questions", [])
        ]

        return SystemDesignSession(
            id=session["id"],
            user_id=session["user_id"],
            track_id=session.get("track_id"),
            topic=session["topic"],
            questions=questions,
            session_type=session.get("session_type"),
            status=session["status"],
            started_at=session["started_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/system-design/sessions/{session_id}", response_model=SystemDesignSession)
async def get_session(
    session_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get session details with responses."""
    try:
        # Get session
        session_response = (
            supabase.table("system_design_sessions")
            .select("*")
            .eq("id", str(session_id))
            .single()
            .execute()
        )

        if not session_response.data:
            raise HTTPException(status_code=404, detail="Session not found")

        session = session_response.data

        # Get responses
        responses_response = (
            supabase.table("system_design_responses")
            .select("*")
            .eq("session_id", str(session_id))
            .execute()
        )

        responses_by_id = {r["question_id"]: r for r in (responses_response.data or [])}

        # Build questions with responses
        questions = []
        for q in session.get("questions", []):
            resp = responses_by_id.get(q["id"])
            questions.append(SessionQuestion(
                id=q["id"],
                text=q["text"],
                focus_area=q["focus_area"],
                key_concepts=q.get("key_concepts", []),
                response=resp.get("response_text") if resp else None,
                word_count=resp.get("word_count") if resp else None,
            ))

        return SystemDesignSession(
            id=session["id"],
            user_id=session["user_id"],
            track_id=session.get("track_id"),
            topic=session["topic"],
            questions=questions,
            session_type=session.get("session_type"),
            status=session["status"],
            started_at=session["started_at"],
            completed_at=session.get("completed_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.post("/system-design/sessions/{session_id}/response")
async def submit_response(
    session_id: UUID,
    request: SubmitResponseRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Submit a response for a question."""
    try:
        # Verify session exists and is in progress
        session_response = (
            supabase.table("system_design_sessions")
            .select("status")
            .eq("id", str(session_id))
            .single()
            .execute()
        )

        if not session_response.data:
            raise HTTPException(status_code=404, detail="Session not found")

        if session_response.data["status"] != "in_progress":
            raise HTTPException(status_code=400, detail="Session is not in progress")

        word_count = len(request.response_text.split())

        # Upsert response
        response = (
            supabase.table("system_design_responses")
            .upsert({
                "session_id": str(session_id),
                "question_id": request.question_id,
                "response_text": request.response_text,
                "word_count": word_count,
            }, on_conflict="session_id,question_id")
            .execute()
        )

        return {
            "success": True,
            "question_id": request.question_id,
            "word_count": word_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit response: {str(e)}")


@router.post("/system-design/sessions/{session_id}/complete", response_model=SessionGrade)
async def complete_session(
    session_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Complete session and trigger grading."""
    try:
        # Get session with track info
        session_response = (
            supabase.table("system_design_sessions")
            .select("*, system_design_tracks(*)")
            .eq("id", str(session_id))
            .single()
            .execute()
        )

        if not session_response.data:
            raise HTTPException(status_code=404, detail="Session not found")

        session = session_response.data

        if session["status"] == "completed":
            # Return existing grade
            grade_response = (
                supabase.table("system_design_grades")
                .select("*")
                .eq("session_id", str(session_id))
                .single()
                .execute()
            )
            if grade_response.data:
                return _parse_grade(grade_response.data)
            raise HTTPException(status_code=400, detail="Session completed but no grade found")

        # Get responses
        responses_response = (
            supabase.table("system_design_responses")
            .select("*")
            .eq("session_id", str(session_id))
            .execute()
        )

        responses_by_id = {r["question_id"]: r["response_text"] for r in (responses_response.data or [])}

        # Build grading context
        track_data = session.get("system_design_tracks", {})
        rubric_data = track_data.get("rubric", {})
        rubric = RubricWeights(**rubric_data) if rubric_data else RubricWeights()

        questions_with_responses = []
        for q in session.get("questions", []):
            questions_with_responses.append({
                "text": q["text"],
                "focus_area": q["focus_area"],
                "key_concepts": q.get("key_concepts", []),
                "response": responses_by_id.get(q["id"], ""),
            })

        # Grade via Gemini
        service = get_system_design_service()
        grading_context = GeminiGradingContext(
            track_type=track_data.get("track_type", "traditional"),
            topic=session["topic"],
            rubric=rubric,
            questions=questions_with_responses,
        )
        grading_result = await service.grade_session(grading_context)

        # Convert question grades to storage format
        question_grades_json = [
            {
                "question_id": qg.question_id,
                "score": qg.score,
                "feedback": qg.feedback,
                "rubric_scores": [
                    {"dimension": rs.dimension, "score": rs.score, "feedback": rs.feedback}
                    for rs in qg.rubric_scores
                ],
                "missed_concepts": qg.missed_concepts,
            }
            for qg in grading_result.question_grades
        ]

        # Store grade
        grade_data = {
            "session_id": str(session_id),
            "overall_score": grading_result.overall_score,
            "overall_feedback": grading_result.overall_feedback,
            "question_grades": question_grades_json,
            "strengths": grading_result.strengths,
            "gaps": grading_result.gaps,
            "review_topics": grading_result.review_topics,
            "would_hire": grading_result.would_hire,
        }

        grade_response = (
            supabase.table("system_design_grades")
            .insert(grade_data)
            .execute()
        )

        if not grade_response.data:
            raise HTTPException(status_code=500, detail="Failed to save grade")

        grade = grade_response.data[0]

        # Update session status
        supabase.table("system_design_sessions").update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", str(session_id)).execute()

        # Add review topics to queue
        user_id = session["user_id"]
        track_id = session.get("track_id")
        for topic in grading_result.review_topics:
            try:
                supabase.table("system_design_review_queue").upsert({
                    "user_id": str(user_id),
                    "track_id": str(track_id) if track_id else None,
                    "topic": topic,
                    "reason": f"Gap identified in session on {session['topic']}",
                    "priority": 1,
                    "interval_days": 1,
                    "source_session_id": str(session_id),
                }, on_conflict="user_id,topic").execute()
            except Exception:
                pass  # Ignore duplicates

        # Update track progress
        if track_id:
            _update_track_progress(
                supabase, user_id, track_id, session["topic"], grading_result.overall_score
            )

        return _parse_grade(grade)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete session: {str(e)}")


@router.get("/system-design/sessions/{session_id}/grade", response_model=SessionGrade)
async def get_session_grade(
    session_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get grade for a completed session."""
    try:
        response = (
            supabase.table("system_design_grades")
            .select("*")
            .eq("session_id", str(session_id))
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Grade not found")

        return _parse_grade(response.data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get grade: {str(e)}")


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


# ============ History ============


@router.get("/system-design/{user_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get user's session history with grades."""
    try:
        # Get sessions with count
        sessions_response = (
            supabase.table("system_design_sessions")
            .select("*, system_design_tracks(name), system_design_grades(overall_score)", count="exact")
            .eq("user_id", str(user_id))
            .order("started_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        total = sessions_response.count or 0
        sessions = []

        for s in (sessions_response.data or []):
            track = s.get("system_design_tracks")
            grade = s.get("system_design_grades")

            sessions.append(SessionHistoryItem(
                id=s["id"],
                track_name=track.get("name") if track else None,
                topic=s["topic"],
                session_type=s.get("session_type"),
                status=s["status"],
                overall_score=grade.get("overall_score") if grade else None,
                started_at=s["started_at"],
                completed_at=s.get("completed_at"),
            ))

        return SessionHistoryResponse(
            sessions=sessions,
            total=total,
            has_more=offset + limit < total,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


# ============ Helpers ============


def _parse_grade(data: dict) -> SessionGrade:
    """Parse grade data from database."""
    question_grades = []
    for qg in data.get("question_grades", []):
        from app.models.system_design_schemas import RubricScore
        rubric_scores = [
            RubricScore(
                dimension=rs["dimension"],
                score=rs["score"],
                feedback=rs.get("feedback", ""),
            )
            for rs in qg.get("rubric_scores", [])
        ]
        question_grades.append(QuestionGrade(
            question_id=qg["question_id"],
            score=qg["score"],
            feedback=qg["feedback"],
            rubric_scores=rubric_scores,
            missed_concepts=qg.get("missed_concepts", []),
        ))

    return SessionGrade(
        id=data["id"],
        session_id=data["session_id"],
        overall_score=data["overall_score"],
        overall_feedback=data["overall_feedback"],
        question_grades=question_grades,
        strengths=data.get("strengths", []),
        gaps=data.get("gaps", []),
        review_topics=data.get("review_topics", []),
        would_hire=data.get("would_hire"),
        graded_at=data["graded_at"],
    )


async def _get_or_generate_daily_questions(
    supabase: Client,
    user_id: UUID,
    track_data: dict,
    topic_name: str,
) -> list[DashboardQuestion]:
    """Get cached daily questions or generate new ones.

    Questions are structured as:
    - One scenario with 3 focused sub-questions (2 concepts each)
    - Day 1: Show parts 1 and 2
    - Day 2: Show part 3
    """
    from uuid import UUID as UUIDType
    import uuid

    track_id = track_data["id"]
    today = datetime.utcnow().date().isoformat()

    # Check for existing questions for today
    try:
        cached_response = (
            supabase.table("system_design_daily_questions")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("track_id", str(track_id))
            .eq("topic", topic_name)
            .eq("serve_date", today)
            .order("part_number")
            .execute()
        )

        if cached_response.data and len(cached_response.data) >= 2:
            # Return cached questions
            return [
                DashboardQuestion(
                    id=q["id"],
                    scenario=q.get("scenario", ""),
                    text=q["question_text"],
                    focus_area=q.get("focus_area", "general"),
                    key_concepts=q.get("key_concepts", []),
                    topic=q["topic"],
                    track_id=UUIDType(q["track_id"]),
                    part_number=q.get("part_number", 1),
                    total_parts=q.get("total_parts", 3),
                    completed=q.get("completed", False),
                )
                for q in cached_response.data[:2]
            ]
    except Exception as e:
        print(f"Failed to fetch cached questions: {e}")

    # Check if there's a part 3 from yesterday's scenario to serve today
    yesterday = (datetime.utcnow() - __import__('datetime').timedelta(days=1)).date().isoformat()
    try:
        leftover_response = (
            supabase.table("system_design_daily_questions")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("track_id", str(track_id))
            .eq("topic", topic_name)
            .eq("serve_date", yesterday)
            .eq("part_number", 3)
            .eq("completed", False)
            .limit(1)
            .execute()
        )

        if leftover_response.data:
            # Move yesterday's part 3 to today and generate 1 new sub-question
            leftover = leftover_response.data[0]
            supabase.table("system_design_daily_questions").update({
                "serve_date": today,
            }).eq("id", leftover["id"]).execute()

            # Generate 1 new sub-question to pair with it
            # (In practice, you might want a fresh scenario for variety)
    except Exception as e:
        print(f"Failed to check leftover questions: {e}")

    # Generate new questions
    try:
        # Find topic info for example systems
        topics = track_data.get("topics", [])
        topic_info = next((t for t in topics if t["name"] == topic_name), None)
        example_systems = topic_info.get("example_systems", []) if topic_info else []

        service = get_system_design_service()
        context = GeminiQuestionContext(
            track_type=track_data["track_type"],
            topic=topic_name,
            example_systems=example_systems,
            user_weak_areas=[],
        )

        # Generate scenario with 3 sub-questions total
        # Today: serve parts 1 & 2, Tomorrow: serve part 3
        generated = await service.generate_dashboard_questions(context, count=3)
        scenario = generated.get("scenario", "")
        sub_questions = generated.get("sub_questions", [])
        total_parts = generated.get("total_parts", 3)
        question_set_id = str(uuid.uuid4())
        tomorrow = (datetime.utcnow() + __import__('datetime').timedelta(days=1)).date().isoformat()

        # Cache all 3 sub-questions
        questions = []
        for i, sq in enumerate(sub_questions):
            part_num = sq.get("part_number", i + 1)
            # Parts 1-2 for today, part 3 for tomorrow
            serve_date = today if part_num <= 2 else tomorrow

            try:
                insert_data = {
                    "user_id": str(user_id),
                    "track_id": str(track_id),
                    "topic": topic_name,
                    "scenario": scenario,
                    "question_text": sq["text"],
                    "focus_area": sq.get("focus_area", "general"),
                    "key_concepts": sq.get("key_concepts", []),
                    "part_number": part_num,
                    "total_parts": total_parts,
                    "question_set_id": question_set_id,
                    "serve_date": serve_date,
                }

                insert_response = (
                    supabase.table("system_design_daily_questions")
                    .insert(insert_data)
                    .execute()
                )

                if insert_response.data and part_num <= 2:
                    q = insert_response.data[0]
                    questions.append(DashboardQuestion(
                        id=q["id"],
                        scenario=q.get("scenario", ""),
                        text=q["question_text"],
                        focus_area=q.get("focus_area", "general"),
                        key_concepts=q.get("key_concepts", []),
                        topic=q["topic"],
                        track_id=UUIDType(q["track_id"]),
                        part_number=q.get("part_number", 1),
                        total_parts=q.get("total_parts", 3),
                        completed=False,
                    ))
            except Exception as e:
                print(f"Failed to cache question: {e}")
                # Create in-memory fallback for today's questions
                if part_num <= 2:
                    questions.append(DashboardQuestion(
                        id=str(uuid.uuid4()),
                        scenario=scenario,
                        text=sq["text"],
                        focus_area=sq.get("focus_area", "general"),
                        key_concepts=sq.get("key_concepts", []),
                        topic=topic_name,
                        track_id=UUIDType(track_id),
                        part_number=part_num,
                        total_parts=total_parts,
                        completed=False,
                    ))

        return questions[:2]
    except Exception as e:
        print(f"Failed to generate daily questions: {e}")
        return []


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


# ============ Simplified Attempts (Single Question Flow) ============


@router.post("/system-design/{user_id}/attempt", response_model=SystemDesignAttempt)
async def create_attempt(
    user_id: UUID,
    request: CreateAttemptRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Create a new single-question system design attempt."""
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
        topics = track_data.get("topics", [])

        # Find topic info
        topic_info = next((t for t in topics if t["name"] == request.topic), None)
        example_systems = topic_info.get("example_systems", []) if topic_info else []

        # Get user's previous weak areas from recent attempts
        weak_areas = []
        try:
            recent_attempts = (
                supabase.table("system_design_attempts")
                .select("review_topics")
                .eq("user_id", str(user_id))
                .eq("status", "graded")
                .order("graded_at", desc=True)
                .limit(5)
                .execute()
            )
            if recent_attempts.data:
                for a in recent_attempts.data:
                    weak_areas.extend(a.get("review_topics") or [])
                weak_areas = list(set(weak_areas))[:5]
        except Exception:
            pass

        # Generate single question via Gemini
        service = get_system_design_service()
        context = GeminiQuestionContext(
            track_type=track_data["track_type"],
            topic=request.topic,
            example_systems=example_systems,
            user_weak_areas=weak_areas,
        )
        generated = await service.generate_single_question(context)

        # Create attempt
        attempt_data = {
            "user_id": str(user_id),
            "track_id": str(request.track_id),
            "topic": request.topic,
            "question_text": generated.text,
            "question_focus_area": generated.focus_area,
            "question_key_concepts": generated.key_concepts,
            "status": "pending",
        }

        response = (
            supabase.table("system_design_attempts")
            .insert(attempt_data)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create attempt")

        attempt = response.data[0]
        return SystemDesignAttempt(
            id=attempt["id"],
            user_id=attempt["user_id"],
            track_id=attempt.get("track_id"),
            topic=attempt["topic"],
            question_text=attempt["question_text"],
            question_focus_area=attempt.get("question_focus_area"),
            question_key_concepts=attempt.get("question_key_concepts") or [],
            status=attempt["status"],
            created_at=attempt["created_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create attempt: {str(e)}")


@router.post("/system-design/attempts/{attempt_id}/submit", response_model=AttemptGrade)
async def submit_attempt(
    attempt_id: UUID,
    request: SubmitAttemptRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Submit response for an attempt and get AI grading."""
    try:
        # Get attempt with track info
        attempt_response = (
            supabase.table("system_design_attempts")
            .select("*, system_design_tracks(*)")
            .eq("id", str(attempt_id))
            .single()
            .execute()
        )

        if not attempt_response.data:
            raise HTTPException(status_code=404, detail="Attempt not found")

        attempt = attempt_response.data

        if attempt["status"] == "graded":
            # Return existing grade
            return AttemptGrade(
                score=attempt["score"],
                verdict=attempt["verdict"],
                feedback=attempt["feedback"],
                missed_concepts=attempt.get("missed_concepts") or [],
                review_topics=attempt.get("review_topics") or [],
            )

        # Calculate word count
        word_count = len(request.response_text.split())

        # Grade via Gemini
        service = get_system_design_service()
        track_data = attempt.get("system_design_tracks", {})

        grading_result = await service.grade_attempt(
            topic=attempt["topic"],
            track_type=track_data.get("track_type", "traditional"),
            question_text=attempt["question_text"],
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
            "missed_concepts": grading_result.missed_concepts,
            "review_topics": grading_result.review_topics,
            "status": "graded",
            "graded_at": datetime.utcnow().isoformat(),
        }

        supabase.table("system_design_attempts").update(update_data).eq("id", str(attempt_id)).execute()

        # Add review topics to queue if score < 7
        if grading_result.score < 7:
            user_id = attempt["user_id"]
            track_id = attempt.get("track_id")
            for topic in grading_result.review_topics:
                try:
                    supabase.table("system_design_review_queue").upsert({
                        "user_id": str(user_id),
                        "track_id": str(track_id) if track_id else None,
                        "topic": topic,
                        "reason": f"Weak area from attempt on {attempt['topic']}",
                        "priority": 1,
                        "interval_days": 1,
                    }, on_conflict="user_id,topic").execute()
                except Exception:
                    pass

        # Update track progress
        track_id = attempt.get("track_id")
        if track_id:
            _update_track_progress(
                supabase, attempt["user_id"], track_id, attempt["topic"], grading_result.score
            )

        return AttemptGrade(
            score=grading_result.score,
            verdict=grading_result.verdict,
            feedback=grading_result.feedback,
            missed_concepts=grading_result.missed_concepts,
            review_topics=grading_result.review_topics,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit attempt: {str(e)}")


@router.get("/system-design/{user_id}/attempts", response_model=AttemptHistoryResponse)
async def get_attempt_history(
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get user's attempt history."""
    try:
        # Get attempts with count
        response = (
            supabase.table("system_design_attempts")
            .select("*, system_design_tracks(name)", count="exact")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        total = response.count or 0
        attempts = []

        for a in (response.data or []):
            track = a.get("system_design_tracks")
            attempts.append(AttemptHistoryItem(
                id=a["id"],
                topic=a["topic"],
                question_text=a["question_text"],
                score=a.get("score"),
                verdict=a.get("verdict"),
                status=a["status"],
                created_at=a["created_at"],
                graded_at=a.get("graded_at"),
                track_name=track.get("name") if track else None,
            ))

        return AttemptHistoryResponse(
            attempts=attempts,
            total=total,
            has_more=offset + limit < total,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attempt history: {str(e)}")


@router.get("/system-design/attempts/{attempt_id}", response_model=SystemDesignAttempt)
async def get_attempt(
    attempt_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get a specific attempt."""
    try:
        response = (
            supabase.table("system_design_attempts")
            .select("*")
            .eq("id", str(attempt_id))
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Attempt not found")

        attempt = response.data
        return SystemDesignAttempt(
            id=attempt["id"],
            user_id=attempt["user_id"],
            track_id=attempt.get("track_id"),
            topic=attempt["topic"],
            question_text=attempt["question_text"],
            question_focus_area=attempt.get("question_focus_area"),
            question_key_concepts=attempt.get("question_key_concepts") or [],
            response_text=attempt.get("response_text"),
            word_count=attempt.get("word_count") or 0,
            score=attempt.get("score"),
            verdict=attempt.get("verdict"),
            feedback=attempt.get("feedback"),
            missed_concepts=attempt.get("missed_concepts") or [],
            review_topics=attempt.get("review_topics") or [],
            status=attempt["status"],
            created_at=attempt["created_at"],
            graded_at=attempt.get("graded_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attempt: {str(e)}")


# ============ Dashboard Integration ============


@router.get("/system-design/{user_id}/dashboard", response_model=SystemDesignDashboardSummary)
async def get_dashboard_summary(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get system design summary for dashboard display."""
    from datetime import timedelta

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

        # Get or generate daily questions
        daily_questions = []
        if next_topic and track_data:
            daily_questions = await _get_or_generate_daily_questions(
                supabase, user_id, track_data, next_topic.topic_name
            )

        # Get reviews due
        reviews_response = supabase.rpc(
            "get_due_system_design_reviews",
            {"p_user_id": str(user_id), "p_limit": 5}
        ).execute()

        reviews_due = []
        if reviews_response.data:
            reviews_due = [SystemDesignReviewItem(**r) for r in reviews_response.data]

        # Get recent sessions this week
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        sessions_response = (
            supabase.table("system_design_sessions")
            .select("id", count="exact")
            .eq("user_id", str(user_id))
            .gte("started_at", week_ago)
            .execute()
        )
        sessions_this_week = sessions_response.count or 0

        # Get most recent score
        recent_grade_response = (
            supabase.table("system_design_grades")
            .select("overall_score, session_id")
            .order("graded_at", desc=True)
            .limit(1)
            .execute()
        )
        recent_score = None
        if recent_grade_response.data:
            # Verify this grade belongs to the user
            grade = recent_grade_response.data[0]
            session_check = (
                supabase.table("system_design_sessions")
                .select("user_id")
                .eq("id", grade["session_id"])
                .eq("user_id", str(user_id))
                .limit(1)
                .execute()
            )
            if session_check.data:
                recent_score = grade["overall_score"]

        return SystemDesignDashboardSummary(
            has_active_track=has_active_track,
            active_track=active_track,
            next_topic=next_topic,
            daily_questions=daily_questions,
            reviews_due_count=len(reviews_due),
            reviews_due=reviews_due,
            recent_score=recent_score,
            sessions_this_week=sessions_this_week,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard summary: {str(e)}")


@router.post("/system-design/daily-questions/{question_id}/submit", response_model=AttemptGrade)
async def submit_dashboard_question(
    question_id: UUID,
    request: SubmitAttemptRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Submit an answer for a dashboard question and get AI grading."""
    try:
        # Get the cached question
        question_response = (
            supabase.table("system_design_daily_questions")
            .select("*, system_design_tracks(*)")
            .eq("id", str(question_id))
            .single()
            .execute()
        )

        if not question_response.data:
            raise HTTPException(status_code=404, detail="Question not found")

        question = question_response.data
        track_data = question.get("system_design_tracks", {})

        # Build full question context with scenario
        scenario = question.get("scenario", "")
        sub_question = question["question_text"]
        full_question = f"{scenario}\n\n{sub_question}" if scenario else sub_question

        # Grade the response (focused on just 2 concepts)
        service = get_system_design_service()
        grading_result = await service.grade_attempt(
            topic=question["topic"],
            track_type=track_data.get("track_type", "traditional"),
            question_text=full_question,
            focus_area=question.get("focus_area") or "general",
            key_concepts=question.get("key_concepts") or [],
            response_text=request.response_text,
        )

        # Mark question as completed
        supabase.table("system_design_daily_questions").update({
            "completed": True,
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", str(question_id)).execute()

        # Create an attempt record for history
        word_count = len(request.response_text.split())
        attempt_data = {
            "user_id": question["user_id"],
            "track_id": question["track_id"],
            "topic": question["topic"],
            "question_text": question["question_text"],
            "question_focus_area": question.get("focus_area"),
            "question_key_concepts": question.get("key_concepts") or [],
            "response_text": request.response_text,
            "word_count": word_count,
            "score": grading_result.score,
            "verdict": grading_result.verdict,
            "feedback": grading_result.feedback,
            "missed_concepts": grading_result.missed_concepts,
            "review_topics": grading_result.review_topics,
            "status": "graded",
            "graded_at": datetime.utcnow().isoformat(),
        }

        supabase.table("system_design_attempts").insert(attempt_data).execute()

        # Add review topics to queue if score < 7
        if grading_result.score < 7:
            user_id = question["user_id"]
            track_id = question.get("track_id")
            for topic in grading_result.review_topics:
                try:
                    supabase.table("system_design_review_queue").upsert({
                        "user_id": str(user_id),
                        "track_id": str(track_id) if track_id else None,
                        "topic": topic,
                        "reason": f"Weak area from dashboard question on {question['topic']}",
                        "priority": 1,
                        "interval_days": 1,
                    }, on_conflict="user_id,topic").execute()
                except Exception:
                    pass

        # Update track progress
        track_id = question.get("track_id")
        if track_id:
            _update_track_progress(
                supabase, question["user_id"], track_id, question["topic"], grading_result.score
            )

        return AttemptGrade(
            score=grading_result.score,
            verdict=grading_result.verdict,
            feedback=grading_result.feedback,
            missed_concepts=grading_result.missed_concepts,
            review_topics=grading_result.review_topics,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit answer: {str(e)}")


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
