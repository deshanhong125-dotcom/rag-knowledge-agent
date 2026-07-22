from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "rag-agent-api",
    }


def test_openapi_contains_public_routes() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/chat" in paths
    assert "/sessions" in paths
    assert "/documents" in paths
