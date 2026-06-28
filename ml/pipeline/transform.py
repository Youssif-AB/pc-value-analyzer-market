from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.app.services.features import CONDITION_SCORE, CPU_SCORE, GPU_SCORE
from backend.app.services.normalization import normalize_cpu, normalize_gpu, normalize_ram_type, normalize_storage_type
from ml.pipeline.quality import validate_market_data


def normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["cpu"] = result["cpu"].map(lambda x: normalize_cpu(None if pd.isna(x) else str(x)).value)
    result["gpu"] = result["gpu"].map(lambda x: normalize_gpu(None if pd.isna(x) else str(x)).value)
    result["ram_type"] = result["ram_type"].map(lambda x: normalize_ram_type(None if pd.isna(x) else str(x)))
    result["storage_type"] = result["storage_type"].map(lambda x: normalize_storage_type(None if pd.isna(x) else str(x)))
    return result


def engineer_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["cpu_score"] = result["cpu"].map(CPU_SCORE).fillna(35).astype(float)
    result["gpu_score"] = result["gpu"].map(GPU_SCORE).fillna(30).astype(float)
    result["condition_score"] = result["condition"].map(CONDITION_SCORE).fillna(0.84).astype(float)
    result["system_age_years"] = result["system_age_years"].fillna(result["system_age_years"].median()).clip(0, 20)
    return result


def build_training_dataset(raw_path: Path, output_path: Path, rejected_path: Path, report_path: Path) -> dict[str, int]:
    raw = pd.read_csv(raw_path)
    normalized = normalize_frame(raw)
    valid, rejected, report = validate_market_data(normalized)
    training = engineer_features(valid)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rejected_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    training.to_csv(output_path, index=False)
    rejected.to_csv(rejected_path, index=False)
    report_path.write_text(json.dumps(report.as_dict(), indent=2))
    return report.as_dict()
