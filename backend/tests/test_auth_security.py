from fastapi.testclient import TestClient
from app.main import app

def test_protected_agents_requires_bearer_token():
    response = TestClient(app).get("/api/v1/agents")
    assert response.status_code == 401
