from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.db import Base
from backend.app.models import Listing, NormalizedSpec, PredictionResult, UserCorrection


def test_database_entities_persist_together() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        listing = Listing(raw_text="RTX 4070 gaming PC", asking_price=1650)
        listing.specs = NormalizedSpec(payload={"gpu": "NVIDIA GeForce RTX 4070", "ram_gb": 32})
        db.add(listing)
        db.flush()
        db.add(UserCorrection(listing_id=listing.id, original_payload={"ram_gb": 16}, corrected_payload={"ram_gb": 32}))
        db.add(PredictionResult(listing_id=listing.id, fair_price=1820, asking_price=1650, rating="GOOD VALUE", model_version="test", latency_ms=12.5))
        db.commit()

        stored = db.scalar(select(Listing).where(Listing.id == listing.id))
        assert stored is not None
        assert stored.specs is not None
        assert stored.specs.payload["ram_gb"] == 32
        assert db.scalar(select(UserCorrection).where(UserCorrection.listing_id == listing.id)) is not None
        assert db.scalar(select(PredictionResult).where(PredictionResult.listing_id == listing.id)) is not None
