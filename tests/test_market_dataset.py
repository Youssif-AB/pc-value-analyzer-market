from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.data.market_dataset import build_market_dataset
from ml.training.train import conformal_quantile, split_dataset


def test_market_dataset_preserves_provenance_and_quarantines_duplicates(tmp_path: Path) -> None:
    raw = tmp_path / "raw.csv"
    pd.DataFrame(
        [
            {
                "source": "ebay",
                "source_listing_id": "1",
                "observed_at": "2026-01-01T00:00:00Z",
                "listing_title": "RTX4070 PC",
                "observed_price": 1000,
                "currency": "CAD",
                "condition": "used",
                "cpu": "i5 12400",
                "gpu": "RTX4070",
                "ram_gb": 16,
                "storage_gb": 1024,
            },
            {
                "source": "ebay",
                "source_listing_id": "1",
                "observed_at": "2026-01-02T00:00:00Z",
                "listing_title": "same",
                "observed_price": 1100,
                "currency": "CAD",
                "condition": "used",
                "cpu": "i5 12400",
                "gpu": "RTX4070",
                "ram_gb": 16,
                "storage_gb": 1024,
            },
            {
                "source": "bestbuy",
                "source_listing_id": "2",
                "observed_at": "bad",
                "listing_title": "bad",
                "observed_price": 1200,
                "currency": "CAD",
                "condition": "new",
                "cpu": "x",
                "gpu": "y",
                "ram_gb": 16,
                "storage_gb": 1024,
            },
        ]
    ).to_csv(raw, index=False)
    paths = [
        tmp_path / name
        for name in ("normalized.csv", "model.csv", "rejected.csv", "quality.json", "manifest.json")
    ]
    manifest = build_market_dataset(raw, *paths)
    assert manifest["rows"]["valid_rows"] == 1
    assert manifest["rows"]["duplicate_rows"] == 1
    valid = pd.read_csv(paths[1])
    rejected = pd.read_csv(paths[2])
    assert valid.loc[0, "gpu"] == "NVIDIA GeForce RTX 4070"
    assert {"source_listing_id", "observed_at", "listing_title", "cpu_raw", "record_key"}.issubset(
        valid.columns
    )
    assert set(rejected.rejection_reason) == {"duplicate", "invalid_timestamp"}


def test_market_dataset_refuses_implicit_currency_conversion(tmp_path: Path) -> None:
    raw = tmp_path / "raw.csv"
    pd.DataFrame(
        [
            {
                "source": "x",
                "source_listing_id": "1",
                "observed_at": "2026-01-01",
                "listing_title": "pc",
                "observed_price": 1000,
                "currency": "USD",
                "condition": "good",
                "cpu": "cpu",
                "gpu": "gpu",
                "ram_gb": 16,
                "storage_gb": 512,
            }
        ]
    ).to_csv(raw, index=False)
    paths = [tmp_path / name for name in ("n.csv", "m.csv", "r.csv", "q.json", "manifest.json")]
    manifest = build_market_dataset(raw, *paths)
    assert manifest["rows"]["valid_rows"] == 0
    assert pd.read_csv(paths[2]).loc[0, "rejection_reason"] == "missing_price_or_fx"


def test_temporal_split_keeps_listing_groups_together() -> None:
    frame = pd.DataFrame(
        {
            "observed_at": pd.date_range("2026-01-01", periods=10, tz="UTC"),
            "record_key": [f"k{i // 2}" for i in range(10)],
        }
    )
    train, calibration, test, method = split_dataset(frame)
    assert "chronological" in method
    assert set(train.record_key).isdisjoint(calibration.record_key)
    assert set(train.record_key).isdisjoint(test.record_key)


def test_conformal_quantile_is_finite_sample_conservative() -> None:
    assert (
        conformal_quantile(pd.Series([1.0, 2.0, 3.0, 20.0]), np.array([1.0, 2.0, 3.0, 0.0]), 0.9)
        == 20
    )


def test_market_dataset_requires_schema(tmp_path: Path) -> None:
    raw = tmp_path / "raw.csv"
    pd.DataFrame([{"source": "x"}]).to_csv(raw, index=False)
    with pytest.raises(ValueError, match="Missing required columns"):
        build_market_dataset(raw, *(tmp_path / str(i) for i in range(5)))
