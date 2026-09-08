# bot.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import MenuButtonWebApp, WebAppInfo

from config import MAIN_BOT_TOKEN, MINIAPP_URL
from handlers import menu, registration
from services.scheduler import init_scheduler, shutdown_scheduler  # <- needs bot

logging.basicConfig(level=logging.INFO)


async def configure_mini_app(bot: Bot) -> None:
    """Expose the Kiani Exchange Mini App through Telegram's persistent menu button."""
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Kiani Exchange",
                web_app=WebAppInfo(url=MINIAPP_URL),
            )
        )
        logging.info("🌐 Telegram Mini App menu button configured: %s", MINIAPP_URL)
    except Exception:
        # Do not prevent the bot from starting if Telegram temporarily rejects the menu update.
        logging.exception("Failed to configure Telegram Mini App menu button")


async def main():
    # Use DefaultBotProperties instead of parse_mode=... at init time
    bot = Bot(
        token=MAIN_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()

    # Routers
    dp.include_router(menu.router)
    dp.include_router(registration.router)

    await configure_mini_app(bot)

    # Start the scheduler WITH the bot instance
    await init_scheduler(bot)

    me = await bot.get_me()
    logging.info(f"🤖 Bot is starting as @{me.username} (id={me.id})")

    try:
        await dp.start_polling(bot)
    finally:
        # clean shutdown
        await shutdown_scheduler()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
