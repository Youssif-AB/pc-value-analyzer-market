from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.observability import LIVE_MARKET_BLEND, LIVE_MARKET_COMPS, PREDICTIONS, PREDICTION_LATENCY
from backend.app.schemas import PredictRequest, PredictionResponse
from backend.app.services.valuation_service import ValuationService

router = APIRouter(prefix="/predict", tags=["prediction"])
valuation_service = ValuationService()


@router.post("", response_model=PredictionResponse)
def predict(request: PredictRequest, db: Session = Depends(get_db)) -> PredictionResponse:
    started = perf_counter()
    try:
        result = valuation_service.predict(db, request.specs, request.asking_price)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    PREDICTION_LATENCY.observe(perf_counter() - started)
    PREDICTIONS.labels(rating=result.rating, confidence=result.confidence).inc()
    LIVE_MARKET_COMPS.observe(result.live_market.comp_count)
    LIVE_MARKET_BLEND.observe(result.live_market.blend_weight)
    return result
