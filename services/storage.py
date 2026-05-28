import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("ytbot.storage")


class Storage:
    def __init__(self, data_folder: str | Path = "pydata") -> None:
        self.data_folder = Path(data_folder)
        self.chats_file = self.data_folder / "telegram_chats.json"
        self.channels_file = self.data_folder / "influencers.json"
        self.chats: list[dict] = []
        self.channels: list[dict] = []
        self._ensure_files()
        self._load()

    def _ensure_files(self) -> None:
        if not self.data_folder.exists():
            log.info("Создаю папку данных: %s", self.data_folder)
            self.data_folder.mkdir(parents=True)
        if not self.chats_file.exists():
            self._write(self.chats_file, [])
        if not self.channels_file.exists():
            self._write(self.channels_file, {"channels": []})

    @staticmethod
    def _write(path: Path, payload) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        try:
            with open(self.chats_file, "r", encoding="utf-8") as f:
                self.chats = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            log.warning("Файл чатов повреждён, начинаю с пустого: %s", e)
            self.chats = []
            self._write(self.chats_file, self.chats)

        try:
            with open(self.channels_file, "r", encoding="utf-8") as f:
                self.channels = json.load(f).get("channels", [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            log.warning("Файл каналов повреждён, начинаю с пустого: %s", e)
            self.channels = []
            self._write(self.channels_file, {"channels": []})

        log.info("Загружено: %d чатов, %d каналов", len(self.chats), len(self.channels))

    def _save_chats(self) -> None:
        self._write(self.chats_file, self.chats)

    def _save_channels(self) -> None:
        self._write(self.channels_file, {"channels": self.channels})

    def add_chat(self, chat_id: int, title: Optional[str] = None,
                 chat_type: Optional[str] = None) -> bool:
        chat_id = int(chat_id)
        if any(c["id"] == chat_id for c in self.chats):
            return False
        self.chats.append({
            "id": chat_id,
            "title": title or str(chat_id),
            "type": chat_type or "неизвестно",
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        self._save_chats()
        return True

    def remove_chat(self, chat_id: int) -> bool:
        chat_id = int(chat_id)
        before = len(self.chats)
        self.chats = [c for c in self.chats if c["id"] != chat_id]
        if len(self.chats) < before:
            self._save_chats()
            return True
        return False

    def get_chats(self) -> list[dict]:
        return self.chats

    def get_chat_ids(self) -> list[int]:
        return [c["id"] for c in self.chats]

    def add_channel(self, name: str, channel_id: str) -> bool:
        name = name.strip()
        channel_id = channel_id.strip()
        if any(c["id"] == channel_id for c in self.channels):
            return False
        self.channels.append({"name": name, "id": channel_id})
        self._save_channels()
        return True

    def remove_channel(self, channel_id: str) -> bool:
        channel_id = channel_id.strip()
        before = len(self.channels)
        self.channels = [c for c in self.channels if c["id"] != channel_id]
        if len(self.channels) < before:
            self._save_channels()
            return True
        return False

    def get_channel(self, channel_id: str) -> Optional[dict]:
        channel_id = channel_id.strip()
        for c in self.channels:
            if c["id"] == channel_id:
                return c
        return None

    def get_channels(self) -> list[dict]:
        return self.channels
