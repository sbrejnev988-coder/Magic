# Multi-stage build для минимального образа
FROM python:3.12-slim AS builder

WORKDIR /app

# Установка uv (быстрый менеджер зависимостей)
RUN pip install --no-cache-dir uv

# Копирование файлов зависимостей
COPY pyproject.toml uv.lock ./

# Создание виртуального окружения и установка зависимостей
RUN uv venv && uv sync --frozen --no-dev

# Финальный образ
FROM python:3.12-slim

WORKDIR /app

# Копирование виртуального окружения из builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Установка системных зависимостей для PostgreSQL и других библиотек
RUN apt-get update && apt-get install -y \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование исходного кода
COPY . .

# Создание необходимых директорий
RUN mkdir -p data uploads logs

# Установка прав на запись
RUN chmod -R a+rw data uploads logs

# Переменные окружения по умолчанию
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Healthcheck для бота
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Запуск бота (точку входа можно изменить через environment)
CMD ["python", "-m", "bot.main"]