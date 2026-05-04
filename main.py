import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import MenuButtonCommands, MenuButtonWebApp, WebAppInfo

from config import BOT_TOKEN
from handlers import category, emotion, feedback, inline, result, saved, start, webapp
from services.db import init_db


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    await init_db()

    bot = Bot(BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(feedback.router)
    dp.include_router(saved.router)
    dp.include_router(inline.router)
    dp.include_router(webapp.router)
    dp.include_router(start.router)
    dp.include_router(category.router)
    dp.include_router(emotion.router)
    dp.include_router(result.router)

    webapp_url = os.getenv("WEBAPP_URL", "").strip()
    try:
        if webapp_url:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="✨ Открыть",
                    web_app=WebAppInfo(url=webapp_url),
                )
            )
            logging.info("Menu button set to WebApp: %s", webapp_url)
        else:
            await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
            logging.info("Menu button set to commands (no WEBAPP_URL)")
    except Exception:
        logging.exception("Failed to set chat menu button")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
