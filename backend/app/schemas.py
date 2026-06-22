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
