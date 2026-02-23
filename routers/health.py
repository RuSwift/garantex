"""
Роутер для health / liveness / readiness.
Все ручки под префиксом /health для удобного ограничения в reverse proxy (location /health/).
"""
from fastapi import APIRouter, Depends, Response
from redis.asyncio import Redis
from sqlalchemy import text

from dependencies import SettingsDepends
import db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health():
    """Проверка здоровья приложения (обратная совместимость)."""
    return {"status": "ok"}


@router.get("/live")
async def live():
    """Liveness: процесс жив, без проверки зависимостей."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(settings: SettingsDepends, response: Response):
    """Readiness: проверка PostgreSQL и Redis. При ошибке — 503."""
    errors = []

    if db.SessionLocal is None:
        errors.append("postgres: database not initialized")
    else:
        try:
            async with db.SessionLocal() as session:
                await session.execute(text("SELECT 1"))
        except Exception as e:
            errors.append(f"postgres: {e!s}")

    try:
        client = Redis.from_url(settings.redis.url, decode_responses=True)
        try:
            await client.ping()
        finally:
            await client.aclose()
    except Exception as e:
        errors.append(f"redis: {e!s}")

    if errors:
        response.status_code = 503
        return {"status": "unhealthy", "detail": "; ".join(errors)}

    return {"status": "ok"}
