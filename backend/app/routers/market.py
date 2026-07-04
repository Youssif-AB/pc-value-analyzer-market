from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.db import get_db
from backend.app.models import LiveMarketListing, MarketRefreshRun
from backend.app.observability import LIVE_MARKET_CACHE
from backend.app.schemas import MarketRefreshResponse, MarketSourceStatus, MarketStatusResponse
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
