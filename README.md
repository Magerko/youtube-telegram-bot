# YouTube → Telegram Notification Bot

Telegram-бот на **aiogram 3**, который отслеживает указанные YouTube-каналы и автоматически постит уведомления о новых видео в подключённые группы/каналы Telegram.

Управление — через инлайн-админку (`/menu`): меню с кнопками, пошаговое добавление каналов, удаление в один тап, выход из любого диалога командой `/cancel`.

## Возможности

- 🎛 Инлайн-админка с понятной навигацией («хлебные крошки», «← Назад», «🏠 Главное меню»)
- 📺 Добавление каналов одним сообщением: ID, URL `/channel/UC…`, URL `/@handle` или `@handle`
- 🗑 Удаление каналов/чатов кнопкой (без копирования ID)
- 📄 Пагинация длинных списков
- 🔔 Подписка/отписка текущего чата одной кнопкой
- 📊 Команда `/status` и кнопка «Статус»
- ✖️ Выход из любого диалога: `/cancel` или кнопка «❌ Отмена»
- 🛡 Admin-only middleware: команды и кнопки доступны только из `ADMIN_USERS`
- 🚦 Корректная обработка rate-limit, недоступных чатов и сетевых таймаутов
- 💾 Постоянное хранение в JSON

## Структура проекта

```
.
├── bot.py                  # точка входа
├── config.py               # настройки из .env
├── keyboards.py            # inline-клавиатуры и callback-токены
├── middlewares.py          # admin-only middleware
├── states.py               # FSM-состояния
├── pyproject.toml          # метаданные + зависимости (PEP 621)
├── Dockerfile
├── docker-compose.yml      # bot + redis
├── .env.example            # шаблон для .env
├── handlers/
│   ├── common.py           # /start, /menu, /cancel, главное меню
│   ├── channels.py         # раздел YouTube + FSM добавления
│   ├── chats.py            # раздел Telegram-чатов
│   └── info.py             # справка и статус
├── services/
│   ├── storage.py          # JSON-хранилище
│   ├── youtube.py          # YouTube Data API + resolver
│   └── notifier.py         # цикл мониторинга и рассылка
├── tests/                  # pytest + pytest-asyncio
│   ├── test_storage.py
│   ├── test_youtube_resolver.py
│   └── test_keyboards.py
└── pydata/                 # создаётся автоматически при первом запуске
    ├── telegram_chats.json
    └── influencers.json
```

## Требования

- Python **3.10+**
- Telegram Bot Token
- YouTube Data API v3 key

## Где взять ключи

### 1. `TELEGRAM_BOT_TOKEN`

1. Откройте в Telegram чат с [@BotFather](https://t.me/BotFather).
2. Отправьте команду `/newbot`.
3. Задайте имя бота и его уникальный username (должен заканчиваться на `bot`).
4. BotFather пришлёт строку вида `123456789:ABC-DEF…` — это и есть токен.

### 2. `YOUTUBE_API_KEY`

1. Зайдите в [Google Cloud Console](https://console.cloud.google.com/).
2. Создайте новый проект (или выберите существующий).
3. В меню слева: **APIs & Services → Library**.
4. Найдите **YouTube Data API v3** → нажмите **Enable**.
5. Перейдите в **APIs & Services → Credentials → Create credentials → API key**.
6. Скопируйте полученный ключ.
7. Сразу нажмите **Edit API key** (или **Restrict key** в окне создания) и настройте ограничения:
   - **Application restrictions** → оставьте как есть (бот работает с бэкенда, IP может меняться; ограничивать по HTTP referrer / IP не нужно).
   - **API restrictions** — это поле в новом UI обязательное → выберите **Restrict key** → в выпадающем списке отметьте **YouTube Data API v3** → **Save**.

> Без ограничения по API ключ работает со всеми Google API — если он утечёт, кто-то израсходует вашу квоту. Restriction на одно API — must have.

> Бесплатная квота YouTube API — 10 000 единиц в сутки; одна проверка канала тратит ~3–5 единиц, поэтому при `CHECK_INTERVAL=300` (5 мин) с 10 каналами квоты хватает с большим запасом.

### 3. `ADMIN_USERS`

Свой Telegram user ID можно узнать у одного из этих ботов:

- [@userinfobot](https://t.me/userinfobot)
- [@getmyid_bot](https://t.me/getmyid_bot)

Если админов несколько — перечислите ID через запятую: `123456789,987654321`.

## Установка (локально)

```bash
git clone https://github.com/Magerko/youtube-telegram-bot.git
cd youtube-telegram-bot

# (опционально) виртуальное окружение
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install .              # только runtime
pip install -e ".[dev]"    # для разработки (с pytest)
```

## Настройка

Скопируйте шаблон и заполните значениями:

```bash
cp .env.example .env
```

`.env`:

```env
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF...
YOUTUBE_API_KEY=AIza...
ADMIN_USERS=123456789
CHECK_INTERVAL=300
DATA_FOLDER=pydata
# REDIS_URL=redis://localhost:6379/0   # см. ниже
```

## Запуск

### Локально

```bash
python bot.py
```

В логах должно появиться: `Бот запущен. Админов: 1`.

> Без `REDIS_URL` FSM-состояния хранятся в памяти и теряются при рестарте. Для продакшна задайте `REDIS_URL` или запустите через docker-compose (Redis включён в стек).

### Docker

В корне есть `Dockerfile` и `docker-compose.yml` со связкой **bot + redis**. Перед запуском заполните `.env` (см. выше), затем:

```bash
docker compose up -d --build
docker compose logs -f bot
```

В compose-стеке `REDIS_URL` и `DATA_FOLDER` подставляются автоматически, данные `pydata/` и Redis-снапшоты сохраняются на хосте/в томе.

Остановить:

```bash
docker compose down
```

## Тесты

```bash
pip install -e ".[dev]"
pytest
```

Покрыто: storage CRUD, YouTube-resolver (с моком API), пагинация и сборка inline-клавиатур.

## Использование

1. Напишите боту `/start` или `/menu` в личке.
2. **📺 YouTube каналы → ➕ Добавить** → пришлите ID, URL канала или `@handle`.
3. Добавьте бота администратором в нужную группу/канал, откройте там `/menu` → **🔔 Чаты уведомлений → ➕ Подписать этот чат**.
4. Дальше бот сам проверяет новые видео каждые `CHECK_INTERVAL` секунд и рассылает уведомления.

### Команды

| Команда   | Назначение                       |
|-----------|----------------------------------|
| `/start`  | Открыть админку                  |
| `/menu`   | То же, что `/start`              |
| `/status` | Краткая сводка                   |
| `/cancel` | Выйти из текущего диалога        |

Всё остальное — кнопками в меню.

## Лицензия

MIT.
