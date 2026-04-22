"""Mistake Journal CRUD router."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.models.schemas import (
    CreateMistakeJournalRequest,
    MistakeJournalEntry,
    MistakeJournalListResponse,
    UpdateMistakeJournalRequest,
)

router = APIRouter()


def _get_supabase():
    from supabase import create_client
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)


def _extract_tags(user_id: str, entry_text: str, supabase) -> list[str]:
    """Extract skill tags from entry text by matching against user's existing skill_scores."""
    try:
        skills_resp = (
            supabase.table("skill_scores")
            .select("tag")
            .eq("user_id", user_id)
            .execute()
        )
        if not skills_resp.data:
            return []

        all_tags = [s["tag"] for s in skills_resp.data]
        text_lower = entry_text.lower()
        return [tag for tag in all_tags if tag.lower() in text_lower]
    except Exception:
        return []


@router.get("/journal/{user_id}", response_model=MistakeJournalListResponse)
async def get_journal_entries(user_id: UUID, include_addressed: bool = False):
    """List journal entries for a user."""
    supabase = _get_supabase()
    user_id_str = str(user_id)

    query = supabase.table("mistake_journal").select("*").eq("user_id", user_id_str)
    if not include_addressed:
        query = query.eq("is_addressed", False)
    query = query.order("created_at", desc=True)

    resp = query.execute()
    entries = [MistakeJournalEntry(**row) for row in (resp.data or [])]

    # Get unaddressed count
    count_resp = (
        supabase.table("mistake_journal")
        .select("id", count="exact")
        .eq("user_id", user_id_str)
        .eq("is_addressed", False)
        .execute()
    )
    unaddressed_count = count_resp.count or 0

    return MistakeJournalListResponse(entries=entries, unaddressed_count=unaddressed_count)


@router.post("/journal/{user_id}", response_model=MistakeJournalEntry, status_code=201)
async def create_journal_entry(user_id: UUID, request: CreateMistakeJournalRequest):
    """Create a new journal entry with auto-extracted tags."""
    supabase = _get_supabase()
    user_id_str = str(user_id)

    tags = _extract_tags(user_id_str, request.entry_text, supabase)

    row = {
        "user_id": user_id_str,
        "entry_text": request.entry_text,
        "tags": tags,
        "entry_type": request.entry_type,
        "problem_slug": request.problem_slug,
        "problem_title": request.problem_title,
        "feed_item_id": str(request.feed_item_id) if request.feed_item_id else None,
    }

    resp = supabase.table("mistake_journal").insert(row).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to create journal entry")

    return MistakeJournalEntry(**resp.data[0])


@router.put("/journal/{user_id}/{entry_id}", response_model=MistakeJournalEntry)
async def update_journal_entry(user_id: UUID, entry_id: UUID, request: UpdateMistakeJournalRequest):
    """Update a journal entry's text or mark it as addressed."""
    supabase = _get_supabase()
    user_id_str = str(user_id)

    updates = {}
    if request.entry_text is not None:
        updates["entry_text"] = request.entry_text
        updates["tags"] = _extract_tags(user_id_str, request.entry_text, supabase)
    if request.is_addressed is not None:
        updates["is_addressed"] = request.is_addressed

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    resp = (
        supabase.table("mistake_journal")
        .update(updates)
        .eq("id", str(entry_id))
        .eq("user_id", user_id_str)
        .execute()
    )

    if not resp.data:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    return MistakeJournalEntry(**resp.data[0])


@router.delete("/journal/{user_id}/{entry_id}")
async def delete_journal_entry(user_id: UUID, entry_id: UUID):
    """Delete a journal entry."""
    supabase = _get_supabase()

    resp = (
        supabase.table("mistake_journal")
        .delete()
        .eq("id", str(entry_id))
        .eq("user_id", str(user_id))
        .execute()
    )

    if not resp.data:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    return {"success": True}
