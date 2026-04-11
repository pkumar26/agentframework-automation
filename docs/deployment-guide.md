# Deployment Guide

[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Azure Container Apps](https://img.shields.io/badge/Azure-Container%20Apps-0078D4?logo=microsoftazure&logoColor=white)](https://learn.microsoft.com/en-us/azure/container-apps/)
[![Azure CLI](https://img.shields.io/badge/Azure%20CLI-2.60+-0078D4?logo=microsoftazure&logoColor=white)](https://learn.microsoft.com/en-us/cli/azure/)
[![Azure Container Registry](https://img.shields.io/badge/ACR-Container%20Registry-0078D4?logo=microsoftazure&logoColor=white)](https://learn.microsoft.com/en-us/azure/container-registry/)

This guide covers how to deploy agents — locally, in Docker, and to Azure Container Apps (ACA) for production.

> **Interactive walkthrough**: The [04_deploy_to_aca](../notebooks/04_deploy_to_aca.ipynb) notebook provides a step-by-step interactive deployment experience.

---

## Table of Contents

- [Deployment Model](#deployment-model)
- [Local Development](#local-development)
- [Docker](#docker)
- [Azure Container Apps](#azure-container-apps)
  - [Prerequisites](#prerequisites)
  - [1. Create Resource Group and ACR](#1-create-resource-group-and-acr)
  - [2. Build and Push Image](#2-build-and-push-image)
  - [3. Deploy via Bicep](#3-deploy-via-bicep)
  - [4. Verify Deployment](#4-verify-deployment)
  - [5. Update a Deployment](#5-update-a-deployment)
- [Bicep Parameter Reference](#bicep-parameter-reference)
- [Environment Configuration](#environment-configuration)
- [Authentication](#authentication)
- [Multiple Agents](#multiple-agents)
- [Health Checks](#health-checks)
- [Troubleshooting](#troubleshooting)

---

## Deployment Model

```
┌────────────────────────────────────────────────────┐
│  Azure AI Foundry (Model Inference)                │
│  Models: GPT-4o, GPT-4.1, custom deployments       │
└──────────────────────┬─────────────────────────────┘
                       │ HTTPS (Responses API)
        ┌──────────────┼──────────────────┐
        │              │                  │
   ┌────▼─────┐  ┌────▼─────┐  ┌────────▼────────┐
   │  Local   │  │  Docker  │  │  Azure Container │
   │  CLI     │  │  :8088   │  │  Apps  :8088     │
   │  dev     │  │  test    │  │  production      │
   └──────────┘  └──────────┘  └──────────────────┘
```

- **Models** stay in Azure AI Foundry — the platform only calls them for inference
- **Agent runtime** (orchestration, tools, instructions) runs locally or in containers
- **Hosting adapter** (`app.py`) exposes agents as HTTP services on port 8088

---

## Local Development

No container needed for development:

```bash
# Interactive CLI
python scripts/run_agent.py --name code-helper

# Single prompt
python scripts/run_agent.py --name code-helper --prompt "Hello"

# As HTTP service (port 8088)
AGENT_NAME=code-helper python app.py
```

The agent connects to your Azure AI Foundry endpoint using `DefaultAzureCredential` (from `az login`).

---

## Docker

### Build and Run

```bash
# Build the image
docker build -t agentframework:latest .

# Run with environment variables
docker run --rm -p 8088:8088 \
  -e AGENT_NAME=code-helper \
  -e AZURE_AI_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project \
  -e AZURE_CLIENT_ID=<client-id> \
  -e AZURE_CLIENT_SECRET=<client-secret> \
  -e AZURE_TENANT_ID=<tenant-id> \
  agentframework:latest
```

### Docker Compose

```bash
# Configure .env with your settings, then:
docker compose up --build
```

The `docker-compose.yml` reads from `.env` automatically. Set `AGENT_NAME` to choose which agent runs.

### Test the Service

```bash
curl -X POST http://localhost:8088/responses \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, what can you do?"}'
```

---

## Azure Container Apps

### Prerequisites

- **Azure CLI** >= 2.60 with Bicep extension — [Install](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
- **Azure subscription** with permissions to create resources
- Authenticated session: `az login`
- An **Azure AI Foundry project** with a model deployment (e.g., `gpt-4o`)
- An **existing Azure Container Registry** (can be in any resource group)
- **Contributor** + **User Access Administrator** roles on the target resource group (for Bicep to create resources and assign roles)

### 1. Create Resource Group and ACR

These are external prerequisites — created once, referenced by the Bicep templates:

```bash
# Variables
RG="agentframework-rg"
LOCATION="eastus"
ACR_NAME="agentframeworkacr"    # Must be globally unique

# Create resource group
az group create --name "$RG" --location "$LOCATION"

# Create Azure Container Registry
az acr create \
  --name "$ACR_NAME" \
  --resource-group "$RG" \
  --sku Basic \
  --admin-enabled false
```

### 2. Build and Push Image

```bash
# Login to ACR
az acr login --name "$ACR_NAME"

# Build and push (using ACR Tasks — no local Docker needed)
az acr build \
  --registry "$ACR_NAME" \
  --image agentframework:v1 \
  .

# Or build locally and push
docker build -t "$ACR_NAME.azurecr.io/agentframework:v1" .
docker push "$ACR_NAME.azurecr.io/agentframework:v1"
```

### 3. Deploy via Bicep

The `infra/` directory contains modular Bicep templates sourced from [ACA-BICEP-Actions](https://github.com/pkumar26/ACA-BICEP-Actions). A single deployment provisions everything: managed identity, ACR role assignment, Log Analytics, ACA environment, and the container app.

**First, update your parameter file** (`infra/parameters.dev.bicepparam`):

```bicep
// Set your actual ACR resource ID
param acrResourceId = '/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.ContainerRegistry/registries/<acr-name>'
```

**Preview changes (what-if):**

```bash
AGENT="code-helper"
IMAGE="$ACR_NAME.azurecr.io/agentframework:v1"
ENDPOINT="https://your-project.services.ai.azure.com/api/projects/your-project"
ACR_RES_ID="/subscriptions/<sub-id>/resourceGroups/$RG/providers/Microsoft.ContainerRegistry/registries/$ACR_NAME"

az deployment group what-if \
  --resource-group "$RG" \
  --template-file infra/main.bicep \
  --parameters environmentName=dev \
  --parameters location="$LOCATION" \
  --parameters appName="$AGENT" \
  --parameters containerImage="$IMAGE" \
  --parameters acrResourceId="$ACR_RES_ID" \
  --parameters "appEnvVars=[{\"name\":\"AGENT_NAME\",\"value\":\"$AGENT\"},{\"name\":\"AZURE_AI_PROJECT_ENDPOINT\",\"value\":\"$ENDPOINT\"},{\"name\":\"ENVIRONMENT\",\"value\":\"dev\"}]"
```

> **Note:** Pass all parameters inline. The `.bicepparam` files cannot be combined with
> supplemental `--parameters` flags due to a Bicep CLI limitation. Copy the `acrResourceId`
> value from your `.bicepparam` file, or set the `ACR_RES_ID` variable above.

**Deploy:**

```bash
az deployment group create \
  --resource-group "$RG" \
  --template-file infra/main.bicep \
  --parameters environmentName=dev \
  --parameters location="$LOCATION" \
  --parameters appName="$AGENT" \
  --parameters containerImage="$IMAGE" \
  --parameters acrResourceId="$ACR_RES_ID" \
  --parameters "appEnvVars=[{\"name\":\"AGENT_NAME\",\"value\":\"$AGENT\"},{\"name\":\"AZURE_AI_PROJECT_ENDPOINT\",\"value\":\"$ENDPOINT\"},{\"name\":\"ENVIRONMENT\",\"value\":\"dev\"}]" \
  --name "agent-$AGENT-dev-$(date +%Y%m%d%H%M)" \
  --mode Incremental
```

This creates all required resources with deterministic names (e.g., `ca-code-helper-dev`, `id-code-helper-dev`). Re-running is idempotent — existing resources are updated in place.

### 4. Verify Deployment

```bash
# Get the FQDN from deployment outputs
FQDN=$(az deployment group show \
  --resource-group "$RG" \
  --name "<deployment-name>" \
  --query "properties.outputs.containerAppFqdn.value" -o tsv)

# Or query the container app directly
FQDN=$(az containerapp show \
  --name "ca-$AGENT-dev" \
  --resource-group "$RG" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

# Test the endpoint
curl -X POST "https://$FQDN/responses" \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello!"}'
```

### 5. Update a Deployment

```bash
# Push a new image version
az acr build --registry "$ACR_NAME" --image agentframework:v2 .

# Re-run the Bicep deployment with the new image
az deployment group create \
  --resource-group "$RG" \
  --template-file infra/main.bicep \
  --parameters environmentName=dev \
  --parameters location="$LOCATION" \
  --parameters appName="$AGENT" \
  --parameters containerImage="$ACR_NAME.azurecr.io/agentframework:v2" \
  --parameters acrResourceId="$ACR_RES_ID" \
  --parameters "appEnvVars=[{\"name\":\"AGENT_NAME\",\"value\":\"$AGENT\"},{\"name\":\"AZURE_AI_PROJECT_ENDPOINT\",\"value\":\"$ENDPOINT\"},{\"name\":\"ENVIRONMENT\",\"value\":\"dev\"}]" \
  --mode Incremental
```

Bicep handles the rolling update — ACA provisions a new revision with the new image.

---

## Bicep Parameter Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `environmentName` | `string` | — | `dev`, `qa`, or `prod` |
| `appName` | `string` | — | Base name for all resources (agent name) |
| `location` | `string` | Resource group location | Azure region |
| `createNewIdentity` | `bool` | `true` | Create new managed identity or use existing |
| `existingIdentityResourceId` | `string` | `''` | Resource ID of existing identity |
| `acrResourceId` | `string` | — | Full ARM resource ID of your ACR |
| `existingManagedEnvironmentId` | `string` | `''` | Reuse existing ACA environment (empty = create new) |
| `subnetId` | `string` | `''` | Subnet ID for VNET integration (empty = no VNET) |
| `containerImage` | `string` | quickstart | Full image reference |
| `targetPort` | `int` | `8088` | Port the container listens on |
| `containerCpu` | `string` | varies by env | CPU cores |
| `containerMemory` | `string` | varies by env | Memory |
| `minReplicas` | `int` | varies by env | Minimum replica count |
| `maxReplicas` | `int` | varies by env | Maximum replica count |
| `ingressExternal` | `bool` | `true` | Expose external HTTP endpoint |
| `appEnvVars` | `array` | `[]` | Non-sensitive env vars (`{ name, value }`) |
| `secretEnvVars` | `array` | `[]` | Key Vault secret refs (`{ name, secretRef, keyVaultSecretUri }`) |

### Environment Sizing Defaults

| Setting | Dev | QA | Prod |
|---------|-----|----|------|
| CPU | 0.25 | 0.5 | 1 |
| Memory | 0.5Gi | 1Gi | 2Gi |
| Min Replicas | 0 | 1 | 1 |
| Max Replicas | 1 | 3 | 10 |

---

## Environment Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AGENT_NAME` | Yes (for `app.py`) | — | Which agent to serve (e.g., `code-helper`) |
| `AZURE_AI_PROJECT_ENDPOINT` | Yes | — | Azure AI Foundry project endpoint URL |
| `AGENT_DEPLOYMENT_NAME` | No | Per-agent default | Override the model deployment name |
| `ENVIRONMENT` | No | `dev` | Environment label (`dev`, `qa`, `prod`) |

### Knowledge Base / Search Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_AI_SEARCH_ENDPOINT` | For search grounding | Azure AI Search service URL (e.g., `https://<name>.search.windows.net`) |
| `AZURE_AI_SEARCH_INDEX_NAME` | For search grounding | Name of the search index to query |
| `AZURE_AI_SEARCH_SEMANTIC_CONFIG` | No | Semantic configuration name for higher-quality ranking |
| `AZURE_AI_SEARCH_INDEXES` | No | JSON array of multiple search indexes (see [Knowledge Base & Search Guide](knowledge-search-guide.md#option-c-multiple-search-indexes)) |

If none of the search variables are set, agents run without search grounding (model-only).
See the [Knowledge Base & Search Guide](knowledge-search-guide.md) for full details.

### Authentication Variables

| Variable | When Needed | Description |
|----------|-------------|-------------|
| `AZURE_CLIENT_ID` | User-assigned MI / service principal | Client ID of the identity. Auto-injected by Bicep for user-assigned MI in ACA |
| `AZURE_CLIENT_SECRET` | Service principal auth | App registration secret |
| `AZURE_TENANT_ID` | Service principal auth | Azure AD tenant ID |
| `AZURE_AUTHORITY_HOST` | Sovereign / government clouds | Authority URL (e.g., `https://login.microsoftonline.us` for US Gov). Omit for commercial cloud |

> **Note:** For ACA deployments using the Bicep templates, `AZURE_CLIENT_ID` is automatically
> injected from the user-assigned managed identity. No manual configuration is needed.

---

## Authentication

`DefaultAzureCredential` is used for all Azure authentication. It automatically tries multiple credential sources in order:

| Environment | Credential Used | Setup |
|-------------|----------------|-------|
| Local development | Azure CLI (`az login`) | Run `az login` before starting |
| Docker (local) | Service principal env vars | Set `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` |
| ACA (production) | **Managed identity** (recommended) | Enable system-assigned managed identity on the container app |

### Using Managed Identity in ACA (Recommended)

The Bicep templates create a **user-assigned managed identity** (`id-{agent}-{env}`) and
automatically inject `AZURE_CLIENT_ID` into the container so `DefaultAzureCredential`
picks it up. No manual identity setup is needed — just assign the RBAC role:

```bash
# Get the managed identity's principal ID
PRINCIPAL_ID=$(az identity show \
  --name "id-$AGENT-dev" \
  --resource-group "$RG" \
  --query principalId -o tsv)

# Assign Cognitive Services User role on the Foundry resource
# Note: "Azure AI Developer" is NOT sufficient — it only covers OpenAI/* data actions,
# not AIServices/agents/* which the Agent Framework requires.
az role assignment create \
  --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Cognitive Services User" \
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-name>"
```

With user-assigned managed identity, no secret environment variables are needed.
The Bicep templates handle `AZURE_CLIENT_ID` injection automatically.

### Required RBAC Roles

The identity (service principal or managed identity) needs access to the Foundry endpoint:

| Role | Scope | Purpose |
|------|-------|---------|
| **Cognitive Services User** | Foundry resource or resource group | Required — covers all `Microsoft.CognitiveServices/*` data actions including `AIServices/agents/*` |

> **Common mistake:** The **Azure AI Developer** role looks appropriate but only covers
> `OpenAI/*`, `SpeechServices/*`, `ContentSafety/*`, and `MaaS/*` data actions — it does
> **not** include `AIServices/agents/*` which the Agent Framework uses. Always use
> **Cognitive Services User** instead.

### Sovereign / Government Clouds

By default, `DefaultAzureCredential` authenticates against the Azure commercial cloud
(`login.microsoftonline.com`). For sovereign clouds, set `AZURE_AUTHORITY_HOST` in your
`.env` file or container environment:

| Cloud | Authority Host |
|-------|----------------|
| Commercial (default) | `https://login.microsoftonline.com` |
| US Government | `https://login.microsoftonline.us` |
| China (21Vianet) | `https://login.chinacloudapi.cn` |

```bash
# .env (for local development / docker-compose)
AZURE_AUTHORITY_HOST=https://login.microsoftonline.us

# ACA deployment — add to appEnvVars in the Bicep command
--parameters "appEnvVars=[...,{\"name\":\"AZURE_AUTHORITY_HOST\",\"value\":\"https://login.microsoftonline.us\"}]"
```

> **Note:** Also ensure your `AZURE_AI_PROJECT_ENDPOINT` points to the corresponding
> sovereign cloud endpoint (e.g., `.usgovcloudapi.net` for US Government).

---

## Knowledge Base / Search Grounding in ACA

[![Azure AI Search](https://img.shields.io/badge/Azure%20AI-Search-0078D4?logo=microsoftazure&logoColor=white)](https://learn.microsoft.com/azure/search/)

To deploy agents with knowledge base grounding to ACA, you need two things:
environment variables and an RBAC role assignment.

### 1. Pass Search Variables at Deploy Time

Search configuration is passed via `appEnvVars` in the Bicep deployment.
The `deploy.yml` workflow reads these from **GitHub repository variables**
and conditionally includes them when set.

**Set these GitHub variables** (Settings → Variables and secrets → Actions → Variables):

| GitHub Variable | Value | Required |
|-----------------|-------|----------|
| `AZURE_AI_SEARCH_ENDPOINT` | `https://<search-service>.search.windows.net` | Yes |
| `AZURE_AI_SEARCH_INDEX_NAME` | `<index-name>` | Yes |
| `AZURE_AI_SEARCH_SEMANTIC_CONFIG` | `<semantic-config-name>` | No |
| `AZURE_AI_SEARCH_INDEXES` | JSON array of `{endpoint, index_name, semantic_config}` | No |

If these variables are not set, the workflow deploys agents without search
grounding — no errors, just model-only answers.

**Manual CLI deployment** — add the search vars to `appEnvVars`:

```bash
# Single index
az deployment group create \
  --resource-group "$RG" \
  --template-file infra/main.bicep \
  --parameters environmentName=dev \
  --parameters appName="$AGENT" \
  --parameters containerImage="$IMAGE" \
  --parameters acrResourceId="$ACR_RES_ID" \
  --parameters "appEnvVars=[\
    {\"name\":\"AGENT_NAME\",\"value\":\"$AGENT\"},\
    {\"name\":\"AZURE_AI_PROJECT_ENDPOINT\",\"value\":\"$ENDPOINT\"},\
    {\"name\":\"AZURE_AI_SEARCH_ENDPOINT\",\"value\":\"https://<search-service>.search.windows.net\"},\
    {\"name\":\"AZURE_AI_SEARCH_INDEX_NAME\",\"value\":\"<index-name>\"},\
    {\"name\":\"ENVIRONMENT\",\"value\":\"dev\"}\
  ]" \
  --mode Incremental
```

```bash
# Multiple indexes (Option C)
az deployment group create \
  --resource-group "$RG" \
  --template-file infra/main.bicep \
  --parameters environmentName=dev \
  --parameters appName="$AGENT" \
  --parameters containerImage="$IMAGE" \
  --parameters acrResourceId="$ACR_RES_ID" \
  --parameters "appEnvVars=[\
    {\"name\":\"AGENT_NAME\",\"value\":\"$AGENT\"},\
    {\"name\":\"AZURE_AI_PROJECT_ENDPOINT\",\"value\":\"$ENDPOINT\"},\
    {\"name\":\"AZURE_AI_SEARCH_INDEXES\",\"value\":\"[{\\\"endpoint\\\":\\\"https://search1.search.windows.net\\\",\\\"index_name\\\":\\\"products\\\"},{\\\"endpoint\\\":\\\"https://search2.search.windows.net\\\",\\\"index_name\\\":\\\"support-docs\\\"}]\"},\
    {\"name\":\"ENVIRONMENT\",\"value\":\"dev\"}\
  ]" \
  --mode Incremental
```

The `.bicepparam` files also contain commented-out examples for reference.

### 2. RBAC: Grant Search Index Data Reader

The managed identity created by Bicep (`id-{agent}-{env}`) needs the
**Search Index Data Reader** role on your Azure AI Search service.
If using multiple indexes (Option C), repeat this for **each** search service:

```bash
PRINCIPAL_ID=$(az identity show \
  --name "id-$AGENT-dev" \
  --resource-group "$RG" \
  --query principalId -o tsv)

az role assignment create \
  --role "Search Index Data Reader" \
  --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<search-service-name>"
```

### How It Works

No code changes are needed. The same `AzureAISearchContextProvider` runs in
ACA as locally — it reads env vars from `AgentBaseConfig` and authenticates
via `DefaultAzureCredential`, which automatically uses the managed identity
in ACA (the Bicep templates inject `AZURE_CLIENT_ID`). When multiple indexes
are configured, the framework creates one provider per index and merges the
results.

See the [Knowledge Base & Search Guide](knowledge-search-guide.md) for
full architecture details, supported index field names, and troubleshooting.

---

## Multiple Agents

Each agent runs as a **separate container app**, all sharing the same Docker image. With Bicep, each agent gets its own deployment with a unique `appName`:

```bash
# Deploy code-helper (creates full infra: identity, ACR role, env, container app)
az deployment group create \
  --resource-group "$RG" \
  --template-file infra/main.bicep \
  --parameters environmentName=dev \
  --parameters location="$LOCATION" \
  --parameters appName=code-helper \
  --parameters containerImage="$IMAGE" \
  --parameters acrResourceId="$ACR_RES_ID" \
  --parameters "appEnvVars=[{\"name\":\"AGENT_NAME\",\"value\":\"code-helper\"},{\"name\":\"AZURE_AI_PROJECT_ENDPOINT\",\"value\":\"$ENDPOINT\"},{\"name\":\"ENVIRONMENT\",\"value\":\"dev\"}]" \
  --mode Incremental

# Deploy doc-assistant (creates its own set of resources)
az deployment group create \
  --resource-group "$RG" \
  --template-file infra/main.bicep \
  --parameters environmentName=dev \
  --parameters location="$LOCATION" \
  --parameters appName=doc-assistant \
  --parameters containerImage="$IMAGE" \
  --parameters acrResourceId="$ACR_RES_ID" \
  --parameters "appEnvVars=[{\"name\":\"AGENT_NAME\",\"value\":\"doc-assistant\"},{\"name\":\"AZURE_AI_PROJECT_ENDPOINT\",\"value\":\"$ENDPOINT\"},{\"name\":\"ENVIRONMENT\",\"value\":\"dev\"}]" \
  --mode Incremental
```

The `AGENT_NAME` environment variable selects which agent the container serves. The same Docker image supports all agents — only the env vars change.

> **CI/CD**: The `deploy.yml` workflow automates this — it loops over all registered agents (or a specific one) and deploys each via Bicep.

---

## Health Checks

The hosting adapter (`azure-ai-agentserver-agentframework`) serves on port 8088. Configure ACA health probes:

```bash
az containerapp update \
  --name "$ACA_NAME" \
  --resource-group "$RG" \
  --set-env-vars AGENT_NAME=code-helper \
  --container-name agentframework \
  --probe-type liveness \
  --probe-path / \
  --probe-port 8088 \
  --probe-interval 30
```

---

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| `DefaultAzureCredential failed` | No valid credentials found | Run `az login` (local) or check service principal env vars (Docker) or managed identity (ACA) |
| `DefaultAzureCredential` fails with gov/sovereign credentials | Wrong authority host | Set `AZURE_AUTHORITY_HOST` to the correct sovereign cloud URL (see [Sovereign / Government Clouds](#sovereign--government-clouds)) |
| `Connection refused on :8088` | Agent not starting | Check `AGENT_NAME` matches a registered agent; check container logs |
| `Model deployment not found` | Wrong deployment name | Verify `AGENT_DEPLOYMENT_NAME` or agent config matches a deployment in your Foundry project |
| `403 Forbidden` / `PermissionDenied` on Foundry | Missing or wrong RBAC role | Assign **Cognitive Services User** role (not Azure AI Developer — it only covers `OpenAI/*` data actions, not `AIServices/agents/*`) |
| `DefaultAzureCredential` fails in ACA | Missing `AZURE_CLIENT_ID` | User-assigned managed identities require `AZURE_CLIENT_ID`. Bicep injects it automatically; verify with `az containerapp show` |
| Container exits immediately | Startup error | Check logs: `az containerapp logs show --name <name> --resource-group <rg>` |
| `ModuleNotFoundError` in container | Missing dependency | Ensure `pyproject.toml` is up to date and the image was rebuilt |
