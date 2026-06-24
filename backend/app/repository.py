from sqlalchemy.orm import Session

from backend.app.models import Listing, NormalizedSpec, PredictionResult, UserCorrection
from backend.app.schemas import CorrectionRequest, ExtractedSpecs, PredictionResponse


def save_listing(db: Session, raw_text: str, extracted: ExtractedSpecs) -> Listing:
    listing = Listing(raw_text=raw_text, asking_price=extracted.asking_price)
    listing.specs = NormalizedSpec(payload=extracted.model_dump(exclude={"asking_price", "extraction_warnings", "normalization_failures"}))
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def save_correction(db: Session, correction: CorrectionRequest, listing_id: int | None = None) -> UserCorrection:
    row = UserCorrection(listing_id=listing_id, original_payload=correction.original_specs.model_dump(), corrected_payload=correction.corrected_specs.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def save_prediction(db: Session, prediction: PredictionResponse, listing_id: int | None, latency_ms: float) -> PredictionResult:
    row = PredictionResult(listing_id=listing_id, fair_price=prediction.estimated_fair_price, asking_price=prediction.asking_price, rating=prediction.rating, model_version=prediction.model_version, latency_ms=latency_ms)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
