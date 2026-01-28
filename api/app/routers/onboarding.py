"""Onboarding API endpoints - User onboarding flow management."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.models.schemas import OnboardingStatus, OnboardingStepUpdate

router = APIRouter()


@router.get("/onboarding/{user_id}", response_model=OnboardingStatus)
async def get_onboarding_status(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Get user's onboarding status.

    Returns the current state of onboarding including which steps
    have been completed and which is the current step.
    """
    try:
        response = (
            supabase.table("user_onboarding")
            .select("*")
            .eq("user_id", str(user_id))
            .execute()
        )

        if response.data:
            return OnboardingStatus(**response.data[0])

        # No onboarding record exists - create one
        new_record = {
            "user_id": str(user_id),
            "has_objective": False,
            "extension_installed": False,
            "history_imported": False,
            "first_path_selected": False,
            "onboarding_complete": False,
            "current_step": 1,
        }

        insert_response = (
            supabase.table("user_onboarding")
            .insert(new_record)
            .execute()
        )

        if insert_response.data:
            return OnboardingStatus(**insert_response.data[0])

        # Return default if insert fails
        return OnboardingStatus(user_id=user_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get onboarding status: {str(e)}")


@router.post("/onboarding/{user_id}/step", response_model=OnboardingStatus)
async def update_onboarding_step(
    user_id: UUID,
    update: OnboardingStepUpdate,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Update a specific onboarding step.

    Step names: "objective", "extension", "history", "path"
    """
    step_field_map = {
        "objective": "has_objective",
        "extension": "extension_installed",
        "history": "history_imported",
        "path": "first_path_selected",
    }

    if update.step not in step_field_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step: {update.step}. Must be one of: {list(step_field_map.keys())}"
        )

    field_name = step_field_map[update.step]

    try:
        # Build update data
        update_data = {
            field_name: update.completed,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Add step-specific metadata
        if update.step == "extension" and update.completed:
            update_data["extension_verified_at"] = datetime.utcnow().isoformat()
        elif update.step == "history" and update.completed:
            update_data["history_imported_at"] = datetime.utcnow().isoformat()
            if update.metadata and "problems_imported_count" in update.metadata:
                update_data["problems_imported_count"] = update.metadata["problems_imported_count"]

        # Upsert the record
        response = (
            supabase.table("user_onboarding")
            .upsert({
                "user_id": str(user_id),
                **update_data,
            })
            .execute()
        )

        if response.data:
            return OnboardingStatus(**response.data[0])

        raise HTTPException(status_code=500, detail="Failed to update onboarding step")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update onboarding step: {str(e)}")


@router.post("/onboarding/{user_id}/verify-extension", response_model=OnboardingStatus)
async def verify_extension_installed(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Verify that the Chrome extension is installed.

    This is called by the extension itself when it loads and detects
    it's connected to the user's account.
    """
    try:
        # Check if user has any submissions (extension would sync these)
        submissions_response = (
            supabase.table("submissions")
            .select("id")
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )

        has_submissions = bool(submissions_response.data)

        # Update onboarding status
        update_data = {
            "user_id": str(user_id),
            "extension_installed": True,
            "extension_verified_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # If there are submissions, also mark history as imported
        if has_submissions:
            # Count submissions for metadata
            count_response = (
                supabase.table("submissions")
                .select("id", count="exact")
                .eq("user_id", str(user_id))
                .execute()
            )
            problems_count = count_response.count or 0

            update_data["history_imported"] = True
            update_data["history_imported_at"] = datetime.utcnow().isoformat()
            update_data["problems_imported_count"] = problems_count

        response = (
            supabase.table("user_onboarding")
            .upsert(update_data)
            .execute()
        )

        if response.data:
            return OnboardingStatus(**response.data[0])

        raise HTTPException(status_code=500, detail="Failed to verify extension")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify extension: {str(e)}")


@router.post("/onboarding/{user_id}/import-history")
async def import_leetcode_history(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Trigger LeetCode history import.

    This initiates the import process which pulls the user's
    LeetCode submission history through the extension.

    Returns status of the import process.
    """
    try:
        # Check if extension is installed first
        onboarding_response = (
            supabase.table("user_onboarding")
            .select("extension_installed")
            .eq("user_id", str(user_id))
            .execute()
        )

        if not onboarding_response.data or not onboarding_response.data[0].get("extension_installed"):
            raise HTTPException(
                status_code=400,
                detail="Extension must be installed before importing history"
            )

        # Count current submissions
        count_response = (
            supabase.table("submissions")
            .select("id", count="exact")
            .eq("user_id", str(user_id))
            .execute()
        )
        current_count = count_response.count or 0

        # Mark history as imported with current count
        # The actual import happens through the extension
        update_response = (
            supabase.table("user_onboarding")
            .update({
                "history_imported": True,
                "history_imported_at": datetime.utcnow().isoformat(),
                "problems_imported_count": current_count,
                "updated_at": datetime.utcnow().isoformat(),
            })
            .eq("user_id", str(user_id))
            .execute()
        )

        return {
            "success": True,
            "problems_imported": current_count,
            "message": "History import completed" if current_count > 0 else "No existing submissions found. Practice on LeetCode and your submissions will sync automatically."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import history: {str(e)}")


@router.post("/onboarding/{user_id}/complete", response_model=OnboardingStatus)
async def complete_onboarding(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Mark onboarding as complete.

    This should only be called after all required steps are done.
    Will verify all steps are complete before marking done.
    """
    try:
        # Get current status
        response = (
            supabase.table("user_onboarding")
            .select("*")
            .eq("user_id", str(user_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Onboarding record not found")

        status = response.data[0]

        # Check all required steps (extension and history can be skipped)
        if not status.get("has_objective"):
            raise HTTPException(
                status_code=400,
                detail="Cannot complete onboarding: objective not set"
            )

        if not status.get("first_path_selected"):
            raise HTTPException(
                status_code=400,
                detail="Cannot complete onboarding: learning path not selected"
            )

        # Mark complete
        update_response = (
            supabase.table("user_onboarding")
            .update({
                "onboarding_complete": True,
                "updated_at": datetime.utcnow().isoformat(),
            })
            .eq("user_id", str(user_id))
            .execute()
        )

        if update_response.data:
            return OnboardingStatus(**update_response.data[0])

        raise HTTPException(status_code=500, detail="Failed to complete onboarding")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete onboarding: {str(e)}")


@router.post("/onboarding/{user_id}/skip-step", response_model=OnboardingStatus)
async def skip_onboarding_step(
    user_id: UUID,
    update: OnboardingStepUpdate,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Skip an onboarding step (for optional steps like extension/history).

    Only "extension" and "history" steps can be skipped.
    """
    skippable_steps = ["extension", "history"]

    if update.step not in skippable_steps:
        raise HTTPException(
            status_code=400,
            detail=f"Step '{update.step}' cannot be skipped. Only {skippable_steps} can be skipped."
        )

    step_field_map = {
        "extension": "extension_installed",
        "history": "history_imported",
    }

    field_name = step_field_map[update.step]

    try:
        # Mark as complete (skipped counts as complete for flow purposes)
        response = (
            supabase.table("user_onboarding")
            .upsert({
                "user_id": str(user_id),
                field_name: True,  # Mark as done even though skipped
                "updated_at": datetime.utcnow().isoformat(),
            })
            .execute()
        )

        if response.data:
            return OnboardingStatus(**response.data[0])

        raise HTTPException(status_code=500, detail="Failed to skip step")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to skip step: {str(e)}")


@router.delete("/onboarding/{user_id}/reset", response_model=OnboardingStatus)
async def reset_onboarding(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Reset onboarding to start over.

    This clears all onboarding progress but does NOT delete
    user data like objectives or submissions.
    """
    try:
        # Reset to initial state
        response = (
            supabase.table("user_onboarding")
            .upsert({
                "user_id": str(user_id),
                "has_objective": False,
                "extension_installed": False,
                "history_imported": False,
                "first_path_selected": False,
                "onboarding_complete": False,
                "current_step": 1,
                "extension_verified_at": None,
                "history_imported_at": None,
                "problems_imported_count": 0,
                "updated_at": datetime.utcnow().isoformat(),
            })
            .execute()
        )

        if response.data:
            return OnboardingStatus(**response.data[0])

        raise HTTPException(status_code=500, detail="Failed to reset onboarding")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset onboarding: {str(e)}")
