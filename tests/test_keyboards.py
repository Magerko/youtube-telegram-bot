"""Тесты для keyboards.paginated_list — границы пагинации и кнопки удаления."""

from __future__ import annotations

from keyboards import CB_NOOP, PAGE_SIZE, paginated_list


def _items(n: int) -> list[dict]:
    return [{"id": f"id_{i}", "name": f"item_{i}"} for i in range(n)]


def _row_texts(rows) -> list[list[str]]:
    return [[btn.text for btn in row] for row in rows]


def test_single_page_no_nav() -> None:
    kb = paginated_list(_items(3), page=0, page_prefix="x:p:", del_prefix="x:d:", back_cb="back")
    rows = _row_texts(kb.inline_keyboard)
    # 3 кнопки удаления + «Назад»; nav-строки нет
    assert len(rows) == 4
    assert all(row[0].startswith("🗑") for row in rows[:3])
    assert rows[-1] == ["← Назад"]


def test_multi_page_shows_nav() -> None:
    kb = paginated_list(_items(PAGE_SIZE * 2 + 1), page=0,
                        page_prefix="x:p:", del_prefix="x:d:", back_cb="back")
    rows = kb.inline_keyboard
    # нав-строка предпоследняя
    nav = rows[-2]
    labels = [b.text for b in nav]
    # На первой странице — только индикатор и «вперёд»
    assert "1/3" in labels
    assert "▶️" in labels
    assert "◀️" not in labels


def test_middle_page_has_both_arrows() -> None:
    kb = paginated_list(_items(PAGE_SIZE * 3), page=1,
                        page_prefix="x:p:", del_prefix="x:d:", back_cb="back")
    nav = kb.inline_keyboard[-2]
    labels = [b.text for b in nav]
    assert "◀️" in labels and "▶️" in labels
    assert "2/3" in labels


def test_last_page_no_forward() -> None:
    kb = paginated_list(_items(PAGE_SIZE * 2 + 1), page=2,
                        page_prefix="x:p:", del_prefix="x:d:", back_cb="back")
    nav = kb.inline_keyboard[-2]
    labels = [b.text for b in nav]
    assert "◀️" in labels and "▶️" not in labels


def test_page_clamped_to_available() -> None:
    # Запрошена страница 99 — должна показаться последняя.
    kb = paginated_list(_items(PAGE_SIZE * 2), page=99,
                        page_prefix="x:p:", del_prefix="x:d:", back_cb="back")
    nav = kb.inline_keyboard[-2]
    labels = [b.text for b in nav]
    assert "2/2" in labels


def test_del_button_carries_id() -> None:
    kb = paginated_list(_items(2), page=0, page_prefix="x:p:", del_prefix="x:d:", back_cb="back")
    first_btn = kb.inline_keyboard[0][0]
    assert first_btn.callback_data == "x:d:id_0"


def test_long_label_truncated() -> None:
    items = [{"id": "i1", "name": "x" * 50}]
    kb = paginated_list(items, page=0, page_prefix="x:p:", del_prefix="x:d:", back_cb="back")
    btn_text = kb.inline_keyboard[0][0].text
    # 🗑 + пробел + max 28 символов
    assert "…" in btn_text


def test_page_indicator_is_noop() -> None:
    kb = paginated_list(_items(PAGE_SIZE + 1), page=0,
                        page_prefix="x:p:", del_prefix="x:d:", back_cb="back")
    nav = kb.inline_keyboard[-2]
    indicator = next(b for b in nav if "/" in b.text)
    assert indicator.callback_data == CB_NOOP
