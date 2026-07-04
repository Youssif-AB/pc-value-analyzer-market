from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.config import Settings
from backend.app.db import Base
from backend.app.models import LiveMarketListing
from backend.app.schemas import NormalizedSpecs
from backend.app.services.live_market import LiveMarketService
from ml.market_sources.base import SourceListing
from ml.pipeline.live_market import refresh_live_market


class FakeSource:
    name = 'fake'

    def fetch(self) -> list[SourceListing]:
        return [
            SourceListing(
                source='fake',
                source_listing_id='1',
                title='Ryzen 7 9800X3D RTX 5070 32GB DDR5 2TB NVMe gaming PC',
                summary='Excellent condition',
                price=2000,
                currency='USD',
                condition='excellent',
            ),
            SourceListing(
                source='fake',
                source_listing_id='2',
                title='Ryzen 5 5600X RTX 3060 16GB DDR4 1TB SSD gaming PC',
                price=700,
                currency='USD',
                condition='good',
            ),
        ]


def test_live_market_refresh_normalizes_and_converts() -> None:
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    settings = Settings(usd_to_cad_override=1.4, market_cache_ttl_hours=24)
    with Session(engine) as db:
        summary = refresh_live_market(db, settings=settings, sources=[FakeSource()], report_path=None)
        rows = db.scalars(select(LiveMarketListing)).all()
    assert summary.status == 'success'
    assert summary.quality['accepted'] == 2
    assert len(rows) == 2
    assert rows[0].price_cad == 2800
    assert rows[0].specs_payload['gpu'] == 'NVIDIA GeForce RTX 5070'
    assert rows[0].specs_payload['condition'] == 'excellent'


def test_live_market_service_selects_similar_comps_and_blends() -> None:
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    target = NormalizedSpecs(
        cpu='AMD Ryzen 7 9800X3D',
        gpu='NVIDIA GeForce RTX 5070',
        ram_gb=32,
        ram_type='DDR5',
        storage_gb=2048,
        storage_type='NVMe SSD',
        condition='good',
        brand='custom',
        system_age_years=0.5,
    )
    specs = target.model_dump()
    with Session(engine) as db:
        for index, (source, price) in enumerate([
            ('ebay', 2200.0), ('ebay', 2250.0), ('bestbuy', 2400.0), ('bestbuy', 2350.0)
        ]):
            db.add(LiveMarketListing(
                source=source,
                source_listing_id=str(index),
                listing_type='active_asking',
                title=f'Comparable {index}',
                price=price,
                currency='CAD',
                price_cad=price,
                condition='good',
                specs_payload=specs,
                extraction_quality=1.0,
                fingerprint=f'f{index}',
                last_seen_at=now,
                expires_at=now + timedelta(hours=24),
                active=True,
            ))
        db.commit()
        evidence = LiveMarketService(Settings(live_comp_min_similarity=0.5)).evidence(
            db,
            target=target,
            target_baseline=2300,
            baseline_predictor=lambda _: 2300,
        )
    assert evidence.comp_count == 4
    assert evidence.source_count == 2
    assert evidence.blend_weight > 0
    assert evidence.adjusted_market_estimate_cad is not None
