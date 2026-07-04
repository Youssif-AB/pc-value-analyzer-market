# PC Specs / Value Analyzer

An end-to-end ML product that turns a messy PC marketplace listing into **reviewable normalized hardware specs**, lets the user correct extraction mistakes, estimates fair value, and explains whether the asking price looks overpriced, fair, or like a good deal.

The current version is a **hybrid valuation system**. A reproducible regression model provides a structural baseline, while fresh comparable PC listings from multiple live sources calibrate that baseline to the current market when enough similar observations are available.

> **Data/accuracy boundary:** the checked-in regression artifact is trained on a synthetic but realistic demo dataset so the full research and deployment workflow is reproducible without redistributing marketplace datasets. Live eBay and Best Buy observations are used as short-lived comparable-market evidence, not silently relabeled as completed-sale ground truth. Real production accuracy still requires licensed recent sold-price data and measured validation against eventual outcomes.

## Product flow

```text
Paste full PC listing
→ extract CPU/GPU/RAM/storage/condition/price
→ normalize messy hardware names
→ show extracted specs
→ user reviews/corrects them
→ feature engineering
→ structural ML estimate
→ retrieve fresh similar market listings
→ hardware-adjust + freshness-weight comparables
→ blend live evidence only when coverage is sufficient
→ compare estimate with asking price
→ value rating + explanation + uncertainty + comparable provenance
```

The correction step remains mandatory. A wrong CPU/GPU/RAM extraction can materially distort both the ML estimate and comparable matching.

## Live market sources

The repository includes permissioned/API-based source adapters rather than HTML scrapers:

| Source | Evidence | Currency | Credential | Role |
|---|---|---|---|---|
| eBay Browse API | active fixed-price / best-offer desktop listings | CAD on `EBAY_CA` | eBay client ID + secret | used-market comparables |
| Best Buy Products + Buying Options APIs | current new retail and open-box gaming desktops | USD | Best Buy API key | retail/open-box market anchor |
| Bank of Canada Valet API | current USD→CAD exchange rate | FX | none | currency normalization |

Active asking and retail prices are **not equivalent to sold prices**. The code stores their provenance and `listing_type`, applies short retention/freshness rules, and only uses them for live calibration. eBay completed-sales history is not treated as generally available because the relevant Marketplace Insights access is restricted.

## Hybrid valuation rule

For a reviewed target PC:

1. The production sklearn pipeline predicts a baseline fair value.
2. Recent live observations are filtered for parse quality and freshness.
3. CPU, GPU, RAM, storage, RAM/storage type, and condition determine comparable similarity.
4. Each comparable is hardware-adjusted using the model's price delta between the target configuration and the comparable configuration.
5. Adjusted comparable prices are aggregated with similarity and freshness weighting.
6. The market estimate is blended with the structural model only when at least three sufficiently similar comparables exist. The live weight is capped so a few noisy seller listings cannot fully override the model.
7. The response exposes comparable count, source diversity, median asking price, adjusted market estimate, blend weight, source links, and an explicit active-listing limitation.

If live sources are unavailable, stale, or too dissimilar, inference automatically falls back to model-only mode.

## What is implemented

### Data science / modeling

- Jupyter research workflow: `notebooks/price_model_analysis.ipynb`
- data ingestion, cleaning, missing-value and distribution analysis
- anomaly/outlier analysis and explicit data-quality quarantine
- CPU/GPU/RAM/storage normalization analysis, including current RTX 50 / Radeon 9000 / Ryzen 9000 / Core Ultra aliases
- leak-free feature engineering
- Linear Regression baseline plus Random Forest and Histogram Gradient Boosting
- MAE, RMSE, R², 5-fold cross-validation
- feature-importance/coefficient analysis
- error analysis by price band, condition, rare/unknown hardware sensitivity
- evidence-based production-model selection
- exported sklearn preprocessing + model pipeline
- MLflow experiment logging, registry integration, and `champion` alias
- explicit methodology separating sold-price training targets from active-market calibration data

