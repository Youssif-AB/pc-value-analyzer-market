from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def create_review_sample(dataset_path: Path, output_path: Path, rows: int = 100) -> None:
    frame = pd.read_csv(dataset_path)
    candidates = frame[
        ["source", "source_listing_id", "cpu_raw", "cpu", "gpu_raw", "gpu"]
    ].drop_duplicates()
    sample = candidates.sample(min(rows, len(candidates)), random_state=42).copy()
    sample["reviewed_cpu"] = ""
    sample["reviewed_gpu"] = ""
    sample["review_notes"] = ""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(output_path, index=False)


def evaluate_review(review_path: Path, report_path: Path) -> dict[str, object]:
    frame = pd.read_csv(review_path, keep_default_na=False)
    reviewed = frame[
        (frame.reviewed_cpu.str.strip() != "") | (frame.reviewed_gpu.str.strip() != "")
    ]
    if reviewed.empty:
        raise ValueError("No human-reviewed labels found; fill reviewed_cpu/reviewed_gpu first")
    metrics: dict[str, object] = {"reviewed_rows": len(reviewed)}
    for component in ("cpu", "gpu"):
        eligible = reviewed[reviewed[f"reviewed_{component}"].str.strip() != ""]
        metrics[f"{component}_reviewed"] = len(eligible)
        metrics[f"{component}_accuracy"] = (
            float(eligible[component].eq(eligible[f"reviewed_{component}"]).mean())
            if len(eligible)
            else None
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(metrics, indent=2))
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sample = sub.add_parser("sample")
    sample.add_argument("--dataset", type=Path, required=True)
    sample.add_argument("--output", type=Path, default=Path("data/review/normalization_sample.csv"))
    sample.add_argument("--rows", type=int, default=100)
    score = sub.add_parser("score")
    score.add_argument("--review", type=Path, required=True)
    score.add_argument("--report", type=Path, default=Path("reports/normalization_quality.json"))
    args = parser.parse_args()
    if args.command == "sample":
        create_review_sample(args.dataset, args.output, args.rows)
    else:
        print(json.dumps(evaluate_review(args.review, args.report), indent=2))


if __name__ == "__main__":
    main()
