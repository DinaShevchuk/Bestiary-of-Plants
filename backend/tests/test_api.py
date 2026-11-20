from dataclasses import replace

from fastapi.testclient import TestClient

from backend.app import main
from backend.app.main import app, service

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_endpoint():
    response = client.get("/api/v1/search", params={"q": "венерина мухоловка", "limit": 3})
    assert response.status_code == 200
    assert response.json()["results"]
    assert response.json()["results"][0]["document_id"] == "plant-dionaea-001"


def test_ask_endpoint_returns_sources():
    response = client.post("/api/v1/ask", json={"query": "Что такое росянка?", "limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["sources"]


def test_empty_query_is_rejected_by_validation():
    response = client.post("/api/v1/ask", json={"query": "   "})
    assert response.status_code == 422


def test_whitespace_search_query_is_rejected():
    response = client.get("/api/v1/search", params={"q": "   "})
    assert response.status_code == 422


def test_plant_profile_endpoint():
    response = client.get("/api/v1/plants/plant-dionaea-001")
    assert response.status_code == 200
    assert response.json()["plant_name"] == "Венерина мухоловка"


def test_identification_reports_missing_api_configuration():
    if not service.settings.plantnet_api_key:
        response = client.post("/api/v1/identify", files={"image": ("plant.jpg", b"not-an-image", "image/jpeg")})
        assert response.status_code == 503


def test_identification_rejects_mime_spoofed_image_before_provider_call(monkeypatch):
    monkeypatch.setattr(main, "settings", replace(main.settings, plantnet_api_key="test-key"))
    response = client.post("/api/v1/identify", files={"image": ("plant.jpg", b"not-a-jpeg", "image/jpeg")})
    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "INVALID_IMAGE_CONTENT"
