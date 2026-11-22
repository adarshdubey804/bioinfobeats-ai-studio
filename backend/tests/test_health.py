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
