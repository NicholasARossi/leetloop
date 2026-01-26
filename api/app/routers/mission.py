"""Mission Control API endpoints - Daily mission generation and tracking."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from supabase import Client

from app.config import get_settings
from app.db.supabase import get_supabase
from app.models.schemas import (
    MainQuest,
    SideQuest,
    DailyObjective,
    MissionResponse,
    MissionGenerateRequest,
    QuestStatus,
)
from app.services.mission_generator import MissionGenerator
from app.services.gemini_gateway import GeminiGateway

router = APIRouter()


@router.get("/mission/{user_id}", response_model=MissionResponse)
async def get_daily_mission(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Get today's daily mission for a user.

    If no mission exists for today, generates one on-demand.

    Returns:
        MissionResponse with objective, main quests, and side quests
    """
    try:
        gemini = GeminiGateway()
        generator = MissionGenerator(supabase, gemini)

        mission_data = await generator.generate_mission(user_id)

        return MissionResponse(
            user_id=UUID(mission_data["user_id"]),
            mission_date=mission_data["mission_date"],
            objective=DailyObjective(
                title=mission_data["objective"]["title"],
                description=mission_data["objective"]["description"],
                skill_tags=mission_data["objective"].get("skill_tags", []),
                target_count=mission_data["objective"].get("target_count", 5),
                completed_count=mission_data["objective"].get("completed_count", 0),
            ),
            main_quests=[
                MainQuest(
                    slug=q["slug"],
                    title=q["title"],
                    difficulty=q.get("difficulty"),
                    category=q.get("category", ""),
                    order=q.get("order", 0),
                    status=QuestStatus(q.get("status", "upcoming")),
                )
                for q in mission_data.get("main_quests", [])
            ],
            side_quests=[
                SideQuest(
                    slug=q["slug"],
                    title=q["title"],
                    difficulty=q.get("difficulty"),
                    reason=q.get("reason", ""),
                    source_problem_slug=q.get("source_problem_slug"),
                    target_weakness=q.get("target_weakness", ""),
                    quest_type=q.get("quest_type", "skill_gap"),
                    completed=q.get("completed", False),
                )
                for q in mission_data.get("side_quests", [])
            ],
            streak=mission_data.get("streak", 0),
            total_completed_today=mission_data.get("total_completed_today", 0),
            can_regenerate=mission_data.get("can_regenerate", True),
            generated_at=datetime.fromisoformat(mission_data["generated_at"].replace("Z", "+00:00"))
            if isinstance(mission_data["generated_at"], str)
            else mission_data["generated_at"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get mission: {str(e)}")


@router.post("/mission/{user_id}/regenerate", response_model=MissionResponse)
async def regenerate_mission(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Regenerate today's mission for a user.

    Limited to 3 regenerations per day.

    Returns:
        MissionResponse with new objective and quests
    """
    try:
        gemini = GeminiGateway()
        generator = MissionGenerator(supabase, gemini)

        mission_data = await generator.generate_mission(user_id, force_regenerate=True)

        if not mission_data.get("can_regenerate", True):
            # Return existing mission with can_regenerate=False to indicate limit reached
            pass

        return MissionResponse(
            user_id=UUID(mission_data["user_id"]),
            mission_date=mission_data["mission_date"],
            objective=DailyObjective(
                title=mission_data["objective"]["title"],
                description=mission_data["objective"]["description"],
                skill_tags=mission_data["objective"].get("skill_tags", []),
                target_count=mission_data["objective"].get("target_count", 5),
                completed_count=mission_data["objective"].get("completed_count", 0),
            ),
            main_quests=[
                MainQuest(
                    slug=q["slug"],
                    title=q["title"],
                    difficulty=q.get("difficulty"),
                    category=q.get("category", ""),
                    order=q.get("order", 0),
                    status=QuestStatus(q.get("status", "upcoming")),
                )
                for q in mission_data.get("main_quests", [])
            ],
            side_quests=[
                SideQuest(
                    slug=q["slug"],
                    title=q["title"],
                    difficulty=q.get("difficulty"),
                    reason=q.get("reason", ""),
                    source_problem_slug=q.get("source_problem_slug"),
                    target_weakness=q.get("target_weakness", ""),
                    quest_type=q.get("quest_type", "skill_gap"),
                    completed=q.get("completed", False),
                )
                for q in mission_data.get("side_quests", [])
            ],
            streak=mission_data.get("streak", 0),
            total_completed_today=mission_data.get("total_completed_today", 0),
            can_regenerate=mission_data.get("can_regenerate", True),
            generated_at=datetime.fromisoformat(mission_data["generated_at"].replace("Z", "+00:00"))
            if isinstance(mission_data["generated_at"], str)
            else mission_data["generated_at"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate mission: {str(e)}")


@router.post("/mission/generate-all")
async def generate_all_missions(
    supabase: Annotated[Client, Depends(get_supabase)] = None,
    x_cron_secret: Annotated[str | None, Header()] = None,
):
    """
    Generate missions for all active users.

    This endpoint is intended to be called by a cron job.
    Requires X-Cron-Secret header for authentication.

    Returns:
        Summary of generation results
    """
    settings = get_settings()

    # Validate cron secret if configured
    if settings.cron_secret:
        if not x_cron_secret or x_cron_secret != settings.cron_secret:
            raise HTTPException(status_code=401, detail="Invalid or missing cron secret")

    try:
        gemini = GeminiGateway()
        generator = MissionGenerator(supabase, gemini)

        results = await generator.generate_all_missions()

        return {
            "success": True,
            "generated": results["generated"],
            "skipped": results["skipped"],
            "failed": results["failed"],
            "total_users": results.get("total_users", 0),
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate missions: {str(e)}")
