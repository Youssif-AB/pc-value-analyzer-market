from __future__ import annotations

import pandas as pd

from backend.app.schemas import NormalizedSpecs

GPU_SCORE = {
    "NVIDIA GeForce RTX 5090": 100,
    "NVIDIA GeForce RTX 5080": 91,
    "NVIDIA GeForce RTX 5070 Ti": 83,
    "NVIDIA GeForce RTX 5070": 75,
    "NVIDIA GeForce RTX 5060 Ti": 66,
    "NVIDIA GeForce RTX 5060": 58,
    "NVIDIA GeForce RTX 5050": 49,
    "NVIDIA GeForce RTX 4090": 96,
    "NVIDIA GeForce RTX 4080 SUPER": 88,
    "NVIDIA GeForce RTX 4080": 86,
    "NVIDIA GeForce RTX 4070 Ti SUPER": 82,
    "NVIDIA GeForce RTX 4070 Ti": 79,
    "NVIDIA GeForce RTX 4070 SUPER": 75,
    "NVIDIA GeForce RTX 4070": 71,
    "NVIDIA GeForce RTX 4060 Ti": 61,
    "NVIDIA GeForce RTX 4060": 53,
    "NVIDIA GeForce RTX 3090": 78,
    "NVIDIA GeForce RTX 3080": 69,
    "NVIDIA GeForce RTX 3070": 58,
    "NVIDIA GeForce RTX 3060": 47,
    "NVIDIA GeForce RTX 2080": 43,
    "AMD Radeon RX 9070 XT": 82,
    "AMD Radeon RX 9070": 76,
    "AMD Radeon RX 9060 XT": 63,
    "AMD Radeon RX 7900 XTX": 88,
    "AMD Radeon RX 7900 XT": 81,
    "AMD Radeon RX 7800 XT": 71,
    "AMD Radeon RX 7700 XT": 63,
    "AMD Radeon RX 7700": 58,
    "AMD Radeon RX 7600": 49,
    "AMD Radeon RX 6800 XT": 66,
    "AMD Radeon RX 6700 XT": 55,
    "AMD Radeon RX 6500 XT": 31,
    "Intel Arc B580": 56,
    "Intel Arc A770": 47,
    "Intel Arc A750": 42,
}

CPU_SCORE = {
    "AMD Ryzen 9 9950X3D": 100,
    "AMD Ryzen 9 9950X": 97,
    "AMD Ryzen 9 9900X3D": 97,
    "AMD Ryzen 9 9900X": 93,
    "AMD Ryzen 7 9800X3D": 99,
    "AMD Ryzen 7 9700X": 89,
    "AMD Ryzen 5 9600X": 81,
    "AMD Ryzen 5 9500F": 73,
    "AMD Ryzen 7 8700F": 79,
    "AMD Ryzen 5 8400F": 68,
    "AMD Ryzen 9 7950X3D": 96,
    "AMD Ryzen 9 7950X": 93,
    "AMD Ryzen 9 7900X": 87,
    "AMD Ryzen 7 7800X3D": 94,
    "AMD Ryzen 7 7700X": 81,
    "AMD Ryzen 7 5800X3D": 76,
    "AMD Ryzen 7 5800X": 68,
    "AMD Ryzen 5 7600X": 73,
    "AMD Ryzen 5 5600X": 57,
    "Intel Core Ultra 9 285K": 97,
    "Intel Core Ultra 7 265K": 90,
    "Intel Core Ultra 7 265F": 86,
    "Intel Core i9-14900K": 96,
    "Intel Core i9-13900K": 92,
    "Intel Core i7-14700K": 90,
    "Intel Core i7-14700F": 86,
    "Intel Core i7-13700K": 84,
    "Intel Core i7-12700K": 74,
    "Intel Core i5-14600K": 82,
    "Intel Core i5-14400F": 72,
    "Intel Core i5-13600K": 77,
    "Intel Core i5-12600K": 66,
    "Intel Core i5-12400": 55,
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
