from __future__ import annotations

import base64
import io
import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "pc-value-matplotlib"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

matplotlib.rcParams["svg.hashsalt"] = "pc-value-analyzer"

PRICE_BAND_ORDER = ("low", "mid", "high")
PRICE_BAND_LABELS = {"low": "Under $800", "mid": "$800–$1,800", "high": "Over $1,800"}
BG = "#101214"
TEXT = "#d8dcdf"
MUTED = "#8f969b"
LINE = "#34393d"
ACCENT = "#65d5a4"
AMBER = "#d7ad62"


def price_bands(values: pd.Series) -> pd.Series:
    """Authoritative price segmentation used by analysis and figures."""
    return pd.cut(values, [-np.inf, 800, 1800, np.inf], labels=PRICE_BAND_ORDER)


def _figure(width: float = 7.2, height: float = 4.2):
    fig, ax = plt.subplots(figsize=(width, height), dpi=144, layout="constrained")
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.tick_params(colors=MUTED, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(LINE)
    ax.xaxis.label.set_color(MUTED)
    ax.yaxis.label.set_color(MUTED)
    ax.title.set_color(TEXT)
    return fig, ax


def _currency(value: float, _position: int) -> str:
    return f"${value:,.0f}"


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="svg", facecolor=fig.get_facecolor(), metadata={"Date": None})
    plt.close(fig)
    # Matplotlib emits harmless trailing spaces in SVG path data; normalize them
    # so generated artifacts remain clean in source control.
    svg = "\n".join(line.rstrip() for line in path.read_text(encoding="utf-8").splitlines())
    path.write_text(svg + "\n", encoding="utf-8")
    return path


def market_context_svg(
    prices: list[float], estimate: float, lower: float, upper: float
) -> str | None:
    usable = [float(value) for value in prices if np.isfinite(value) and value >= 0]
    if not usable:
        return None
    fig, ax = _figure(7.2, 2.15)
    offsets = np.array([((index % 3) - 1) * 0.055 for index in range(len(usable))])
    ax.scatter(
        usable, offsets, s=30, color=MUTED, alpha=0.9, label="Live comparable asks", zorder=3
    )
    ax.plot(
        [lower, upper],
        [0.28, 0.28],
        color=AMBER,
        linewidth=5,
        solid_capstyle="round",
        label="Prediction interval",
    )
    ax.scatter(
        [estimate],
        [0.28],
        s=80,
        color=ACCENT,
        edgecolor=BG,
        linewidth=1.2,
        label="Model estimate",
        zorder=4,
    )
    ax.set_ylim(-0.2, 0.48)
    ax.set_yticks([])
    ax.xaxis.set_major_formatter(FuncFormatter(_currency))
    ax.grid(axis="x", color=LINE, linewidth=0.7, alpha=0.65)
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.0),
        ncols=3,
        frameon=False,
        labelcolor=TEXT,
        fontsize=8,
    )
    buffer = io.BytesIO()
    fig.savefig(buffer, format="svg", facecolor=fig.get_facecolor(), metadata={"Date": None})
    plt.close(fig)
    return "data:image/svg+xml;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def generate_evaluation_figures(
    predictions: pd.DataFrame, segments: pd.DataFrame, output_dir: Path, nominal_coverage: float
) -> dict[str, str]:
    required = {"actual", "prediction", "residual", "lower", "upper", "price_band"}
    if predictions.empty or not required.issubset(predictions.columns):
        return {}
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}

    fig, ax = _figure()
    limits = [
        min(predictions.actual.min(), predictions.prediction.min()),
        max(predictions.actual.max(), predictions.prediction.max()),
    ]
    ax.scatter(
        predictions.actual,
        predictions.prediction,
        s=18,
        color=ACCENT,
        alpha=0.66,
        edgecolors="none",
    )
    ax.plot(limits, limits, color=AMBER, linewidth=1.2, linestyle="--", label="Ideal prediction")
    ax.set(xlabel="Actual observed price (CAD)", ylabel="Predicted price (CAD)")
    ax.xaxis.set_major_formatter(FuncFormatter(_currency))
    ax.yaxis.set_major_formatter(FuncFormatter(_currency))
    ax.grid(color=LINE, linewidth=0.6, alpha=0.55)
    ax.legend(frameon=False, labelcolor=TEXT, fontsize=8)
    paths["predicted_vs_actual"] = str(_save(fig, output_dir / "predicted_vs_actual.svg"))

    price = segments[segments.segment.eq("price_band")].copy()
    price["order"] = price.value.map({name: i for i, name in enumerate(PRICE_BAND_ORDER)})
    price = price.sort_values("order")
    fig, ax = _figure()
    bars = ax.bar(
        [PRICE_BAND_LABELS.get(v, v) for v in price.value], price.mae, color=ACCENT, width=0.62
    )
    for bar, count in zip(bars, price["count"], strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"N={int(count)}",
            ha="center",
            va="bottom",
            color=MUTED,
            fontsize=8,
        )
    ax.set(ylabel="Mean absolute error (CAD)")
    ax.yaxis.set_major_formatter(FuncFormatter(_currency))
    ax.grid(axis="y", color=LINE, linewidth=0.6, alpha=0.55)
    paths["error_by_price_band"] = str(_save(fig, output_dir / "error_by_price_band.svg"))

    fig, ax = _figure()
    ax.scatter(
        predictions.actual, predictions.residual, s=18, color=ACCENT, alpha=0.66, edgecolors="none"
    )
    ax.axhline(0, color=AMBER, linewidth=1.2, linestyle="--")
    ax.set(xlabel="Actual observed price (CAD)", ylabel="Residual: actual − predicted (CAD)")
    ax.xaxis.set_major_formatter(FuncFormatter(_currency))
    ax.yaxis.set_major_formatter(FuncFormatter(_currency))
    ax.grid(color=LINE, linewidth=0.6, alpha=0.55)
    paths["residual_diagnostic"] = str(_save(fig, output_dir / "residual_vs_actual.svg"))

    grouped = (
        predictions.groupby("price_band", observed=True)
        .agg(
            count=("actual", "size"),
            coverage=("covered", "mean"),
            mean_width=("interval_width", "mean"),
        )
        .reset_index()
    )
    grouped["order"] = grouped.price_band.astype(str).map(
        {name: i for i, name in enumerate(PRICE_BAND_ORDER)}
    )
    grouped = grouped.sort_values("order")
    fig, ax = _figure()
    bars = ax.bar(
        [PRICE_BAND_LABELS.get(str(v), str(v)) for v in grouped.price_band],
        grouped.coverage * 100,
        color=ACCENT,
        width=0.62,
    )
    ax.axhline(
        nominal_coverage * 100,
        color=AMBER,
        linewidth=1.2,
        linestyle="--",
        label=f"Nominal {nominal_coverage:.0%}",
    )
    for bar, row in zip(bars, grouped.itertuples(), strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"N={row.count}\nwidth ${row.mean_width:,.0f}",
            ha="center",
            va="bottom",
            color=MUTED,
            fontsize=8,
        )
    ax.set(ylabel="Empirical interval coverage", ylim=(0, 112))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0f}%"))
    ax.grid(axis="y", color=LINE, linewidth=0.6, alpha=0.55)
    ax.legend(frameon=False, labelcolor=TEXT, fontsize=8)
    paths["conformal_by_price_band"] = str(
        _save(fig, output_dir / "conformal_coverage_by_price_band.svg")
    )
    return paths
