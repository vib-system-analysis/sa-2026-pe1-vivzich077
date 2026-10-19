from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_describes_stub_service() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"name": "ai-test-writer", "status": "stub"}


def test_health_check_is_ready() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
