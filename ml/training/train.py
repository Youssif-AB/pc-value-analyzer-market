from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.training.visualization import generate_evaluation_figures, price_bands

FEATURES = [
    "cpu",
    "gpu",
    "ram_type",
    "storage_type",
    "condition",
    "brand",
    "source",
    "ram_gb",
    "storage_gb",
    "system_age_years",
    "cpu_score",
    "gpu_score",
    "condition_score",
    "cpu_generation",
    "gpu_generation",
    "component_age_years",
]
CATEGORICAL = [
    "cpu",
    "gpu",
    "ram_type",
    "storage_type",
    "condition",
    "brand",
    "source",
    "cpu_generation",
    "gpu_generation",
]
NUMERIC = [column for column in FEATURES if column not in CATEGORICAL]
TARGET = "target_price"
RANDOM_SEED = 42
TEST_SIZE = 0.2
CV_FOLDS = 5
DEFAULT_MLFLOW_TRACKING_URI = "http://localhost:5000"
DEFAULT_MLFLOW_EXPERIMENT = "pc-value-analyzer"
DEFAULT_REGISTERED_MODEL = "PCValueAnalyzer"
FEATURE_SETS = {
    "hardware": ["cpu", "gpu", "ram_type", "storage_type", "ram_gb", "storage_gb"],
    "hardware_condition": [
        "cpu",
        "gpu",
        "ram_type",
        "storage_type",
        "ram_gb",
        "storage_gb",
        "condition",
    ],
    "hardware_condition_age": [
        "cpu",
        "gpu",
        "ram_type",
        "storage_type",
        "ram_gb",
        "storage_gb",
        "condition",
        "system_age_years",
        "cpu_generation",
        "gpu_generation",
        "component_age_years",
    ],
    "all": FEATURES,
}


def make_preprocessor(
    scale_numeric: bool = False, features: list[str] | None = None
) -> ColumnTransformer:
    selected = features or FEATURES
    categorical = [x for x in CATEGORICAL if x in selected]
    numeric = [x for x in NUMERIC if x in selected]
    numeric_steps: list[tuple[str, object]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scale", StandardScaler()))
    return ColumnTransformer(
        [
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                categorical,
            ),
            ("numeric", Pipeline(numeric_steps), numeric),
        ]
    )


def candidate_models(features: list[str] | None = None) -> dict[str, Pipeline]:
    return {
        "linear_regression": Pipeline(
            [("preprocess", make_preprocessor(True, features)), ("model", LinearRegression())]
        ),
        "random_forest": Pipeline(
            [
                ("preprocess", make_preprocessor(False, features)),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=280,
                        max_depth=16,
                        min_samples_leaf=2,
                        random_state=RANDOM_SEED,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("preprocess", make_preprocessor(False, features)),
                (
                    "model",
                    HistGradientBoostingRegressor(
                        max_iter=280,
                        learning_rate=0.055,
                        max_leaf_nodes=24,
                        l2_regularization=0.4,
                        random_state=RANDOM_SEED,
                    ),
                ),
            ]
        ),
    }


def evaluate(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "r2": float(r2_score(y_true, y_pred)),
    }


def _mlflow_model_params(name: str, model: Pipeline) -> dict[str, object]:
    estimator = model.named_steps["model"]
    params: dict[str, object] = {
        "algorithm": type(estimator).__name__,
        "candidate": name,
        "random_seed": RANDOM_SEED,
        "test_size": TEST_SIZE,
        "cv_folds": CV_FOLDS,
        "feature_count": len(FEATURES),
    }
    params.update(
        {
            f"model__{k}": v
            for k, v in estimator.get_params(deep=False).items()
            if v is not None and isinstance(v, (str, int, float, bool))
        }
    )
    return params


