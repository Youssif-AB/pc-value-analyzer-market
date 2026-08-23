from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from backend.app.services.normalization import (
    normalize_condition,
    normalize_cpu,
    normalize_gpu,
    normalize_ram_type,
    normalize_storage_type,
)

REQUIRED_COLUMNS = {
    "source",
    "source_listing_id",
    "observed_at",
    "listing_title",
    "observed_price",
    "currency",
    "condition",
    "cpu",
    "gpu",
    "ram_gb",
    "storage_gb",
}


@dataclass(frozen=True)
class DatasetQuality:
    raw_rows: int
    valid_rows: int
    rejected_rows: int
    duplicate_rows: int
    unresolved_cpu_rows: int
    unresolved_gpu_rows: int
    missing_component_rates: dict[str, float]
    source_distribution: dict[str, int]
    price_summary: dict[str, float]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_key(frame: pd.DataFrame) -> pd.Series:
    explicit = (
        frame["source"].astype(str).str.strip()
        + ":"
        + frame["source_listing_id"].astype(str).str.strip()
    )
    fallback = (
        frame["source"].astype(str)
        + "|"
        + frame["listing_title"]
        .astype(str)
        .str.lower()
        .str.replace(r"\W+", " ", regex=True)
        .str.strip()
    ).map(lambda value: hashlib.sha256(value.encode()).hexdigest()[:24])
    missing = frame["source_listing_id"].isna() | frame["source_listing_id"].astype(
        str
    ).str.strip().eq("")
    return explicit.mask(missing, fallback)


def build_market_dataset(
    raw_path: Path,
    normalized_path: Path,
    model_path: Path,
    rejected_path: Path,
    report_path: Path,
    manifest_path: Path,
    target_currency: str = "CAD",
) -> dict[str, object]:
    """Validate an authorized listing export and preserve row-level provenance.

    Input prices must already be in ``target_currency`` unless ``price_cad`` is supplied.
    This deliberately refuses implicit FX conversion so a stale or invented rate cannot enter
    training unnoticed.
    """
    raw = pd.read_csv(raw_path)
    missing = REQUIRED_COLUMNS.difference(raw.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    frame = raw.copy()
    frame["observed_at"] = pd.to_datetime(frame["observed_at"], utc=True, errors="coerce")
    for column in ("observed_price", "price_cad", "ram_gb", "storage_gb", "system_age_years"):
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    currency = frame["currency"].astype(str).str.upper().str.strip()
    if "price_cad" in frame:
        frame["target_price"] = frame["price_cad"]
    else:
        frame["target_price"] = frame["observed_price"].where(currency.eq(target_currency))

    cpu_results = frame["cpu"].map(
        lambda value: normalize_cpu(None if pd.isna(value) else str(value))
    )
    gpu_results = frame["gpu"].map(
        lambda value: normalize_gpu(None if pd.isna(value) else str(value))
    )
    frame["cpu_raw"] = frame["cpu"]
    frame["gpu_raw"] = frame["gpu"]
    frame["cpu"] = cpu_results.map(lambda result: result.value)
    frame["gpu"] = gpu_results.map(lambda result: result.value)
    frame["cpu_normalization_confidence"] = cpu_results.map(lambda result: result.confidence)
    frame["gpu_normalization_confidence"] = gpu_results.map(lambda result: result.confidence)
    frame["cpu_normalization_status"] = cpu_results.map(lambda result: result.reason)
    frame["gpu_normalization_status"] = gpu_results.map(lambda result: result.reason)
    frame["ram_type"] = frame.get("ram_type", pd.Series(index=frame.index, dtype=object)).map(
        lambda value: normalize_ram_type(None if pd.isna(value) else str(value))
    )
    frame["storage_type"] = frame.get(
        "storage_type", pd.Series(index=frame.index, dtype=object)
    ).map(lambda value: normalize_storage_type(None if pd.isna(value) else str(value)))
    frame["condition"] = frame["condition"].map(normalize_condition)
    frame["record_key"] = _record_key(frame)

    duplicate = frame.duplicated("record_key", keep="first")
    invalid = (
        frame["observed_at"].isna()
        | frame["target_price"].isna()
        | ~frame["target_price"].between(75, 15000)
        | frame["ram_gb"].isna()
        | ~frame["ram_gb"].between(2, 512)
        | frame["storage_gb"].isna()
        | ~frame["storage_gb"].between(32, 32768)
        | duplicate
    )
    reasons = pd.Series("", index=frame.index, dtype=object)
    for mask, label in (
        (duplicate, "duplicate"),
        (frame["observed_at"].isna(), "invalid_timestamp"),
        (frame["target_price"].isna(), "missing_price_or_fx"),
        (~frame["target_price"].between(75, 15000), "invalid_price"),
        (frame["ram_gb"].isna() | ~frame["ram_gb"].between(2, 512), "invalid_ram"),
        (frame["storage_gb"].isna() | ~frame["storage_gb"].between(32, 32768), "invalid_storage"),
    ):
        reasons = reasons.mask(mask & reasons.eq(""), label)
    frame["rejection_reason"] = reasons
    valid = frame.loc[~invalid].sort_values("observed_at").copy()
    rejected = frame.loc[invalid].copy()

    missing_rates = {
        column: round(float(valid[column].isna().mean()), 4)
        for column in ("cpu", "gpu", "ram_gb", "storage_gb", "condition")
    }
    price = valid["target_price"]
    quality = DatasetQuality(
        raw_rows=len(frame),
        valid_rows=len(valid),
        rejected_rows=len(rejected),
        duplicate_rows=int(duplicate.sum()),
        unresolved_cpu_rows=int(valid["cpu_normalization_confidence"].eq(0).sum()),
        unresolved_gpu_rows=int(valid["gpu_normalization_confidence"].eq(0).sum()),
        missing_component_rates=missing_rates,
        source_distribution={str(k): int(v) for k, v in valid["source"].value_counts().items()},
        price_summary={
            k: round(float(v), 2)
            for k, v in price.describe()[["min", "25%", "50%", "75%", "max"]].items()
        }
        if len(price)
        else {},
    )
    for path in (normalized_path, model_path, rejected_path, report_path, manifest_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    frame.drop(columns="rejection_reason").to_csv(normalized_path, index=False)
    valid.to_csv(model_path, index=False)
    rejected.to_csv(rejected_path, index=False)
    report_path.write_text(json.dumps(quality.as_dict(), indent=2))
    manifest = {
        "dataset_id": f"market-listings-{_sha256(raw_path)[:12]}",
        "created_at": datetime.now(UTC).isoformat(),
        "raw_file": str(raw_path),
        "raw_sha256": _sha256(raw_path),
        "target": "observed market listing price",
        "target_currency": target_currency,
        "rows": quality.as_dict(),
        "date_min": valid["observed_at"].min().isoformat() if len(valid) else None,
        "date_max": valid["observed_at"].max().isoformat() if len(valid) else None,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a provenance-preserving real listing dataset"
    )
    parser.add_argument("--input", type=Path, required=True, help="Authorized API/user export CSV")
    parser.add_argument(
        "--normalized", type=Path, default=Path("data/normalized/market_listings.csv")
    )
    parser.add_argument("--output", type=Path, default=Path("data/validated/market_listings.csv"))
    parser.add_argument("--rejected", type=Path, default=Path("data/rejected/market_listings.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/real_data_quality.json"))
    parser.add_argument(
        "--manifest", type=Path, default=Path("data/manifests/market_listings.json")
    )
    args = parser.parse_args()
    print(
        json.dumps(
            build_market_dataset(
                args.input, args.normalized, args.output, args.rejected, args.report, args.manifest
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
