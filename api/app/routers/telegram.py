"""Telegram bot webhook endpoint."""

import json

from fastapi import APIRouter, HTTPException, Request

from app.config import get_settings
from app.services.telegram_bot import get_bot_application

router = APIRouter()


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Receive Telegram updates via webhook."""
    settings = get_settings()
    bot_app = get_bot_application()

    if not bot_app:
        raise HTTPException(status_code=503, detail="Bot not configured")

    # Verify webhook secret if configured
    if settings.telegram_webhook_secret:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")

    body = await request.json()

    # Process the update
    from telegram import Update
    update = Update.de_json(body, bot_app.bot)

    # Initialize the application if not yet done
    if not bot_app.running:
        await bot_app.initialize()

    await bot_app.process_update(update)

    return {"ok": True}


@router.post("/telegram/setup-webhook")
async def setup_webhook(request: Request):
    """Set up the Telegram webhook. Call once after deployment."""
    settings = get_settings()
    bot_app = get_bot_application()

    if not bot_app:
        raise HTTPException(status_code=503, detail="Bot not configured")

    # Verify this is an authorized request (simple secret check)
    body = await request.json()
    webhook_url = body.get("webhook_url")
    if not webhook_url:
        raise HTTPException(status_code=400, detail="webhook_url required")

    if not bot_app.running:
        await bot_app.initialize()

    # Set webhook with Telegram
    result = await bot_app.bot.set_webhook(
        url=f"{webhook_url}/api/telegram/webhook",
        secret_token=settings.telegram_webhook_secret,
    )

    return {"ok": result, "webhook_url": f"{webhook_url}/api/telegram/webhook"}


@router.get("/telegram/webhook-info")
async def webhook_info():
    """Check current webhook status."""
    bot_app = get_bot_application()

    if not bot_app:
        raise HTTPException(status_code=503, detail="Bot not configured")

    if not bot_app.running:
        await bot_app.initialize()

    info = await bot_app.bot.get_webhook_info()

    return {
        "url": info.url,
        "has_custom_certificate": info.has_custom_certificate,
        "pending_update_count": info.pending_update_count,
        "last_error_date": info.last_error_date,
        "last_error_message": info.last_error_message,
    }


@router.post("/telegram/send-morning-checklist")
async def send_morning_checklist(request: Request):
    """Send the morning checklist to all linked users. Called by Cloud Scheduler."""
    settings = get_settings()
    bot_app = get_bot_application()

    if not bot_app:
        raise HTTPException(status_code=503, detail="Bot not configured")

    # Verify cron secret if configured
    if settings.cron_secret:
        body = await request.json() if await request.body() else {}
        if body.get("secret") != settings.cron_secret:
            auth_header = request.headers.get("Authorization", "")
            if f"Bearer {settings.cron_secret}" not in auth_header:
                raise HTTPException(status_code=403, detail="Unauthorized")

    if not bot_app.running:
        await bot_app.initialize()

    # Get all active linked users
    from app.db.supabase import get_supabase_client
    from app.services.telegram_bot import _get_or_generate_checklist, _build_checklist_message, _build_checklist_keyboard
    from datetime import date

    supabase = get_supabase_client()
    links_resp = (
        supabase.table("telegram_user_links")
        .select("telegram_chat_id, user_id")
        .eq("is_active", True)
        .execute()
    )

    today = date.today()
    sent_count = 0

    for link in (links_resp.data or []):
        try:
            items = _get_or_generate_checklist(link["user_id"], today)
            if not items:
                continue

            text = _build_checklist_message(items, today)
            keyboard = _build_checklist_keyboard(items)

            await bot_app.bot.send_message(
                chat_id=link["telegram_chat_id"],
                text=text,
                reply_markup=keyboard,
            )
            sent_count += 1
        except Exception as e:
            print(f"Failed to send to chat {link['telegram_chat_id']}: {e}")

    return {"ok": True, "sent_count": sent_count}
