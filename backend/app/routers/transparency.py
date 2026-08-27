from __future__ import annotations

import base64
import json
from pathlib import Path

import pandas as pd
from fastapi import APIRouter

from backend.app.config import get_settings
from backend.app.schemas import EvaluationFigure, ModelPerformanceResponse
from ml.training.visualization import PRICE_BAND_LABELS

router = APIRouter(prefix="/model-performance", tags=["model transparency"])

ALT = {
    "predicted_vs_actual": "Held-out actual prices plotted against model predictions with an ideal diagonal reference line.",
    "error_by_price_band": "Held-out mean absolute error for PCs under $800, from $800 to $1,800, and over $1,800, with sample counts.",
}


@router.get("", response_model=ModelPerformanceResponse)
def model_performance() -> ModelPerformanceResponse:
    settings = get_settings()
    try:
        metadata = json.loads(settings.model_metadata_path.read_text())
    except (OSError, json.JSONDecodeError):
        return ModelPerformanceResponse(
            available=False, note="Held-out evaluation metadata is unavailable."
        )
    version = str(metadata.get("model_version", ""))
    figures = []
    manifest = metadata.get("evaluation_figures", {})
    for key in ("predicted_vs_actual", "error_by_price_band"):
        item = manifest.get(key, {}) if isinstance(manifest, dict) else {}
        path = Path(str(item.get("path", "")))
        try:
            in_report_dir = path.resolve().is_relative_to(settings.evaluation_report_dir.resolve())
        except OSError:
            in_report_dir = False
        if (
            item.get("model_version") != version
            or not in_report_dir
            or not path.is_file()
            or path.suffix != ".svg"
        ):
            continue
        try:
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError:
            continue
        figures.append(
            EvaluationFigure(key=key, data_uri=f"data:image/svg+xml;base64,{encoded}", alt=ALT[key])
        )
    bands = []
    error_path = settings.evaluation_report_dir / "error_analysis.csv"
    if error_path.exists():
        errors = pd.read_csv(error_path)
        for row in errors[errors.segment.eq("price_band")].itertuples():
            bands.append(
                {
                    "band": str(row.value),
                    "label": PRICE_BAND_LABELS.get(str(row.value), str(row.value)),
                    "count": int(row.count),
                    "mae": round(float(row.mae), 2),
                }
            )
    count = int(metadata.get("split_counts", {}).get("test", 0))
    available = len(figures) == 2
    return ModelPerformanceResponse(
        available=available,
        model_version=version,
        data_scope=str(metadata.get("data_scope", "unknown")),
        target_definition=str(metadata.get("target_definition", "unknown")),
        sample_count=count,
        mae=metadata.get("validation_mae"),
        rmse=metadata.get("validation_rmse"),
        r2=metadata.get("validation_r2"),
        price_bands=bands if available else [],
        figures=figures if available else [],
        note="Metrics and figures use the untouched held-out evaluation split; live comparable asks are not included."
        if available
        else "Matching held-out figures are unavailable for this model version.",
    )
