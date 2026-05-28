"""Парсер канала из URL/ID/handle. YouTube API мокаем — реальной сети нет."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.youtube import RE_CHANNEL_ID, RE_HANDLE


# ───────────── regex ─────────────
class TestRegex:
    def test_channel_id_from_plain(self) -> None:
        m = RE_CHANNEL_ID.search("UC-lHJZR3Gqxm24_Vd_AJ5Yw")
        assert m is not None
        assert m.group(1) == "UC-lHJZR3Gqxm24_Vd_AJ5Yw"

    def test_channel_id_from_full_url(self) -> None:
        m = RE_CHANNEL_ID.search("https://www.youtube.com/channel/UC-lHJZR3Gqxm24_Vd_AJ5Yw")
        assert m is not None
        assert m.group(1) == "UC-lHJZR3Gqxm24_Vd_AJ5Yw"

    def test_channel_id_invalid_prefix(self) -> None:
        assert RE_CHANNEL_ID.search("XX-lHJZR3Gqxm24_Vd_AJ5Yw") is None

    def test_handle_with_at(self) -> None:
        m = RE_HANDLE.search("@PewDiePie")
        assert m is not None
        assert m.group(1) == "PewDiePie"

    def test_handle_in_url(self) -> None:
        m = RE_HANDLE.search("https://youtube.com/@MrBeast")
        assert m is not None
        assert m.group(1) == "MrBeast"


# ───────────── resolve_channel ─────────────
@pytest.fixture
def mocked_client():
    """YouTubeClient с замоканным googleapiclient build."""
    with patch("services.youtube.build") as build_mock:
        from services.youtube import YouTubeClient
        client = YouTubeClient("FAKE_KEY")
        yield client, build_mock.return_value


def _fake_response(channel_id: str, title: str) -> dict:
    return {"items": [{"id": channel_id, "snippet": {"title": title}}]}


def _setup_channels_list(yt_mock, response: dict) -> MagicMock:
    """Настроить yt.channels().list(**kwargs).execute() → response. Возвращает list mock."""
    list_mock = MagicMock()
    list_mock.execute.return_value = response
    yt_mock.channels.return_value.list.return_value = list_mock
    return list_mock


async def test_resolve_by_id(mocked_client) -> None:
    client, yt_mock = mocked_client
    _setup_channels_list(yt_mock, _fake_response("UC-lHJZR3Gqxm24_Vd_AJ5Yw", "PewDiePie"))

    result = await client.resolve_channel("UC-lHJZR3Gqxm24_Vd_AJ5Yw")
    assert result == ("UC-lHJZR3Gqxm24_Vd_AJ5Yw", "PewDiePie")

    # Должно искать через id=, а не forHandle=
    kwargs = yt_mock.channels.return_value.list.call_args.kwargs
    assert kwargs.get("id") == "UC-lHJZR3Gqxm24_Vd_AJ5Yw"
    assert "forHandle" not in kwargs


async def test_resolve_by_url(mocked_client) -> None:
    client, yt_mock = mocked_client
    _setup_channels_list(yt_mock, _fake_response("UC-lHJZR3Gqxm24_Vd_AJ5Yw", "PewDiePie"))

    result = await client.resolve_channel(
        "https://youtube.com/channel/UC-lHJZR3Gqxm24_Vd_AJ5Yw"
    )
    assert result == ("UC-lHJZR3Gqxm24_Vd_AJ5Yw", "PewDiePie")


async def test_resolve_by_handle(mocked_client) -> None:
    client, yt_mock = mocked_client
    _setup_channels_list(yt_mock, _fake_response("UC_mrbeast", "MrBeast"))

    result = await client.resolve_channel("@MrBeast")
    assert result == ("UC_mrbeast", "MrBeast")
    kwargs = yt_mock.channels.return_value.list.call_args.kwargs
    assert kwargs.get("forHandle") == "@MrBeast"


async def test_resolve_handle_in_url(mocked_client) -> None:
    client, yt_mock = mocked_client
    _setup_channels_list(yt_mock, _fake_response("UC_mrbeast", "MrBeast"))

    result = await client.resolve_channel("https://youtube.com/@MrBeast")
    assert result == ("UC_mrbeast", "MrBeast")


async def test_resolve_garbage_returns_none(mocked_client) -> None:
    client, _ = mocked_client
    assert await client.resolve_channel("какой-то мусор без признаков ID") is None


async def test_resolve_unknown_channel(mocked_client) -> None:
    client, yt_mock = mocked_client
    _setup_channels_list(yt_mock, {"items": []})
    assert await client.resolve_channel("UC-lHJZR3Gqxm24_Vd_AJ5Yw") is None


async def test_resolve_api_error_returns_none(mocked_client) -> None:
    client, yt_mock = mocked_client
    yt_mock.channels.return_value.list.return_value.execute.side_effect = RuntimeError("boom")
    assert await client.resolve_channel("UC-lHJZR3Gqxm24_Vd_AJ5Yw") is None
