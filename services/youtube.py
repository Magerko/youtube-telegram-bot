"""Тонкая обёртка над YouTube Data API v3 с асинхронными вызовами."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from googleapiclient.discovery import build

log = logging.getLogger("ytbot.youtube")

RE_CHANNEL_ID = re.compile(r"(UC[A-Za-z0-9_-]{22})")
RE_HANDLE = re.compile(r"@([A-Za-z0-9_.\-]{3,})")


class YouTubeClient:
    """Все вызовы googleapiclient синхронны — оборачиваем в `asyncio.to_thread`."""

    def __init__(self, api_key: str) -> None:
        self._yt = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
        self._verified: set[str] = set()

    # ───────────── resolve ─────────────
    async def resolve_channel(self, query: str) -> Optional[tuple[str, str]]:
        """Из произвольной строки (URL/ID/@handle) вернуть (channel_id, title)."""
        channel_id: Optional[str] = None
        handle: Optional[str] = None

        m = RE_CHANNEL_ID.search(query)
        if m:
            channel_id = m.group(1)
        else:
            m = RE_HANDLE.search(query)
            if m:
                handle = "@" + m.group(1)
            elif query.startswith("@"):
                handle = query

        if not (channel_id or handle):
            return None

        def _call() -> dict:
            kwargs = {"part": "snippet"}
            if channel_id:
                kwargs["id"] = channel_id
            else:
                kwargs["forHandle"] = handle
            return self._yt.channels().list(**kwargs).execute()

        try:
            response = await asyncio.to_thread(_call)
        except Exception as e:
            log.error("YouTube API ошибка резолва %r: %s", query, e)
            return None

        items = response.get("items") if response else None
        if not items:
            return None
        item = items[0]
        return item["id"], item["snippet"]["title"]

    # ───────────── verify ─────────────
    async def verify_channel(self, channel_id: str) -> bool:
        if channel_id in self._verified:
            return True

        def _call() -> dict:
            return self._yt.channels().list(part="id", id=channel_id).execute()

        try:
            response = await asyncio.to_thread(_call)
        except Exception as e:
            log.error("verify_channel %s: %s", channel_id, e)
            return False
        if response.get("items"):
            self._verified.add(channel_id)
            return True
        return False

    # ───────────── new uploads ─────────────
    async def get_new_uploads(
        self, channel_id: str, since: datetime
    ) -> list[dict]:
        """Список новых видео канала после `since`, отсортированный по убыванию даты."""

        def _activities() -> dict:
            return self._yt.activities().list(
                part="contentDetails,snippet",
                channelId=channel_id,
                publishedAfter=since.isoformat(),
                maxResults=5,
            ).execute()

        def _video(video_id: str) -> dict:
            return self._yt.videos().list(
                part="snippet,statistics,contentDetails",
                id=video_id,
            ).execute()

        try:
            activities = await asyncio.to_thread(_activities)
        except Exception as e:
            log.error("activities() для %s: %s", channel_id, e)
            return []

        results: list[tuple[datetime, dict]] = []
        for item in activities.get("items", []):
            if "upload" not in item.get("contentDetails", {}):
                continue
            video_id = item["contentDetails"]["upload"]["videoId"]
            try:
                response = await asyncio.to_thread(_video, video_id)
            except Exception as e:
                log.error("videos() для %s: %s", video_id, e)
                continue
            items = response.get("items")
            if not items:
                continue
            video = items[0]
            upload_date = datetime.fromisoformat(
                video["snippet"]["publishedAt"].replace("Z", "+00:00")
            )
            results.append((upload_date, video))

        results.sort(key=lambda x: x[0], reverse=True)
        return [v for _, v in results]
