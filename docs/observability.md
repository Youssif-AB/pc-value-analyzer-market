# Inference observability

The FastAPI service exposes Prometheus-format metrics at `/metrics`.

Tracked signals include prediction latency, missing key extraction fields, normalization failures, prediction counts by value rating/confidence, and API errors. Prediction records in PostgreSQL also retain model version and latency for audit/debugging.

For a public deployment, dashboards should additionally aggregate input feature distributions (CPU/GPU tier, RAM/storage, condition, age) and prediction distributions over time. Alerts should focus on shifts that indicate model staleness: rising unknown-hardware rates, sustained latency regressions, large changes in predicted-price distribution, or a sudden increase in low-confidence predictions.

Ground-truth pricing arrives later than inference, so model-error monitoring requires joining eventual observed/sold outcomes back to prediction records. Without that feedback, production monitoring can detect drift and extraction problems but cannot truthfully claim live MAE.
