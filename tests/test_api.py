from fastapi.testclient import TestClient

from backend.app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_prediction_api_returns_explanation() -> None:
    payload = {
        "asking_price": 1650,
        "specs": {
            "cpu": "AMD Ryzen 7 7800X3D",
            "gpu": "NVIDIA GeForce RTX 4070",
            "ram_gb": 32,
            "ram_type": "DDR5",
            "storage_gb": 2048,
            "storage_type": "NVMe SSD",
            "condition": "good",
            "brand": "custom",
            "system_age_years": 1.0,
        },
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["estimated_fair_price"] > 0
    assert body["rating"] in {"GREAT DEAL", "GOOD VALUE", "FAIR", "OVERPRICED", "HIGHLY OVERPRICED"}
    assert body["lower_bound"] < body["upper_bound"]
    assert body["drivers"]


def test_malformed_prediction_rejected() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json={"asking_price": -1, "specs": {}})
    assert response.status_code == 422
