from ml.training.train import (
    CV_FOLDS,
    DEFAULT_MLFLOW_EXPERIMENT,
    DEFAULT_MLFLOW_TRACKING_URI,
    DEFAULT_REGISTERED_MODEL,
    FEATURES,
    RANDOM_SEED,
    _mlflow_model_params,
    candidate_models,
)


def test_mlflow_candidate_params_describe_existing_models() -> None:
    models = candidate_models()

    assert set(models) == {
        "linear_regression",
        "random_forest",
        "hist_gradient_boosting",
    }
    for name, pipeline in models.items():
        params = _mlflow_model_params(name, pipeline)
        assert params["candidate"] == name
        assert params["algorithm"] == type(pipeline.named_steps["model"]).__name__
        assert params["random_seed"] == RANDOM_SEED
        assert params["cv_folds"] == CV_FOLDS
        assert params["feature_count"] == len(FEATURES)

    assert models["random_forest"].named_steps["model"].n_estimators == 280
    assert _mlflow_model_params("random_forest", models["random_forest"])["model__max_depth"] == 16


def test_mlflow_defaults_match_integration_contract() -> None:
    assert DEFAULT_MLFLOW_TRACKING_URI == "http://localhost:5000"
    assert DEFAULT_MLFLOW_EXPERIMENT == "pc-value-analyzer"
    assert DEFAULT_REGISTERED_MODEL == "PCValueAnalyzer"
