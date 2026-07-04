# Live market sources

## Why source adapters instead of scraping HTML

The project uses documented APIs where possible. Marketplace HTML changes frequently, may require authentication/anti-bot handling, and can create terms/licensing problems that are unnecessary for a portfolio project. Each source implements a small adapter contract that returns normalized `SourceListing` records.

## eBay Browse API

Purpose: current used/prebuilt/custom desktop comparables in the Canadian eBay marketplace.

Configuration:

```dotenv
EBAY_CLIENT_ID=
EBAY_CLIENT_SECRET=
EBAY_MARKETPLACE_ID=EBAY_CA
EBAY_CATEGORY_ID=179
EBAY_SEARCH_QUERIES=gaming desktop,rtx gaming pc,custom gaming pc
EBAY_RESULT_LIMIT=50
```

The adapter obtains an Application OAuth token and queries Browse search. It requests fixed-price / best-offer inventory rather than auction bid states. Records are tagged `active_asking`.

Completed/sold-history data is a different evidence class. The project does not pretend Browse results are sold outcomes, and it does not assume unrestricted access to eBay Marketplace Insights.

## Best Buy APIs

Purpose: current retail and open-box gaming-desktop anchors.

Configuration:

```dotenv
BESTBUY_API_KEY=
BESTBUY_CATEGORY_ID=pcmcat287600050002
BESTBUY_RESULT_LIMIT=100
```

The Products API supplies current catalog/pricing observations. The Buying Options/Open Box endpoint supplies open-box offers for matching SKUs. New retail records are tagged `retail_new`; open-box records are tagged `retail_open_box`.

These are useful for replacement-cost/current-retail context but are not equivalent to second-hand completed transactions.

## Bank of Canada Valet FX

Best Buy prices are USD while the application target currency is CAD. The FX adapter retrieves `FXUSDCAD` from Bank of Canada's Valet API. No API key is required.

For deterministic tests or an environment without FX access:

```dotenv
USD_TO_CAD_OVERRIDE=1.38
```

## Adding another source

Implement `MarketSource.fetch()` in `ml/market_sources/` and return `SourceListing` objects containing:

- stable source listing ID;
- source name and listing type;
- title/summary;
- raw price and currency;
- canonical listing URL/image where available;
- condition and source timestamp where available.

Register the adapter in `ml/pipeline/live_market.py`. Do not bypass the common extraction, currency normalization, quality, fingerprinting, TTL, or audit steps.

## Secrets and provider terms

Never commit provider credentials. Keep `.env` local, use GitHub/Azure secret stores in deployment, and review each provider's current developer terms before increasing retention, request volume, redistribution, or commercial use. The live cache is intentionally operational and short-lived.
