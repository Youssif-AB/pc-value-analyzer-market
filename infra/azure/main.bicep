targetScope = 'resourceGroup'

@description('Azure region for the Container Apps environment.')
param location string = resourceGroup().location

@description('Globally unique Azure Container Registry name.')
param acrName string

@secure()
@description('Production PostgreSQL SQLAlchemy URL.')
param databaseUrl string

@description('Prefect Cloud/server API URL used by the always-on market refresher.')
param prefectApiUrl string

@secure()
@description('Prefect API key; blank is acceptable for a self-hosted server that does not require one.')
param prefectApiKey string = ''

@secure()
param ebayClientId string = ''

@secure()
param ebayClientSecret string = ''

@secure()
param bestbuyApiKey string = ''

@secure()
param marketRefreshToken string

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'pc-value-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'pc-value-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspace.properties.customerId
        sharedKey: workspace.listKeys().primarySharedKey
      }
    }
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource web 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'pc-value-web'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        transport: 'auto'
      }
    }
    template: {
      containers: [{
        name: 'web'
        image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
        resources: { cpu: json('0.25'), memory: '0.5Gi' }
      }]
      scale: { minReplicas: 0, maxReplicas: 3 }
    }
  }
}

resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'pc-value-api'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      secrets: [
        { name: 'database-url', value: databaseUrl }
        { name: 'market-refresh-token', value: marketRefreshToken }
      ]
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
    }
    template: {
      containers: [{
        name: 'api'
        image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
        env: [
          { name: 'DATABASE_URL', secretRef: 'database-url' }
          { name: 'CORS_ORIGINS', value: 'https://${web.properties.configuration.ingress.fqdn}' }
          { name: 'APP_ENV', value: 'production' }
          { name: 'MODEL_ARTIFACT_PATH', value: '/app/backend/artifacts/price_model.joblib' }
          { name: 'MODEL_METADATA_PATH', value: '/app/backend/artifacts/model_metadata.json' }
          { name: 'LIVE_MARKET_ENABLED', value: 'true' }
          { name: 'MARKET_CURRENCY', value: 'CAD' }
          { name: 'MARKET_REFRESH_TOKEN', secretRef: 'market-refresh-token' }
        ]
        resources: { cpu: json('0.5'), memory: '1Gi' }
      }]
      scale: { minReplicas: 0, maxReplicas: 5 }
    }
  }
}

resource marketWorker 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'pc-value-market-worker'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      secrets: [
        { name: 'database-url', value: databaseUrl }
        { name: 'prefect-api-key', value: prefectApiKey }
        { name: 'ebay-client-id', value: ebayClientId }
        { name: 'ebay-client-secret', value: ebayClientSecret }
        { name: 'bestbuy-api-key', value: bestbuyApiKey }
      ]
    }
    template: {
      containers: [{
        name: 'market-worker'
        image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
        command: ['python']
        args: ['-m', 'ml.pipeline.live_market_flow']
        env: [
          { name: 'DATABASE_URL', secretRef: 'database-url' }
          { name: 'APP_ENV', value: 'production' }
          { name: 'LIVE_MARKET_ENABLED', value: 'true' }
          { name: 'MARKET_CURRENCY', value: 'CAD' }
          { name: 'PREFECT_API_URL', value: prefectApiUrl }
          { name: 'PREFECT_API_KEY', secretRef: 'prefect-api-key' }
          { name: 'EBAY_CLIENT_ID', secretRef: 'ebay-client-id' }
          { name: 'EBAY_CLIENT_SECRET', secretRef: 'ebay-client-secret' }
          { name: 'EBAY_MARKETPLACE_ID', value: 'EBAY_CA' }
          { name: 'EBAY_CATEGORY_ID', value: '179' }
          { name: 'BESTBUY_API_KEY', secretRef: 'bestbuy-api-key' }
          { name: 'BESTBUY_CATEGORY_ID', value: 'pcmcat287600050002' }
          { name: 'BANK_OF_CANADA_FX_ENABLED', value: 'true' }
        ]
        resources: { cpu: json('0.5'), memory: '1Gi' }
      }]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

output acrLoginServer string = acr.properties.loginServer
output apiFqdn string = api.properties.configuration.ingress.fqdn
output webFqdn string = web.properties.configuration.ingress.fqdn