### Live data engineering

- eBay Browse source adapter with OAuth client-credentials flow
- Best Buy Products + open-box source adapter
- Bank of Canada FX adapter with optional deterministic override
- source-level failure isolation so one provider outage does not destroy the entire refresh
- raw listing normalization through the same extraction contract used by the product
- duplicate fingerprint detection and source/listing upserts
- malformed/invalid observation rejection
- extraction-quality scores
- per-source provenance, first/last seen timestamps, TTL expiry, and active flags
- PostgreSQL market cache and refresh-run audit records
- Prefect refresh flow with retries and hourly schedule
- live market quality report at `reports/live_market_quality.json`

### Product / engineering

- React + TypeScript listing input, loading/error states, spec review/correction, result explanation, responsive styling
- live market status banner and comparable evidence cards
- FastAPI extraction, correction, prediction, market status/refresh, health, and Prometheus endpoints
- PostgreSQL entities for listings, normalized specs, corrections, predictions, model metadata, live market observations, and refresh runs
- inference observability for latency, extraction failures, normalization failures, comparable counts, live blend weights, cache size, confidence/rating distribution
- Docker Compose for web, API, PostgreSQL, MLflow, Prefect Server, and the scheduled market refresher
- automated tests for normalization, messy extraction, feature engineering, malformed inputs, API inference, deterministic model behavior, database integration, provider adapters, FX, live-market dedupe, and hybrid comparable selection
- GitHub Actions CI for Python tests/lint, frontend build, and container builds
- Azure Container Apps deployment scaffolding

## Evidence-selected demo model

The checked-in demo run selects the model with the lowest mean 5-fold cross-validation MAE on the training split:

| Model | CV MAE | Holdout MAE | RMSE | R² |
|---|---:|---:|---:|---:|
| **Linear Regression** | **$134.37** | **$138.27** | **$174.02** | **0.758** |
| Histogram Gradient Boosting | $147.46 | $160.36 | $198.60 | 0.684 |
| Random Forest | $158.02 | $175.41 | $221.72 | 0.606 |

These are synthetic-demo metrics, not real-market accuracy claims. The simpler model wins the included comparison by measured generalization rather than prestige.

## Repository structure

```text
backend/                 FastAPI app, serving, market matching, DB models
backend/artifacts/       exported demo model + version metadata
frontend/                React + TypeScript + Vite UI
ml/market_sources/       eBay, Best Buy, FX source adapters
ml/pipeline/             training flow + live-market refresh flow
ml/training/             model comparison, export, MLflow registration
data/raw/                reproducible demo sold-market observations
data/processed/          valid training data + quarantined rows
notebooks/               visible research/model-development notebook
reports/                 quality, model, error, and live-market artifacts
db/                      PostgreSQL migration/init
docs/                    architecture, live sources, pipeline, methodology, deployment
infra/azure/             Azure Container Apps Bicep
.github/workflows/       CI and production deployment workflows
tests/                   unit/API/integration/source/model-consistency tests
```

## Quick start — local stack

This compose file deliberately uses host ports that can coexist with the user's existing TransactScope project:

```text
PC Value web      8080
PC Value API      8001
PC Value MLflow   5001
Prefect           4200
PostgreSQL        5432
```

Create `.env`:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

### Add live source credentials

Edit `.env` and set at least one market provider:

```dotenv
EBAY_CLIENT_ID=your-ebay-client-id
EBAY_CLIENT_SECRET=your-ebay-client-secret
BESTBUY_API_KEY=your-best-buy-api-key
MARKET_REFRESH_TOKEN=replace-this-for-any-public-deployment
```

Bank of Canada FX requires no key. If no provider credentials are configured, the app still runs but valuation stays in `model_only` mode.

Start everything:

```bash
docker compose up --build
```

