# MLflow experiment and registry contract

The training pipeline logs candidate parameters and MAE/RMSE/R² metrics to the `pc-value-analyzer` experiment. After cross-validation chooses the winner, the selected sklearn pipeline is registered as `pc-value-regressor`.

The selected registry version receives the `champion` alias and `validation_status=selected_by_cv`. Application code can therefore target a promotion decision rather than hard-code a model version.

Locally, Docker Compose exposes MLflow at `http://localhost:5002`; containers reach it at `http://mlflow:5000`. Its backend store is PostgreSQL and artifacts use the `mlflow_artifacts` volume.

## What MLflow does not do

The live comparable cache is not an MLflow experiment and active market listings are not automatically fed into model training. A retraining run must be supplied a training dataset with a defensible target such as completed sale price and must independently pass validation/CV/failure analysis before promotion.

A future licensed sold-data source can be added to the Prefect training flow without changing the runtime live-market adapter contract.
