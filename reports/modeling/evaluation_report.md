# Held-out evaluation report

Model `demo-20260827-v1` · N=240 untouched held-out development observations

## Predicted vs actual

**Question:** How closely do predictions match observations excluded from training?
**Result:** MAE $141.21, RMSE $176.60, R² 0.750.
**Conclusion:** The scatter documents the measured spread around the ideal diagonal; these aggregate metrics quantify it without a qualitative quality claim.

## Error by price band

**Question:** Does absolute error change with actual PC price?
**Result:** Lowest measured MAE: mid ($124.99, N=180); highest: high ($189.89, N=58).
**Conclusion:** Error differs across the configured under-$800 / $800–$1,800 / over-$1,800 segments.
**Limitation:** The smallest segment has N=2; small segments are weak evidence and should not be generalized.

## Residual diagnostic

**Question:** Do residuals (actual − predicted) lean positive or negative or widen by price?
**Result:** Mean held-out residual $11.66; positive means underprediction and negative means overprediction.
**Conclusion:** The figure exposes the observed direction and spread without asserting a pattern from visual inspection alone.
**Limitation:** A residual plot diagnoses this fixed held-out sample; it does not establish future bias.

## Conformal uncertainty

**Question:** Do split-conformal intervals reach their nominal coverage across price bands?
**Result:** Overall empirical coverage 90.0% versus configured 90.0%; mean width $565.92. Segment results: low 100.0% (N=2, width $566), mid 93.9% (N=180, width $566), high 77.6% (N=58, width $566).
**Conclusion:** Measured segment coverage and width show where the fixed evaluation sample differs from the configured target.
**Limitation:** Split-conformal coverage is empirical and exchangeability-dependent, not a guarantee for future listings.
