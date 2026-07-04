targetScope = 'resourceGroup'

@description('Azure region for the Container Apps environment.')
param location string = resourceGroup().location

@description('Globally unique Azure Container Registry name.')
param acrName string

@secure()
@description('Production PostgreSQL SQLAlchemy URL. Store this as a GitHub Environment secret.')
param databaseUrl string

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
      secrets: [{ name: 'database-url', value: databaseUrl }]
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
        ]
        resources: { cpu: json('0.5'), memory: '1Gi' }
      }]
      scale: { minReplicas: 0, maxReplicas: 5 }
    }
  }
}

output acrLoginServer string = acr.properties.loginServer
output apiFqdn string = api.properties.configuration.ingress.fqdn
output webFqdn string = web.properties.configuration.ingress.fqdn
