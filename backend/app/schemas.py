from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Condition = Literal["new", "like_new", "excellent", "good", "fair", "parts"]
ValueRating = Literal["GREAT DEAL", "GOOD VALUE", "FAIR", "OVERPRICED", "HIGHLY OVERPRICED"]


class ExtractRequest(BaseModel):
    listing_text: str = Field(min_length=20, max_length=12000)


class NormalizedSpecs(BaseModel):
    cpu: str | None = None
    gpu: str | None = None
    ram_gb: int | None = Field(default=None, ge=2, le=512)
    ram_type: str | None = None
    storage_gb: int | None = Field(default=None, ge=32, le=32768)
    storage_type: str | None = None
    condition: Condition = "good"
    brand: str | None = None
    system_age_years: float | None = Field(default=None, ge=0, le=20)


class ExtractedSpecs(NormalizedSpecs):
    asking_price: float | None = Field(default=None, ge=0, le=100000)
    extraction_warnings: list[str] = Field(default_factory=list)
    normalization_failures: list[str] = Field(default_factory=list)


class PredictRequest(BaseModel):
    specs: NormalizedSpecs
    asking_price: float = Field(gt=0, le=100000)
    source_listing: str | None = Field(default=None, max_length=12000)


class FeatureContribution(BaseModel):
    feature: str
    direction: Literal["up", "down", "neutral"]
    explanation: str


class MarketComparable(BaseModel):
    source: str
    title: str
    price_cad: float
    condition: str
    similarity: float = Field(ge=0, le=1)
    url: str | None = None
    observed_at: datetime | None = None


class LiveMarketEvidence(BaseModel):
    enabled: bool
    comp_count: int = 0
    source_count: int = 0
    sources: list[str] = Field(default_factory=list)
    median_asking_price_cad: float | None = None
    adjusted_market_estimate_cad: float | None = None
    blend_weight: float = Field(default=0, ge=0, le=1)
    newest_observation_at: datetime | None = None
    valuation_method: Literal["model_only", "hybrid_live_comps"] = "model_only"
    comparables: list[MarketComparable] = Field(default_factory=list)
    note: str = "Active asking-price comparables are market evidence, not completed-sale ground truth."


class PredictionResponse(BaseModel):
    estimated_fair_price: float
    asking_price: float
    difference_percent: float
    rating: ValueRating
    lower_bound: float
    upper_bound: float
    model_version: str
    confidence: Literal["low", "medium", "high"]
    drivers: list[FeatureContribution]
    warnings: list[str]
    live_market: LiveMarketEvidence


class AnalyzeRequest(ExtractRequest):
    pass


class AnalyzeResponse(BaseModel):
    extracted: ExtractedSpecs
    ready_for_prediction: bool


class CorrectionRequest(BaseModel):
    original_specs: NormalizedSpecs
    corrected_specs: NormalizedSpecs
    source_listing: str | None = Field(default=None, max_length=12000)

    @field_validator("corrected_specs")
    @classmethod
    def require_key_hardware(cls, value: NormalizedSpecs) -> NormalizedSpecs:
        if not value.cpu and not value.gpu:
            raise ValueError("At least one of CPU or GPU must be supplied after correction")
        return value


class MarketListingItem(BaseModel):
    id: int
    source: str
    source_listing_id: str
    listing_type: str
    title: str
    summary: str | None = None
    url: str | None = None
    image_url: str | None = None
    price: float
    currency: str
    price_cad: float
    condition: str
    specs: NormalizedSpecs
    extraction_quality: float = Field(ge=0, le=1)
    listed_at: datetime | None = None
    last_seen_at: datetime


class MarketBrowseResponse(BaseModel):
    items: list[MarketListingItem]
    total: int
    limit: int
    offset: int
    next_offset: int | None = None


class MarketSourceStatus(BaseModel):
    source: str
    configured: bool
    active_observations: int
    newest_observation_at: datetime | None = None


class MarketStatusResponse(BaseModel):
    live_market_enabled: bool
    target_currency: str
    total_active_observations: int
    sources: list[MarketSourceStatus]
    last_refresh_status: str | None = None
    last_refresh_at: datetime | None = None


class MarketRefreshResponse(BaseModel):
    status: str
    sources: dict[str, int]
    quality: dict[str, int]
