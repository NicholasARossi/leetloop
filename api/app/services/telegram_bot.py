"""Telegram bot service for Life Ops daily checklist interaction."""

from datetime import date, datetime
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.config import get_settings
from app.db.supabase import get_supabase_client
from app.services.lifeops_service import generate_daily_items


def _get_user_id(chat_id: int) -> Optional[str]:
    """Look up LeetLoop user_id from Telegram chat_id."""
    supabase = get_supabase_client()

    # Check link table first
    resp = (
        supabase.table("telegram_user_links")
        .select("user_id")
        .eq("telegram_chat_id", chat_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if resp.data:
        return resp.data[0]["user_id"]

    # Fallback to env var for single-user setup
    settings = get_settings()
    return settings.telegram_owner_user_id


def _get_or_generate_checklist(user_id: str, target_date: date) -> list[dict]:
    """Get or generate today's checklist items. Returns raw dicts."""
    supabase = get_supabase_client()

    # Check existing
    existing = (
        supabase.table("lifeops_daily_items")
        .select("*")
        .eq("user_id", user_id)
        .eq("checklist_date", target_date.isoformat())
        .order("sort_order")
        .execute()
    )

    if existing.data:
        return existing.data

    # Generate from task definitions
    tasks_resp = (
        supabase.table("lifeops_tasks")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .execute()
    )
    tasks = tasks_resp.data or []

    cats_resp = (
        supabase.table("lifeops_categories")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    categories = {c["id"]: c for c in (cats_resp.data or [])}

    new_items = generate_daily_items(tasks, categories, user_id, target_date)
    if not new_items:
        return []

    inserted = supabase.table("lifeops_daily_items").insert(new_items).execute()
    return inserted.data or []


def _build_checklist_message(items: list[dict], target_date: date) -> str:
    """Build the checklist text message."""
    if not items:
        return "No tasks for today. Set up tasks in the web dashboard at /life-ops/manage"

    completed = sum(1 for i in items if i.get("is_completed"))
    total = len(items)
    all_done = completed == total

    # Group by category
    groups: dict[str, list[dict]] = {}
    for item in items:
        key = item.get("category_name") or "Uncategorized"
        groups.setdefault(key, []).append(item)

    date_str = target_date.strftime("%A, %B %d")
    header = f"{'All done!' if all_done else 'Checklist'} — {date_str}\n"
    header += f"{completed}/{total} completed"
    if all_done:
        header += " ✓"
    header += "\n"

    # Progress bar
    bar_len = 10
    filled = round(bar_len * completed / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    header += f"[{bar}]\n"

    lines = [header]

    for cat_name, cat_items in groups.items():
        cat_done = sum(1 for i in cat_items if i.get("is_completed"))
        lines.append(f"\n{cat_name} ({cat_done}/{len(cat_items)})")
        for item in cat_items:
            check = "✅" if item.get("is_completed") else "⬜"
            lines.append(f"  {check} {item['task_title']}")

    return "\n".join(lines)


def _build_checklist_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    """Build inline keyboard with toggle buttons for each incomplete item."""
    buttons = []
    for item in items:
        if item.get("is_completed"):
            # Show completed items as undo buttons
            buttons.append([
                InlineKeyboardButton(
                    f"✅ {item['task_title']}",
                    callback_data=f"toggle:{item['id']}",
                )
            ])
        else:
            buttons.append([
                InlineKeyboardButton(
                    f"⬜ {item['task_title']}",
                    callback_data=f"toggle:{item['id']}",
                )
            ])

    # Add refresh button
    buttons.append([
        InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
    ])

    return InlineKeyboardMarkup(buttons)


def _toggle_item(item_id: str) -> dict:
    """Toggle a checklist item. Returns updated item."""
    supabase = get_supabase_client()

    current = (
        supabase.table("lifeops_daily_items")
        .select("id, is_completed")
        .eq("id", item_id)
        .limit(1)
        .execute()
    )

    if not current.data:
        return {}

    new_completed = not current.data[0]["is_completed"]
    now = datetime.utcnow().isoformat() if new_completed else None

    updated = (
        supabase.table("lifeops_daily_items")
        .update({"is_completed": new_completed, "completed_at": now})
        .eq("id", item_id)
        .execute()
    )

    return updated.data[0] if updated.data else {}


def _get_streak_text(user_id: str) -> str:
    """Get streak summary text."""
    supabase = get_supabase_client()

    streak_resp = (
        supabase.table("lifeops_streaks")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not streak_resp.data:
        return "No streak data yet. Complete a full day to start!"

    s = streak_resp.data[0]
    lines = [
        "📊 Stats",
        f"  Current streak: {s.get('current_streak', 0)} days",
        f"  Longest streak: {s.get('longest_streak', 0)} days",
        f"  Perfect days: {s.get('total_perfect_days', 0)}",
    ]
    if s.get("last_completed_date"):
        lines.append(f"  Last perfect day: {s['last_completed_date']}")

    return "\n".join(lines)


# ============ Command Handlers ============


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — link account or show welcome."""
    chat_id = update.effective_chat.id
    settings = get_settings()

    # Auto-link using owner user ID if configured
    if settings.telegram_owner_user_id:
        supabase = get_supabase_client()
        # Upsert link
        supabase.table("telegram_user_links").upsert(
            {
                "telegram_chat_id": chat_id,
                "user_id": settings.telegram_owner_user_id,
                "telegram_username": update.effective_user.username if update.effective_user else None,
                "is_active": True,
            },
            on_conflict="telegram_chat_id",
        ).execute()

        await update.message.reply_text(
            "Linked! You're all set.\n\n"
            "Commands:\n"
            "  /today — Today's checklist\n"
            "  /stats — Streak & completion stats\n"
            "  /help — Show this message"
        )
    else:
        await update.message.reply_text(
            "Welcome to LeetLoop Life Ops!\n\n"
            "Set TELEGRAM_OWNER_USER_ID in your env to link your account."
        )


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /today — show today's checklist with inline buttons."""
    chat_id = update.effective_chat.id
    user_id = _get_user_id(chat_id)

    if not user_id:
        await update.message.reply_text("Account not linked. Run /start first.")
        return

    today = date.today()
    items = _get_or_generate_checklist(user_id, today)
    text = _build_checklist_message(items, today)
    keyboard = _build_checklist_keyboard(items) if items else None

    await update.message.reply_text(text, reply_markup=keyboard)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats — show streak and completion summary."""
    chat_id = update.effective_chat.id
    user_id = _get_user_id(chat_id)

    if not user_id:
        await update.message.reply_text("Account not linked. Run /start first.")
        return

    text = _get_streak_text(user_id)
    await update.message.reply_text(text)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help."""
    await update.message.reply_text(
        "LeetLoop Life Ops Bot\n\n"
        "Commands:\n"
        "  /today — Today's checklist\n"
        "  /stats — Streak & completion stats\n"
        "  /help — Show this message"
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button taps (toggle items, refresh)."""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    user_id = _get_user_id(chat_id)

    if not user_id:
        await query.edit_message_text("Account not linked. Run /start first.")
        return

    data = query.data

    if data == "refresh":
        # Just refresh the message
        pass
    elif data.startswith("toggle:"):
        item_id = data.split(":", 1)[1]
        _toggle_item(item_id)

    # Refresh the checklist display
    today = date.today()
    items = _get_or_generate_checklist(user_id, today)
    text = _build_checklist_message(items, today)
    keyboard = _build_checklist_keyboard(items) if items else None

    try:
        await query.edit_message_text(text, reply_markup=keyboard)
    except Exception:
        # Message unchanged (e.g., double-tap) — ignore
        pass


# ============ Bot Setup ============


def create_bot_application() -> Optional[Application]:
    """Create and configure the Telegram bot application."""
    settings = get_settings()

    if not settings.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN not set — bot disabled")
        return None

    app = Application.builder().token(settings.telegram_bot_token).build()

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CallbackQueryHandler(handle_callback))

    return app


# Singleton
_bot_app: Optional[Application] = None


def get_bot_application() -> Optional[Application]:
    """Get or create the bot application singleton."""
    global _bot_app
    if _bot_app is None:
        _bot_app = create_bot_application()
    return _bot_app
