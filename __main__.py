import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import settings
from bot.database.db import init_db
from bot.handlers import user, admin
from bot.middlewares.db import DbSessionMiddleware
from bot.scheduler import check_expired_subscriptions


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    session_maker = await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware(session_maker))

    dp.include_router(admin.router)
    dp.include_router(user.router)

    # === ПЛАНИРОВЩИК ===
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        check_expired_subscriptions,
        trigger="interval",
        minutes=60,
        args=[bot, session_maker],
        id="check_subscriptions",
        replace_existing=True,
    )
    scheduler.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
