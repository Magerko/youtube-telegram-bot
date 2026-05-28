import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _parse_admins(raw: str) -> frozenset[int]:
    return frozenset(int(x.strip()) for x in raw.split(",") if x.strip())


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Переменная окружения {name} обязательна. Заполните .env")
    return value


@dataclass(frozen=True)
class Settings:
    bot_token: str
    youtube_api_key: str
    admin_users: frozenset[int]
    check_interval: int
    data_folder: str
    redis_url: str | None


settings = Settings(
    bot_token=_required("TELEGRAM_BOT_TOKEN"),
    youtube_api_key=_required("YOUTUBE_API_KEY"),
    admin_users=_parse_admins(os.getenv("ADMIN_USERS", "")),
    check_interval=int(os.getenv("CHECK_INTERVAL", "300")),
    data_folder=os.getenv("DATA_FOLDER", "pydata"),
    redis_url=os.getenv("REDIS_URL") or None,
)
