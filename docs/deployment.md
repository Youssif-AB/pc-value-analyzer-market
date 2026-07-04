# Azure deployment

The repository is prepared for Azure Container Apps. A live deployment is not claimed by this archive because subscription credentials and provider secrets are external to the repository.

## Production topology

`infra/azure/main.bicep` provisions:

- Azure Container Registry;
- Container Apps environment + Log Analytics;
- public React web app;
- public FastAPI service;
- always-on `pc-value-market-worker` using the same backend image but running `python -m ml.pipeline.live_market_flow`.

The market worker has no public ingress. It connects to a Prefect Cloud workspace or a separately hosted Prefect Server via `PREFECT_API_URL`, performs an immediate refresh, and serves the hourly Prefect schedule.

## Required GitHub production configuration

Variables:

- `AZURE_RESOURCE_GROUP`
- `AZURE_LOCATION`
- `AZURE_ACR_NAME`
- `PREFECT_API_URL`

Secrets:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `PRODUCTION_DATABASE_URL`
- `PREFECT_API_KEY` (blank only if the selected Prefect Server does not require it)
- `EBAY_CLIENT_ID`
- `EBAY_CLIENT_SECRET`
- `BESTBUY_API_KEY`
- `MARKET_REFRESH_TOKEN`

The Azure identity uses GitHub OIDC rather than a long-lived Azure password. Provider credentials stay in GitHub Environment/Azure secret stores and are never baked into container images.

## Database

Use Azure Database for PostgreSQL Flexible Server or another production PostgreSQL service. Apply `db/migrations/001_init.sql` to create application/live-market tables. The same logical server may host MLflow separately, but production MLflow does not need to be on the public request path because the approved model artifact is served by the API image.

## Market refresher

Local Docker Compose provides Prefect Server itself. In Azure, the recommended configuration is Prefect Cloud for the scheduled market worker so the Container App does not also have to operate a stateful orchestration control plane.

The worker's source credentials are independent. If one provider fails, the refresh can complete as `partial` and retain valid observations from the other provider until TTL expiry.

## Model promotion

The checked-in structural artifact demonstrates the workflow with synthetic sold-price data. A real promotion should train against licensed recent completed-sale outcomes, log all candidates to MLflow, validate CV + holdout + failure segments, and only then move the approved registry version to the `champion` alias.

Live active-market volume is not a substitute for this validation gate.

## Workflow order

`.github/workflows/deploy-azure.yml`:

1. logs into Azure with GitHub OIDC;
2. provisions infrastructure/secrets;
3. grants API/web/worker managed identities `AcrPull`;
4. builds one backend image and deploys it to both API and market-worker roles;
5. obtains the API hostname;
6. builds the frontend with the live API URL;
7. locks CORS to the deployed web origin;
8. smoke-tests `/health` and `/api/v1/market/status`.

All images are Linux containers; CI also builds them on Ubuntu runners.
