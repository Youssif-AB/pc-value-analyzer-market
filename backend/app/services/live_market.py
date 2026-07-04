from __future__ import annotations

from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import Settings, get_settings
from backend.app.models import LiveMarketListing
from backend.app.schemas import LiveMarketEvidence, MarketComparable, NormalizedSpecs
from backend.app.services.features import CONDITION_SCORE, CPU_SCORE, GPU_SCORE


def _ratio_similarity(left: int | float | None, right: int | float | None) -> float | None:
    if not left or not right:
        return None
    low, high = sorted((float(left), float(right)))
    return max(0.0, min(1.0, low / high))


def _score_similarity(name_a: str | None, name_b: str | None, score_map: dict[str, int]) -> float | None:
    if not name_a or not name_b:
        return None
    if name_a == name_b:
        return 1.0
    a = score_map.get(name_a)
    b = score_map.get(name_b)
    if a is None or b is None:
        return 0.2 if name_a.lower() == name_b.lower() else 0.0
    return max(0.0, 1.0 - abs(a - b) / 55.0)


def similarity(target: NormalizedSpecs, comp: NormalizedSpecs) -> float:
    parts: list[tuple[float, float | None]] = [
        (0.40, _score_similarity(target.gpu, comp.gpu, GPU_SCORE)),
        (0.29, _score_similarity(target.cpu, comp.cpu, CPU_SCORE)),
        (0.10, _ratio_similarity(target.ram_gb, comp.ram_gb)),
        (0.08, _ratio_similarity(target.storage_gb, comp.storage_gb)),
        (0.06, 1.0 - min(1.0, abs(CONDITION_SCORE.get(target.condition, 0.84) - CONDITION_SCORE.get(comp.condition, 0.84)))),
        (0.04, 1.0 if target.ram_type and target.ram_type == comp.ram_type else 0.4 if target.ram_type and comp.ram_type else None),
        (0.03, 1.0 if target.storage_type and target.storage_type == comp.storage_type else 0.5 if target.storage_type and comp.storage_type else None),
    ]
    available = [(weight, value) for weight, value in parts if value is not None]
    if not available:
        return 0.0
    denominator = sum(weight for weight, _ in available)
    return max(0.0, min(1.0, sum(weight * float(value) for weight, value in available) / denominator))


def _weighted_median(values: list[tuple[float, float]]) -> float:
    ordered = sorted(values, key=lambda pair: pair[0])
    total = sum(weight for _, weight in ordered)
    threshold = total / 2
    cumulative = 0.0
    for value, weight in ordered:
        cumulative += weight
        if cumulative >= threshold:
            return value
    return ordered[-1][0]


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class LiveMarketService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def evidence(
        self,
        db: Session,
        target: NormalizedSpecs,
        target_baseline: float,
        baseline_predictor: Callable[[NormalizedSpecs], float],
    ) -> LiveMarketEvidence:
        if not self.settings.live_market_enabled:
            return LiveMarketEvidence(enabled=False)
        cutoff = datetime.now(UTC) - timedelta(hours=self.settings.live_comp_max_age_hours)
        rows = db.scalars(
            select(LiveMarketListing).where(
                LiveMarketListing.active.is_(True),
                LiveMarketListing.last_seen_at >= cutoff,
                LiveMarketListing.extraction_quality >= 0.50,
            ).order_by(LiveMarketListing.last_seen_at.desc()).limit(2000)
        ).all()
        ranked: list[tuple[LiveMarketListing, NormalizedSpecs, float, float, float]] = []
        now = datetime.now(UTC)
        for row in rows:
            try:
                comp_specs = NormalizedSpecs.model_validate(row.specs_payload)
            except Exception:
                continue
            score = similarity(target, comp_specs)
            if score < self.settings.live_comp_min_similarity:
                continue
            comp_baseline = baseline_predictor(comp_specs)
            raw_adjustment = target_baseline - comp_baseline
            max_adjustment = row.price_cad * 0.45
            adjustment = max(-max_adjustment, min(max_adjustment, raw_adjustment))
            adjusted = max(50.0, row.price_cad + adjustment)
            age_reference = row.listed_at or row.last_seen_at
            age_hours = max(0.0, (now - _aware(age_reference)).total_seconds() / 3600)
            freshness = max(0.25, 1.0 - age_hours / max(1, self.settings.live_comp_max_age_hours))
            weight = score**2 * freshness
            ranked.append((row, comp_specs, score, adjusted, weight))
        ranked.sort(key=lambda item: (item[2], item[4]), reverse=True)
        ranked = ranked[: self.settings.live_comp_max_results]
        if not ranked:
            return LiveMarketEvidence(enabled=True)

        source_names = sorted({row.source for row, *_ in ranked})
        adjusted_values = [(adjusted, weight) for _, _, _, adjusted, weight in ranked]
        adjusted_market = _weighted_median(adjusted_values)
        median_asking = median(row.price_cad for row, *_ in ranked)
        blend_weight = 0.0
        if len(ranked) >= 3:
            blend_weight = min(
                self.settings.live_comp_blend_cap,
                0.18 + 0.055 * min(len(ranked), 7) + 0.10 * min(max(0, len(source_names) - 1), 1),
            )
        comps = [
            MarketComparable(
                source=row.source,
                title=row.title,
                price_cad=round(row.price_cad, 2),
                condition=row.condition,
                similarity=round(score, 3),
                url=row.url,
                observed_at=row.listed_at or row.last_seen_at,
            )
            for row, _, score, _, _ in ranked[:8]
        ]
        newest = max(_aware(row.last_seen_at) for row, *_ in ranked)
        return LiveMarketEvidence(
            enabled=True,
            comp_count=len(ranked),
            source_count=len(source_names),
            sources=source_names,
            median_asking_price_cad=round(float(median_asking), 2),
            adjusted_market_estimate_cad=round(float(adjusted_market), 2),
            blend_weight=round(blend_weight, 3),
            newest_observation_at=newest,
            valuation_method="hybrid_live_comps" if blend_weight > 0 else "model_only",
            comparables=comps,
        )
