from contextlib import suppress
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import CB_HELP, CB_MAIN, CB_STATUS, back_to
from services.notifier import Notifier
from services.storage import Storage

router = Router(name="info")

TXT_HELP = (
    "ℹ️ <b>Справка</b>\n\n"
    "Бот отслеживает указанные YouTube-каналы и шлёт уведомления о новых видео "
    "в подключённые Telegram-чаты.\n\n"
    "<b>Быстрый старт:</b>\n"
    "1. 📺 <b>YouTube каналы</b> → ➕ Добавить → пришлите ID, URL или @handle.\n"
    "2. Добавьте бота админом в нужный чат/канал и нажмите там "
    "🔔 <b>Чаты уведомлений</b> → ➕ Подписать этот чат.\n\n"
    "<b>Команды:</b>\n"
    "• /menu — открыть админку\n"
    "• /cancel — выйти из текущего диалога\n"
    "• /status — краткая сводка\n\n"
    "В любом меню есть кнопка «← Назад» или «🏠 Главное меню»."
)


def _status_text(notifier: Notifier, storage: Storage) -> str:
    uptime = datetime.now(timezone.utc) - notifier.started_at
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    return (
        "📊 <b>Статус бота</b>\n\n"
        f"• Мониторинг: {'🟢 активен' if notifier.running else '🔴 остановлен'}\n"
        f"• Аптайм: <code>{h:02d}:{m:02d}:{s:02d}</code>\n"
        f"• Интервал проверки: <code>{notifier.check_interval}s</code>\n"
        f"• Каналов под мониторингом: <b>{len(storage.get_channels())}</b>\n"
        f"• Подписанных чатов: <b>{len(storage.get_chats())}</b>\n"
        f"• Уведомлений за сессию: <b>{notifier.notifications_sent}</b>"
    )


async def _render(update: Message | CallbackQuery, text: str, kb) -> None:
    if isinstance(update, CallbackQuery):
        with suppress(TelegramBadRequest):
            await update.message.edit_text(text, reply_markup=kb)
        await update.answer()
    else:
        await update.answer(text, reply_markup=kb)


@router.callback_query(F.data == CB_HELP, StateFilter("*"))
async def cb_help(cq: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _render(cq, TXT_HELP, back_to(CB_MAIN))


@router.callback_query(F.data == CB_STATUS, StateFilter("*"))
async def cb_status(cq: CallbackQuery, state: FSMContext,
                    notifier: Notifier, storage: Storage) -> None:
    await state.clear()
    await _render(cq, _status_text(notifier, storage), back_to(CB_MAIN))


@router.message(Command("status"), StateFilter("*"))
async def cmd_status(message: Message, state: FSMContext,
                     notifier: Notifier, storage: Storage) -> None:
    await state.clear()
    await message.answer(_status_text(notifier, storage), reply_markup=back_to(CB_MAIN))
