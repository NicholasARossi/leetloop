"""Learning paths endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.models.schemas import (
    CompleteProblemRequest,
    LearningPath,
    LearningPathSummary,
    PathCategory,
    PathProblem,
    PathProgressResponse,
    SetCurrentPathRequest,
    UserPathProgress,
)

router = APIRouter()


def parse_path_categories(categories_json: list) -> list[PathCategory]:
    """Parse JSONB categories into PathCategory models."""
    result = []
    for cat in categories_json:
        problems = [
            PathProblem(
                slug=p["slug"],
                title=p["title"],
                difficulty=p["difficulty"],
                order=p["order"],
            )
            for p in cat.get("problems", [])
        ]
        result.append(
            PathCategory(
                name=cat["name"],
                order=cat["order"],
                problems=problems,
            )
        )
    return result


@router.get("/paths", response_model=list[LearningPathSummary])
async def list_paths(
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """List all available learning paths."""
    try:
        response = (
            supabase.table("learning_paths")
            .select("id, name, description, total_problems")
            .order("name")
            .execute()
        )
        return [LearningPathSummary(**p) for p in response.data] if response.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list paths: {str(e)}")


@router.get("/paths/{path_id}", response_model=LearningPath)
async def get_path(
    path_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get a specific learning path with all problems."""
    try:
        response = (
            supabase.table("learning_paths")
            .select("*")
            .eq("id", str(path_id))
            .single()
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Path not found")

        path_data = response.data
        categories = parse_path_categories(path_data.get("categories", []))

        return LearningPath(
            id=path_data["id"],
            name=path_data["name"],
            description=path_data.get("description"),
            total_problems=path_data["total_problems"],
            categories=categories,
            created_at=path_data.get("created_at"),
            updated_at=path_data.get("updated_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get path: {str(e)}")


@router.get("/paths/{path_id}/progress/{user_id}", response_model=PathProgressResponse)
async def get_path_progress(
    path_id: UUID,
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get user's progress on a specific learning path."""
    try:
        # Get the path
        path_response = (
            supabase.table("learning_paths")
            .select("*")
            .eq("id", str(path_id))
            .single()
            .execute()
        )
        if not path_response.data:
            raise HTTPException(status_code=404, detail="Path not found")

        path_data = path_response.data
        categories = parse_path_categories(path_data.get("categories", []))

        path = LearningPath(
            id=path_data["id"],
            name=path_data["name"],
            description=path_data.get("description"),
            total_problems=path_data["total_problems"],
            categories=categories,
            created_at=path_data.get("created_at"),
            updated_at=path_data.get("updated_at"),
        )

        # Get user progress
        progress_response = (
            supabase.table("user_path_progress")
            .select("*")
            .eq("path_id", str(path_id))
            .eq("user_id", str(user_id))
            .execute()
        )

        progress = None
        completed_problems = []
        if progress_response.data:
            progress_data = progress_response.data[0]
            completed_problems = progress_data.get("completed_problems", []) or []
            progress = UserPathProgress(
                id=progress_data["id"],
                user_id=progress_data["user_id"],
                path_id=progress_data["path_id"],
                completed_problems=completed_problems,
                current_category=progress_data.get("current_category"),
                started_at=progress_data["started_at"],
                last_activity_at=progress_data.get("last_activity_at"),
            )

        # Also check submissions for completed problems (auto-detect)
        submissions_response = (
            supabase.table("submissions")
            .select("problem_slug")
            .eq("user_id", str(user_id))
            .eq("status", "Accepted")
            .execute()
        )
        solved_slugs = set()
        if submissions_response.data:
            solved_slugs = {s["problem_slug"] for s in submissions_response.data}

        # Combine manually completed + auto-detected from submissions
        all_completed = set(completed_problems) | solved_slugs

        # Calculate progress per category
        categories_progress = {}
        for cat in categories:
            cat_slugs = [p.slug for p in cat.problems]
            cat_completed = [slug for slug in cat_slugs if slug in all_completed]
            categories_progress[cat.name] = {
                "total": len(cat.problems),
                "completed": len(cat_completed),
                "problems": [
                    {
                        "slug": p.slug,
                        "title": p.title,
                        "difficulty": p.difficulty.value if p.difficulty else None,
                        "completed": p.slug in all_completed,
                    }
                    for p in cat.problems
                ],
            }

        completed_count = len(all_completed & {p.slug for cat in categories for p in cat.problems})
        completion_percentage = (completed_count / path.total_problems * 100) if path.total_problems > 0 else 0

        return PathProgressResponse(
            path=path,
            progress=progress,
            completed_count=completed_count,
            completion_percentage=round(completion_percentage, 1),
            categories_progress=categories_progress,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get path progress: {str(e)}")


@router.post("/paths/{path_id}/complete/{user_id}")
async def complete_problem(
    path_id: UUID,
    user_id: UUID,
    request: CompleteProblemRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Mark a problem as completed in a path."""
    try:
        # Check if user has progress record
        progress_response = (
            supabase.table("user_path_progress")
            .select("*")
            .eq("path_id", str(path_id))
            .eq("user_id", str(user_id))
            .execute()
        )

        now = datetime.utcnow().isoformat()

        if not progress_response.data:
            # Create new progress record
            supabase.table("user_path_progress").insert({
                "user_id": str(user_id),
                "path_id": str(path_id),
                "completed_problems": [request.problem_slug],
                "started_at": now,
                "last_activity_at": now,
            }).execute()
        else:
            # Update existing record
            current = progress_response.data[0]
            completed = current.get("completed_problems", []) or []
            if request.problem_slug not in completed:
                completed.append(request.problem_slug)

            supabase.table("user_path_progress").update({
                "completed_problems": completed,
                "last_activity_at": now,
            }).eq("id", current["id"]).execute()

        # Update user streak
        try:
            supabase.rpc("update_user_streak", {"p_user_id": str(user_id)}).execute()
        except Exception:
            pass  # Streak update is optional

        return {"success": True, "problem_slug": request.problem_slug}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete problem: {str(e)}")


@router.put("/users/{user_id}/current-path")
async def set_current_path(
    user_id: UUID,
    request: SetCurrentPathRequest,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Set user's current learning path."""
    try:
        # Verify path exists
        path_response = (
            supabase.table("learning_paths")
            .select("id, name")
            .eq("id", str(request.path_id))
            .execute()
        )
        if not path_response.data:
            raise HTTPException(status_code=404, detail="Path not found")

        # Upsert user settings
        settings_response = (
            supabase.table("user_settings")
            .select("user_id")
            .eq("user_id", str(user_id))
            .execute()
        )

        if not settings_response.data:
            supabase.table("user_settings").insert({
                "user_id": str(user_id),
                "current_path_id": str(request.path_id),
            }).execute()
        else:
            supabase.table("user_settings").update({
                "current_path_id": str(request.path_id),
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("user_id", str(user_id)).execute()

        # Initialize path progress if not exists
        progress_response = (
            supabase.table("user_path_progress")
            .select("id")
            .eq("user_id", str(user_id))
            .eq("path_id", str(request.path_id))
            .execute()
        )

        if not progress_response.data:
            supabase.table("user_path_progress").insert({
                "user_id": str(user_id),
                "path_id": str(request.path_id),
                "completed_problems": [],
                "started_at": datetime.utcnow().isoformat(),
            }).execute()

        return {
            "success": True,
            "path_id": str(request.path_id),
            "path_name": path_response.data[0]["name"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set current path: {str(e)}")


@router.get("/users/{user_id}/current-path", response_model=PathProgressResponse)
async def get_current_path(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """Get user's current learning path with progress."""
    try:
        # Get user settings
        settings_response = (
            supabase.table("user_settings")
            .select("current_path_id")
            .eq("user_id", str(user_id))
            .execute()
        )

        if not settings_response.data or not settings_response.data[0].get("current_path_id"):
            # Default to NeetCode 150
            default_path_id = "11111111-1111-1111-1111-111111111150"
        else:
            default_path_id = settings_response.data[0]["current_path_id"]

        # Get path progress
        return await get_path_progress(UUID(default_path_id), user_id, supabase)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get current path: {str(e)}")
