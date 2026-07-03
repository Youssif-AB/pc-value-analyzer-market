# Model card — PC fair-value regressor

**Model artifact:** `backend/artifacts/price_model.joblib`  
**Demo model version:** `demo-20260820-v1`  
**Selected estimator:** Linear Regression pipeline  
**Selection rule:** lowest 5-fold CV MAE on the training split

## Intended use

Estimate a rough fair-market price for a reviewed desktop PC configuration and compare it with a seller's asking price. The model supports decision assistance, not guaranteed appraisal, insurance valuation, or financial advice.

## Inputs

Canonical CPU/GPU, RAM amount/type, storage amount/type, condition, brand/builder, age, and engineered CPU/GPU/condition scores. Asking price is not a model input.

## Metrics on included demo data

MAE: $138.27; RMSE: $174.02; R²: 0.758; 5-fold CV MAE: $134.37. These are synthetic-demo metrics and must not be represented as real-market performance.

## Uncertainty

The API derives an interval from holdout residual dispersion and expands it when key hardware is missing. This is a pragmatic uncertainty heuristic, not a calibrated probabilistic interval.

## Limitations

The artifact ships for reproducibility. It requires retraining on licensed, recent, region-appropriate market observations before production pricing claims are defensible. New hardware, unusual custom builds, bundles, mining/workstation configurations, and ambiguous condition can produce larger error.
