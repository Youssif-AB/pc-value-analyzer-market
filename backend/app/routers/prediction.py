from time import perf_counter

from fastapi import APIRouter, HTTPException

from backend.app.observability import PREDICTIONS, PREDICTION_LATENCY
from backend.app.schemas import PredictRequest, PredictionResponse
from backend.app.services.model_service import ModelService

router = APIRouter(prefix="/predict", tags=["prediction"])
model_service = ModelService()


@router.post("", response_model=PredictionResponse)
def predict(request: PredictRequest) -> PredictionResponse:
    started = perf_counter()
    try:
        result = model_service.predict(request.specs, request.asking_price)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    PREDICTION_LATENCY.observe(perf_counter() - started)
    PREDICTIONS.labels(rating=result.rating, confidence=result.confidence).inc()
    return result
