from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd

from ml.training.visualization import generate_evaluation_figures, market_context_svg, price_bands


def fixture_predictions() -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "actual": [600, 700, 1100, 1500, 2100, 2600],
            "prediction": [650, 670, 1050, 1620, 2000, 2800],
        }
    )
    frame["residual"] = frame.actual - frame.prediction
    frame["lower"] = frame.prediction - 250
    frame["upper"] = frame.prediction + 250
    frame["covered"] = frame.actual.between(frame.lower, frame.upper)
    frame["interval_width"] = frame.upper - frame.lower
    frame["price_band"] = price_bands(frame.actual)
    return frame


def test_evaluation_figures_are_headless_and_nonempty(tmp_path: Path) -> None:
    predictions = fixture_predictions()
    segments = pd.DataFrame(
        [
            {
                "segment": "price_band",
                "value": band,
                "count": len(group),
                "mae": (group.actual - group.prediction).abs().mean(),
            }
            for band, group in predictions.groupby("price_band", observed=True)
        ]
    )
    paths = generate_evaluation_figures(predictions, segments, tmp_path, 0.9)
    assert set(paths) == {
        "predicted_vs_actual",
        "error_by_price_band",
        "residual_diagnostic",
        "conformal_by_price_band",
    }
    assert all(Path(path).stat().st_size > 1_000 for path in paths.values())


def test_missing_optional_plot_data_is_graceful(tmp_path: Path) -> None:
    assert market_context_svg([], 1000, 800, 1200) is None
    assert generate_evaluation_figures(pd.DataFrame(), pd.DataFrame(), tmp_path, 0.9) == {}


def test_market_context_contains_only_supplied_comparable_prices() -> None:
    uri = market_context_svg([900, 1100, 1400], 1200, 950, 1450)
    assert uri and uri.startswith("data:image/svg+xml;base64,")
    svg = base64.b64decode(uri.split(",", 1)[1])
    assert len(svg) > 1_000
