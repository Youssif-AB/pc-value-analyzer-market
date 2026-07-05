from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.db import get_db
from backend.app.models import LiveMarketListing, MarketRefreshRun
from backend.app.observability import LIVE_MARKET_CACHE
from backend.app.schemas import (
    MarketBrowseResponse,
    MarketListingItem,
    MarketRefreshResponse,
    MarketSourceStatus,
    MarketStatusResponse,
    NormalizedSpecs,
)
from ml.pipeline.live_market import refresh_live_market

router = APIRouter(prefix="/market", tags=["market"])
settings = get_settings()


@router.get("/status", response_model=MarketStatusResponse)
def market_status(db: Session = Depends(get_db)) -> MarketStatusResponse:
    now = datetime.now(UTC)
    total = db.scalar(
        select(func.count()).select_from(LiveMarketListing).where(
            LiveMarketListing.active.is_(True),
            LiveMarketListing.expires_at >= now,
        )
    ) or 0
    source_rows: list[MarketSourceStatus] = []
    for source in ["ebay", "bestbuy"]:
        count = db.scalar(
            select(func.count()).select_from(LiveMarketListing).where(
                LiveMarketListing.source == source,
                LiveMarketListing.active.is_(True),
                LiveMarketListing.expires_at >= now,
            )
        ) or 0
        newest = db.scalar(
            select(func.max(LiveMarketListing.last_seen_at)).where(
                LiveMarketListing.source == source,
                LiveMarketListing.active.is_(True),
            )
        )
        LIVE_MARKET_CACHE.labels(source=source).set(int(count))
        source_rows.append(
            MarketSourceStatus(
                source=source,
                configured=source in settings.configured_market_sources,
                active_observations=int(count),
                newest_observation_at=newest,
            )
        )
    last_run = db.scalar(select(MarketRefreshRun).order_by(MarketRefreshRun.started_at.desc()).limit(1))
    return MarketStatusResponse(
        live_market_enabled=settings.live_market_enabled,
        target_currency=settings.market_currency,
        total_active_observations=int(total),
        sources=source_rows,
        last_refresh_status=last_run.status if last_run else None,
        last_refresh_at=(last_run.finished_at or last_run.started_at) if last_run else None,
    )


@router.get("/listings", response_model=MarketBrowseResponse)
def market_listings(
    q: str | None = Query(default=None, max_length=120),
    source: str | None = Query(default=None, max_length=32),
    condition: str | None = Query(default=None, max_length=32),
    listing_type: str | None = Query(default=None, max_length=32),
    min_price: float | None = Query(default=None, ge=0, le=100000),
    max_price: float | None = Query(default=None, ge=0, le=100000),
    sort: Literal["newest", "price_asc", "price_desc", "quality"] = "newest",
    limit: int = Query(default=24, ge=1, le=60),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> MarketBrowseResponse:
    """Browse the current normalized market cache used by the valuation service."""

    now = datetime.now(UTC)
    filters = [LiveMarketListing.active.is_(True), LiveMarketListing.expires_at >= now]
    if q and q.strip():
        term = f"%{q.strip()}%"
        filters.append(or_(LiveMarketListing.title.ilike(term), LiveMarketListing.summary.ilike(term)))
    if source and source != "all":
        filters.append(LiveMarketListing.source == source)
    if condition and condition != "all":
        filters.append(LiveMarketListing.condition == condition)
    if listing_type and listing_type != "all":
        filters.append(LiveMarketListing.listing_type == listing_type)
    if min_price is not None:
        filters.append(LiveMarketListing.price_cad >= min_price)
    if max_price is not None:
        filters.append(LiveMarketListing.price_cad <= max_price)

    total = db.scalar(select(func.count()).select_from(LiveMarketListing).where(*filters)) or 0
    order_by = {
        "newest": (desc(LiveMarketListing.last_seen_at), desc(LiveMarketListing.id)),
        "price_asc": (asc(LiveMarketListing.price_cad), desc(LiveMarketListing.last_seen_at)),
        "price_desc": (desc(LiveMarketListing.price_cad), desc(LiveMarketListing.last_seen_at)),
        "quality": (desc(LiveMarketListing.extraction_quality), desc(LiveMarketListing.last_seen_at)),
    }[sort]
    rows = db.scalars(
        select(LiveMarketListing)
        .where(*filters)
        .order_by(*order_by)
        .offset(offset)
        .limit(limit)
    ).all()

    items = [
        MarketListingItem(
            id=row.id,
            source=row.source,
            source_listing_id=row.source_listing_id,
            listing_type=row.listing_type,
            title=row.title,
            summary=row.summary,
            url=row.url,
            image_url=row.image_url,
            price=row.price,
            currency=row.currency,
            price_cad=row.price_cad,
            condition=row.condition,
            specs=NormalizedSpecs.model_validate(row.specs_payload),
            extraction_quality=row.extraction_quality,
            listed_at=row.listed_at,
            last_seen_at=row.last_seen_at,
        )
        for row in rows
    ]
    next_offset = offset + len(items) if offset + len(items) < int(total) else None
    return MarketBrowseResponse(items=items, total=int(total), limit=limit, offset=offset, next_offset=next_offset)


@router.post("/refresh", response_model=MarketRefreshResponse)
def market_refresh(
    x_market_refresh_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> MarketRefreshResponse:
    expected = settings.market_refresh_token
    if not expected:
        raise HTTPException(status_code=503, detail="MARKET_REFRESH_TOKEN is not configured; use the Prefect refresh deployment instead.")
    if x_market_refresh_token != expected:
        raise HTTPException(status_code=401, detail="Invalid market refresh token")
    summary = refresh_live_market(db, settings=settings)
    return MarketRefreshResponse(status=summary.status, sources=summary.sources, quality=summary.quality)
