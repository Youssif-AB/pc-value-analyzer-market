# Demo walkthrough

## Before starting

Set eBay and/or Best Buy credentials in `.env`. The app remains usable without them, but live market status will show zero configured/available observations and predictions will fall back to `model_only`.

Start:

```bash
docker compose up --build
```

Open:

- app: `http://localhost:8080`
- API docs: `http://localhost:8001/docs`
- live market status: `http://localhost:8001/api/v1/market/status`
- MLflow: `http://localhost:5001`
- Prefect: `http://localhost:4200`

## User journey

1. Paste a full PC listing.
2. The API extracts CPU, GPU, RAM, storage, condition, age, brand, and asking price.
3. Review and correct the normalized values.
4. Submit the reviewed configuration.
5. The structural model creates a baseline estimate.
6. Fresh normalized market observations are searched for sufficiently similar systems.
7. If enough comparables exist, the response blends a bounded live-market estimate with the baseline.
8. The UI shows fair price, value rating, uncertainty, structural drivers, market blend, and comparable source links.

## Example listing

```text
Gaming PC - like new. Ryzen 7 7800X3D, GeForce RTX 4070 12GB,
32GB DDR5, 2TB M.2 NVMe. Asking $1,650. Built about 1 year old.
```

The extractor distinguishes RTX 4070 `12GB` VRAM from `32GB DDR5` system memory; that failure mode is regression-tested.

## Example response modes

When no reliable live evidence exists:

```text
valuation_method: model_only
live blend: 0%
```

When at least three fresh sufficiently similar observations exist:

```text
valuation_method: hybrid_live_comps
structural model estimate: ...
adjusted live market estimate: ...
live blend: bounded percentage
comparables: source/title/price/similarity/url
```

Do not expect the same numeric result every day: the live component is intentionally time-sensitive.

## API smoke test

```bash
curl -X POST http://localhost:8001/api/v1/extract \
  -H 'Content-Type: application/json' \
  -d '{"listing_text":"Gaming PC - like new. Ryzen 7 7800X3D, GeForce RTX 4070 12GB, 32GB DDR5, 2TB M.2 NVMe. Asking $1,650. Built about 1 year old."}'
```
