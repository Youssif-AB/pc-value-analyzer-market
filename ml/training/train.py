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
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

FEATURES = [
    "cpu", "gpu", "ram_type", "storage_type", "condition", "brand",
    "ram_gb", "storage_gb", "system_age_years", "cpu_score", "gpu_score", "condition_score",
]
CATEGORICAL = ["cpu", "gpu", "ram_type", "storage_type", "condition", "brand"]
NUMERIC = ["ram_gb", "storage_gb", "system_age_years", "cpu_score", "gpu_score", "condition_score"]
TARGET = "sold_price"


def make_preprocessor(scale_numeric: bool = False) -> ColumnTransformer:
    numeric_steps: list[tuple[str, object]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scale", StandardScaler()))
    return ColumnTransformer([
        ("categorical", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), CATEGORICAL),
        ("numeric", Pipeline(numeric_steps), NUMERIC),
    ])


def candidate_models() -> dict[str, Pipeline]:
    return {
        "linear_regression": Pipeline([("preprocess", make_preprocessor(scale_numeric=True)), ("model", LinearRegression())]),
        "random_forest": Pipeline([("preprocess", make_preprocessor()), ("model", RandomForestRegressor(n_estimators=280, max_depth=16, min_samples_leaf=2, random_state=42, n_jobs=-1))]),
        "hist_gradient_boosting": Pipeline([("preprocess", make_preprocessor()), ("model", HistGradientBoostingRegressor(max_iter=280, learning_rate=0.055, max_leaf_nodes=24, l2_regularization=0.4, random_state=42))]),
    }


def evaluate(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "r2": float(r2_score(y_true, y_pred)),
    }


def _maybe_log_mlflow(name: str, model: Pipeline, metrics: dict[str, float], cv_mae: float, enabled: bool) -> None:
    if not enabled:
        return
    try:
        import mlflow
        import mlflow.sklearn
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
        mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT_NAME", "pc-value-analyzer"))
        with mlflow.start_run(run_name=name):
            mlflow.log_param("candidate", name)
            mlflow.log_metric("cv_mae", cv_mae)
            for metric, value in metrics.items():
                mlflow.log_metric(metric, value)
            mlflow.sklearn.log_model(model, name="model")
    except Exception as exc:
        print(f"MLflow logging skipped after error: {exc}")



def register_selected_model(model: Pipeline, metadata: dict[str, object], comparison_path: Path) -> str | None:
    """Log the evidence-selected model and assign the registry alias used by serving/deployment."""
    try:
        import mlflow
        import mlflow.sklearn
        from mlflow import MlflowClient

        tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "pc-value-analyzer")
        model_name = os.getenv("MODEL_NAME", "pc-value-regressor")
        alias = os.getenv("MODEL_ALIAS", "champion")
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=f"selected-{metadata['selected_model']}") as run:
            mlflow.set_tags({
                "selection_rule": str(metadata["selection_rule"]),
                "data_scope": "synthetic_demo",
                "lifecycle": "selected",
            })
            for key in ("validation_mae", "validation_rmse", "validation_r2", "cv_mae_mean", "residual_std"):
                mlflow.log_metric(key, float(metadata[key]))
            mlflow.log_param("selected_model", str(metadata["selected_model"]))
            mlflow.log_artifact(str(comparison_path), artifact_path="evaluation")
            mlflow.sklearn.log_model(
                model,
                name="model",
                registered_model_name=model_name,
                input_example=pd.DataFrame([{
                    "cpu": "AMD Ryzen 7 7800X3D", "gpu": "NVIDIA GeForce RTX 4070",
                    "ram_type": "DDR5", "storage_type": "NVMe SSD", "condition": "good",
                    "brand": "custom", "ram_gb": 32, "storage_gb": 2048,
                    "system_age_years": 1.5, "cpu_score": 96, "gpu_score": 72, "condition_score": 0.84,
                }]),
            )
        client = MlflowClient(tracking_uri=tracking_uri)
        versions = [v for v in client.search_model_versions(f"name='{model_name}'") if v.run_id == run.info.run_id]
        if not versions:
            return None
        version = max(versions, key=lambda item: int(item.version)).version
        client.set_registered_model_alias(model_name, alias, version)
        client.set_model_version_tag(model_name, version, "validation_status", "selected_by_cv")
        return str(version)
    except Exception as exc:
        print(f"Selected-model registry logging skipped after error: {exc}")
        return None

def train(input_path: Path, output_path: Path, metadata_path: Path, comparison_path: Path, enable_mlflow: bool = False) -> dict[str, object]:
    frame = pd.read_csv(input_path)
    X = frame[FEATURES]
    y = frame[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    rows: list[dict[str, float | str]] = []
    fitted: dict[str, Pipeline] = {}

    for name, pipeline in candidate_models().items():
        cv_scores = -cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="neg_mean_absolute_error", n_jobs=-1)
        pipeline.fit(X_train, y_train)
        pred = pipeline.predict(X_test)
        metrics = evaluate(y_test, pred)
        row: dict[str, float | str] = {"model": name, "cv_mae_mean": float(cv_scores.mean()), "cv_mae_std": float(cv_scores.std()), **metrics}
        rows.append(row)
        fitted[name] = pipeline
        _maybe_log_mlflow(name, pipeline, metrics, float(cv_scores.mean()), enable_mlflow)

    comparison = pd.DataFrame(rows).sort_values("cv_mae_mean", ascending=True)
    winner_name = str(comparison.iloc[0]["model"])
    winner = fitted[winner_name]
    holdout_pred = winner.predict(X_test)
    residual_std = float(np.std(y_test.to_numpy() - holdout_pred))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(winner, output_path)
    comparison.to_csv(comparison_path, index=False)
    version = f"demo-{datetime.now(UTC).strftime('%Y%m%d')}-v1"
    metadata = {
        "model_version": version,
        "selected_model": winner_name,
        "selection_rule": "lowest 5-fold cross-validation MAE on training split",
        "validation_mae": float(comparison.loc[comparison["model"] == winner_name, "mae"].iloc[0]),
        "validation_rmse": float(comparison.loc[comparison["model"] == winner_name, "rmse"].iloc[0]),
        "validation_r2": float(comparison.loc[comparison["model"] == winner_name, "r2"].iloc[0]),
        "cv_mae_mean": float(comparison.iloc[0]["cv_mae_mean"]),
        "residual_std": residual_std,
        "feature_contract": FEATURES,
        "target": TARGET,
        "data_disclaimer": "Metrics are from the included synthetic demo market dataset, not production market evidence.",
    }
    if enable_mlflow:
        registry_version = register_selected_model(winner, metadata, comparison_path)
        if registry_version is not None:
            metadata["mlflow_registered_version"] = registry_version
            metadata["mlflow_alias"] = os.getenv("MODEL_ALIAS", "champion")
    metadata_path.write_text(json.dumps(metadata, indent=2))
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/processed/training.csv"))
    parser.add_argument("--output", type=Path, default=Path("backend/artifacts/price_model.joblib"))
    parser.add_argument("--metadata", type=Path, default=Path("backend/artifacts/model_metadata.json"))
    parser.add_argument("--comparison", type=Path, default=Path("reports/modeling/model_comparison.csv"))
    parser.add_argument("--mlflow", action="store_true")
    args = parser.parse_args()
    metadata = train(args.input, args.output, args.metadata, args.comparison, args.mlflow)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
