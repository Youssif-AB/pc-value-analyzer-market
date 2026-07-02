# MLflow experiment and registry contract

The training pipeline logs every candidate's parameters and MAE/RMSE/R² metrics to the `pc-value-analyzer` experiment. After cross-validation chooses the winner, the selected pipeline is logged again with the model-comparison table and registered as `pc-value-regressor`.

The selected registry version receives the `champion` alias and a `validation_status=selected_by_cv` tag. This keeps the application/deployment contract stable while allowing new model versions to be registered and promoted without hard-coding a version number.

For local development, `docker compose up` starts a database-backed MLflow tracking/registry server at port 5000. The backend store is PostgreSQL and model artifacts use the `mlflow_artifacts` Docker volume.

The included artifact and metrics are based on synthetic demo data. Promotion of a real production model should require a licensed recent dataset, passing data-quality checks, acceptable holdout and cross-validation metrics, and reviewed failure analysis.
