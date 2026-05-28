import logging
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards import (
    CB_CHATS,
    CB_CHAT_ADD_HERE,
    CB_CHAT_DEL,
    CB_CHAT_DEL_HERE,
    CB_CHAT_PAGE,
    PAGE_SIZE,
    back_to,
    chats_menu,
    paginated_list,
)
from services.storage import Storage

log = logging.getLogger("ytbot.chats")
router = Router(name="chats")


def _parse_page(data: str, prefix: str) -> int:
    if data.startswith(prefix):
        try:
            return int(data[len(prefix):])
        except ValueError:
            pass
    return 0


async def _edit(cq: CallbackQuery, text: str, kb) -> None:
    with suppress(TelegramBadRequest):
        await cq.message.edit_text(text, reply_markup=kb)
    await cq.answer()


@router.callback_query(F.data == CB_CHATS, StateFilter("*"))
async def cb_chats(cq: CallbackQuery, state: FSMContext, storage: Storage) -> None:
    await state.clear()
    text = (
        "🏠 / 🔔 <b>Чаты уведомлений</b>\n\n"
        f"Подписано чатов: <b>{len(storage.get_chats())}</b>\n\n"
        "Кнопки «Подписать/отписать этот чат» работают в группе/канале, "
        "где запущен бот."
    )
    await _edit(cq, text, chats_menu())


@router.callback_query(F.data == CB_CHAT_ADD_HERE, StateFilter("*"))
async def cb_chat_add_here(cq: CallbackQuery, state: FSMContext, storage: Storage) -> None:
    await state.clear()
    chat = cq.message.chat
    try:
        info = await cq.bot.get_chat(chat.id)
        title = info.title or info.full_name or str(chat.id)
    except Exception:
        title = chat.title or str(chat.id)
    if storage.add_chat(chat.id, title, chat.type):
        await cq.answer(f"Чат «{title}» подписан ✅", show_alert=True)
        log.info("Чат подписан: %s (%s)", title, chat.id)
    else:
        await cq.answer("Этот чат уже подписан.", show_alert=True)
    await cb_chats(cq, state, storage)


@router.callback_query(F.data == CB_CHAT_DEL_HERE, StateFilter("*"))
async def cb_chat_del_here(cq: CallbackQuery, state: FSMContext, storage: Storage) -> None:
    await state.clear()
    chat_id = cq.message.chat.id
    if storage.remove_chat(chat_id):
        await cq.answer("Чат отписан ✅", show_alert=True)
        log.info("Чат отписан: %s", chat_id)
    else:
        await cq.answer("Этот чат не подписан.", show_alert=True)
    await cb_chats(cq, state, storage)


@router.callback_query(F.data.startswith("ct:list:"), StateFilter("*"))
async def cb_chats_list(cq: CallbackQuery, state: FSMContext, storage: Storage) -> None:
    await state.clear()
    chats = storage.get_chats()
    if not chats:
        await _edit(
            cq,
            "🏠 / 🔔 / 📋 <b>Подписанные чаты</b>\n\nСписок пуст.",
            back_to(CB_CHATS, "← Назад"),
        )
        return
    page = _parse_page(cq.data, CB_CHAT_PAGE)
    start = page * PAGE_SIZE
    lines = ["🏠 / 🔔 / 📋 <b>Подписанные чаты</b>\n"]
    for i, c in enumerate(chats[start:start + PAGE_SIZE], start=start + 1):
        lines.append(
            f"{i}. <b>{c.get('title', c['id'])}</b> "
            f"<i>({c.get('type', '?')})</i>\n   <code>{c['id']}</code>"
        )
    lines.append("\nНажмите 🗑, чтобы отписать чат.")
    await _edit(cq, "\n".join(lines), paginated_list(
        chats, page, CB_CHAT_PAGE, CB_CHAT_DEL, CB_CHATS,
        label_key="title", id_key="id",
    ))


@router.callback_query(F.data.startswith(CB_CHAT_DEL), StateFilter("*"))
async def cb_chat_delete(cq: CallbackQuery, state: FSMContext, storage: Storage) -> None:
    await state.clear()
    raw = cq.data[len(CB_CHAT_DEL):]
    try:
        chat_id = int(raw)
    except ValueError:
        await cq.answer("Некорректный ID", show_alert=True)
        return
    if storage.remove_chat(chat_id):
        await cq.answer(f"Чат {chat_id} отписан")
        log.info("Чат отписан: %s", chat_id)
    else:
        await cq.answer("Не найден", show_alert=True)
    cq.data = "ct:list:0"
    await cb_chats_list(cq, state, storage)
