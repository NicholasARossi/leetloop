"""Today's Focus endpoints - Daily mission control."""

from datetime import datetime, date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.models.schemas import (
    DailyFocusProblem,
    Difficulty,
    TodaysFocus,
)

router = APIRouter()


@router.get("/today/{user_id}", response_model=TodaysFocus)
async def get_todays_focus(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Get daily mission data for Today's Focus page.

    Combines:
    - Reviews due today (from spaced repetition queue)
    - Next problems from user's current path
    - Skill builder recommendations based on weak areas
    - Streak and daily goal progress
    """
    try:
        now = datetime.utcnow()
        today = date.today().isoformat()

        # 1. Get streak info
        streak = 0
        streak_response = (
            supabase.table("user_streaks")
            .select("current_streak, last_activity_date")
            .eq("user_id", str(user_id))
            .execute()
        )
        if streak_response.data:
            streak_data = streak_response.data[0]
            last_date = streak_data.get("last_activity_date")
            if last_date:
                # Check if streak is still valid
                last_date_obj = datetime.fromisoformat(last_date.replace("Z", "+00:00")).date() if isinstance(last_date, str) else last_date
                days_diff = (date.today() - last_date_obj).days
                if days_diff <= 1:
                    streak = streak_data.get("current_streak", 0)

        # 2. Get daily goal from user settings
        daily_goal = 5
        settings_response = (
            supabase.table("user_settings")
            .select("daily_goal, current_path_id")
            .eq("user_id", str(user_id))
            .execute()
        )
        current_path_id = None
        if settings_response.data:
            daily_goal = settings_response.data[0].get("daily_goal", 5)
            current_path_id = settings_response.data[0].get("current_path_id")

        # 3. Count problems completed today
        completed_today = 0
        today_submissions = (
            supabase.table("submissions")
            .select("id", count="exact")
            .eq("user_id", str(user_id))
            .eq("status", "Accepted")
            .gte("submitted_at", f"{today}T00:00:00")
            .execute()
        )
        completed_today = today_submissions.count or 0

        # 4. Get reviews due
        reviews_due = []
        reviews_response = (
            supabase.table("review_queue")
            .select("problem_slug, problem_title, reason, priority")
            .eq("user_id", str(user_id))
            .lte("next_review", now.isoformat())
            .order("priority", desc=True)
            .limit(5)
            .execute()
        )
        if reviews_response.data:
            for r in reviews_response.data:
                reviews_due.append(
                    DailyFocusProblem(
                        slug=r["problem_slug"],
                        title=r.get("problem_title") or r["problem_slug"].replace("-", " ").title(),
                        difficulty=None,
                        category="Review",
                        reason=r.get("reason", "Due for review"),
                        priority=1,
                    )
                )

        # 5. Get next problems from current path
        path_problems = []
        if current_path_id:
            path_problems = await _get_next_path_problems(supabase, user_id, current_path_id)
        else:
            # Default to NeetCode 150
            path_problems = await _get_next_path_problems(
                supabase, user_id, "11111111-1111-1111-1111-111111111150"
            )

        # 6. Get skill builder recommendations
        skill_builders = await _get_skill_builders(supabase, user_id)

        # 7. Generate LLM insight (placeholder - can be enhanced later)
        llm_insight = await _generate_llm_insight(supabase, user_id, reviews_due, skill_builders)

        return TodaysFocus(
            user_id=user_id,
            streak=streak,
            daily_goal=daily_goal,
            completed_today=completed_today,
            reviews_due=reviews_due,
            path_problems=path_problems,
            skill_builders=skill_builders,
            llm_insight=llm_insight,
            generated_at=now,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get today's focus: {str(e)}")


async def _get_next_path_problems(
    supabase: Client,
    user_id: UUID,
    path_id: str,
    limit: int = 3,
) -> list[DailyFocusProblem]:
    """Get next uncompleted problems from user's current path."""
    try:
        # Get path data
        path_response = (
            supabase.table("learning_paths")
            .select("categories")
            .eq("id", path_id)
            .single()
            .execute()
        )
        if not path_response.data:
            return []

        categories = path_response.data.get("categories", [])

        # Get user's completed problems (from path progress and submissions)
        progress_response = (
            supabase.table("user_path_progress")
            .select("completed_problems")
            .eq("user_id", str(user_id))
            .eq("path_id", path_id)
            .execute()
        )
        completed = set()
        if progress_response.data:
            completed = set(progress_response.data[0].get("completed_problems", []) or [])

        # Also check accepted submissions
        submissions_response = (
            supabase.table("submissions")
            .select("problem_slug")
            .eq("user_id", str(user_id))
            .eq("status", "Accepted")
            .execute()
        )
        if submissions_response.data:
            for s in submissions_response.data:
                completed.add(s["problem_slug"])

        # Find next uncompleted problems
        result = []
        for cat in sorted(categories, key=lambda x: x.get("order", 0)):
            if len(result) >= limit:
                break
            for prob in sorted(cat.get("problems", []), key=lambda x: x.get("order", 0)):
                if prob["slug"] not in completed:
                    result.append(
                        DailyFocusProblem(
                            slug=prob["slug"],
                            title=prob["title"],
                            difficulty=prob.get("difficulty"),
                            category=cat["name"],
                            reason=f"Next in {cat['name']}",
                            priority=2,
                        )
                    )
                    if len(result) >= limit:
                        break

        return result
    except Exception:
        return []


async def _get_skill_builders(
    supabase: Client,
    user_id: UUID,
    limit: int = 3,
) -> list[DailyFocusProblem]:
    """Get skill builder recommendations based on weak areas."""
    try:
        # Get weakest skills
        skills_response = (
            supabase.table("skill_scores")
            .select("tag, score")
            .eq("user_id", str(user_id))
            .order("score")
            .limit(3)
            .execute()
        )

        if not skills_response.data:
            return []

        weak_skills = [s for s in skills_response.data if s["score"] < 60]
        if not weak_skills:
            return []

        result = []

        for skill in weak_skills:
            if len(result) >= limit:
                break

            # Find a failed problem with this tag that user should retry
            failed_response = (
                supabase.table("submissions")
                .select("problem_slug, problem_title, difficulty")
                .eq("user_id", str(user_id))
                .neq("status", "Accepted")
                .contains("tags", [skill["tag"]])
                .order("submitted_at", desc=True)
                .limit(1)
                .execute()
            )

            if failed_response.data:
                prob = failed_response.data[0]
                if not any(r.slug == prob["problem_slug"] for r in result):
                    result.append(
                        DailyFocusProblem(
                            slug=prob["problem_slug"],
                            title=prob.get("problem_title") or prob["problem_slug"].replace("-", " ").title(),
                            difficulty=prob.get("difficulty"),
                            category=skill["tag"],
                            reason=f"Strengthen {skill['tag']} (score: {skill['score']:.0f}%)",
                            priority=3,
                        )
                    )

        return result
    except Exception:
        return []


async def _generate_llm_insight(
    supabase: Client,
    user_id: UUID,
    reviews_due: list[DailyFocusProblem],
    skill_builders: list[DailyFocusProblem],
) -> str:
    """Generate a personalized insight message."""
    try:
        # Get recent failure patterns
        failures_response = (
            supabase.table("submissions")
            .select("tags, difficulty")
            .eq("user_id", str(user_id))
            .neq("status", "Accepted")
            .order("submitted_at", desc=True)
            .limit(10)
            .execute()
        )

        if not failures_response.data:
            return "Start your journey! Complete your first problem to get personalized insights."

        # Count tag frequencies in failures
        tag_counts = {}
        for sub in failures_response.data:
            for tag in (sub.get("tags") or []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if not tag_counts:
            return "Keep practicing! Your insights will become more personalized as you solve more problems."

        # Find most common failure pattern
        top_tag = max(tag_counts, key=tag_counts.get)
        count = tag_counts[top_tag]

        if count >= 3:
            return f"You've struggled with '{top_tag}' problems recently ({count} attempts). Focus on understanding the underlying pattern before moving on."

        if reviews_due:
            return f"You have {len(reviews_due)} review(s) due. Complete these first to reinforce your learning before tackling new problems."

        if skill_builders:
            weak_area = skill_builders[0].category
            return f"Your '{weak_area}' skills need work. Try easier problems in this category to build fundamentals."

        return "Great progress! Keep up the consistent practice to maintain your skills."
    except Exception:
        return "Keep practicing! Your personalized insights are being generated."
