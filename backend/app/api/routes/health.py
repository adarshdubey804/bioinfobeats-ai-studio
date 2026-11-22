"""Liveness and dependency-aware readiness probes."""
from fastapi import APIRouter, HTTPException
from redis import Redis
from sqlalchemy import text
from app.core.config import settings
from app.db.session import engine

router = APIRouter()


@router.get("/health", tags=["health"])
def health():
    """Backward-compatible liveness endpoint."""
    return {"status": "ok", "service": "bioinfobeats-api"}


@router.get("/health/live", tags=["health"])
def liveness():
    return {"status": "alive", "service": "bioinfobeats-api"}


def _database_ready() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _redis_ready() -> bool:
    client = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
    try:
        return bool(client.ping())
    except Exception:
        return False
    finally:
        client.close()


@router.get("/health/ready", tags=["health"])
def readiness():
    dependencies = {"database": _database_ready(), "redis": _redis_ready()}
    ready = all(dependencies.values())
    if not ready:
        raise HTTPException(status_code=503, detail={"status": "not_ready", "dependencies": dependencies})
    return {"status": "ready", "dependencies": dependencies}
