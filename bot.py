"""Точка входа: настройка Bot/Dispatcher, регистрация роутеров, запуск мониторинга."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from handlers import channels_router, chats_router, common_router, info_router
from middlewares import AdminOnlyMiddleware
from services.notifier import Notifier
from services.storage import Storage
from services.youtube import YouTubeClient

logging.basicConfig(
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
logging.getLogger("aiogram.event").setLevel(logging.WARNING)
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
log = logging.getLogger("ytbot")


async def on_startup(notifier: Notifier) -> None:
    notifier.start()
    log.info("Бот запущен. Админов: %d", len(settings.admin_users))


async def on_shutdown(notifier: Notifier, bot: Bot) -> None:
    log.info("Завершение…")
    await notifier.stop()
    await bot.session.close()


async def main() -> None:
    if not settings.admin_users:
        log.warning("ADMIN_USERS пуст — никто не сможет управлять ботом.")

    bot = Bot(
        settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )
    dp = Dispatcher(storage=MemoryStorage())

    storage = Storage(settings.data_folder)
    youtube = YouTubeClient(settings.youtube_api_key)
    notifier = Notifier(bot, storage, youtube, settings.check_interval)

    # Доступ — outer-middleware, чтобы отсекать до фильтров.
    admin_mw = AdminOnlyMiddleware(settings.admin_users)
    dp.message.outer_middleware(admin_mw)
    dp.callback_query.outer_middleware(admin_mw)

    # Routers (common раньше остальных — он перехватывает /cancel и навигацию).
    dp.include_routers(common_router, info_router, channels_router, chats_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(
        bot,
        storage=storage,
        youtube=youtube,
        notifier=notifier,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Остановлено пользователем")
