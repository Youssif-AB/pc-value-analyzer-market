# Modeling methodology

## Objective and target hygiene

The structural model estimates fair value from reviewed hardware and condition features. The included training target is `sold_price`. `asking_price` is explicitly excluded from the model feature contract and is only compared with the final valuation afterward.

The live system adds current asking/retail/open-box observations, but these are **not promoted into training labels**. Seller asking prices and store retail prices answer a different question from a completed transaction. Treating them as the same target would introduce systematic label bias.

## Candidate models and selection

The reproducible demo run compares Linear Regression, Random Forest, and Histogram Gradient Boosting. Selection uses the lowest mean 5-fold cross-validation MAE on the training split, then reports holdout MAE, RMSE, and R².

| Candidate | CV MAE | Holdout MAE | RMSE | R² |
|---|---:|---:|---:|---:|
| Linear Regression | $134.37 | $138.27 | $174.02 | 0.758 |
| Histogram Gradient Boosting | $147.46 | $160.36 | $198.60 | 0.684 |
| Random Forest | $158.02 | $175.41 | $221.72 | 0.606 |

Linear Regression is the shipped demo winner. That is evidence about this dataset/split, not a universal claim about PC pricing.

## Feature engineering

The structural contract uses canonical CPU/GPU identity, compact ordinal CPU/GPU performance tiers, RAM capacity/type, storage capacity/type, condition, brand/prebuilt indicator, and system age. Current normalization covers RTX 50-series, Radeon 9000-series, Ryzen 9000-series, Intel Core Ultra, and common prior generations.

The hand-maintained performance tiers are coarse ordering features, not benchmark scores. Exact benchmark precision would create false confidence and maintenance burden; canonical identity remains available to the model as a categorical feature.

Categorical values are one-hot encoded with unknown-category handling. Numeric fields are median-imputed. The preprocessing graph is exported inside the sklearn pipeline so notebook and API inference share the same transformation contract.

## Live comparable calibration

For a target configuration `T` and a comparable `C`:

```text
structural_delta = model(T) - model(C)
adjusted_comp    = asking_price(C) + structural_delta
```

The adjustment is bounded so a model outlier cannot create an absurd comparable price. Adjusted comparables are then aggregated with a weighted median using hardware similarity and freshness.

Similarity is intentionally dominated by GPU and CPU because they explain most gaming-PC value variation. RAM, storage, condition, and memory/storage type provide secondary refinement.

The final hybrid estimate is:

```text
final = (1 - live_weight) * structural_model + live_weight * live_market_estimate
```

The live weight requires at least three qualifying comparables, rises with coverage/source diversity, and is capped below 1.0. If evidence is insufficient, `live_weight = 0` and the result remains model-only.

This architecture is more defensible than either extreme:

- static model only: stable but can lag launches and rapid price changes;
- raw comps only: current but noisy, seller-biased, and weak for mismatched hardware.

## Explainability

The notebook inspects coefficients/importance and failure regions. The API returns simple structural drivers plus a live-market driver when comparables influence the result. Comparable cards expose source, title, price, similarity, and source URL so the market contribution is inspectable rather than hidden.

## Production model promotion

A replacement model should only receive MLflow's `champion` alias when it improves validated generalization on licensed recent sold-price data, passes failure-analysis checks, remains stable on rare/unknown hardware, and does not depend on leaked target proxies.

Live asking-price volume alone is not sufficient evidence for model promotion.
