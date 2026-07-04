from prometheus_client import Counter, Gauge, Histogram

PREDICTION_LATENCY = Histogram("pcvalue_prediction_latency_seconds", "Prediction endpoint latency")
EXTRACTION_FAILURES = Counter("pcvalue_extraction_failures_total", "Listings missing key extracted hardware", ["field"])
NORMALIZATION_FAILURES = Counter("pcvalue_normalization_failures_total", "Unrecognized normalized hardware aliases", ["component"])
PREDICTIONS = Counter("pcvalue_predictions_total", "Prediction requests", ["rating", "confidence"])
API_ERRORS = Counter("pcvalue_api_errors_total", "Unhandled API errors", ["route"])
LIVE_MARKET_COMPS = Histogram("pcvalue_live_market_comp_count", "Number of fresh comparables used per valuation")
LIVE_MARKET_BLEND = Histogram("pcvalue_live_market_blend_weight", "Weight assigned to live market comparables")
LIVE_MARKET_CACHE = Gauge("pcvalue_live_market_cache_rows", "Current active live market cache rows", ["source"])