def add_domain_features(frame: pd.DataFrame) -> pd.DataFrame:
    from backend.app.services.features import CONDITION_SCORE, CPU_SCORE, GPU_SCORE

    result = frame.copy()
    for column, default in (
        ("source", "unknown"),
        ("brand", "custom"),
        ("ram_type", "UNKNOWN"),
        ("storage_type", "UNKNOWN"),
    ):
        if column not in result:
            result[column] = default
    result["cpu_score"] = (
        result["cpu"].map(CPU_SCORE).fillna(result["cpu_score"] if "cpu_score" in result else 35)
    )
    result["gpu_score"] = (
        result["gpu"].map(GPU_SCORE).fillna(result["gpu_score"] if "gpu_score" in result else 30)
    )
    result["condition_score"] = (
        result["condition"]
        .map(CONDITION_SCORE)
        .fillna(result["condition_score"] if "condition_score" in result else 0.84)
    )
    result["cpu_generation"] = (
        result["cpu"]
        .astype(str)
        .str.extract(r"(?:Ryzen\s+\d\s+|i[3579]-|Ultra\s+\d\s+)(\d{1,2})", expand=False)
        .fillna("unknown")
    )
    result["gpu_generation"] = (
        result["gpu"]
        .astype(str)
        .str.extract(r"(?:RTX|RX|Arc\s+[AB])(\d{1,2})", expand=False)
        .fillna("unknown")
    )
    if "system_age_years" not in result:
        result["system_age_years"] = np.nan
    result["component_age_years"] = result["system_age_years"]
    return result


