from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from ml.market_sources.google_shopping import GoogleShoppingSource
from backend.app.config import Settings, get_settings
from backend.app.db import Base, engine
from backend.app.models import LiveMarketListing, MarketRefreshRun
from backend.app.services.extraction import extract_listing
from ml.market_sources.base import MarketSource, MarketSourceError, SourceListing
from ml.market_sources.bestbuy import BestBuySource
from ml.market_sources.ebay import EbayBrowseSource
from ml.market_sources.fx import FxConverter


@dataclass
class RefreshSummary:
    status: str
    sources: dict[str, int]
    quality: dict[str, int]
    errors: dict[str, str]

    def as_dict(self) -> dict[str, object]:
        return {"status": self.status, "sources": self.sources, "quality": self.quality, "errors": self.errors}


def _source_adapters(settings: Settings) -> list[MarketSource]:
    sources: list[MarketSource] = []

    if settings.ebay_client_id and settings.ebay_client_secret:
        sources.append(EbayBrowseSource(settings))

    if settings.serpapi_api_key:
        sources.append(GoogleShoppingSource(settings))

    if settings.bestbuy_api_key:
        sources.append(BestBuySource(settings))

    return sources

def _fingerprint(item: SourceListing, specs: dict[str, object], price_cad: float) -> str:
    identity = {
        "cpu": specs.get("cpu"),
        "gpu": specs.get("gpu"),
        "ram_gb": specs.get("ram_gb"),
        "storage_gb": specs.get("storage_gb"),
        "condition": specs.get("condition"),
        "price_bucket": round(price_cad / 25) * 25,
        "title": " ".join(item.title.lower().split()),
    }
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def _quality_score(specs: dict[str, object]) -> float:
    weights = {"cpu": 0.34, "gpu": 0.38, "ram_gb": 0.12, "storage_gb": 0.10, "ram_type": 0.03, "storage_type": 0.03}
    return round(sum(weight for field, weight in weights.items() if specs.get(field)), 3)


def _normalized_row(item: SourceListing, converter: FxConverter, settings: Settings) -> dict[str, object] | None:
    if item.price <= 0 or not item.title.strip():
        return None
    price_cad = converter.to_cad(item.price, item.currency)
    if not 75 <= price_cad <= 30000:
        return None
    source_text = "\n".join(part for part in [item.title, item.summary or ""] if part)
    extracted = extract_listing(source_text)
    specs = extracted.model_dump(exclude={"asking_price", "extraction_warnings", "normalization_failures"})
    # Provider condition is authoritative when the source supplies it (for example Best Buy new/open-box).
    specs["condition"] = item.condition or specs.get("condition") or "good"
    # A usable comparable needs at least one major compute component. Low-quality rows are retained
    # only when they still contain enough structure to be useful for monitoring.
    if not specs.get("cpu") and not specs.get("gpu"):
        return None
    now = datetime.now(UTC)
    return {
        "source": item.source,
        "source_listing_id": item.source_listing_id,
        "listing_type": item.listing_type,
        "title": item.title[:2000],
        "summary": (item.summary or "")[:4000] or None,
        "url": item.url,
        "image_url": item.image_url,
        "price": float(item.price),
        "currency": item.currency.upper(),
        "price_cad": round(price_cad, 2),
        "condition": item.condition,
        "specs_payload": specs,
        "extraction_quality": _quality_score(specs),
        "fingerprint": _fingerprint(item, specs, price_cad),
        "listed_at": item.listed_at,
        "last_seen_at": now,
        "expires_at": now + timedelta(hours=settings.market_cache_ttl_hours),
        "active": True,
    }


def refresh_live_market(
    db: Session,
    settings: Settings | None = None,
    sources: list[MarketSource] | None = None,
    report_path: Path | None = Path("reports/live_market_quality.json"),
) -> RefreshSummary:
    settings = settings or get_settings()
    adapters = sources if sources is not None else _source_adapters(settings)
    converter = FxConverter(settings)
    run = MarketRefreshRun(status="running", source_stats={}, quality_stats={})
    db.add(run)
    db.commit()
    db.refresh(run)

    source_counts: dict[str, int] = {}
    errors: dict[str, str] = {}
    quality = {
        "fetched": 0,
        "accepted": 0,
        "rejected": 0,
        "duplicate_fingerprints": 0,
        "inserted": 0,
        "updated": 0,
        "purged": 0,
    }
    seen_fingerprints: set[str] = set()

    try:
        for adapter in adapters:
            try:
                raw_items = adapter.fetch()
            except Exception as exc:  # Source failures must not erase healthy feeds.
                errors[adapter.name] = str(exc)
                source_counts[adapter.name] = 0
                continue
            source_counts[adapter.name] = len(raw_items)
            quality["fetched"] += len(raw_items)
            for item in raw_items:
                try:
                    row = _normalized_row(item, converter, settings)
                except MarketSourceError as exc:
                    errors[item.source] = str(exc)
                    quality["rejected"] += 1
                    continue
                if row is None:
                    quality["rejected"] += 1
                    continue
                fingerprint = str(row["fingerprint"])
                if fingerprint in seen_fingerprints:
                    quality["duplicate_fingerprints"] += 1
                    continue
                seen_fingerprints.add(fingerprint)
                existing = db.scalar(
                    select(LiveMarketListing).where(
                        LiveMarketListing.source == row["source"],
                        LiveMarketListing.source_listing_id == row["source_listing_id"],
                    )
                )
                if existing is None:
                    db.add(LiveMarketListing(**row))
                    quality["inserted"] += 1
                else:
                    for field, value in row.items():
                        setattr(existing, field, value)
                    quality["updated"] += 1
                quality["accepted"] += 1
        db.commit()

        now = datetime.now(UTC)
        expired = db.scalars(select(LiveMarketListing).where(LiveMarketListing.expires_at < now)).all()
        quality["purged"] = len(expired)
        if expired:
            db.execute(delete(LiveMarketListing).where(LiveMarketListing.expires_at < now))
            db.commit()

        if not adapters:
            status = "no_sources_configured"
        elif errors and quality["accepted"]:
            status = "partial"
        elif errors:
            status = "failed"
        else:
            status = "success"
        run.status = status
        run.finished_at = datetime.now(UTC)
        run.source_stats = source_counts
        run.quality_stats = quality
        run.error_message = "; ".join(f"{key}: {value}" for key, value in errors.items()) or None
        db.commit()
        summary = RefreshSummary(status=status, sources=source_counts, quality=quality, errors=errors)
        if report_path is not None:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(summary.as_dict(), indent=2, default=str))
        return summary
    except Exception as exc:
        db.rollback()
        run = db.get(MarketRefreshRun, run.id)
        if run:
            run.status = "failed"
            run.finished_at = datetime.now(UTC)
            run.error_message = str(exc)
            db.commit()
        raise


def refresh_with_app_database(settings: Settings | None = None) -> RefreshSummary:
    settings = settings or get_settings()
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        return refresh_live_market(db, settings=settings)
