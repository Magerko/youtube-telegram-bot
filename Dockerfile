FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Сначала только метаданные — слой зависимостей будет кешироваться отдельно.
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY bot.py config.py keyboards.py middlewares.py states.py ./
COPY handlers ./handlers
COPY services ./services

# Папка для JSON-данных монтируется как volume.
RUN mkdir -p /app/pydata

# Непривилегированный пользователь.
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin bot \
    && chown -R bot:bot /app
USER bot

CMD ["python", "bot.py"]
