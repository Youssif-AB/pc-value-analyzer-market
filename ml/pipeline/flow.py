from __future__ import annotations

import json
from pathlib import Path

try:
    from prefect import flow, task
except ImportError:  # Allows local unit tests without requiring the orchestrator runtime.
    def task(fn):
        return fn
    def flow(*_args, **_kwargs):
        def decorator(fn):
            return fn
        return decorator

from ml.pipeline.transform import build_training_dataset
from ml.training.train import train

RAW = Path("data/raw/sample_market_listings.csv")
TRAINING = Path("data/processed/training.csv")
REJECTED = Path("data/processed/rejected.csv")
QUALITY = Path("reports/data_quality.json")
MODEL = Path("backend/artifacts/price_model.joblib")
METADATA = Path("backend/artifacts/model_metadata.json")
COMPARISON = Path("reports/modeling/model_comparison.csv")


@task
def validate_transform() -> dict[str, int]:
    return build_training_dataset(RAW, TRAINING, REJECTED, QUALITY)


@task
def train_model() -> dict[str, object]:
    return train(TRAINING, MODEL, METADATA, COMPARISON, enable_mlflow=True)


@flow(name="pc-market-training-pipeline", log_prints=True)
def training_flow() -> dict[str, object]:
    quality = validate_transform()
    metadata = train_model()
    summary = {"quality": quality, "model": metadata}
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    training_flow()
