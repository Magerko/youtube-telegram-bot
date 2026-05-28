from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Telegram ограничивает callback_data 64 байтами, поэтому префиксы короткие
CB_MAIN = "m:main"
CB_CHANNELS = "m:channels"
CB_CHATS = "m:chats"
CB_HELP = "m:help"
CB_STATUS = "m:status"

CB_CH_ADD = "ch:add"
CB_CH_LIST = "ch:list:0"
CB_CH_DEL = "ch:del:"
CB_CH_PAGE = "ch:list:"

CB_CHAT_ADD_HERE = "ct:add_here"
CB_CHAT_DEL_HERE = "ct:del_here"
CB_CHAT_LIST = "ct:list:0"
CB_CHAT_DEL = "ct:del:"
CB_CHAT_PAGE = "ct:list:"

CB_CANCEL = "cancel"
CB_NOOP = "noop"

PAGE_SIZE = 6


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📺 YouTube каналы", callback_data=CB_CHANNELS)
    kb.button(text="🔔 Чаты уведомлений", callback_data=CB_CHATS)
    kb.button(text="📊 Статус", callback_data=CB_STATUS)
    kb.button(text="ℹ️ Справка", callback_data=CB_HELP)
    kb.adjust(2, 2)
    return kb.as_markup()


def channels_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить канал", callback_data=CB_CH_ADD)
    kb.button(text="📋 Список", callback_data=CB_CH_LIST)
    kb.button(text="🏠 Главное меню", callback_data=CB_MAIN)
    kb.adjust(2, 1)
    return kb.as_markup()


def chats_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Подписать этот чат", callback_data=CB_CHAT_ADD_HERE)
    kb.button(text="➖ Отписать этот чат", callback_data=CB_CHAT_DEL_HERE)
    kb.button(text="📋 Все чаты", callback_data=CB_CHAT_LIST)
    kb.button(text="🏠 Главное меню", callback_data=CB_MAIN)
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def back_to(target: str = CB_MAIN, label: str = "🏠 Главное меню") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=target)]]
    )


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data=CB_CANCEL)]]
    )


def paginated_list(
    items: list[dict],
    page: int,
    page_prefix: str,
    del_prefix: str,
    back_cb: str,
    label_key: str = "name",
    id_key: str = "id",
) -> InlineKeyboardMarkup:
    total = len(items)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    chunk = items[start:start + PAGE_SIZE]

    rows: list[list[InlineKeyboardButton]] = []
    for item in chunk:
        label = str(item.get(label_key) or item.get(id_key))
        if len(label) > 28:
            label = label[:27] + "…"
        rows.append([InlineKeyboardButton(
            text=f"🗑 {label}", callback_data=f"{del_prefix}{item[id_key]}",
        )])

    if total_pages > 1:
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"{page_prefix}{page - 1}"))
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data=CB_NOOP))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"{page_prefix}{page + 1}"))
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="← Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
