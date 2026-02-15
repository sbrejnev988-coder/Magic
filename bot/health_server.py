"""
HTTP healthcheck сервер для Docker и мониторинга.

Запускает фоновый aiohttp‑сервер на порту 8080 (настраивается через HEALTH_PORT).
Предоставляет эндпоинты:
- GET /health → 200 OK с JSON статусом бота.
- GET /metrics → метрики (заглушка для Prometheus).
- GET / → краткая информация.

Сервер запускается в отдельной задаче (asyncio.Task) и останавливается при завершении бота.
"""

import asyncio
import json
import logging
import os
import psutil
import socket
from datetime import datetime, timezone
from typing import Optional

from aiohttp import web

logger = logging.getLogger(__name__)

# Порт по умолчанию (можно переопределить через HEALTH_PORT)
DEFAULT_PORT = int(os.getenv("HEALTH_PORT", "8080"))
HOST = os.getenv("HEALTH_HOST", "0.0.0.0")


async def health_handler(request: web.Request) -> web.Response:
    """Основной healthcheck эндпоинт."""
    pid = os.getpid()
    process = psutil.Process(pid)
    create_time = datetime.fromtimestamp(process.create_time())
    uptime = datetime.now() - create_time

    # Простейшая проверка состояния БД (опционально)
    db_ok = True
    try:
        # Можно добавить реальный запрос к БД
        pass
    except Exception:
        db_ok = False

    status = {
        "status": "healthy",
        "service": "mysticbot",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "uptime_seconds": uptime.total_seconds(),
        "pid": pid,
        "memory_rss_mb": process.memory_info().rss / 1024 / 1024,
        "cpu_percent": process.cpu_percent(),
        "database": "ok" if db_ok else "unavailable",
    }

    return web.Response(
        text=json.dumps(status, indent=2, ensure_ascii=False),
        content_type="application/json",
    )


async def metrics_handler(request: web.Request) -> web.Response:
    """Заглушка для Prometheus метрик."""
    # В будущем можно добавить реальные метрики (например, через prometheus_client)
    metrics = "# HELP mysticbot_info Information about MysticBot\n"
    metrics += "# TYPE mysticbot_info gauge\n"
    metrics += 'mysticbot_info{version="1.0.0"} 1\n'

    return web.Response(text=metrics, content_type="text/plain; version=0.0.4")


async def root_handler(request: web.Request) -> web.Response:
    """Корневой эндпоинт с краткой информацией."""
    html = """
    <html>
    <head><title>MysticBot Health Server</title></head>
    <body>
    <h1>MysticBot Health Server</h1>
    <p>Сервер мониторинга и healthcheck для Telegram‑бота MysticBot.</p>
    <ul>
    <li><a href="/health">/health</a> — статус бота (JSON)</li>
    <li><a href="/metrics">/metrics</a> — метрики Prometheus</li>
    </ul>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")


def create_app() -> web.Application:
    """Создание aiohttp приложения."""
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/metrics", metrics_handler)
    app.router.add_get("/", root_handler)
    return app


async def start_health_server(
    port: int = DEFAULT_PORT, host: str = HOST
) -> web.TCPSite:
    """
    Запускает healthcheck сервер в фоне.
    Возвращает объект TCPSite (можно использовать для остановки).
    """
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"Healthcheck сервер запущен на http://{host}:{port}")
    return site


async def stop_health_server(runner: web.AppRunner) -> None:
    """Останавливает healthcheck сервер."""
    await runner.cleanup()
    logger.info("Healthcheck сервер остановлен")


async def run_server_forever(port: int = DEFAULT_PORT, host: str = HOST) -> None:
    """Бесконечный цикл запуска сервера (для standalone режима)."""
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"Healthcheck сервер запущен на http://{host}:{port}")
    try:
        await asyncio.Future()  # бесконечное ожидание
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    # Запуск сервера как отдельного приложения (для тестирования)
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_server_forever())
