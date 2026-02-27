"""Coaching endpoints for AI-powered assistance."""

import asyncio
from typing import Annotated, AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from supabase import Client

from app.db.supabase import get_supabase
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    CodeAnalysisRequest,
    CodeAnalysisResponse,
)
from app.services.code_analyzer import CodeAnalyzer
from app.services.gemini_gateway import GeminiGateway
from app.services.pattern_analyzer import get_pattern_analyzer

router = APIRouter()


def _query_previous_attempts(supabase: Client, user_id: str, problem_slug: str, exclude_submission_id: str = None) -> list[dict]:
    """Query previous attempts on the same problem for context."""
    query = (
        supabase.table("submissions")
        .select("status, status_msg, total_correct, total_testcases, language, submitted_at")
        .eq("user_id", user_id)
        .eq("problem_slug", problem_slug)
        .order("submitted_at", desc=True)
        .limit(5)
    )
    response = query.execute()
    attempts = response.data or []
    # Filter out the current submission if provided
    if exclude_submission_id:
        attempts = [a for a in attempts if a.get("id") != exclude_submission_id]
    return attempts


@router.post("/coaching/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Interactive coaching chat endpoint.

    Context can include:
    - current_problem: slug of problem being worked on
    - submission_id: recent submission to discuss
    """
    try:
        gateway = GeminiGateway()

        # Build context from user's data
        context_str = await _build_context(supabase, request)

        # Generate response
        response = await gateway.chat(
            message=request.message,
            history=request.history,
            system_context=context_str,
        )

        return ChatResponse(
            message=response,
            suggestions=_extract_suggestions(response),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/coaching/chat/stream")
async def chat_stream(
    request: ChatRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Streaming chat endpoint using Server-Sent Events.

    Returns SSE stream of chat response chunks.
    """
    try:
        gateway = GeminiGateway()
        context_str = await _build_context(supabase, request)

        async def generate() -> AsyncGenerator[str, None]:
            async for chunk in gateway.chat_stream(
                message=request.message,
                history=request.history,
                system_context=context_str,
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream failed: {str(e)}")


@router.post("/coaching/analyze", response_model=CodeAnalysisResponse)
async def analyze_code(
    request: CodeAnalysisRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Analyze submitted code for issues and improvements.

    Returns analysis including:
    - Summary of the code
    - Identified issues and root cause
    - Suggestions for improvement with specific fix
    - Pattern type and concept gap classification
    - Time/space complexity analysis
    """
    try:
        analyzer = CodeAnalyzer()

        # Query previous attempts on this problem for context
        previous_attempts = _query_previous_attempts(
            supabase,
            str(request.user_id),
            request.problem_slug,
            str(request.submission_id),
        )

        analysis = await analyzer.analyze(
            code=request.code,
            language=request.language,
            problem_slug=request.problem_slug,
            status=request.status.value,
            code_output=request.code_output,
            expected_output=request.expected_output,
            status_msg=request.status_msg,
            total_correct=request.total_correct,
            total_testcases=request.total_testcases,
            previous_attempts=previous_attempts,
        )

        # Store insight for feedback loop (non-blocking)
        if analysis.pattern_type or analysis.concept_gap or analysis.root_cause:
            try:
                supabase.table("submission_insights").insert({
                    "submission_id": str(request.submission_id),
                    "user_id": str(request.user_id),
                    "pattern_type": analysis.pattern_type,
                    "concept_gap": analysis.concept_gap,
                    "root_cause": analysis.root_cause,
                }).execute()
            except Exception:
                pass  # Don't fail analysis if insight storage fails

        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/coaching/tips/{user_id}")
async def get_personalized_tips(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get personalized tips based on user's recent performance, pattern analysis, and submission insights."""
    try:
        gateway = GeminiGateway()
        user_id_str = str(user_id)

        # Get recent failures with error context
        failures = (
            supabase.table("submissions")
            .select("problem_slug, status, tags, status_msg, total_correct, total_testcases")
            .eq("user_id", user_id_str)
            .neq("status", "Accepted")
            .order("submitted_at", desc=True)
            .limit(5)
            .execute()
        )

        # Get weak skills
        weak_skills = (
            supabase.table("skill_scores")
            .select("tag, score")
            .eq("user_id", user_id_str)
            .order("score")
            .limit(5)
            .execute()
        )

        # Get cached pattern analysis
        pattern_analysis = {}
        try:
            pattern_resp = (
                supabase.table("user_pattern_analysis")
                .select("patterns")
                .eq("user_id", user_id_str)
                .limit(1)
                .execute()
            )
            if pattern_resp.data:
                pattern_analysis = pattern_resp.data[0].get("patterns", {})
        except Exception:
            pass

        # Get recent submission insights
        submission_insights = []
        try:
            insights_resp = (
                supabase.table("submission_insights")
                .select("pattern_type, concept_gap")
                .eq("user_id", user_id_str)
                .order("created_at", desc=True)
                .limit(15)
                .execute()
            )
            if insights_resp.data:
                submission_insights = insights_resp.data
        except Exception:
            pass

        context = {
            "recent_failures": failures.data if failures.data else [],
            "weak_skills": weak_skills.data if weak_skills.data else [],
            "pattern_analysis": pattern_analysis,
            "submission_insights": submission_insights,
        }

        tips = await gateway.generate_tips(context)

        return {"tips": tips}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate tips: {str(e)}")


@router.get("/patterns/{user_id}")
async def get_patterns(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Get pattern analysis for a user's recent submissions.

    Returns cached analysis if fresh, otherwise generates new analysis via Gemini.
    """
    try:
        analyzer = get_pattern_analyzer(supabase)
        patterns = await analyzer.analyze_patterns(user_id)
        return patterns
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {str(e)}")


async def _build_context(supabase: Client, request: ChatRequest) -> str:
    """Build context string from user data for the AI."""
    context_parts = []

    # Add explicit context from request
    if request.context:
        if "current_problem" in request.context:
            context_parts.append(f"User is working on: {request.context['current_problem']}")

        if "submission_id" in request.context:
            # Fetch submission details
            sub = (
                supabase.table("submissions")
                .select("*")
                .eq("id", request.context["submission_id"])
                .single()
                .execute()
            )
            if sub.data:
                context_parts.append(f"Recent submission: {sub.data['status']} on {sub.data['problem_slug']}")
                if sub.data.get("code"):
                    context_parts.append(f"Code ({sub.data['language']}):\n```\n{sub.data['code'][:1000]}\n```")

    # Get user's weak areas
    weak = (
        supabase.table("skill_scores")
        .select("tag, score")
        .eq("user_id", str(request.user_id))
        .order("score")
        .limit(3)
        .execute()
    )
    if weak.data:
        weak_tags = [f"{w['tag']} ({w['score']:.0f})" for w in weak.data]
        context_parts.append(f"User's weak areas: {', '.join(weak_tags)}")

    return "\n".join(context_parts) if context_parts else ""


def _extract_suggestions(response: str) -> list[str]:
    """Extract follow-up suggestions from the response."""
    suggestions = []

    # Look for common patterns in the response
    suggestion_triggers = [
        "you might want to",
        "try practicing",
        "consider reviewing",
        "I recommend",
    ]

    lines = response.split("\n")
    for line in lines:
        line_lower = line.lower()
        if any(trigger in line_lower for trigger in suggestion_triggers):
            suggestions.append(line.strip())

    return suggestions[:3]  # Limit to 3 suggestions
