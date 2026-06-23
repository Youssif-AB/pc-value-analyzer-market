from __future__ import annotations

import pandas as pd

from backend.app.schemas import NormalizedSpecs

GPU_SCORE = {
    "NVIDIA GeForce RTX 4090": 100,
    "NVIDIA GeForce RTX 4080": 90,
    "NVIDIA GeForce RTX 4070 Ti SUPER": 84,
    "NVIDIA GeForce RTX 4070 Ti": 80,
    "NVIDIA GeForce RTX 4070": 72,
    "NVIDIA GeForce RTX 4060 Ti": 62,
    "NVIDIA GeForce RTX 4060": 54,
    "NVIDIA GeForce RTX 3090": 82,
    "NVIDIA GeForce RTX 3080": 72,
    "NVIDIA GeForce RTX 3070": 60,
    "NVIDIA GeForce RTX 3060": 48,
    "NVIDIA GeForce RTX 2080": 44,
    "AMD Radeon RX 7900 XTX": 92,
    "AMD Radeon RX 7900 XT": 84,
    "AMD Radeon RX 7800 XT": 73,
    "AMD Radeon RX 7700 XT": 64,
    "AMD Radeon RX 7600": 50,
    "AMD Radeon RX 6800 XT": 69,
    "AMD Radeon RX 6700 XT": 57,
    "Intel Arc A770": 48,
    "Intel Arc A750": 43,
}

CPU_SCORE = {
    "AMD Ryzen 9 7950X3D": 100,
    "AMD Ryzen 9 7950X": 95,
    "AMD Ryzen 9 7900X": 88,
    "AMD Ryzen 7 7800X3D": 96,
    "AMD Ryzen 7 7700X": 82,
    "AMD Ryzen 7 5800X3D": 78,
    "AMD Ryzen 7 5800X": 70,
    "AMD Ryzen 5 7600X": 74,
    "AMD Ryzen 5 5600X": 58,
    "Intel Core i9-14900K": 100,
    "Intel Core i9-13900K": 95,
    "Intel Core i7-14700K": 93,
    "Intel Core i7-13700K": 87,
    "Intel Core i7-12700K": 76,
    "Intel Core i5-14600K": 84,
    "Intel Core i5-13600K": 79,
    "Intel Core i5-12600K": 68,
    "Intel Core i5-12400": 56,
}

CONDITION_SCORE = {"new": 1.0, "like_new": 0.95, "excellent": 0.90, "good": 0.84, "fair": 0.72, "parts": 0.35}

FEATURE_COLUMNS = [
    "cpu", "gpu", "ram_type", "storage_type", "condition", "brand",
    "ram_gb", "storage_gb", "system_age_years", "cpu_score", "gpu_score", "condition_score",
]


def specs_to_record(specs: NormalizedSpecs) -> dict[str, object]:
    return {
        "cpu": specs.cpu or "UNKNOWN",
        "gpu": specs.gpu or "UNKNOWN",
        "ram_type": specs.ram_type or "UNKNOWN",
        "storage_type": specs.storage_type or "UNKNOWN",
        "condition": specs.condition,
        "brand": specs.brand or "custom",
        "ram_gb": specs.ram_gb or 0,
        "storage_gb": specs.storage_gb or 0,
        "system_age_years": specs.system_age_years if specs.system_age_years is not None else 3.0,
        "cpu_score": CPU_SCORE.get(specs.cpu or "", 35),
        "gpu_score": GPU_SCORE.get(specs.gpu or "", 30),
        "condition_score": CONDITION_SCORE.get(specs.condition, 0.84),
    }


def specs_to_frame(specs: NormalizedSpecs) -> pd.DataFrame:
    return pd.DataFrame([specs_to_record(specs)], columns=FEATURE_COLUMNS)
