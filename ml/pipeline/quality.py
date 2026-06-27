from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass
class QualityReport:
    total_rows: int
    valid_rows: int
    duplicate_rows: int
    missing_cpu: int
    missing_gpu: int
    invalid_ram: int
    invalid_storage: int
    invalid_target_price: int
    normalization_failures: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


def validate_market_data(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, QualityReport]:
    required = {"source_id", "cpu", "gpu", "ram_gb", "storage_gb", "condition", "sold_price"}
    missing_columns = required.difference(frame.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    duplicate = frame.duplicated(subset=["source_id"], keep="first") | frame.duplicated(keep="first")
    missing_cpu = frame["cpu"].isna() | frame["cpu"].astype(str).str.strip().eq("")
    missing_gpu = frame["gpu"].isna() | frame["gpu"].astype(str).str.strip().eq("")
    invalid_ram = ~frame["ram_gb"].between(2, 512, inclusive="both")
    invalid_storage = ~frame["storage_gb"].between(32, 32768, inclusive="both")
    invalid_target = ~frame["sold_price"].between(75, 15000, inclusive="both")
    unknown_hardware = frame["cpu"].astype(str).str.contains("unknown", case=False, na=False) | frame["gpu"].astype(str).str.contains("unknown", case=False, na=False)

    invalid = duplicate | missing_cpu | missing_gpu | invalid_ram | invalid_storage | invalid_target
    valid = frame.loc[~invalid].copy()
    rejected = frame.loc[invalid].copy()
    report = QualityReport(
        total_rows=len(frame),
        valid_rows=len(valid),
        duplicate_rows=int(duplicate.sum()),
        missing_cpu=int(missing_cpu.sum()),
        missing_gpu=int(missing_gpu.sum()),
        invalid_ram=int(invalid_ram.sum()),
        invalid_storage=int(invalid_storage.sum()),
        invalid_target_price=int(invalid_target.sum()),
        normalization_failures=int(unknown_hardware.sum()),
    )
    return valid, rejected, report
