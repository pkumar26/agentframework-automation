using './main.bicep'

// =============================================================================
// PROD Environment Parameters — Agent Framework
// =============================================================================
// Base configuration for production. Per-agent overrides (appName,
// containerImage, appEnvVars) are applied at deploy time via CLI overrides.
// =============================================================================

param environmentName = 'prod'
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
param containerCpu = '1'
param containerMemory = '2Gi'
param minReplicas = 1
param maxReplicas = 10
param ingressExternal = true

// --- Environment Variables (overridden per-agent at deploy time) ---
param appEnvVars = [
  { name: 'ENVIRONMENT', value: 'prod' }
  // Uncomment to enable Azure AI Search grounding (Option A: explicit endpoint + index):
  // { name: 'AZURE_AI_SEARCH_ENDPOINT', value: 'https://<search-service>.search.windows.net' }
  // { name: 'AZURE_AI_SEARCH_INDEX_NAME', value: '<index-name>' }
  // { name: 'AZURE_AI_SEARCH_SEMANTIC_CONFIG', value: '<semantic-config-name>' }  // optional
  //
  // Uncomment to enable MCP servers (shared — all agents connect to these):
  // { name: 'MCP_SERVERS', value: '[{"name":"github","transport":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-github"]}]' }
  //
  // Per-agent MCP servers (override shared config for a specific agent):
  // { name: 'CODE_HELPER_MCP_SERVERS', value: '[{"name":"github","transport":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-github"]}]' }
]

// --- Secrets (uncomment when Key Vault secrets are ready) ---
param secretEnvVars = []

// --- Tags ---
param tags = {
  Environment: 'prod'
  Project: 'agentframework'
  ManagedBy: 'bicep'
}
