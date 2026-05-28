import logging
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import (
    CB_CHANNELS,
    CB_CH_ADD,
    CB_CH_DEL,
    CB_CH_PAGE,
    PAGE_SIZE,
    back_to,
    cancel_kb,
    channels_menu,
    paginated_list,
)
from services.storage import Storage
from services.youtube import YouTubeClient
from states import AddChannel

log = logging.getLogger("ytbot.channels")
router = Router(name="channels")


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


@router.callback_query(F.data == CB_CHANNELS, StateFilter("*"))
async def cb_channels(cq: CallbackQuery, state: FSMContext, storage: Storage) -> None:
    await state.clear()
    text = (
        "🏠 / 📺 <b>YouTube каналы</b>\n\n"
        f"Под мониторингом: <b>{len(storage.get_channels())}</b>"
    )
    await _edit(cq, text, channels_menu())


@router.callback_query(F.data.startswith("ch:list:"), StateFilter("*"))
async def cb_channels_list(cq: CallbackQuery, state: FSMContext, storage: Storage) -> None:
    await state.clear()
    channels = storage.get_channels()
    if not channels:
        await _edit(
            cq,
            "🏠 / 📺 / 📋 <b>Список каналов</b>\n\nСписок пуст. Нажмите ➕ чтобы добавить.",
            back_to(CB_CHANNELS, "← Назад"),
        )
        return

    page = _parse_page(cq.data, CB_CH_PAGE)
    start = page * PAGE_SIZE
    lines = ["🏠 / 📺 / 📋 <b>Список каналов</b>\n"]
    for i, ch in enumerate(channels[start:start + PAGE_SIZE], start=start + 1):
        lines.append(f"{i}. <b>{ch['name']}</b>\n   <code>{ch['id']}</code>")
    lines.append("\nНажмите 🗑, чтобы удалить.")
    await _edit(cq, "\n".join(lines), paginated_list(
        channels, page, CB_CH_PAGE, CB_CH_DEL, CB_CHANNELS,
    ))


@router.callback_query(F.data.startswith(CB_CH_DEL), StateFilter("*"))
async def cb_channel_delete(cq: CallbackQuery, state: FSMContext, storage: Storage) -> None:
    await state.clear()
    channel_id = cq.data[len(CB_CH_DEL):]
    ch = storage.get_channel(channel_id)
    if storage.remove_channel(channel_id):
        await cq.answer(f"Удалён: {ch['name'] if ch else channel_id}")
        log.info("Канал удалён: %s (%s)", ch and ch["name"], channel_id)
    else:
        await cq.answer("Не найден", show_alert=True)
    cq.data = "ch:list:0"
    await cb_channels_list(cq, state, storage)


@router.callback_query(F.data == CB_CH_ADD)
async def cb_channel_add_start(cq: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddChannel.waiting_input)
    await _edit(
        cq,
        "🏠 / 📺 / ➕ <b>Добавление канала</b>\n\n"
        "Отправьте одним сообщением:\n"
        "• ID канала (<code>UC…</code>)\n"
        "• ссылку <code>https://youtube.com/channel/UC…</code>\n"
        "• ссылку <code>https://youtube.com/@handle</code>\n"
        "• handle <code>@handle</code>\n\n"
        "Для выхода — /cancel или кнопка ниже.",
        cancel_kb(),
    )


@router.message(AddChannel.waiting_input)
async def msg_channel_input(
    message: Message,
    state: FSMContext,
    storage: Storage,
    youtube: YouTubeClient,
) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пустой ввод. Пришлите ID/URL/handle или /cancel.",
                             reply_markup=cancel_kb())
        return

    await message.bot.send_chat_action(message.chat.id, "typing")
    resolved = await youtube.resolve_channel(text)
    if not resolved:
        await message.answer(
            "❌ Не удалось распознать канал. Проверьте ввод или /cancel.",
            reply_markup=cancel_kb(),
        )
        return

    ch_id, ch_name = resolved
    if storage.add_channel(ch_name, ch_id):
        log.info("Канал добавлен: %s (%s)", ch_name, ch_id)
        await message.answer(
            f"✅ Канал добавлен!\n\n<b>{ch_name}</b>\n<code>{ch_id}</code>",
            reply_markup=back_to(CB_CHANNELS, "← К каналам"),
        )
    else:
        await message.answer(
            f"ℹ️ Канал уже под мониторингом: <b>{ch_name}</b>",
            reply_markup=back_to(CB_CHANNELS, "← К каналам"),
        )
    await state.clear()
