"""Meta objectives endpoints for career goal tracking."""

from datetime import date, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.utils import parse_iso_datetime
from app.models.schemas import (
    CreateObjectiveRequest,
    MetaObjective,
    MetaObjectiveResponse,
    ObjectiveProgress,
    ObjectiveTemplate,
    ObjectiveTemplateSummary,
    PaceStatus,
    SkillGap,
    UpdateObjectiveRequest,
)

router = APIRouter()


def calculate_pace_status(
    objective: dict,
    cumulative_problems: int,
    problems_this_week: int,
) -> PaceStatus:
    """Calculate the current pace status for an objective."""
    today = date.today()
    started_at = objective["started_at"]
    if isinstance(started_at, str):
        started_at = parse_iso_datetime(started_at).date()
    elif isinstance(started_at, datetime):
        started_at = started_at.date()

    target_deadline = objective["target_deadline"]
    if isinstance(target_deadline, str):
        target_deadline = date.fromisoformat(target_deadline)

    weekly_target = objective.get("weekly_problem_target", 25)

    days_elapsed = max(1, (today - started_at).days)
    days_total = max(1, (target_deadline - started_at).days)
    days_remaining = max(0, (target_deadline - today).days)

    # Calculate expected progress
    weeks_total = days_total / 7.0
    total_problems_target = int(weekly_target * weeks_total)
    expected_problems = int((days_elapsed / days_total) * total_problems_target)

    # Calculate pace percentage
    pace_percentage = (cumulative_problems / max(1, expected_problems)) * 100

    # Determine status
    if pace_percentage >= 110:
        status = "ahead"
    elif pace_percentage >= 90:
        status = "on_track"
    elif pace_percentage >= 70:
        status = "behind"
    else:
        status = "critical"

    # Calculate problems behind
    problems_behind = max(0, expected_problems - cumulative_problems)

    # Calculate daily rate needed to catch up
    problems_remaining = total_problems_target - cumulative_problems
    daily_rate_needed = problems_remaining / max(1, days_remaining) if days_remaining > 0 else 0

    # Project completion date based on current rate
    if cumulative_problems > 0 and days_elapsed > 0:
        daily_rate = cumulative_problems / days_elapsed
        if daily_rate > 0:
            days_to_completion = int(total_problems_target / daily_rate)
            projected_completion = started_at + timedelta(days=days_to_completion)
        else:
            projected_completion = None
    else:
        projected_completion = None

    return PaceStatus(
        status=status,
        problems_this_week=problems_this_week,
        weekly_target=weekly_target,
        problems_behind=problems_behind,
        pace_percentage=round(pace_percentage, 1),
        projected_completion_date=projected_completion,
        daily_rate_needed=round(daily_rate_needed, 1),
    )


def calculate_skill_gaps(
    required_skills: dict[str, float],
    current_scores: dict[str, float],
) -> list[SkillGap]:
    """Calculate skill gaps between required and current scores."""
    gaps = []
    for domain, target_score in required_skills.items():
        current_score = current_scores.get(domain, 0.0)
        gap = max(0, target_score - current_score)
        gaps.append(
            SkillGap(
                domain=domain,
                current_score=round(current_score, 1),
                target_score=target_score,
                gap=round(gap, 1),
                priority=0,  # Will be set after sorting
            )
        )

    # Sort by gap (largest first) and assign priorities
    gaps.sort(key=lambda x: x.gap, reverse=True)
    for i, gap in enumerate(gaps):
        gap.priority = i + 1

    return gaps


