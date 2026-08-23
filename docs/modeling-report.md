# Modeling report

## Evidence status and target

No authorized historical real-listing export is checked into this repository. Therefore the number of real usable training observations is **0**, no real date range exists, and no real-world accuracy is claimed. The shipped artifact remains a development demonstration trained on 1,196 validated synthetic rows.

When an authorized eBay, Best Buy, Google Shopping, open-dataset, or user export is imported, the supervised target is **observed market listing price in CAD**. It is an asking/listing price, not a completed-sale price or verified resale outcome. A completed-price target may only be configured for a source whose provenance establishes that semantic.

## Pipeline and provenance

`ml.data.market_dataset` accepts a documented CSV export, requires source/listing identity, timestamp, title, observed price, currency, condition, and hardware fields, and writes separate normalized, validated, rejected, quality-report, and manifest outputs. The manifest contains a SHA-256 digest, row counts, target definition, currency, and date range. Non-CAD observations require an explicit precomputed `price_cad`; the pipeline never invents or silently fetches an FX rate.

Duplicates are grouped by source/listing ID. Missing timestamps, invalid prices, invalid capacities, duplicate rows, and absent FX values are quarantined with a reason. The quality report includes raw/valid/rejected/duplicate counts, missing-component rates, source counts, normalization resolution, and price quantiles.

## Validation and leakage controls

Real timestamped data is sorted chronologically into oldest 60% training, next 20% calibration, and newest 20% untouched test data. All snapshots sharing a listing identity remain in one split. Model selection uses grouped folds inside the training period. The calibration period is reserved for split-conformal intervals and feature-ablation comparison. The newest test period is read only for final metrics and interval coverage.

The timestamp-free synthetic fixture necessarily uses a seeded 60/20/20 random demo split. That result is not evidence for deployment.

## Current demo results

| Candidate | Test MAE | Test RMSE | R² |
|---|---:|---:|---:|
| Overall median | $279 | $353 | 0.00 |
| Linear regression | $141 | $177 | 0.75 |
| Histogram gradient boosting | see `reports/modeling/model_comparison.csv` | | |
| Random forest | see `reports/modeling/model_comparison.csv` | | |

Linear regression is the demo champion because it has the lowest training cross-validation MAE. The 90% split-conformal interval has 90% empirical demo-test coverage and a mean width of $566. These figures are synthetic-only.

Feature-ablation measurements are in `reports/modeling/feature_ablation.csv`. Segment counts, MAE, RMSE, and mean residual by price band, source, condition, CPU/GPU generation, and common/rare/unseen coverage are in `reports/modeling/error_analysis.csv`. They must be regenerated after a real import; no feature or segment conclusion from the demo data is asserted as a market finding.

## Normalization

CPU/GPU aliases return a canonical ID, match status, confidence, and reason. Unmatched values remain unresolved instead of being coerced. Run `ml.data.normalization_review sample` to produce a deterministic representative review sheet, have a human fill the reviewed identifiers, then run `score`. No normalization accuracy is claimed until that reviewed benchmark exists.

## Uncertainty and coverage

The fitted absolute residual quantile from the calibration period forms the split-conformal interval. The API exposes target and measured test coverage, plus training-frequency coverage for CPU, GPU, and their combination. Rare/unseen hardware lowers confidence and widens the interval. Coverage is empirical and not guaranteed for shifted markets or individual listings.

## MLflow and selection

Each candidate run logs dataset ID, split method, feature set, parameters, CV MAE, held-out MAE/RMSE/R², interval coverage/width, the trained pipeline, comparison, ablation, and error artifacts. Only the selected candidate is registered and assigned the `champion` alias. Dataset identity in model metadata ties serving to the creating manifest.

## Required human/external input

Before production training: supply a sufficiently large authorized listing export with timestamps and stable listing IDs, document its terms/license, run the importer, review the normalization sample, and decide whether active asking price meets the product need. Completed-sale valuation requires a separately authorized sold-price source. Live comparables remain independent current evidence and are not training ground truth.
