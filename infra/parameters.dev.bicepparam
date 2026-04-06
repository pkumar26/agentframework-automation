using './main.bicep'

// =============================================================================
// DEV Environment Parameters — Agent Framework
// =============================================================================
// Base configuration for dev. Per-agent overrides (appName, containerImage,
// appEnvVars) are applied at deploy time via CLI parameter overrides.
// =============================================================================

param environmentName = 'dev'
param appName = 'agentfw'               // Overridden per-agent at deploy time
param location = 'usgovarizona'         // Azure Government region

// --- Identity: create a new one per agent ---
param createNewIdentity = true
// param existingIdentityResourceId = ''

// --- ACR (full ARM resource ID — update with your ACR) ---
// For Azure Government, ACR uses azurecr.us domain
param acrResourceId = '/subscriptions/ec27ea62-bfa8-4a38-a9fb-c88a2f4fb31b/resourceGroups/<acr-rg>/providers/Microsoft.ContainerRegistry/registries/<acr-name>'

// --- ACA Environment ---
param existingManagedEnvironmentId = ''   // Leave empty to create a new environment
param subnetId = ''                        // Leave empty for no VNET integration

// --- Container App ---
param containerImage = 'mcr.microsoft.com/k8se/quickstart:latest'  // Overridden at deploy time
param targetPort = 8088
param containerCpu = '0.25'
param containerMemory = '0.5Gi'
param minReplicas = 0
param maxReplicas = 1
param ingressExternal = true

// --- Environment Variables (overridden per-agent at deploy time) ---
param appEnvVars = [
  { name: 'ENVIRONMENT', value: 'dev' }
  { name: 'AZURE_AUTHORITY_HOST', value: 'https://login.microsoftonline.us/' }
  { name: 'AZURE_AI_PROJECT_ENDPOINT', value: 'https://ai-openai-arizona.openai.azure.us/' }
  { name: 'AGENT_DEPLOYMENT_NAME', value: 'gpt-4o' }
]

// --- Secrets (uncomment when Key Vault secrets are ready) ---
param secretEnvVars = []
// param secretEnvVars = [
//   {
//     name: 'AZURE_CLIENT_SECRET'
//     secretRef: 'azure-client-secret'
//     keyVaultSecretUri: 'https://kv-agentfw-dev.vault.azure.net/secrets/azure-client-secret'
//   }
// ]

// --- Tags ---
param tags = {
  Environment: 'dev'
  Project: 'agentframework'
  ManagedBy: 'bicep'
}