def split_dataset(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    times = (
        pd.to_datetime(frame.get("observed_at"), errors="coerce", utc=True)
        if "observed_at" in frame
        else pd.Series(pd.NaT, index=frame.index)
    )
    if times.isna().any():
        train_val, test = train_test_split(frame, test_size=0.2, random_state=RANDOM_SEED)
        train, calibration = train_test_split(train_val, test_size=0.25, random_state=RANDOM_SEED)
        return (
            train,
            calibration,
            test,
            "deterministic random split (timestamps unavailable; demo only)",
        )
    ordered = frame.assign(_time=times).sort_values("_time")
    group_col = (
        "record_key" if "record_key" in ordered else "source_id" if "source_id" in ordered else None
    )
    if group_col:
        groups = ordered.groupby(group_col, sort=False)["_time"].max().sort_values()
        n = len(groups)
        a, b = max(1, int(n * 0.6)), max(2, int(n * 0.8))
        train_ids, cal_ids = set(groups.index[:a]), set(groups.index[a:b])
        train = ordered[ordered[group_col].isin(train_ids)]
        calibration = ordered[ordered[group_col].isin(cal_ids)]
        test = ordered[~ordered[group_col].isin(train_ids | cal_ids)]
    else:
        a, b = int(len(ordered) * 0.6), int(len(ordered) * 0.8)
        train, calibration, test = ordered.iloc[:a], ordered.iloc[a:b], ordered.iloc[b:]
    if min(len(train), len(calibration), len(test)) == 0:
        raise ValueError("At least five dated listing groups are required")
    return (
        train.drop(columns="_time"),
        calibration.drop(columns="_time"),
        test.drop(columns="_time"),
        "chronological 60/20/20 grouped by listing identity",
    )


def conformal_quantile(y_true: pd.Series, predictions: np.ndarray, coverage: float = 0.9) -> float:
    residuals = np.abs(y_true.to_numpy() - predictions)
    level = min(1.0, np.ceil((len(residuals) + 1) * coverage) / len(residuals))
    return float(np.quantile(residuals, level, method="higher"))


def error_analysis(
    frame: pd.DataFrame, y: pd.Series, prediction: np.ndarray, training: pd.DataFrame
) -> pd.DataFrame:
    work = frame.copy()
    work["actual"] = y.to_numpy()
    work["prediction"] = prediction
    work["residual"] = work.actual - work.prediction
    work["price_band"] = price_bands(work.actual)
    cpu, gpu = training.cpu.value_counts(), training.gpu.value_counts()
    work["coverage_segment"] = np.where(
        ~work.cpu.isin(cpu.index) | ~work.gpu.isin(gpu.index),
        "unseen",
        np.where(
            work.cpu.map(cpu).fillna(0).lt(5) | work.gpu.map(gpu).fillna(0).lt(5), "rare", "common"
        ),
    )
    rows = []
    for column in (
        "price_band",
        "source",
        "condition",
        "cpu_generation",
        "gpu_generation",
        "coverage_segment",
    ):
        for value, group in work.groupby(column, observed=True, dropna=False):
            rows.append(
                {
                    "segment": column,
                    "value": str(value),
                    "count": len(group),
                    "mae": mean_absolute_error(group.actual, group.prediction),
                    "rmse": mean_squared_error(group.actual, group.prediction) ** 0.5,
                    "mean_residual": group.residual.mean(),
                }
            )
    return pd.DataFrame(rows)


def _log_mlflow(
    name: str,
    model: Pipeline,
    row: pd.Series,
    training: pd.DataFrame,
    target: str,
    metadata: dict[str, object],
    artifacts: list[Path],
    enabled: bool,
) -> str | None:
    if not enabled:
        return None
    import mlflow
    import mlflow.sklearn
    from mlflow.models import infer_signature

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", DEFAULT_MLFLOW_TRACKING_URI))
    mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT_NAME", DEFAULT_MLFLOW_EXPERIMENT))
    with mlflow.start_run(run_name=name) as run:
        mlflow.log_params(
            {
                **_mlflow_model_params(name, model),
                "dataset_id": metadata["dataset_id"],
                "split_method": metadata["split_method"],
                "feature_set": "all",
            }
        )
        mlflow.log_metrics(
            {
                "cv_mae_mean": row.cv_mae_mean,
                "cv_mae_std": row.cv_mae_std,
                "test_mae": row.mae,
                "test_rmse": row.rmse,
                "test_r2": row.r2,
                "interval_coverage": metadata["test_interval_coverage"],
                "interval_width": metadata["mean_interval_width"],
            }
        )
        mlflow.set_tags({"data_scope": metadata["data_scope"], "model_role": "candidate"})
        for artifact in artifacts:
            mlflow.log_artifact(str(artifact), artifact_path="evaluation")
        sample = training[FEATURES]
        mlflow.sklearn.log_model(
            model,
            name="model",
            signature=infer_signature(sample, model.predict(sample)),
            input_example=sample.head(5),
        )
        return run.info.run_id


def register_selected_model(run_id: str, metadata: dict[str, object], comparison_path: Path) -> str:
    import mlflow
    from mlflow import MlflowClient

    uri = os.getenv("MLFLOW_TRACKING_URI", DEFAULT_MLFLOW_TRACKING_URI)
    name = os.getenv("MLFLOW_REGISTERED_MODEL_NAME", DEFAULT_REGISTERED_MODEL)
    alias = os.getenv("MLFLOW_MODEL_ALIAS", "champion")
    mlflow.set_tracking_uri(uri)
    registered = mlflow.register_model(f"runs:/{run_id}/model", name)
    MlflowClient(tracking_uri=uri).set_registered_model_alias(name, alias, registered.version)
    return str(registered.version)


def write_evaluation_report(
    path: Path,
    metadata: dict[str, object],
    errors: pd.DataFrame,
    heldout: pd.DataFrame,
) -> None:
    price = errors[errors.segment.eq("price_band")].sort_values("mae")
    lowest, highest = price.iloc[0], price.iloc[-1]
    coverage = heldout.groupby("price_band", observed=True).agg(
        count=("covered", "size"), coverage=("covered", "mean"), width=("interval_width", "mean")
    )
    segment_results = ", ".join(
        f"{index} {row.coverage:.1%} (N={int(row['count'])}, width ${row.width:,.0f})"
        for index, row in coverage.iterrows()
    )
    smallest = int(price["count"].min())
    text = f"""# Held-out evaluation report

Model `{metadata["model_version"]}` · N={metadata["split_counts"]["test"]} untouched held-out observations · {metadata["data_scope"]}

## Predicted vs actual

**Question:** How closely do predictions match observations excluded from training?
**Result:** MAE ${metadata["validation_mae"]:,.2f}, RMSE ${metadata["validation_rmse"]:,.2f}, R² {metadata["validation_r2"]:.3f}.
**Conclusion:** The scatter documents the measured spread around the ideal diagonal; these aggregate metrics quantify it without a qualitative quality claim.
**Limitation:** {metadata["data_disclaimer"]}

## Error by price band

**Question:** Does absolute error change with actual PC price?
**Result:** Lowest measured MAE: {lowest["value"]} (${lowest["mae"]:,.2f}, N={int(lowest["count"])}); highest: {highest["value"]} (${highest["mae"]:,.2f}, N={int(highest["count"])}).
**Conclusion:** Error differs across the configured under-$800 / $800–$1,800 / over-$1,800 segments.
**Limitation:** The smallest segment has N={smallest}; small segments are weak evidence and should not be generalized.

## Residual diagnostic

**Question:** Do residuals (actual − predicted) lean positive or negative or widen by price?
**Result:** Mean held-out residual ${heldout.residual.mean():,.2f}; positive means underprediction and negative means overprediction.
**Conclusion:** The figure exposes the observed direction and spread without asserting a pattern from visual inspection alone.
**Limitation:** A residual plot diagnoses this fixed held-out sample; it does not establish future bias.

## Conformal uncertainty

**Question:** Do split-conformal intervals reach their nominal coverage across price bands?
**Result:** Overall empirical coverage {metadata["test_interval_coverage"]:.1%} versus configured {metadata["conformal_coverage_target"]:.1%}; mean width ${metadata["mean_interval_width"]:,.2f}. Segment results: {segment_results}.
**Conclusion:** Measured segment coverage and width show where the fixed evaluation sample differs from the configured target.
**Limitation:** Split-conformal coverage is empirical and exchangeability-dependent, not a guarantee for future listings.
"""
    path.write_text(text, encoding="utf-8")


def train(
    input_path: Path,
    output_path: Path,
    metadata_path: Path,
    comparison_path: Path,
    enable_mlflow: bool = False,
    manifest_path: Path | None = None,
) -> dict[str, object]:
    frame = add_domain_features(pd.read_csv(input_path))
    target = TARGET if TARGET in frame else "sold_price"
    scope = (
        "synthetic_demo"
        if set(frame.source.astype(str)) == {"synthetic_demo"}
        else "real_market_listing"
    )
    training, calibration, test, split_method = split_dataset(frame)
    groups = training.get("record_key")
    cv = (
        GroupKFold(n_splits=min(CV_FOLDS, training.record_key.nunique()))
        if groups is not None and training.record_key.nunique() >= 2
        else KFold(CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)
    )
    baseline = float(training[target].median())
    rows = [
        {
            "model": "overall_median_baseline",
            "cv_mae_mean": mean_absolute_error(
                calibration[target], np.full(len(calibration), baseline)
            ),
            "cv_mae_std": 0.0,
            **evaluate(test[target], np.full(len(test), baseline)),
        }
    ]
    fitted = {}
    for name, pipeline in candidate_models().items():
        scores = -cross_val_score(
            pipeline,
            training[FEATURES],
            training[target],
            cv=cv,
            groups=groups,
            scoring="neg_mean_absolute_error",
            n_jobs=-1,
        )
        pipeline.fit(training[FEATURES], training[target])
        cal_pred = pipeline.predict(calibration[FEATURES])
        test_pred = pipeline.predict(test[FEATURES])
        rows.append(
            {
                "model": name,
                "cv_mae_mean": scores.mean(),
                "cv_mae_std": scores.std(),
                **evaluate(test[target], test_pred),
            }
        )
        fitted[name] = (pipeline, cal_pred, test_pred)
    comparison = pd.DataFrame(rows).sort_values("cv_mae_mean")
    winner_name = str(comparison[comparison.model.ne("overall_median_baseline")].iloc[0].model)
    winner, cal_pred, test_pred = fitted[winner_name]
    quantile = conformal_quantile(calibration[target], cal_pred)
    coverage = float(
        np.mean(
            (test[target].to_numpy() >= test_pred - quantile)
            & (test[target].to_numpy() <= test_pred + quantile)
        )
    )
    ablations = []
    for feature_id, selected in FEATURE_SETS.items():
        model = candidate_models(selected)[winner_name]
        model.fit(training[selected], training[target])
        ablations.append(
            {
                "feature_set": feature_id,
                "feature_count": len(selected),
                **evaluate(calibration[target], model.predict(calibration[selected])),
            }
        )
    errors = error_analysis(test, test[target], test_pred, training)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(winner, output_path)
    comparison.to_csv(comparison_path, index=False)
    ablation_path = comparison_path.with_name("feature_ablation.csv")
    error_path = comparison_path.with_name("error_analysis.csv")
    pd.DataFrame(ablations).to_csv(ablation_path, index=False)
    errors.to_csv(error_path, index=False)
    heldout = pd.DataFrame(
        {
            "actual": test[target].to_numpy(),
            "prediction": test_pred,
            "residual": test[target].to_numpy() - test_pred,
            "lower": test_pred - quantile,
            "upper": test_pred + quantile,
        }
    )
    heldout["covered"] = heldout.actual.between(heldout.lower, heldout.upper)
    heldout["interval_width"] = heldout.upper - heldout.lower
    heldout["price_band"] = price_bands(heldout.actual)
    heldout_path = comparison_path.with_name("heldout_predictions.csv")
    heldout.to_csv(heldout_path, index=False)
    figure_paths = generate_evaluation_figures(
        heldout, errors, comparison_path.parent / "figures", nominal_coverage=0.9
    )
    manifest = (
        json.loads(manifest_path.read_text()) if manifest_path and manifest_path.exists() else {}
    )
    config_counts = training.groupby(["cpu", "gpu"]).size()
    metrics = evaluate(test[target], test_pred)
    model_version = (
        f"{'demo' if scope == 'synthetic_demo' else 'market'}-"
        f"{datetime.now(UTC).strftime('%Y%m%d')}-v1"
    )
    metadata = {
        "model_version": model_version,
        "selected_model": winner_name,
        "selection_rule": "lowest grouped training CV MAE; final metrics from untouched test split",
        "target": target,
        "target_definition": "synthetic demo sold price"
        if scope == "synthetic_demo"
        else "observed market listing price in CAD",
        "data_scope": scope,
        "dataset_id": manifest.get("dataset_id", "unmanifested-demo"),
        "split_method": split_method,
        "split_counts": {
            "train": len(training),
            "calibration": len(calibration),
            "test": len(test),
        },
        "validation_mae": metrics["mae"],
        "validation_rmse": metrics["rmse"],
        "validation_r2": metrics["r2"],
        "conformal_coverage_target": 0.9,
        "conformal_quantile": quantile,
        "test_interval_coverage": coverage,
        "mean_interval_width": 2 * quantile,
        "evaluation_figures": {
            name: {
                "path": str(Path(path).as_posix()),
                "model_version": model_version,
            }
            for name, path in figure_paths.items()
        },
        "feature_contract": FEATURES,
        "training_frequencies": {
            "cpu": training.cpu.value_counts().to_dict(),
            "gpu": training.gpu.value_counts().to_dict(),
            "configuration": {
                "|||".join(map(str, key)): int(value) for key, value in config_counts.items()
            },
        },
        "data_disclaimer": "Metrics are from synthetic demo data, not real-market evidence."
        if scope == "synthetic_demo"
        else "The target is active asking/listing price, not verified completed-sale value.",
    }
    report_path = comparison_path.with_name("evaluation_report.md")
    write_evaluation_report(report_path, metadata, errors, heldout)
    run_ids = {}
    for name, (model, _, _) in fitted.items():
        row = comparison[comparison.model.eq(name)].iloc[0]
        run_id = _log_mlflow(
            name,
            model,
            row,
            training,
            target,
            metadata,
            [comparison_path, ablation_path, error_path, heldout_path, report_path]
            + ([Path(path) for path in figure_paths.values()] if name == winner_name else []),
            enable_mlflow,
        )
        if run_id:
            run_ids[name] = run_id
    if enable_mlflow:
        metadata.update(
            {
                "mlflow_run_ids": run_ids,
                "mlflow_registered_model": os.getenv(
                    "MLFLOW_REGISTERED_MODEL_NAME", DEFAULT_REGISTERED_MODEL
                ),
                "mlflow_registered_version": register_selected_model(
                    run_ids[winner_name], metadata, comparison_path
                ),
                "mlflow_alias": os.getenv("MLFLOW_MODEL_ALIAS", "champion"),
            }
        )
    metadata_path.write_text(json.dumps(metadata, indent=2))
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/processed/training.csv"))
    parser.add_argument("--output", type=Path, default=Path("backend/artifacts/price_model.joblib"))
    parser.add_argument(
        "--metadata", type=Path, default=Path("backend/artifacts/model_metadata.json")
    )
    parser.add_argument(
        "--comparison", type=Path, default=Path("reports/modeling/model_comparison.csv")
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--mlflow", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            train(
                args.input, args.output, args.metadata, args.comparison, args.mlflow, args.manifest
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
