# Azure deployment

The repository is prepared for Azure Container Apps, but no live Azure deployment is claimed by this repository alone. Deployment requires an Azure subscription, an existing production PostgreSQL database, and GitHub Environment credentials.

## Resources

`infra/azure/main.bicep` provisions a Log Analytics workspace, Container Apps environment, Azure Container Registry, public web container app, and public API container app. The API receives its PostgreSQL connection string as a Container Apps secret.

The production workflow builds both images inside ACR, grants each Container App's system-managed identity the `AcrPull` role, deploys the API first, discovers its live hostname, builds the frontend with that API URL, updates CORS to the deployed web origin, and performs a health smoke test.

## GitHub production environment

Configure these environment variables:

- `AZURE_RESOURCE_GROUP`
- `AZURE_LOCATION`
- `AZURE_ACR_NAME`

Configure these environment secrets:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `PRODUCTION_DATABASE_URL`

The Azure identity should use federated GitHub OIDC credentials rather than a long-lived Azure password. Scope its permissions to the deployment resource group and ACR roles required by the workflow.

## Database

Use Azure Database for PostgreSQL Flexible Server or another production PostgreSQL service. Create the application schema with `db/migrations/001_init.sql`. Keep the connection string in the GitHub `production` Environment and Container Apps secret store; do not commit it.

## Model promotion

The image currently contains the evidence-selected demo artifact. For real deployment, train on licensed recent market data, register the selected version in MLflow, promote it through the `champion` alias, and only then bake or retrieve that approved artifact for the API revision.

## Linux validation

All Docker images are Linux-based. CI builds the API and web containers on Ubuntu runners, and Azure Container Apps runs Linux containers.