Open:

- web app: `http://localhost:8080`
- FastAPI docs: `http://localhost:8001/docs`
- market status: `http://localhost:8001/api/v1/market/status`
- Prometheus metrics: `http://localhost:8001/metrics`
- MLflow: `http://localhost:5001`
- Prefect Server: `http://localhost:4200`

The `market-refresher` container performs an immediate refresh and then serves an hourly Prefect schedule. Provider failures are isolated and written to refresh-run metadata rather than crashing valuation.

## Manual market refresh

The scheduled Prefect flow is the normal path. For development, the API also exposes an authenticated refresh endpoint:

```bash
curl -X POST http://localhost:8001/api/v1/market/refresh \
  -H "X-Market-Refresh-Token: $MARKET_REFRESH_TOKEN"
```

Check cache/source status:

```bash
curl http://localhost:8001/api/v1/market/status
```

## Local Python development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
uvicorn backend.app.main:app --reload --port 8001
```

Run one live-market refresh directly:

```bash
python - <<'PY'
from ml.pipeline.live_market import refresh_with_app_database
print(refresh_with_app_database())
PY
```

Run the scheduled Prefect market flow:

```bash
export PREFECT_API_URL=http://localhost:4200/api
python -m ml.pipeline.live_market_flow
```

Generate demo sold-price data and retrain the baseline:

```bash
python -m ml.data.generate_sample_data --rows 1200 --output data/raw/sample_market_listings.csv
python -m ml.pipeline.flow
```

## API contract

Core endpoints:

- `POST /api/v1/extract` — parse and normalize a listing
- `POST /api/v1/extract/review` — parse plus readiness signal
- `POST /api/v1/corrections` — persist reviewed user corrections
- `POST /api/v1/predict` — hybrid valuation from corrected specs
- `GET /api/v1/market/status` — source configuration/cache freshness
- `POST /api/v1/market/refresh` — authenticated manual refresh
- `GET /health` — liveness
- `GET /metrics` — inference/live-market telemetry

`asking_price` is never a model feature. It is only compared with the estimated fair value after inference.

## Testing

```bash
pytest -q
```

The current backend/data suite has **22 passing tests**, including mocked eBay/Best Buy provider calls, FX conversion, live ingestion/deduplication, multi-source comparable selection, normalization, extraction edge cases, feature leakage protection, API behavior, deterministic inference, and SQLAlchemy persistence.

Frontend CI runs TypeScript lint/build independently. Dependency installation timed out in the artifact-generation environment, so the final frontend build is intentionally left to CI/Docker rather than falsely reported as locally verified here.

## Documentation index

- `docs/architecture.md` — runtime + live-data architecture
- `docs/live-market-sources.md` — provider contract, credentials, retention, source semantics
- `docs/data-pipeline.md` — sold-price training path and active-market refresh path
- `docs/modeling-methodology.md` — model selection + hybrid calibration rationale
- `docs/failure-analysis.md` — model and live-market failure modes
- `docs/model-card.md` — intended use, metrics, hybrid limitations
- `docs/mlflow.md` — tracking/registry contract
- `docs/observability.md` — production telemetry and delayed ground truth
- `docs/deployment.md` — Linux/Azure/GitHub deployment path
- `docs/demo.md` — end-to-end walkthrough

## Development history

The archive keeps the requested **35-commit repository shape** without backdating Git timestamps. The June 21–July 8 distribution remains a planning/milestone document rather than falsified history.

## Interview story

> I built a full-stack PC valuation product that extracts and normalizes messy listings, makes the user review critical specs, compares multiple regression models in Jupyter and MLflow, serves the evidence-selected model, continuously pools fresh eBay and Best Buy market observations with Prefect, normalizes currency with Bank of Canada data, deduplicates and quality-checks the feed, and combines structural ML estimates with provenance-visible live comparables instead of pretending active asking prices are sold-price labels.
