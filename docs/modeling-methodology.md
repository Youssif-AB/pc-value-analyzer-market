# Modeling methodology

## Objective and target

The model estimates a fair market value from reviewed hardware and condition features. The demo training target is `sold_price`. `asking_price` is explicitly excluded from the feature contract and is only compared with the prediction afterward to produce a value rating.

## Candidate models and selection

The reproducible demo run compares Linear Regression, Random Forest, and Histogram Gradient Boosting. Selection uses the **lowest mean 5-fold cross-validation MAE on the training split**, then reports holdout MAE, RMSE, and R².

| Candidate | CV MAE | Holdout MAE | RMSE | R² |
|---|---:|---:|---:|---:|
| Linear Regression | $134.37 | $138.27 | $174.02 | 0.758 |
| Histogram Gradient Boosting | $147.46 | $160.36 | $198.60 | 0.684 |
| Random Forest | $158.02 | $175.41 | $221.72 | 0.606 |

Linear Regression is therefore the shipped demo winner. That is not a claim that linear regression is universally best for PC pricing; it is the measured winner on this particular synthetic dataset and split.

## Feature engineering

The production contract uses canonical CPU/GPU identity, compact CPU/GPU performance scores, RAM capacity/type, storage capacity/type, condition, brand/prebuilt indicator, and system age. Unknown hardware receives conservative fallback scores rather than a fabricated exact tier.

Categorical features are one-hot encoded with unknown-category handling. Numeric fields are median-imputed, and the linear baseline additionally standardizes numeric values. The entire preprocessing graph is exported inside the sklearn pipeline so notebook and API inference share the same transformation logic.

## Explainability

The notebook inspects model-native coefficients/importance and performs failure analysis by price region, condition, and hardware. The API also provides user-facing drivers based on reviewed hardware tiers and condition. Those user-facing explanations are deliberately simple and should not be presented as exact SHAP decompositions.

## Production decision rule

A new model should only replace the registry `champion` when it improves validated generalization on licensed recent data, passes failure-analysis checks, maintains acceptable behavior on rare/unknown hardware, and does not depend on leaked target proxies.
