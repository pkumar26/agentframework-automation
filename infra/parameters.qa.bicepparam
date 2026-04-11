using './main.bicep'

// =============================================================================
// QA Environment Parameters — Agent Framework
// =============================================================================
// Base configuration for QA. Per-agent overrides (appName, containerImage,
// appEnvVars) are applied at deploy time via CLI parameter overrides.
// =============================================================================

param environmentName = 'qa'
param appName = 'agentfw'               // Overridden per-agent at deploy time
param location = 'eastus'

// --- Identity: create a new one per agent ---
param createNewIdentity = true
// param existingIdentityResourceId = ''

// --- ACR (full ARM resource ID — update with your ACR) ---
param acrResourceId = '/subscriptions/<subscription-id>/resourceGroups/<acr-rg>/providers/Microsoft.ContainerRegistry/registries/<acr-name>'

// --- ACA Environment ---
param existingManagedEnvironmentId = ''
param subnetId = ''

// --- Container App ---
param containerImage = 'mcr.microsoft.com/k8se/quickstart:latest'  // Overridden at deploy time
param targetPort = 8088
param containerCpu = '0.5'
param containerMemory = '1Gi'
param minReplicas = 1
param maxReplicas = 3
param ingressExternal = true

// --- Environment Variables (overridden per-agent at deploy time) ---
param appEnvVars = [
  { name: 'ENVIRONMENT', value: 'qa' }
  // Uncomment to enable Azure AI Search grounding (Option A: explicit endpoint + index):
  // { name: 'AZURE_AI_SEARCH_ENDPOINT', value: 'https://<search-service>.search.windows.net' }
  // { name: 'AZURE_AI_SEARCH_INDEX_NAME', value: '<index-name>' }
  // { name: 'AZURE_AI_SEARCH_SEMANTIC_CONFIG', value: '<semantic-config-name>' }  // optional
]

// --- Secrets (uncomment when Key Vault secrets are ready) ---
param secretEnvVars = []

// --- Tags ---
param tags = {
  Environment: 'qa'
  Project: 'agentframework'
  ManagedBy: 'bicep'
}
