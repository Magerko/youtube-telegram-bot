"""Цикл мониторинга YouTube-каналов и рассылка уведомлений в Telegram-чаты."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from io import BytesIO

import aiohttp
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import BufferedInputFile

from services.storage import Storage
from services.youtube import YouTubeClient

log = logging.getLogger("ytbot.notifier")

BATCH_SIZE = 3
BATCH_PAUSE_SEC = 3
PER_CHAT_PAUSE_SEC = 2


class Notifier:
    def __init__(
        self,
        bot: Bot,
        storage: Storage,
        youtube: YouTubeClient,
        check_interval: int,
    ) -> None:
        self.bot = bot
        self.storage = storage
        self.youtube = youtube
        self.check_interval = check_interval

        self.shutdown_event = asyncio.Event()
        self.running = False
        self.started_at = datetime.now(timezone.utc)
        self.notifications_sent = 0
        self._last_check: dict[str, datetime] = {}
        self._task: asyncio.Task | None = None

    # ───────────── lifecycle ─────────────
    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop(), name="notifier-loop")

    async def stop(self) -> None:
        self.shutdown_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    # ───────────── main loop ─────────────
    async def _loop(self) -> None:
        self.running = True
        log.info("Notifier запущен (интервал %d сек)", self.check_interval)
        try:
            while not self.shutdown_event.is_set():
                await self._tick()
                if self.shutdown_event.is_set():
                    break
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(), timeout=self.check_interval
                    )
                except asyncio.TimeoutError:
                    pass
        finally:
            self.running = False
            log.info("Notifier остановлен")

    async def _tick(self) -> None:
        channels = self.storage.get_channels()
        log.info("Проверка %d каналов", len(channels))

        conn = aiohttp.TCPConnector(limit=5, force_close=True)
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
            for channel in channels:
                if self.shutdown_event.is_set():
                    return
                try:
                    await self._check_channel(session, channel)
                except Exception:
                    log.exception("Ошибка проверки %s", channel.get("name"))
                await asyncio.sleep(2)

    async def _check_channel(self, session: aiohttp.ClientSession, channel: dict) -> None:
        channel_id = channel["id"].strip()
        if not await self.youtube.verify_channel(channel_id):
            log.warning("Канал не существует: %s (%s)", channel.get("name"), channel_id)
            return

        since = self._last_check.get(
            channel_id,
            datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0),
        )
        videos = await self.youtube.get_new_uploads(channel_id, since)
        for video in videos:
            if self.shutdown_event.is_set():
                return
            await self._process_video(session, video)
        self._last_check[channel_id] = datetime.now(timezone.utc)

    # ───────────── video → notification ─────────────
    async def _process_video(self, session: aiohttp.ClientSession, video: dict) -> None:
        video_id = video["id"]
        thumbs = video["snippet"]["thumbnails"]
        thumbnail_url = (thumbs.get("maxres") or thumbs.get("high") or thumbs["default"])["url"]
        async with session.get(thumbnail_url) as response:
            if response.status != 200:
                log.warning("Не удалось скачать thumbnail %s: HTTP %s", video_id, response.status)
                return
            thumb = await response.read()

        upload_date = datetime.fromisoformat(
            video["snippet"]["publishedAt"].replace("Z", "+00:00")
        )
        formatted_date = upload_date.strftime("%Y-%m-%d %H:%M UTC")
        channel_title = video["snippet"]["channelTitle"]
        title = video["snippet"]["title"]
        channel_id = video["snippet"]["channelId"]

        caption = (
            f"🔥 <b>НОВОЕ ВИДЕО — СМОТРИТЕ СЕЙЧАС</b> 🔥\n"
            f"═══════════════\n"
            f"🎬 <b><a href='https://youtube.com/watch?v={video_id}'>{title}</a></b>\n"
            f"📺 <b><a href='https://youtube.com/channel/{channel_id}?sub_confirmation=1'>"
            f"{channel_title}</a></b>\n"
            f"📅 {formatted_date}\n"
            f"#НовоеВидео #{channel_title.replace(' ', '')}"
        )
        await self._broadcast(thumb, caption, filename=f"{video_id}.jpg")

    async def _broadcast(self, thumb: bytes, caption: str, filename: str) -> None:
        chat_ids = self.storage.get_chat_ids()
        for i in range(0, len(chat_ids), BATCH_SIZE):
            if self.shutdown_event.is_set():
                return
            for chat_id in chat_ids[i:i + BATCH_SIZE]:
                await self._send_one(chat_id, thumb, caption, filename)
                await asyncio.sleep(PER_CHAT_PAUSE_SEC)
            if i + BATCH_SIZE < len(chat_ids):
                await asyncio.sleep(BATCH_PAUSE_SEC)

    async def _send_one(self, chat_id: int, thumb: bytes, caption: str, filename: str) -> None:
        photo = BufferedInputFile(thumb, filename=filename)
        try:
            await self.bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
            self.notifications_sent += 1
            log.info("Уведомление → %s", chat_id)
        except TelegramRetryAfter as e:
            log.warning("Rate limit, sleep %s s (chat %s)", e.retry_after, chat_id)
            await asyncio.sleep(e.retry_after)
            try:
                await self.bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
                self.notifications_sent += 1
            except TelegramAPIError as retry_e:
                log.error("Повтор → %s не удался: %s", chat_id, retry_e)
        except TelegramForbiddenError as e:
            log.warning("Чат %s недоступен (отписываем): %s", chat_id, e)
            self.storage.remove_chat(chat_id)
        except TelegramAPIError as e:
            msg = str(e).lower()
            if "chat not found" in msg or "kicked" in msg or "blocked" in msg:
                log.warning("Чат %s недоступен (отписываем): %s", chat_id, e)
                self.storage.remove_chat(chat_id)
            else:
                log.error("Не удалось отправить в %s: %s", chat_id, e)
