# Error and failure analysis

## Demo holdout findings

The current artifact is evaluated on the synthetic demo dataset, so these numbers validate the workflow rather than real-market accuracy.

Price-band reports in `reports/modeling/error_by_price_band.csv` show how absolute error changes across budget, mid-range, high-end, and enthusiast systems. Condition-level reports are stored separately in `reports/modeling/error_by_condition.csv`.

The analysis explicitly asks:

- whether high-end/enthusiast systems have larger absolute error;
- whether rare or unknown GPUs/CPUs increase uncertainty;
- whether condition segments behave differently;
- how predictions shift when recognized CPU/GPU identity is replaced with an unknown fallback;
- whether residuals show systematic under/overprediction by predicted-price region.

## Known failure modes

**Rare or newly released hardware.** Alias normalization and tier mappings can lag hardware releases. The API surfaces missing/unrecognized fields and widens uncertainty when key components are absent.

**VRAM versus system RAM.** Messy listings frequently place GPU VRAM beside RAM. A regression test covers this exact failure after the initial parser incorrectly interpreted `RTX 4070 12GB` as 12 GB system RAM.

**Bundles and partial systems.** Listings that include monitor/peripherals or sell only a tower/parts can distort price semantics. A real ingestion adapter should classify bundle contents or reject them.

**Condition ambiguity.** Seller language is subjective. The review UI lets the user correct condition before valuation.

**Market drift.** Hardware prices can change quickly after launches, shortages, new generations, or regional supply changes. Unknown-hardware rate and input/prediction distributions should be monitored, and the model should be retrained on recent observations.

**Currency/region.** The demo UI displays CAD, but the model data does not yet encode region or FX. A real public deployment must train and serve a region-specific model or add explicit market/currency features.
