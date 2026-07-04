# Error and failure analysis

## Structural-model findings

The checked-in model is evaluated on synthetic demo data, so its metrics validate the research workflow rather than real-market accuracy. Reports under `reports/modeling/` break error down by price band, condition, and hardware identity and probe sensitivity to unknown hardware.

## Known structural failure modes

**Rare/new hardware.** Canonical aliases and ordinal tiers can lag new releases. The normalization map now includes current RTX 50, Radeon 9000, Ryzen 9000, and Intel Core Ultra parts, but this remains a maintenance surface.

**VRAM versus system RAM.** Listings often place GPU VRAM beside system RAM. Regression tests protect the `RTX 4070 12GB` versus `32GB DDR5` ambiguity.

**Bundles and partial systems.** Monitor/peripheral bundles and part-only listings distort the meaning of total price. Live ingestion should reject obvious non-system observations where possible; user review remains necessary for pasted listings.

**Condition ambiguity.** Seller condition language is subjective. The user can correct it before valuation.

## Live-market failure modes

**Asking-price bias.** Active listings reflect seller intent, not completed transactions. The architecture limits their role to bounded calibration and never reports them as sold-price ground truth.

**Retail/used mismatch.** Best Buy retail/open-box evidence can anchor replacement cost but may be a poor match for used custom PCs. Listing type remains visible, and source diversity does not erase this semantic difference.

**Sparse comparables.** Brand-new enthusiast builds or unusual workstation configurations may have fewer than three sufficiently similar comps. The system falls back to the structural model rather than forcing a live answer.

**Provider outage/rate limiting.** Each source refresh fails independently. Cached observations remain usable until TTL expiry; refresh runs expose partial/failure state.

**Cross-source duplicates.** Syndicated/duplicated systems can appear across feeds. Source IDs prevent same-provider duplicates; normalized fingerprints reduce duplicate influence within a refresh. Fingerprinting is heuristic and can still miss near-duplicates.

**FX movement.** USD Best Buy observations depend on USD/CAD conversion. Bank of Canada FX is retrieved at refresh time; a manual override exists for deterministic/test environments.

**Normalization mismatch.** A live feed can be healthy while newly launched hardware normalizes to unknown. Monitor unknown rates and low comparable counts together.

## What would establish real accuracy

A defensible production evaluation requires a recent, region-appropriate completed-sales dataset that was not used for training, with enough coverage across price bands and hardware generations. Measure MAE/RMSE/R² for the structural model and the hybrid estimator separately, then analyze whether live calibration improves or harms each segment.
