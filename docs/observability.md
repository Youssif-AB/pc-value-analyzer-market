# Inference and live-market observability

The FastAPI service exposes Prometheus-format metrics at `/metrics`.

## Inference signals

- prediction latency;
- extraction failures by missing key field;
- normalization failures by component;
- prediction counts by rating and confidence;
- API errors.

## Live-market signals

- comparable count per valuation;
- live-market blend weight per valuation;
- active market-cache rows by source;
- source fetch/accept/reject counts in `market_refresh_runs`;
- duplicate fingerprints;
- insert/update/purge counts;
- source failures and partial-refresh status;
- newest observation timestamp per provider.

These signals answer different operational questions. A low comparable count means the live calibration is weak even if provider ingestion itself is healthy. A high cache count with low match count can indicate normalization lag or a market inventory mismatch.

## Drift and delayed truth

Dashboards should aggregate input distributions (CPU/GPU tier, RAM/storage, condition, age), prediction distributions, unknown-hardware rate, comparable similarity, and live blend weight over time.

True production error still requires an observed outcome later. Without joining eventual sale outcomes back to prior predictions, telemetry can detect drift, stale feeds, provider failures, parsing failures, and unusual prediction distributions—but it cannot truthfully claim live MAE/RMSE.

Active asking prices should not be used as a fake ground-truth shortcut for monitoring accuracy.
