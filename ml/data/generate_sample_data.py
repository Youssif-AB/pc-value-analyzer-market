from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd

from backend.app.services.features import CONDITION_SCORE, CPU_SCORE, GPU_SCORE

CPU_VALUES = list(CPU_SCORE)
GPU_VALUES = list(GPU_SCORE)
RAM_OPTIONS = [8, 16, 32, 64, 128]
STORAGE_OPTIONS = [256, 512, 1024, 2048, 4096]
RAM_TYPES = ["DDR4", "DDR5"]
STORAGE_TYPES = ["SATA SSD", "NVMe SSD", "HDD"]
CONDITIONS = ["new", "like_new", "excellent", "good", "fair"]
BRANDS = ["custom", "Alienware", "Dell", "HP", "Lenovo", "ASUS", "MSI"]


def generate(n: int = 1200, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    for i in range(n):
        cpu = rng.choice(CPU_VALUES)
        gpu = rng.choice(GPU_VALUES)
        ram = rng.choices(RAM_OPTIONS, weights=[3, 20, 35, 18, 2])[0]
        storage = rng.choices(STORAGE_OPTIONS, weights=[2, 12, 42, 28, 6])[0]
        ram_type = "DDR5" if (CPU_SCORE[cpu] > 75 and rng.random() < 0.75) else rng.choice(RAM_TYPES)
        storage_type = rng.choices(STORAGE_TYPES, weights=[15, 80, 5])[0]
        condition = rng.choices(CONDITIONS, weights=[8, 12, 22, 48, 10])[0]
        brand = rng.choice(BRANDS)
        age = round(max(0, np_rng.normal(2.8, 1.7)), 1)
        base = 210 + GPU_SCORE[gpu] * 13.2 + CPU_SCORE[cpu] * 5.3 + ram * 4.0 + storage * 0.13
        premium = 110 if ram_type == "DDR5" else 0
        premium += 120 if storage_type == "NVMe SSD" else -90 if storage_type == "HDD" else 0
        premium += 90 if brand in {"Alienware", "ASUS", "MSI"} else 0
        fair_price = (base + premium) * CONDITION_SCORE[condition] * max(0.52, 1 - age * 0.055)
        heteroscedastic_noise = np_rng.normal(0, 70 + fair_price * 0.06)
        sold_price = max(120, fair_price + heteroscedastic_noise)
        asking_price = max(120, sold_price * np_rng.normal(1.04, 0.10))
        rows.append({
            "source": "synthetic_demo",
            "source_id": f"demo-{i:05d}",
            "cpu": cpu,
            "gpu": gpu,
            "ram_gb": ram,
            "ram_type": ram_type,
            "storage_gb": storage,
            "storage_type": storage_type,
            "condition": condition,
            "brand": brand,
            "system_age_years": age,
            "asking_price": round(asking_price, 2),
            "sold_price": round(sold_price, 2),
        })
    frame = pd.DataFrame(rows)
    # Seed a small number of realistic data-quality defects for the pipeline to detect.
    if n >= 100:
        frame.loc[3, "gpu"] = None
        frame.loc[17, "ram_gb"] = -8
        frame.loc[31, "sold_price"] = 99999
        frame.loc[54] = frame.loc[53]
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data/raw/sample_market_listings.csv"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    generate(args.rows, args.seed).to_csv(args.output, index=False)
    print(f"Wrote {args.rows} demo observations to {args.output}")


if __name__ == "__main__":
    main()
