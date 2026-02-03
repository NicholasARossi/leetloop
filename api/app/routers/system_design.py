"""System Design Review endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.models.system_design_schemas import (
    CompleteReviewRequest,
    CompleteReviewResponse,
    CreateSessionRequest,
    GeminiGradingContext,
    GeminiQuestionContext,
    QuestionGrade,
    RubricWeights,
    SessionGrade,
    SessionHistoryItem,
    SessionHistoryResponse,
    SessionQuestion,
    SubmitResponseRequest,
    SystemDesignReviewItem,
    SystemDesignSession,
    SystemDesignTrack,
    TopicInfo,
    TrackProgressResponse,
    TrackSummary,
    UserTrackProgress,
)
from app.services.system_design_service import get_system_design_service

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

        # Get user progress
        progress_response = (
            supabase.table("user_track_progress")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("track_id", str(track_id))
            .maybeSingle()
            .execute()
        )

        progress = None
        completion_percentage = 0.0
        next_topic = None

        if progress_response.data:
            progress = UserTrackProgress(**progress_response.data)
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

        # Generate questions via Gemini
        service = get_system_design_service()
        context = GeminiQuestionContext(
            track_type=track_data["track_type"],
            topic=request.topic,
            example_systems=example_systems,
            user_weak_areas=weak_areas,
        )
        generated = await service.generate_questions(context)

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


def _update_track_progress(
    supabase: Client,
    user_id: str,
    track_id: str,
    topic: str,
    score: float,
):
    """Update user's track progress after completing a session."""
    try:
        # Get existing progress
        progress_response = (
            supabase.table("user_track_progress")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("track_id", str(track_id))
            .maybeSingle()
            .execute()
        )

        if progress_response.data:
            # Update existing
            progress = progress_response.data
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
