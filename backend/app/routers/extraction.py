from fastapi import APIRouter

from backend.app.observability import EXTRACTION_FAILURES, NORMALIZATION_FAILURES
from backend.app.schemas import AnalyzeRequest, AnalyzeResponse, ExtractRequest, ExtractedSpecs
from backend.app.services.extraction import extract_listing

router = APIRouter(prefix="/extract", tags=["extraction"])


def _record_failures(result: ExtractedSpecs) -> None:
    for field in ("cpu", "gpu", "ram_gb", "storage_gb"):
        if getattr(result, field) is None:
            EXTRACTION_FAILURES.labels(field=field).inc()
    for failure in result.normalization_failures:
        component = "cpu" if "CPU" in failure else "gpu"
        NORMALIZATION_FAILURES.labels(component=component).inc()


@router.post("", response_model=ExtractedSpecs)
def extract(request: ExtractRequest) -> ExtractedSpecs:
    result = extract_listing(request.listing_text)
    _record_failures(result)
    return result


@router.post("/review", response_model=AnalyzeResponse)
def review(request: AnalyzeRequest) -> AnalyzeResponse:
    result = extract_listing(request.listing_text)
    _record_failures(result)
    ready = result.cpu is not None and result.gpu is not None and result.asking_price is not None
    return AnalyzeResponse(extracted=result, ready_for_prediction=ready)
