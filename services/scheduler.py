# services/scheduler.py
from __future__ import annotations

import inspect
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

log = logging.getLogger(__name__)

# Global scheduler + bot holder
scheduler = AsyncIOScheduler(timezone=timezone.utc)
_bot: Optional[Bot] = None

# Keep job ids per user so we can cancel them later
_user_jobs: Dict[int, List[str]] = {}


async def init_scheduler(bot: Bot) -> None:
    """
    Call once from bot.py after creating Bot().
    """
    global _bot
    _bot = bot
    if not scheduler.running:
        scheduler.start()
        log.info("apscheduler Scheduler started")


async def shutdown_scheduler() -> None:
    """
    Gracefully stop scheduler on app shutdown.
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("apscheduler Scheduler stopped")


async def _safe_fetch_user(user_id: int) -> Optional[dict]:
    """
    Tries to read user from your database. Works with both sync/async get_user.
    Returns None if unavailable or on any error.
    """
    try:
        from database import get_user  # avoid circular import at module import time
    except Exception as e:
        log.debug("scheduler: database.get_user not available: %r", e)
        return None

    try:
        if inspect.iscoroutinefunction(get_user):
            return await get_user(user_id)  # type: ignore[misc]
        # assume sync callable
        return get_user(user_id)  # type: ignore[misc]
    except Exception as e:
        log.debug("scheduler: get_user(%s) failed: %r", user_id, e)
        return None


async def _send_reminder(user_id: int, reminder_no: int) -> None:
    """
    Internal job: send a reminder if user still needs it.
    """
    if _bot is None:
        return

    # Optional: read DB to skip users who finished or who have non-+98 phone
    user = await _safe_fetch_user(user_id)

    # Skip if finished
    if user and (user.get("kyc_status") in {"Completed", "Approved"}):
        log.info("scheduler: user %s already completed KYC; canceling reminders", user_id)
        cancel_user_reminders(user_id)
        return

    # Skip if shared phone exists and is not +98 (cannot finish -> don't nag)
    if user and user.get("phone_number") and not str(user["phone_number"]).startswith("+98"):
        log.info("scheduler: user %s has non +98 phone; canceling reminders", user_id)
        cancel_user_reminders(user_id)
        return

    texts = {
        1: "⏰ یادآوری: شما ثبت‌نام را شروع کرده‌اید، لطفا ادامه دهید.",
        2: "📋 فقط چند مرحله باقی مانده! ثبت‌نام خود را تکمیل کنید.",
        3: "⚡ هنوز ثبت‌نام تکمیل نشده. همین حالا ادامه دهید.",
        4: "⚠️ آخرین یادآوری: بدون تکمیل ثبت‌نام حساب شما فعال نخواهد شد.",
    }

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ادامه ثبت‌نام", callback_data="jump:1")],
        [InlineKeyboardButton(text="🚫 عدم یادآوری", callback_data="cancel_reminders")],
    ])

    try:
        await _bot.send_message(chat_id=user_id, text=texts.get(reminder_no, texts[1]), reply_markup=kb)
        log.info("scheduler: sent reminder #%s to user %s", reminder_no, user_id)
    except Exception as e:
        # Ignore send errors (blocked bot, etc.)
        log.debug("scheduler: send_message to %s failed: %r", user_id, e)


def schedule_user_reminders(user_id: int) -> None:
    """
    Schedule 4 reminders at +1h, +24h, +48h, +7d from now.
    Replaces existing jobs for the user if present.
    """
    now = datetime.now(timezone.utc)
    delays = [3600, 86400, 172800, 604800]  # seconds
    job_ids: List[str] = []

    for idx, secs in enumerate(delays, start=1):
        run_at = now + timedelta(seconds=secs)
        trig = DateTrigger(run_date=run_at, timezone=timezone.utc)
        job_id = f"rem-{user_id}-{idx}"
        try:
            job = scheduler.add_job(
                _send_reminder,
                trigger=trig,
                args=[user_id, idx],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=300,  # 5 minutes
            )
            job_ids.append(job.id)
        except Exception as e:
            log.debug("scheduler: add_job failed for user %s idx %s: %r", user_id, idx, e)

    _user_jobs[user_id] = job_ids
    log.info("scheduler: scheduled reminders for user %s -> %s", user_id, job_ids)


def cancel_user_reminders(user_id: int) -> None:
    """
    Cancel all scheduled reminders for a user.
    """
    ids = _user_jobs.pop(user_id, [])
    for jid in ids:
        try:
            scheduler.remove_job(jid)
            log.info("apscheduler.scheduler Removed job %s", jid)
        except Exception:
            # already gone / never existed
            pass

