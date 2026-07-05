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
    assert body["live_market"]["valuation_method"] in {"model_only", "hybrid_live_comps"}
    assert "blend_weight" in body["live_market"]


def test_malformed_prediction_rejected() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json={"asking_price": -1, "specs": {}})
    assert response.status_code == 422


def test_market_status_api_returns_source_state() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/market/status")
    assert response.status_code == 200
    body = response.json()
    assert body["target_currency"] == "CAD"
    assert {source["source"] for source in body["sources"]} == {"ebay", "bestbuy"}


def test_market_browse_api_filters_and_pages() -> None:
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    from backend.app.db import Base, get_db
    from backend.app.models import LiveMarketListing

    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    specs = {
        'cpu': 'AMD Ryzen 7 7800X3D',
        'gpu': 'NVIDIA GeForce RTX 4070',
        'ram_gb': 32,
        'ram_type': 'DDR5',
        'storage_gb': 2048,
        'storage_type': 'NVMe SSD',
        'condition': 'good',
        'brand': 'custom',
        'system_age_years': 1.0,
    }
    with Session(engine) as db:
        for index, price in enumerate([1500.0, 1700.0, 1900.0]):
            db.add(LiveMarketListing(
                source='ebay' if index < 2 else 'bestbuy',
                source_listing_id=f'browse-{index}',
                listing_type='active_asking',
                title=f'RTX 4070 gaming PC {index}',
                summary='Ryzen 7 desktop',
                price=price,
                currency='CAD',
                price_cad=price,
                condition='good',
                specs_payload=specs,
                extraction_quality=0.95,
                fingerprint=f'browse-f{index}',
                last_seen_at=now - timedelta(minutes=index),
                expires_at=now + timedelta(hours=24),
                active=True,
            ))
        db.commit()

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.get('/api/v1/market/listings', params={'q': 'RTX 4070', 'source': 'ebay', 'sort': 'price_asc', 'limit': 1})
        assert response.status_code == 200
        body = response.json()
        assert body['total'] == 2
        assert len(body['items']) == 1
        assert body['items'][0]['price_cad'] == 1500.0
        assert body['items'][0]['specs']['gpu'] == 'NVIDIA GeForce RTX 4070'
        assert body['next_offset'] == 1
    finally:
        app.dependency_overrides.pop(get_db, None)
