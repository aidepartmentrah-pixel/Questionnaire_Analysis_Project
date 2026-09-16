from fastapi.testclient import TestClient


def test_health_returns_200_with_stable_payload(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["app_name"], str) and body["app_name"]
    assert isinstance(body["environment"], str) and body["environment"]
    assert isinstance(body["version"], str) and body["version"]
