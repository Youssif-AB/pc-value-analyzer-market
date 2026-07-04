from __future__ import annotations

from statistics import pstdev

from sqlalchemy.orm import Session

from backend.app.schemas import FeatureContribution, NormalizedSpecs, PredictionResponse
from backend.app.services.live_market import LiveMarketService
from backend.app.services.model_service import ModelService


class ValuationService:
    def __init__(self, model_service: ModelService | None = None, live_market_service: LiveMarketService | None = None) -> None:
        self.model_service = model_service or ModelService()
        self.live_market_service = live_market_service or LiveMarketService()

    def predict(self, db: Session, specs: NormalizedSpecs, asking_price: float) -> PredictionResponse:
        baseline = self.model_service.predict(specs, asking_price)
        evidence = self.live_market_service.evidence(
            db,
            target=specs,
            target_baseline=baseline.estimated_fair_price,
            baseline_predictor=self.model_service.predict_price,
        )
        weight = evidence.blend_weight
        if not weight or evidence.adjusted_market_estimate_cad is None:
            warnings = list(baseline.warnings)
            if evidence.enabled and evidence.comp_count:
                warnings.append(f"Found {evidence.comp_count} live comparable(s), but evidence was too sparse to blend into the estimate.")
            elif evidence.enabled:
                warnings.append("No sufficiently similar fresh live comparables are cached yet; using the ML baseline only.")
            return baseline.model_copy(update={"live_market": evidence, "warnings": warnings})

        market_estimate = evidence.adjusted_market_estimate_cad
        final_estimate = (1 - weight) * baseline.estimated_fair_price + weight * market_estimate
        difference = ((asking_price - final_estimate) / final_estimate) * 100
        base_half_width = max(75.0, (baseline.upper_bound - baseline.lower_bound) / 2)
        comp_prices = [comp.price_cad for comp in evidence.comparables]
        market_half_width = 1.28 * max(75.0, pstdev(comp_prices) if len(comp_prices) > 1 else 120.0)
        half_width = (1 - weight) * base_half_width + weight * market_half_width

        confidence = baseline.confidence
        if evidence.source_count >= 2 and evidence.comp_count >= 6:
            confidence = "medium" if baseline.confidence == "low" else "high"
        elif evidence.comp_count >= 4 and baseline.confidence == "low":
            confidence = "medium"

        drivers = list(baseline.drivers)
        direction = "up" if market_estimate > baseline.estimated_fair_price else "down" if market_estimate < baseline.estimated_fair_price else "neutral"
        drivers.append(
            FeatureContribution(
                feature="Live market",
                direction=direction,
                explanation=f"{evidence.comp_count} fresh comparable listings across {evidence.source_count} source(s) contributed {round(weight * 100)}% of the final estimate.",
            )
        )
        warnings = list(baseline.warnings)
        warnings.append("Live sources are active asking/open-box prices, not guaranteed completed-sale prices; the app keeps that evidence separate from supervised training labels.")

        return baseline.model_copy(
            update={
                "estimated_fair_price": round(final_estimate, 2),
                "difference_percent": round(difference, 1),
                "rating": self.model_service.rating(difference),
                "lower_bound": round(max(0, final_estimate - half_width), 2),
                "upper_bound": round(final_estimate + half_width, 2),
                "confidence": confidence,
                "drivers": drivers[:5],
                "warnings": warnings,
                "live_market": evidence,
            }
        )
