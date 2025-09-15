# -*- coding: utf-8 -*-
# services/idle_guard.py
import asyncio
import logging
from typing import Dict, Tuple, Optional

from aiogram import Bot
from keyboards import main_menu_kb

logger = logging.getLogger(__name__)

_IDLE_SECONDS = 300  # 5 minutes
_tasks: Dict[int, asyncio.Task] = {}  # user_id -> task


def rearm(user_id: int, chat_id: int, bot: Bot, timeout: int = _IDLE_SECONDS) -> None:
    """Start/refresh user's idle timer."""
    # cancel previous
    t = _tasks.pop(user_id, None)
    if t and not t.done():
        t.cancel()

    async def _job():
        try:
            await asyncio.sleep(timeout)
            await bot.send_message(
                chat_id,
                "⏰ به منوی اصلی برگشتیم.",
                reply_markup=main_menu_kb(),
            )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning("idle job failed for %s: %s", user_id, e)

    _tasks[user_id] = asyncio.create_task(_job())


# Aiogram v3 middleware to automatically rearm on any user activity
from aiogram.dispatcher.middlewares.base import BaseMiddleware


class ActivityMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        bot: Bot = data["bot"]
        user = getattr(event, "from_user", None)
        chat = getattr(event, "chat", None)

        user_id = getattr(user, "id", None)
        chat_id: Optional[int] = getattr(chat, "id", None)

        # CallbackQuery has no event.chat; use message.chat
        if chat_id is None and hasattr(event, "message") and event.message:
            chat_id = getattr(event.message.chat, "id", None)

        if user_id and chat_id:
            rearm(user_id, chat_id, bot)

        return await handler(event, data)

