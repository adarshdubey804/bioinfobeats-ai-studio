from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import health

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_liveness_endpoint():
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_reports_unavailable_dependencies(monkeypatch):
    monkeypatch.setattr(health, "_database_ready", lambda: True)
    monkeypatch.setattr(health, "_redis_ready", lambda: False)
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["detail"]["dependencies"] == {"database": True, "redis": False}


def test_readiness_when_dependencies_are_healthy(monkeypatch):
    monkeypatch.setattr(health, "_database_ready", lambda: True)
    monkeypatch.setattr(health, "_redis_ready", lambda: True)
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_provider_configuration_reports_missing_core_without_secrets(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "tavily_api_key", "configured-secret")
    monkeypatch.setattr(settings, "elevenlabs_api_key", "")
    monkeypatch.setattr(settings, "elevenlabs_voice_id", "voice-id")
    monkeypatch.setattr(settings, "openai_api_key", "image-secret")
    result = health.provider_configuration()
    assert result["core_ready"] is False
    assert set(result["core_missing"]) == {"llm", "elevenlabs_tts"}
    assert "configured-secret" not in str(result)
    assert "image-secret" not in str(result)


def test_provider_configuration_marks_core_ready_when_required_keys_exist(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_api_key", "llm-secret")
    monkeypatch.setattr(settings, "tavily_api_key", "tavily-secret")
    monkeypatch.setattr(settings, "elevenlabs_api_key", "tts-secret")
    monkeypatch.setattr(settings, "elevenlabs_voice_id", "voice-id")
    monkeypatch.setattr(settings, "openai_api_key", "image-secret")
    result = health.provider_configuration()
    assert result["core_ready"] is True
    assert result["core_missing"] == []
    assert result["providers"]["replicate_motion_video"]["configured"] is False