@router.get("/objectives/templates", response_model=list[ObjectiveTemplateSummary])
async def list_templates(
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """List all available objective templates."""
    try:
        response = (
            supabase.table("objective_templates")
            .select("id, name, company, role, level, description, estimated_weeks")
            .order("company")
            .execute()
        )
        return [ObjectiveTemplateSummary(**t) for t in response.data] if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")


@router.get("/objectives/templates/{template_id}", response_model=ObjectiveTemplate)
async def get_template(
    template_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get a specific objective template with full details."""
    try:
        response = (
            supabase.table("objective_templates")
            .select("*")
            .eq("id", str(template_id))
            .single()
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Template not found")

        return ObjectiveTemplate(**response.data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get template: {str(e)}")


@router.post("/objectives/{user_id}", response_model=MetaObjective)
async def create_objective(
    user_id: UUID,
    request: CreateObjectiveRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Create a new objective for a user."""
    try:
        # Check if user already has an active objective
        existing = (
            supabase.table("meta_objectives")
            .select("id")
            .eq("user_id", str(user_id))
            .eq("status", "active")
            .execute()
        )

        if existing.data:
            # Deactivate existing objective
            supabase.table("meta_objectives").update({
                "status": "paused",
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", existing.data[0]["id"]).execute()

        # If template_id provided, merge template data
        required_skills = request.required_skills
        path_ids = request.path_ids

        if request.template_id:
            template_response = (
                supabase.table("objective_templates")
                .select("*")
                .eq("id", str(request.template_id))
                .single()
                .execute()
            )
            if template_response.data:
                template = template_response.data
                # Use template skills if not provided
                if not required_skills:
                    required_skills = template.get("required_skills", {})
                if not path_ids:
                    path_ids = template.get("recommended_path_ids", [])

        # Create new objective
        objective_data = {
            "user_id": str(user_id),
            "title": request.title,
            "target_company": request.target_company,
            "target_role": request.target_role,
            "target_level": request.target_level,
            "target_deadline": request.target_deadline.isoformat(),
            "weekly_problem_target": request.weekly_problem_target,
            "daily_problem_minimum": request.daily_problem_minimum,
            "required_skills": required_skills,
            "path_ids": [str(p) for p in path_ids],
            "template_id": str(request.template_id) if request.template_id else None,
            "status": "active",
            "started_at": datetime.utcnow().isoformat(),
        }

        response = (
            supabase.table("meta_objectives")
            .insert(objective_data)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create objective")

        return MetaObjective(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create objective: {str(e)}")


@router.get("/objectives/{user_id}", response_model=MetaObjectiveResponse)
async def get_objective(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get user's active objective with pace status and skill gaps."""
    try:
        # Get active objective (don't use .single() as it throws on empty result)
        objective_response = (
            supabase.table("meta_objectives")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("status", "active")
            .limit(1)
            .execute()
        )

        if not objective_response.data:
            raise HTTPException(status_code=404, detail="No active objective found")

        objective_data = objective_response.data[0]
        objective = MetaObjective(**objective_data)

        # Get cumulative problems solved since objective started
        started_at = objective_data["started_at"]
        submissions_response = (
            supabase.table("submissions")
            .select("problem_slug")
            .eq("user_id", str(user_id))
            .eq("status", "Accepted")
            .gte("submitted_at", started_at)
            .execute()
        )

        solved_slugs = set()
        if submissions_response.data:
            solved_slugs = {s["problem_slug"] for s in submissions_response.data}

        cumulative_problems = len(solved_slugs)

        # Get problems solved this week
        week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        week_submissions_response = (
            supabase.table("submissions")
            .select("problem_slug")
            .eq("user_id", str(user_id))
            .eq("status", "Accepted")
            .gte("submitted_at", week_start)
            .execute()
        )

        week_slugs = set()
        if week_submissions_response.data:
            week_slugs = {s["problem_slug"] for s in week_submissions_response.data}

        problems_this_week = len(week_slugs)

        # Calculate pace status
        pace_status = calculate_pace_status(
            objective_data,
            cumulative_problems,
            problems_this_week,
        )

        # Get current skill scores
        skills_response = (
            supabase.table("skill_scores")
            .select("tag, score")
            .eq("user_id", str(user_id))
            .execute()
        )

        current_scores = {}
        if skills_response.data:
            current_scores = {s["tag"]: s["score"] for s in skills_response.data}

        # Calculate skill gaps
        required_skills = objective_data.get("required_skills", {})
        skill_gaps = calculate_skill_gaps(required_skills, current_scores)

        # Calculate readiness percentage (average of skill scores / targets)
        readiness_scores = []
        for domain, target in required_skills.items():
            current = current_scores.get(domain, 0)
            readiness_scores.append(min(100, (current / target) * 100) if target > 0 else 100)

        readiness_percentage = sum(readiness_scores) / len(readiness_scores) if readiness_scores else 0

        # Calculate days and targets
        today = date.today()
        target_deadline = objective.target_deadline
        started_at_date = objective.started_at.date() if isinstance(objective.started_at, datetime) else objective.started_at
        days_remaining = max(0, (target_deadline - today).days)
        total_days = max(1, (target_deadline - started_at_date).days)
        weeks_total = total_days / 7.0
        total_problems_target = int(objective.weekly_problem_target * weeks_total)

        return MetaObjectiveResponse(
            objective=objective,
            pace_status=pace_status,
            skill_gaps=skill_gaps,
            days_remaining=days_remaining,
            total_days=total_days,
            problems_solved=cumulative_problems,
            total_problems_target=total_problems_target,
            readiness_percentage=round(readiness_percentage, 1),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get objective: {str(e)}")


@router.put("/objectives/{user_id}", response_model=MetaObjective)
async def update_objective(
    user_id: UUID,
    request: UpdateObjectiveRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Update user's active objective."""
    try:
        # Get current objective
        current = (
            supabase.table("meta_objectives")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("status", "active")
            .single()
            .execute()
        )

        if not current.data:
            raise HTTPException(status_code=404, detail="No active objective found")

        # Build update data
        update_data = {"updated_at": datetime.utcnow().isoformat()}

        if request.title is not None:
            update_data["title"] = request.title
        if request.target_deadline is not None:
            update_data["target_deadline"] = request.target_deadline.isoformat()
        if request.weekly_problem_target is not None:
            update_data["weekly_problem_target"] = request.weekly_problem_target
        if request.daily_problem_minimum is not None:
            update_data["daily_problem_minimum"] = request.daily_problem_minimum
        if request.required_skills is not None:
            update_data["required_skills"] = request.required_skills
        if request.path_ids is not None:
            update_data["path_ids"] = [str(p) for p in request.path_ids]
        if request.status is not None:
            update_data["status"] = request.status

        response = (
            supabase.table("meta_objectives")
            .update(update_data)
            .eq("id", current.data["id"])
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update objective")

        return MetaObjective(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update objective: {str(e)}")


@router.get("/objectives/{user_id}/progress", response_model=list[ObjectiveProgress])
async def get_progress_history(
    user_id: UUID,
    days: int = 30,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get progress history for user's active objective."""
    try:
        # Get active objective
        objective = (
            supabase.table("meta_objectives")
            .select("id")
            .eq("user_id", str(user_id))
            .eq("status", "active")
            .single()
            .execute()
        )

        if not objective.data:
            raise HTTPException(status_code=404, detail="No active objective found")

        # Get progress records
        since_date = (date.today() - timedelta(days=days)).isoformat()
        progress_response = (
            supabase.table("objective_progress")
            .select("*")
            .eq("objective_id", objective.data["id"])
            .gte("progress_date", since_date)
            .order("progress_date", desc=True)
            .execute()
        )

        return [ObjectiveProgress(**p) for p in progress_response.data] if progress_response.data else []
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@router.get("/objectives/{user_id}/pace", response_model=PaceStatus)
async def get_pace_status(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get real-time pace calculation for user's active objective."""
    try:
        # Get active objective
        objective_response = (
            supabase.table("meta_objectives")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("status", "active")
            .single()
            .execute()
        )

        if not objective_response.data:
            raise HTTPException(status_code=404, detail="No active objective found")

        objective_data = objective_response.data

        # Get cumulative problems solved
        started_at = objective_data["started_at"]
        submissions_response = (
            supabase.table("submissions")
            .select("problem_slug")
            .eq("user_id", str(user_id))
            .eq("status", "Accepted")
            .gte("submitted_at", started_at)
            .execute()
        )

        solved_slugs = set()
        if submissions_response.data:
            solved_slugs = {s["problem_slug"] for s in submissions_response.data}

        cumulative_problems = len(solved_slugs)

        # Get problems this week
        week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        week_response = (
            supabase.table("submissions")
            .select("problem_slug")
            .eq("user_id", str(user_id))
            .eq("status", "Accepted")
            .gte("submitted_at", week_start)
            .execute()
        )

        week_slugs = set()
        if week_response.data:
            week_slugs = {s["problem_slug"] for s in week_response.data}

        problems_this_week = len(week_slugs)

        return calculate_pace_status(
            objective_data,
            cumulative_problems,
            problems_this_week,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pace: {str(e)}")


@router.delete("/objectives/{user_id}")
async def delete_objective(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Delete user's active objective."""
    try:
        response = (
            supabase.table("meta_objectives")
            .delete()
            .eq("user_id", str(user_id))
            .eq("status", "active")
            .execute()
        )

        return {"success": True, "deleted": len(response.data) if response.data else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete objective: {str(e)}")
