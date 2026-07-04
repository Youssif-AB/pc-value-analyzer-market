# Model card — PC fair-value hybrid estimator

**Structural artifact:** `backend/artifacts/price_model.joblib`
**Demo model version:** `demo-20260820-v1`
**Selected structural estimator:** Linear Regression pipeline
**Runtime estimator:** structural model + optional live comparable calibration

## Intended use

Estimate a rough fair-market price for a user-reviewed desktop PC configuration and compare it with a seller's asking price. The product is decision support, not a guaranteed appraisal, insurance valuation, or financial instrument.

## Structural inputs

Canonical CPU/GPU, RAM amount/type, storage amount/type, condition, brand/builder, age, and engineered CPU/GPU/condition tiers. Asking price is not a model input.

## Live evidence inputs

Recent normalized eBay active asking listings and Best Buy new/open-box desktop prices can calibrate the structural estimate. USD observations are converted to CAD with Bank of Canada FX. Each observation retains provenance, listing type, age, and extraction quality.

## Metrics on included structural demo data

MAE: $138.27; RMSE: $174.02; R²: 0.758; 5-fold CV MAE: $134.37. These are synthetic-demo metrics and must not be represented as real-market performance.

No offline MAE/RMSE claim is attached to the live hybrid layer until it is evaluated against a real held-out completed-sales dataset.

## Uncertainty

The structural API interval starts from holdout residual dispersion and expands when key hardware is missing. Hybrid mode also incorporates comparable-price dispersion. This remains a pragmatic uncertainty heuristic, not a calibrated probabilistic interval.

## Limitations

- active asking prices can be higher than eventual sale prices;
- retail/open-box prices differ from used private-market transactions;
- new/rare hardware may have sparse comparable coverage;
- bundles, peripherals, custom cooling/aesthetics, workstation use, and local pickup effects are incompletely represented;
- condition is subjective;
- source APIs can be unavailable or rate-limited;
- hand-maintained hardware tiers can lag launches;
- current source coverage is not the same as comprehensive local-market coverage;
- the shipped structural artifact uses synthetic demo training data.

The system therefore exposes whether valuation is `model_only` or `hybrid_live_comps`, the live blend weight, comparable count/source count, and source-visible comparable evidence.
