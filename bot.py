import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

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


async def on_shutdown(notifier: Notifier, bot: Bot, fsm_storage: BaseStorage) -> None:
    log.info("Завершение…")
    await notifier.stop()
    await fsm_storage.close()
    await bot.session.close()


def _build_fsm_storage() -> BaseStorage:
    if settings.redis_url:
        log.info("FSM storage: Redis (%s)", settings.redis_url)
        return RedisStorage.from_url(settings.redis_url)
    log.warning("FSM storage: MemoryStorage — состояния теряются при рестарте")
    return MemoryStorage()


async def main() -> None:
    if not settings.admin_users:
        log.warning("ADMIN_USERS пуст — никто не сможет управлять ботом")

    bot = Bot(
        settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )
    fsm_storage = _build_fsm_storage()
    dp = Dispatcher(storage=fsm_storage)

    storage = Storage(settings.data_folder)
    youtube = YouTubeClient(settings.youtube_api_key)
    notifier = Notifier(bot, storage, youtube, settings.check_interval)

    admin_mw = AdminOnlyMiddleware(settings.admin_users)
    dp.message.outer_middleware(admin_mw)
    dp.callback_query.outer_middleware(admin_mw)

    # common первым — там /cancel и навигация, которые должны побеждать state-фильтры
    dp.include_routers(common_router, info_router, channels_router, chats_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(
        bot,
        storage=storage,
        youtube=youtube,
        notifier=notifier,
        fsm_storage=fsm_storage,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Остановлено пользователем")
