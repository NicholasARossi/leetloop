"""ML Coding Drills endpoints."""

import time
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.models.ml_coding_schemas import (
    CompleteMLCodingReviewRequest,
    CompleteMLCodingReviewResponse,
    MLCodingDailyBatch,
    MLCodingDailyExercise,
    MLCodingDashboardSummary,
    MLCodingExerciseGrade,
    MLCodingProblem,
    MLCodingReviewItem,
    SubmitMLCodingExerciseRequest,
)
from app.services.ml_coding_service import get_ml_coding_service

router = APIRouter()

# In-memory TTL cache for dashboard
_ml_dashboard_cache: dict[str, tuple[float, MLCodingDashboardSummary]] = {}
_ML_DASHBOARD_CACHE_TTL = 300  # 5 minutes

# In-memory TTL cache for daily exercises
_ml_daily_cache: dict[str, tuple[float, MLCodingDailyBatch]] = {}
_ML_DAILY_CACHE_TTL = 60  # 1 minute


# ============ Problems ============


@router.get("/ml-coding/problems", response_model=list[MLCodingProblem])
async def list_problems(
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """List all ML coding problems."""
    try:
        response = (
            supabase.table("ml_coding_problems")
            .select("*")
            .order("sort_order")
            .execute()
        )
        return [MLCodingProblem(**p) for p in response.data] if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list problems: {str(e)}")


# ============ Daily Exercises ============


@router.get("/ml-coding/{user_id}/daily-exercises", response_model=MLCodingDailyBatch)
async def get_daily_exercises(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get today's ML coding exercise batch. Generates if not exists."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cache_key = f"ml:{user_id}:{today}"

    cached = _ml_daily_cache.get(cache_key)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    try:
        existing = (
            supabase.table("ml_coding_daily_exercises")
            .select("*, ml_coding_problems(*)")
            .eq("user_id", str(user_id))
            .eq("generated_date", today)
            .order("sort_order")
            .execute()
        )

        if existing.data:
            batch = _build_batch_response(existing.data, today)
            _ml_daily_cache[cache_key] = (time.monotonic() + _ML_DAILY_CACHE_TTL, batch)
            return batch

        # Generate new batch
        batch = await _generate_daily_batch(supabase, user_id, today)
        _ml_daily_cache[cache_key] = (time.monotonic() + _ML_DAILY_CACHE_TTL, batch)
        return batch

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get daily exercises: {str(e)}")


@router.post("/ml-coding/daily-exercises/{exercise_id}/submit", response_model=MLCodingExerciseGrade)
async def submit_exercise(
    exercise_id: UUID,
    request: SubmitMLCodingExerciseRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Submit code for an ML coding exercise and get Gemini grade."""
    try:
        # Get the exercise with problem details
        exercise_response = (
            supabase.table("ml_coding_daily_exercises")
            .select("*, ml_coding_problems(*)")
            .eq("id", str(exercise_id))
            .single()
            .execute()
        )

        if not exercise_response.data:
            raise HTTPException(status_code=404, detail="Exercise not found")

        exercise = exercise_response.data

        # Already completed - return existing grade
        if exercise["status"] == "completed":
            return MLCodingExerciseGrade(
                score=exercise["score"],
                verdict=exercise["verdict"],
                feedback=exercise["feedback"] or "",
                correctness_score=exercise["correctness_score"],
                code_quality_score=exercise["code_quality_score"],
                math_understanding_score=exercise["math_understanding_score"],
                missed_concepts=exercise.get("missed_concepts") or [],
                suggested_improvements=exercise.get("suggested_improvements") or [],
            )

        problem = exercise.get("ml_coding_problems") or {}

        # Grade via Gemini
        service = get_ml_coding_service()
        grade = await service.grade_code(
            problem_title=problem.get("title", "ML Coding Problem"),
            prompt_text=exercise["prompt_text"],
            key_concepts=problem.get("key_concepts") or [],
            math_concepts=problem.get("math_concepts") or [],
            submitted_code=request.submitted_code,
        )

        # Update exercise record
        update_data = {
            "submitted_code": request.submitted_code,
            "score": float(grade.score),
            "verdict": grade.verdict,
            "feedback": grade.feedback,
            "correctness_score": float(grade.correctness_score),
            "code_quality_score": float(grade.code_quality_score),
            "math_understanding_score": float(grade.math_understanding_score),
            "missed_concepts": grade.missed_concepts,
            "suggested_improvements": grade.suggested_improvements,
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
        }

        supabase.table("ml_coding_daily_exercises").update(update_data).eq(
            "id", str(exercise_id)
        ).execute()

        # Add to review queue if score < 7
        if grade.score < 7 and problem.get("slug"):
            try:
                supabase.table("ml_coding_review_queue").upsert(
                    {
                        "user_id": exercise["user_id"],
                        "problem_slug": problem["slug"],
                        "reason": f"Score {grade.score:.1f} on {problem.get('title', 'problem')}",
                        "priority": 1,
                        "interval_days": 1,
                    },
                    on_conflict="user_id,problem_slug",
                ).execute()
            except Exception:
                pass

        # Invalidate caches
        today = datetime.utcnow().strftime("%Y-%m-%d")
        _ml_daily_cache.pop(f"ml:{exercise['user_id']}:{today}", None)
        _ml_dashboard_cache.pop(str(exercise["user_id"]), None)

        return grade

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit exercise: {str(e)}")


@router.post("/ml-coding/{user_id}/daily-exercises/regenerate", response_model=MLCodingDailyBatch)
async def regenerate_daily_exercises(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Delete pending exercises for today, keep completed ones, generate new ones."""
    today = datetime.utcnow().strftime("%Y-%m-%d")

    try:
        # Delete pending exercises for today
        supabase.table("ml_coding_daily_exercises").delete().eq(
            "user_id", str(user_id)
        ).eq("generated_date", today).eq("status", "pending").execute()

        # Get remaining completed exercises
        remaining = (
            supabase.table("ml_coding_daily_exercises")
            .select("*, ml_coding_problems(*)")
            .eq("user_id", str(user_id))
            .eq("generated_date", today)
            .order("sort_order")
            .execute()
        )

        completed_exercises = remaining.data or []
        completed_count = len(completed_exercises)
        target_total = 3
        slots_to_fill = max(0, target_total - completed_count)

        if slots_to_fill == 0:
            batch = _build_batch_response(completed_exercises, today)
            _ml_daily_cache.pop(f"ml:{user_id}:{today}", None)
            return batch

        batch = await _generate_daily_batch(
            supabase, user_id, today,
            existing_exercises=completed_exercises,
            target_count=slots_to_fill,
        )

        _ml_daily_cache.pop(f"ml:{user_id}:{today}", None)
        return batch

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate exercises: {str(e)}")


# ============ Reviews ============


@router.get("/ml-coding/{user_id}/reviews", response_model=list[MLCodingReviewItem])
async def get_due_reviews(
    user_id: UUID,
    limit: int = 10,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get ML coding problems due for review."""
    try:
        response = supabase.rpc(
            "get_due_ml_coding_reviews",
            {"p_user_id": str(user_id), "p_limit": limit},
        ).execute()

        return [MLCodingReviewItem(**r) for r in response.data] if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reviews: {str(e)}")


@router.post("/ml-coding/reviews/{review_id}/complete", response_model=CompleteMLCodingReviewResponse)
async def complete_review(
    review_id: UUID,
    request: CompleteMLCodingReviewRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Mark an ML coding review as complete (pass/fail)."""
    try:
        supabase.rpc(
            "complete_ml_coding_review",
            {"p_review_id": str(review_id), "p_success": request.success},
        ).execute()

        updated = (
            supabase.table("ml_coding_review_queue")
            .select("*")
            .eq("id", str(review_id))
            .single()
            .execute()
        )

        if not updated.data:
            raise HTTPException(status_code=404, detail="Review not found")

        return CompleteMLCodingReviewResponse(
            id=review_id,
            next_review=updated.data["next_review"],
            new_interval_days=updated.data["interval_days"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete review: {str(e)}")


# ============ Dashboard ============


@router.get("/ml-coding/{user_id}/dashboard", response_model=MLCodingDashboardSummary)
async def get_dashboard(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get ML coding dashboard summary."""
    cache_key = str(user_id)
    cached = _ml_dashboard_cache.get(cache_key)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    try:
        # Total problems
        problems_response = (
            supabase.table("ml_coding_problems")
            .select("id", count="exact")
            .execute()
        )
        problems_total = problems_response.count or 10

        # Problems attempted (distinct problem_ids from completed exercises)
        attempted_response = (
            supabase.table("ml_coding_daily_exercises")
            .select("problem_id")
            .eq("user_id", str(user_id))
            .eq("status", "completed")
            .execute()
        )
        attempted_ids = set()
        if attempted_response.data:
            for row in attempted_response.data:
                if row.get("problem_id"):
                    attempted_ids.add(row["problem_id"])
        problems_attempted = len(attempted_ids)

        # Today's exercises
        today = datetime.utcnow().strftime("%Y-%m-%d")
        today_response = (
            supabase.table("ml_coding_daily_exercises")
            .select("status, score")
            .eq("user_id", str(user_id))
            .eq("generated_date", today)
            .execute()
        )

        today_count = 0
        today_completed = 0
        if today_response.data:
            today_count = len(today_response.data)
            today_completed = sum(1 for e in today_response.data if e["status"] == "completed")

        # Average score from recent completed exercises
        recent_response = (
            supabase.table("ml_coding_daily_exercises")
            .select("score")
            .eq("user_id", str(user_id))
            .eq("status", "completed")
            .order("completed_at", desc=True)
            .limit(10)
            .execute()
        )

        recent_scores = []
        if recent_response.data:
            recent_scores = [float(r["score"]) for r in recent_response.data if r.get("score") is not None]

        average_score = round(sum(recent_scores) / len(recent_scores), 1) if recent_scores else None

        # Reviews due
        reviews_response = supabase.rpc(
            "get_due_ml_coding_reviews",
            {"p_user_id": str(user_id), "p_limit": 10},
        ).execute()
        reviews_due_count = len(reviews_response.data) if reviews_response.data else 0

        summary = MLCodingDashboardSummary(
            problems_attempted=problems_attempted,
            problems_total=problems_total,
            today_exercise_count=today_count,
            today_completed_count=today_completed,
            average_score=average_score,
            reviews_due_count=reviews_due_count,
            recent_scores=recent_scores[:5],
        )

        _ml_dashboard_cache[cache_key] = (time.monotonic() + _ML_DASHBOARD_CACHE_TTL, summary)
        return summary

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")


# ============ Internal Helpers ============


async def _generate_daily_batch(
    supabase: Client,
    user_id: UUID,
    today: str,
    existing_exercises: list[dict] = None,
    target_count: int = 3,
) -> MLCodingDailyBatch:
    """Generate a batch of ML coding exercises for today."""
    existing_exercises = existing_exercises or []
    start_order = len(existing_exercises)

    # 1. Get all problems
    problems_response = (
        supabase.table("ml_coding_problems")
        .select("*")
        .order("sort_order")
        .execute()
    )
    all_problems = problems_response.data or []

    if not all_problems:
        raise HTTPException(status_code=500, detail="No ML coding problems available")

    # 2. Get due reviews
    reviews_response = supabase.rpc(
        "get_due_ml_coding_reviews",
        {"p_user_id": str(user_id), "p_limit": 1},
    ).execute()

    review_slugs = set()
    if reviews_response.data:
        review_slugs = {r["problem_slug"] for r in reviews_response.data}

    # 3. Get recently done problem IDs (last 7 days) to avoid repetition
    from datetime import timedelta
    week_ago = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")
    recent_response = (
        supabase.table("ml_coding_daily_exercises")
        .select("problem_id")
        .eq("user_id", str(user_id))
        .gte("generated_date", week_ago)
        .execute()
    )
    recent_problem_ids = set()
    if recent_response.data:
        recent_problem_ids = {r["problem_id"] for r in recent_response.data if r.get("problem_id")}

    # Also exclude problems already done today
    existing_problem_ids = {e.get("problem_id") for e in existing_exercises if e.get("problem_id")}

    # 4. Get user's weak areas from recent exercises
    weak_areas = []
    try:
        weak_response = (
            supabase.table("ml_coding_daily_exercises")
            .select("missed_concepts")
            .eq("user_id", str(user_id))
            .eq("status", "completed")
            .order("completed_at", desc=True)
            .limit(5)
            .execute()
        )
        if weak_response.data:
            for r in weak_response.data:
                weak_areas.extend(r.get("missed_concepts") or [])
            weak_areas = list(set(weak_areas))[:5]
    except Exception:
        pass

    # 5. Select problems: 1 review + remaining new
    selected = []

    # Review slot
    for p in all_problems:
        if p["slug"] in review_slugs and len(selected) < 1:
            selected.append({**p, "is_review": True})

    # New problem slots (avoid recently done)
    new_needed = target_count - len(selected)
    for p in all_problems:
        if len(selected) >= target_count:
            break
        if p["id"] in recent_problem_ids or p["id"] in existing_problem_ids:
            continue
        if any(s["id"] == p["id"] for s in selected):
            continue
        selected.append({**p, "is_review": False})

    # If still need more, pull from recent (cycling through bank)
    if len(selected) < target_count:
        for p in all_problems:
            if len(selected) >= target_count:
                break
            if any(s["id"] == p["id"] for s in selected):
                continue
            if p["id"] in existing_problem_ids:
                continue
            selected.append({**p, "is_review": False})

    # 6. Generate variations via Gemini
    service = get_ml_coding_service()
    problems_for_gen = [
        {
            "title": p["title"],
            "description": p["description"],
            "key_concepts": p.get("key_concepts", []),
            "math_concepts": p.get("math_concepts", []),
            "is_review": p.get("is_review", False),
        }
        for p in selected
    ]

    variations = await service.generate_batch_variations(problems_for_gen, weak_areas)

    # 7. Insert into database
    rows = []
    for i, (problem, variation) in enumerate(zip(selected, variations)):
        rows.append({
            "user_id": str(user_id),
            "problem_id": problem["id"],
            "generated_date": today,
            "sort_order": start_order + i,
            "prompt_text": variation["prompt_text"],
            "starter_code": variation.get("starter_code"),
            "is_review": problem.get("is_review", False),
            "status": "pending",
        })

    if rows:
        supabase.table("ml_coding_daily_exercises").insert(rows).execute()

    # 8. Fetch all exercises for today and return
    all_response = (
        supabase.table("ml_coding_daily_exercises")
        .select("*, ml_coding_problems(*)")
        .eq("user_id", str(user_id))
        .eq("generated_date", today)
        .order("sort_order")
        .execute()
    )

    return _build_batch_response(all_response.data or [], today)


def _build_batch_response(exercises_data: list[dict], today: str) -> MLCodingDailyBatch:
    """Build an MLCodingDailyBatch from raw exercise rows."""
    exercises = []
    completed_count = 0
    scores = []

    for ex in exercises_data:
        problem = ex.get("ml_coding_problems") or {}
        exercises.append(MLCodingDailyExercise(
            id=ex["id"],
            problem_id=ex.get("problem_id"),
            problem_slug=problem.get("slug"),
            problem_title=problem.get("title"),
            prompt_text=ex["prompt_text"],
            starter_code=ex.get("starter_code"),
            status=ex["status"],
            is_review=ex.get("is_review", False),
            sort_order=ex.get("sort_order", 0),
            submitted_code=ex.get("submitted_code"),
            score=ex.get("score"),
            verdict=ex.get("verdict"),
            feedback=ex.get("feedback"),
            correctness_score=ex.get("correctness_score"),
            code_quality_score=ex.get("code_quality_score"),
            math_understanding_score=ex.get("math_understanding_score"),
            missed_concepts=ex.get("missed_concepts") or [],
            suggested_improvements=ex.get("suggested_improvements") or [],
            completed_at=ex.get("completed_at"),
        ))
        if ex["status"] == "completed":
            completed_count += 1
            if ex.get("score") is not None:
                scores.append(float(ex["score"]))

    average_score = round(sum(scores) / len(scores), 1) if scores else None

    return MLCodingDailyBatch(
        generated_date=today,
        exercises=exercises,
        completed_count=completed_count,
        total_count=len(exercises),
        average_score=average_score,
    )
