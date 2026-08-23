from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

from backend.app.config import get_settings
from backend.app.schemas import (
    FeatureContribution,
    LiveMarketEvidence,
    NormalizedSpecs,
    PredictionResponse,
)
from backend.app.services.features import CPU_SCORE, GPU_SCORE, specs_to_frame


@dataclass
class LoadedModel:
    model: object
    version: str
    validation_mae: float | None
    residual_std: float
    data_disclaimer: str | None
    conformal_quantile: float
    interval_coverage_target: float | None
    interval_empirical_coverage: float | None
    training_frequencies: dict[str, dict[str, int]]


class ModelService:
    def __init__(self, model_path: Path | None = None, metadata_path: Path | None = None) -> None:
        settings = get_settings()
        self.settings = settings
        self.model_path = Path(model_path or settings.model_artifact_path)
        self.metadata_path = Path(metadata_path or settings.model_metadata_path)
        self.loaded: LoadedModel | None = None

    def load(self) -> LoadedModel:
        if self.loaded is not None:
            return self.loaded
        if not self.model_path.exists():
            raise RuntimeError(
                f"Model artifact not found at {self.model_path}. Run the training pipeline first."
            )
        model = joblib.load(self.model_path)
        metadata: dict[str, object] = {}
        if self.metadata_path.exists():
            metadata = json.loads(self.metadata_path.read_text())
        self.loaded = LoadedModel(
            model=model,
            version=str(metadata.get("model_version", "local-unversioned")),
            validation_mae=float(metadata["validation_mae"])
            if metadata.get("validation_mae") is not None
            else None,
            residual_std=float(metadata.get("residual_std", 220.0)),
            data_disclaimer=str(metadata.get("data_disclaimer"))
            if metadata.get("data_disclaimer")
            else None,
            conformal_quantile=float(
                metadata.get("conformal_quantile", metadata.get("residual_std", 220.0) * 1.28)
            ),
            interval_coverage_target=float(metadata["conformal_coverage_target"])
            if metadata.get("conformal_coverage_target") is not None
            else None,
            interval_empirical_coverage=float(metadata["test_interval_coverage"])
            if metadata.get("test_interval_coverage") is not None
            else None,
            training_frequencies=metadata.get("training_frequencies", {}),
        )
        return self.loaded

    def predict_price(self, specs: NormalizedSpecs) -> float:
        loaded = self.load()
        frame = specs_to_frame(specs)
        return max(50.0, float(np.asarray(loaded.model.predict(frame))[0]))

    def predict(self, specs: NormalizedSpecs, asking_price: float) -> PredictionResponse:
        loaded = self.load()
        estimate = self.predict_price(specs)
        difference_percent = ((asking_price - estimate) / estimate) * 100
        missing = [
            name
            for name, value in (
                ("CPU", specs.cpu),
                ("GPU", specs.gpu),
                ("RAM", specs.ram_gb),
                ("storage", specs.storage_gb),
            )
            if not value
        ]
        cpu_count = loaded.training_frequencies.get("cpu", {}).get(specs.cpu or "", 0)
        gpu_count = loaded.training_frequencies.get("gpu", {}).get(specs.gpu or "", 0)
        config_key = f"{specs.cpu}|||{specs.gpu}"
        config_count = loaded.training_frequencies.get("configuration", {}).get(config_key, 0)
        coverage_score = min(
            1.0, (min(cpu_count, 20) + min(gpu_count, 20) + 2 * min(config_count, 10)) / 60
        )
        if not loaded.training_frequencies:
            coverage_score = 0.5 if not missing else 0.2
        coverage_label = (
            "strong" if coverage_score >= 0.67 else "limited" if coverage_score >= 0.25 else "weak"
        )
        interval = loaded.conformal_quantile * (
            1 + 0.2 * len(missing) + (0.35 if coverage_label == "weak" else 0)
        )
        confidence = (
            "high"
            if coverage_label == "strong" and not missing
            else "medium"
            if coverage_label == "limited" and len(missing) <= 1
            else "low"
        )
        warnings = (
            [f"Missing or unrecognized {', '.join(missing)} increases uncertainty."]
            if missing
            else []
        )
        if coverage_label == "weak":
            warnings.append(
                "Weak training coverage: this CPU/GPU configuration was rare or unseen in training."
            )
        warnings.append(
            "Market estimates are data-dependent and are not a guarantee of resale value."
        )
        if loaded.data_disclaimer:
            warnings.append(loaded.data_disclaimer)
        return PredictionResponse(
            estimated_fair_price=round(estimate, 2),
            asking_price=round(asking_price, 2),
            difference_percent=round(difference_percent, 1),
            rating=self.rating(difference_percent),
            lower_bound=round(max(0, estimate - interval), 2),
            upper_bound=round(estimate + interval, 2),
            model_version=loaded.version,
            confidence=confidence,
            coverage_score=round(coverage_score, 2),
            coverage_label=coverage_label,
            interval_coverage_target=loaded.interval_coverage_target,
            interval_empirical_coverage=loaded.interval_empirical_coverage,
            drivers=self.drivers(specs),
            warnings=warnings,
            live_market=LiveMarketEvidence(enabled=self.settings.live_market_enabled),
        )

    @staticmethod
    def rating(diff: float) -> str:
        if diff <= -18:
            return "GREAT DEAL"
        if diff <= -7:
            return "GOOD VALUE"
        if diff < 8:
            return "FAIR"
        if diff < 20:
            return "OVERPRICED"
        return "HIGHLY OVERPRICED"

    @staticmethod
    def drivers(specs: NormalizedSpecs) -> list[FeatureContribution]:
        drivers: list[FeatureContribution] = []
        gpu_score = GPU_SCORE.get(specs.gpu or "", 30)
        cpu_score = CPU_SCORE.get(specs.cpu or "", 35)
        drivers.append(
            FeatureContribution(
                feature="GPU",
                direction="up" if gpu_score >= 65 else "neutral",
                explanation=f"{specs.gpu or 'Unknown GPU'} maps to a performance tier of {gpu_score}/100.",
            )
        )
        drivers.append(
            FeatureContribution(
                feature="CPU",
                direction="up" if cpu_score >= 75 else "neutral",
                explanation=f"{specs.cpu or 'Unknown CPU'} maps to a performance tier of {cpu_score}/100.",
            )
        )
        if (specs.ram_gb or 0) >= 32:
            drivers.append(
                FeatureContribution(
                    feature="RAM",
                    direction="up",
                    explanation=f"{specs.ram_gb} GB RAM supports a premium over 16 GB systems.",
                )
            )
        if specs.condition in {"fair", "parts"}:
            drivers.append(
                FeatureContribution(
                    feature="Condition",
                    direction="down",
                    explanation=f"Condition is marked {specs.condition}, which reduces expected market value.",
                )
            )
        return drivers[:4]
