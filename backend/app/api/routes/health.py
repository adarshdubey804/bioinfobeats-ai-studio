"""Liveness and dependency-aware readiness probes."""
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from app.models.user import User
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


def provider_configuration():
    """Report configuration presence only; this does not make paid provider calls."""
    checks = {
        "llm": bool(settings.llm_api_key),
        "web_research_tavily": bool(settings.tavily_api_key),
        "youtube_data_api": bool(settings.youtube_api_key),
        "elevenlabs_tts": bool(settings.elevenlabs_api_key and settings.elevenlabs_voice_id),
        "openai_image_generation": bool(settings.openai_api_key),
        "replicate_motion_video": bool(settings.replicate_api_token and settings.replicate_video_model_version),
        "buffer_publishing": bool(settings.buffer_access_token),
        "google_youtube_analytics": bool(settings.google_oauth_client_id and settings.google_oauth_client_secret and settings.oauth_token_encryption_key),
    }
    required_for_core = ["llm", "web_research_tavily", "elevenlabs_tts", "openai_image_generation"]
    missing = [name for name in required_for_core if not checks[name]]
    return {
        "providers": {name: {"configured": configured} for name, configured in checks.items()},
        "core_missing": missing,
        "core_ready": not missing,
        "note": "Configuration presence only. Credentials, quotas, model access and live provider connectivity have not been tested.",
    }


@router.get("/health/providers", tags=["health"])
def provider_readiness(user: User = Depends(get_current_user)):
    return provider_configuration()
