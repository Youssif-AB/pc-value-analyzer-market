# Data pipeline

```mermaid
flowchart TD
    A[Raw listing / market observations] --> B[Schema and field validation]
    B --> C{Pass quality rules?}
    C -->|No| Q[Quarantine rejected rows + reason counts]
    C -->|Yes| D[Canonical CPU/GPU/RAM/storage normalization]
    D --> E[Feature engineering]
    E --> F[Training-ready dataset]
    F --> G[Train/test split]
    G --> H[5-fold CV across candidate regressors]
    H --> I[Holdout MAE / RMSE / R²]
    I --> J[Failure analysis + explainability]
    J --> K[Export selected pipeline]
    K --> L[MLflow registry champion alias]
```

## Data-quality checks

`ml.pipeline.quality.validate_market_data` rejects or records duplicate source IDs/rows, missing CPU/GPU, impossible RAM/storage capacity, impossible target prices, and normalization failures. The flow writes both the valid training dataset and a rejected-row file plus JSON quality statistics.

The quality layer is deliberately before training. A model should not silently absorb malformed prices or impossible hardware values and then make those defects part of its learned behavior.

## Source adapter contract

The included CSV is synthetic demo data. A real source adapter should output the same columns (`source_id`, normalized hardware candidates, condition, age, asking price if available, and an observed target such as sold price). Marketplace terms, licensing, and privacy constraints should be reviewed before adding a scraper. The rest of the pipeline is source-agnostic.
