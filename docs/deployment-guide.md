# Deployment Guide

[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Azure Container Apps](https://img.shields.io/badge/Azure-Container%20Apps-0078D4?logo=microsoftazure&logoColor=white)](https://learn.microsoft.com/en-us/azure/container-apps/)
[![Azure CLI](https://img.shields.io/badge/Azure%20CLI-2.60+-0078D4?logo=microsoftazure&logoColor=white)](https://learn.microsoft.com/en-us/cli/azure/)
[![Azure Container Registry](https://img.shields.io/badge/ACR-Container%20Registry-0078D4?logo=microsoftazure&logoColor=white)](https://learn.microsoft.com/en-us/azure/container-registry/)

This guide covers how to deploy agents — locally, in Docker, and to Azure Container Apps (ACA) for production.

---

## Table of Contents

- [Deployment Model](#deployment-model)
- [Local Development](#local-development)
- [Docker](#docker)
- [Azure Container Apps](#azure-container-apps)
  - [Prerequisites](#prerequisites)
  - [1. Create Container Registry](#1-create-container-registry)
  - [2. Build and Push Image](#2-build-and-push-image)
  - [3. Create Container App Environment](#3-create-container-app-environment)
  - [4. Deploy the Container App](#4-deploy-the-container-app)
  - [5. Verify Deployment](#5-verify-deployment)
  - [6. Update a Deployment](#6-update-a-deployment)
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

- **Azure CLI** >= 2.60 — [Install](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
- **Azure subscription** with permissions to create resources
- Authenticated session: `az login`
- An **Azure AI Foundry project** with a model deployment (e.g., `gpt-4o`)
- A **service principal** or **managed identity** with access to the Foundry endpoint

### 1. Create Container Registry

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

### 3. Create Container App Environment

```bash
ACA_ENV="agentframework-env"

az containerapp env create \
  --name "$ACA_ENV" \
  --resource-group "$RG" \
  --location "$LOCATION"
```

### 4. Deploy the Container App

```bash
ACA_NAME="code-helper"
FOUNDRY_ENDPOINT="https://your-project.services.ai.azure.com/api/projects/your-project"

az containerapp create \
  --name "$ACA_NAME" \
  --resource-group "$RG" \
  --environment "$ACA_ENV" \
  --image "$ACR_NAME.azurecr.io/agentframework:v1" \
  --registry-server "$ACR_NAME.azurecr.io" \
  --target-port 8088 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1Gi \
  --env-vars \
    AGENT_NAME=code-helper \
    AZURE_AI_PROJECT_ENDPOINT="$FOUNDRY_ENDPOINT" \
    AZURE_CLIENT_ID=secretref:azure-client-id \
    AZURE_CLIENT_SECRET=secretref:azure-client-secret \
    AZURE_TENANT_ID=secretref:azure-tenant-id \
  --secrets \
    azure-client-id="<your-client-id>" \
    azure-client-secret="<your-client-secret>" \
    azure-tenant-id="<your-tenant-id>"
```

> **Tip:** For production, use **managed identity** instead of service principal secrets. See [Authentication](#authentication).

### 5. Verify Deployment

```bash
# Get the FQDN
FQDN=$(az containerapp show \
  --name "$ACA_NAME" \
  --resource-group "$RG" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

# Test the endpoint
curl -X POST "https://$FQDN/responses" \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello!"}'
```

### 6. Update a Deployment

```bash
# Push a new image version
az acr build --registry "$ACR_NAME" --image agentframework:v2 .

# Update the container app
az containerapp update \
  --name "$ACA_NAME" \
  --resource-group "$RG" \
  --image "$ACR_NAME.azurecr.io/agentframework:v2"
```

---

## Environment Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AGENT_NAME` | Yes (for `app.py`) | — | Which agent to serve (e.g., `code-helper`) |
| `AZURE_AI_PROJECT_ENDPOINT` | Yes | — | Azure AI Foundry project endpoint URL |
| `AGENT_DEPLOYMENT_NAME` | No | Per-agent default | Override the model deployment name |
| `ENVIRONMENT` | No | `dev` | Environment label (`dev`, `qa`, `prod`) |

### Authentication Variables

| Variable | When Needed | Description |
|----------|-------------|-------------|
| `AZURE_CLIENT_ID` | Service principal auth | App registration client ID |
| `AZURE_CLIENT_SECRET` | Service principal auth | App registration secret |
| `AZURE_TENANT_ID` | Service principal auth | Azure AD tenant ID |
| _(none)_ | Managed identity | Managed identity auto-detects — no env vars needed |

---

## Authentication

`DefaultAzureCredential` is used for all Azure authentication. It automatically tries multiple credential sources in order:

| Environment | Credential Used | Setup |
|-------------|----------------|-------|
| Local development | Azure CLI (`az login`) | Run `az login` before starting |
| Docker (local) | Service principal env vars | Set `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` |
| ACA (production) | **Managed identity** (recommended) | Enable system-assigned managed identity on the container app |

### Using Managed Identity in ACA (Recommended)

```bash
# Enable system-assigned managed identity
az containerapp identity assign \
  --name "$ACA_NAME" \
  --resource-group "$RG" \
  --system-assigned

# Get the identity's principal ID
PRINCIPAL_ID=$(az containerapp identity show \
  --name "$ACA_NAME" \
  --resource-group "$RG" \
  --query "principalId" -o tsv)

# Assign Cognitive Services User role on the Foundry resource
az role assignment create \
  --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Cognitive Services User" \
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-name>"
```

With managed identity, no secret environment variables are needed in the container app.

### Required RBAC Roles

The identity (service principal or managed identity) needs access to the Foundry endpoint:

| Role | Scope | Purpose |
|------|-------|---------|
| **Cognitive Services User** | Foundry resource or resource group | Call model inference APIs |
| **Azure AI User** | Foundry resource or resource group | Additional agent service access |

---

## Multiple Agents

Each agent runs as a **separate container app** (or Docker container), all sharing the same image:

```bash
# Deploy code-helper
az containerapp create --name code-helper ... --env-vars AGENT_NAME=code-helper ...

# Deploy doc-assistant  
az containerapp create --name doc-assistant ... --env-vars AGENT_NAME=doc-assistant ...
```

The `AGENT_NAME` environment variable selects which agent the container serves. The same Docker image supports all agents — only the env var changes.

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
| `Connection refused on :8088` | Agent not starting | Check `AGENT_NAME` matches a registered agent; check container logs |
| `Model deployment not found` | Wrong deployment name | Verify `AGENT_DEPLOYMENT_NAME` or agent config matches a deployment in your Foundry project |
| `403 Forbidden` on Foundry calls | Missing RBAC | Assign `Cognitive Services User` role to the identity on the Foundry resource |
| Container exits immediately | Startup error | Check logs: `az containerapp logs show --name <name> --resource-group <rg>` |
| `ModuleNotFoundError` in container | Missing dependency | Ensure `requirements.txt` is up to date and the image was rebuilt |
