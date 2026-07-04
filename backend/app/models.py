from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db import Base


class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_text: Mapped[str] = mapped_column(Text)
    asking_price: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    specs: Mapped["NormalizedSpec | None"] = relationship(back_populates="listing", uselist=False, cascade="all, delete-orphan")


class NormalizedSpec(Base):
    __tablename__ = "normalized_specs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    listing: Mapped[Listing] = relationship(back_populates="specs")


class UserCorrection(Base):
    __tablename__ = "user_corrections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id", ondelete="SET NULL"), nullable=True)
    original_payload: Mapped[dict] = mapped_column(JSON)
    corrected_payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PredictionResult(Base):
    __tablename__ = "prediction_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id", ondelete="SET NULL"), nullable=True)
    fair_price: Mapped[float] = mapped_column(Float)
    asking_price: Mapped[float] = mapped_column(Float)
    rating: Mapped[str] = mapped_column(String(32))
    model_version: Mapped[str] = mapped_column(String(128))
    latency_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelMetadata(Base):
    __tablename__ = "model_metadata"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(128))
    version: Mapped[str] = mapped_column(String(128), unique=True)
    metrics: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="candidate")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketObservation(Base):
    """Legacy/raw historical observation table retained for backward compatibility."""

    __tablename__ = "market_observations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(128))
    source_id: Mapped[str] = mapped_column(String(256), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    observed_price: Mapped[float] = mapped_column(Float)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LiveMarketListing(Base):
    """Short-lived normalized cache used for live comparable listings.

    This is deliberately separate from training labels: active asking prices are not completed-sale
    outcomes and should not silently become supervised targets.
    """

    __tablename__ = "live_market_listings"
    __table_args__ = (UniqueConstraint("source", "source_listing_id", name="uq_live_market_source_listing"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    source_listing_id: Mapped[str] = mapped_column(String(256))
    listing_type: Mapped[str] = mapped_column(String(32), default="active")
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    price_cad: Mapped[float] = mapped_column(Float, index=True)
    condition: Mapped[str] = mapped_column(String(32), default="good")
    specs_payload: Mapped[dict] = mapped_column(JSON)
    extraction_quality: Mapped[float] = mapped_column(Float, default=0.0)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    listed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class MarketRefreshRun(Base):
    __tablename__ = "market_refresh_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    source_stats: Mapped[dict] = mapped_column(JSON, default=dict)
    quality_stats: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
