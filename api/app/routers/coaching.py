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

router = APIRouter()


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
    - Identified issues
    - Suggestions for improvement
    - Time/space complexity analysis
    """
    try:
        analyzer = CodeAnalyzer()

        analysis = await analyzer.analyze(
            code=request.code,
            language=request.language,
            problem_slug=request.problem_slug,
            status=request.status.value,
        )

        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/coaching/tips/{user_id}")
async def get_personalized_tips(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get personalized tips based on user's recent performance."""
    try:
        gateway = GeminiGateway()

        # Get recent failures
        failures = (
            supabase.table("submissions")
            .select("problem_slug, status, tags, code")
            .eq("user_id", str(user_id))
            .neq("status", "Accepted")
            .order("submitted_at", desc=True)
            .limit(5)
            .execute()
        )

        # Get weak skills
        weak_skills = (
            supabase.table("skill_scores")
            .select("tag, score")
            .eq("user_id", str(user_id))
            .order("score")
            .limit(3)
            .execute()
        )

        context = {
            "recent_failures": failures.data if failures.data else [],
            "weak_skills": weak_skills.data if weak_skills.data else [],
        }

        tips = await gateway.generate_tips(context)

        return {"tips": tips}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate tips: {str(e)}")


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
