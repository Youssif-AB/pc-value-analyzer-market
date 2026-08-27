# MLflow experiment and registry contract

The training pipeline logs each candidate's parameters, full preprocessing/inference pipeline, input example, model signature, and holdout MAE/RMSE/R² metrics to the `pc-value-analyzer` experiment. The selected candidate's Tracking run also receives the predicted-vs-actual, price-band error, residual, and conformal-coverage SVGs, held-out plot inputs, and generated evaluation report under `evaluation/`. After the unchanged five-fold cross-validation rule chooses the winner, that candidate run's model is registered as `PCValueAnalyzer`.

The selected registry version receives the `champion` alias and `validation_status=selected_by_cv`. Application code can therefore target a promotion decision rather than hard-code a model version.

`MLFLOW_TRACKING_URI` configures the server and defaults to `http://localhost:5000` for host-based training. `MLFLOW_EXPERIMENT_NAME`, `MLFLOW_REGISTERED_MODEL_NAME`, and `MLFLOW_MODEL_ALIAS` can override the defaults. No ModelControl source dependency is used: integration is exclusively through the MLflow API.

Run tracking explicitly with:

```bash
python -m ml.training.train --mlflow
```

Without `--mlflow`, the same local training and artifact export workflow runs without contacting an MLflow server. The Docker Compose stack in this repository exposes its own optional MLflow service on port 5002; containers reach that service at `http://mlflow:5000`.

## What MLflow does not do

The live comparable cache is not an MLflow experiment and active market listings are not automatically fed into model training. A retraining run must be supplied a training dataset with a defensible target such as completed sale price and must independently pass validation/CV/failure analysis before promotion.

A future licensed sold-data source can be added to the Prefect training flow without changing the runtime live-market adapter contract.
