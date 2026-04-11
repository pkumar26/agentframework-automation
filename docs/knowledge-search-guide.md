# Knowledge Base & Search Guide

[![Azure AI Search](https://img.shields.io/badge/Azure%20AI-Search-0078D4?logo=microsoftazure&logoColor=white)](https://learn.microsoft.com/azure/search/)
[![Azure AI Foundry](https://img.shields.io/badge/Azure%20AI-Foundry-0089D6?logo=microsoftazure&logoColor=white)](https://ai.azure.com/)
[![DefaultAzureCredential](https://img.shields.io/badge/Auth-DefaultAzureCredential-blue?logo=microsoftazure&logoColor=white)](https://learn.microsoft.com/python/api/azure-identity/azure.identity.defaultazurecredential)

This guide explains how to ground your agents on your own data using
**Azure AI Search** so they answer exclusively from your knowledge base
instead of general model knowledge.

## How It Works

The platform uses a **context provider** pattern from the Microsoft Agent Framework.
Before every model turn, the `AzureAISearchContextProvider`:

1. Extracts the latest user message from the conversation
2. Queries your Azure AI Search index (keyword or semantic search)
3. Injects the top results into the agent's context via `extend_instructions()`
4. The model receives a strict grounding prompt telling it to answer **only**
   from the search results

This is transparent to individual agents — any agent automatically gets RAG
grounding when the search config is present.

```
User message
    │
    ▼
┌──────────────────────────────┐
│  AzureAISearchContextProvider│
│  (before_run hook)           │
│                              │
│  1. Extract query            │
│  2. Search index             │
│  3. Inject results + prompt  │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Agent (model call)          │
│  Answers from injected       │
│  search results only         │
└──────────────────────────────┘
```

## Prerequisites

![Azure CLI](https://img.shields.io/badge/Azure%20CLI-2.60+-0078D4?logo=microsoftazure&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)

- An Azure AI Search service with at least one populated index
- The `azure-search-documents` package (already in project dependencies)
- Authentication: `az login` locally, or a managed identity in Container Apps

## Configuration

There are two ways to connect your agents to a search index. Both are
configured entirely through environment variables (`.env` file).

### Option A: Explicit Endpoint + Index Name

Set both values directly:

```bash
# .env
AZURE_AI_SEARCH_ENDPOINT=https://<search-service>.search.windows.net
AZURE_AI_SEARCH_INDEX_NAME=<index-name>
```

Use this when you know the exact search service URL and index name.

### Option B: Foundry Knowledge Base Name

If your search index is registered as a knowledge base in Azure AI Foundry,
you can reference it by name and the platform resolves the endpoint and index
automatically:

```bash
# .env
AZURE_AI_SEARCH_KNOWLEDGE_BASE=<knowledge-base-name>
```

This uses the Foundry project's `indexes` and `connections` APIs to look up
the underlying search service endpoint and index name. To find the correct
knowledge base name, use the listing cell in
[notebook 02](../notebooks/02_build_and_run_agent.ipynb) or run:

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient(
    endpoint="<your-foundry-endpoint>",
    credential=DefaultAzureCredential(),
)
for idx in client.indexes.list():
    print(f"{idx.name}  →  index: {idx.index_name}")
```

> **Note:** The knowledge base name in the Foundry API may differ from the
> display name shown in the Azure AI Foundry portal.

### Optional: Semantic Search

If your index has a semantic configuration, enable it for higher-quality
ranking:

```bash
# .env (add alongside Option A or B)
AZURE_AI_SEARCH_SEMANTIC_CONFIG=<semantic-config-name>
```

Without this, the provider uses standard keyword search.

## RBAC / Permissions

![RBAC](https://img.shields.io/badge/RBAC-Search%20Index%20Data%20Reader-green?logo=microsoftazure&logoColor=white)

The identity running the agent needs the **Search Index Data Reader** role on
the Azure AI Search service.

### Local Development

Your `az login` identity needs the role:

```bash
# Find your search service resource ID
az search service show \
  --name <search-service-name> \
  --resource-group <rg> \
  --query id -o tsv

# Assign the role
az role assignment create \
  --role "Search Index Data Reader" \
  --assignee <your-email-or-object-id> \
  --scope <search-service-resource-id>
```

Or assign it in the Azure portal: **Search service → Access control (IAM) →
Add role assignment → Search Index Data Reader**.

### Container Apps (Production)

Assign the role to the Container App's **managed identity**:

```bash
PRINCIPAL_ID=$(az identity show \
  --name "id-$AGENT-dev" \
  --resource-group "$RG" \
  --query principalId -o tsv)

az role assignment create \
  --role "Search Index Data Reader" \
  --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --scope <search-service-resource-id>
```

## CI/CD: Deploy with Search Grounding

The `deploy.yml` workflow automatically passes search configuration to ACA
when the corresponding **GitHub repository variables** are set.

**Set these in your repo** (Settings → Variables and secrets → Actions → Variables):

| GitHub Variable | Value |
|-----------------|-------|
| `AZURE_AI_SEARCH_ENDPOINT` | `https://<search-service>.search.windows.net` |
| `AZURE_AI_SEARCH_INDEX_NAME` | `<index-name>` |
| `AZURE_AI_SEARCH_SEMANTIC_CONFIG` | `<semantic-config-name>` *(optional)* |

The workflow conditionally includes each variable only when it is set —
if none are configured, agents deploy without search grounding (no errors).

The `.bicepparam` parameter files (`infra/parameters.{dev,qa,prod}.bicepparam`)
also contain commented-out examples for manual CLI deployments.

For the full ACA deployment walkthrough, see the
[Deployment Guide — Knowledge Base / Search Grounding](deployment-guide.md#knowledge-base--search-grounding-in-aca).

## Config Reference

All fields are defined in `AgentBaseConfig` ([agents/_base/config.py](../agents/_base/config.py))
and read automatically from environment variables:

| Environment Variable | Config Field | Required | Description |
|---------------------|-------------|----------|-------------|
| `AZURE_AI_SEARCH_ENDPOINT` | `azure_ai_search_endpoint` | Option A | Search service URL |
| `AZURE_AI_SEARCH_INDEX_NAME` | `azure_ai_search_index_name` | Option A | Index to query |
| `AZURE_AI_SEARCH_KNOWLEDGE_BASE` | `azure_ai_search_knowledge_base` | Option B | Foundry knowledge base name |
| `AZURE_AI_SEARCH_SEMANTIC_CONFIG` | `azure_ai_search_semantic_config` | No | Semantic configuration name |

If none of these are set, agents run without search grounding (model-only).

## Architecture

The integration is built from two components:

### `AzureAISearchContextProvider` ([agents/_base/integrations/search.py](../agents/_base/integrations/search.py))

A `BaseContextProvider` subclass that:

- Creates a `SearchClient` with `DefaultAzureCredential`
- In `before_run()`, extracts the user query and calls `SearchClient.search()`
- Looks for content in fields named `content`, `chunk`, or `snippet`
  (falls back to the first long string field)
- Extracts source titles from `title` or `doc_url` fields
- Injects results via `context.extend_instructions()` with a strict
  grounding prompt

### `_collect_context_providers()` ([agents/_base/agent_factory.py](../agents/_base/agent_factory.py))

Called by `create_agent()` to wire up providers at assembly time:

1. Checks for explicit `endpoint` + `index_name` in config
2. If not found, tries to resolve `knowledge_base` via the Foundry API
3. Wraps the resolved config in an `AzureAISearchContextProvider`
4. Returns the providers list passed to `client.as_agent(context_providers=...)`

## Supported Index Field Names

The provider auto-detects content from these field names (in priority order):

| Field | Purpose |
|-------|---------|
| `content` | Primary content field (common in push-based indexes) |
| `chunk` | Chunked content (common in Foundry-created indexes) |
| `snippet` | Snippet field (common in SharePoint/connector indexes) |
| `title` | Document title (for source citations) |
| `doc_url` | Document URL (filename extracted for citations if no `title`) |

If none of these match, the provider falls back to the first string field
longer than 50 characters (skipping `@search.*` metadata and `*_vector` fields).

## Troubleshooting

### Agent answers from general knowledge, not the knowledge base

- Verify `.env` has the search config (Option A or B)
- Check agent logs for `Enabled Azure AI Search context provider`
- Check for `Injected N search results` in logs during conversations
- If you see `No search results`, the index may be empty or the query
  didn't match — try a broader question

### 403 Forbidden on search queries

Your identity lacks the **Search Index Data Reader** role. See
[RBAC / Permissions](#rbac--permissions) above.

### Knowledge base name not found

The API name may differ from the portal display name. Run the listing
snippet in [Option B](#option-b-foundry-knowledge-base-name) to see
the actual API names.

### Search results found but content is empty

Your index uses a non-standard field name for content. Check the field
names in the Azure portal (Search service → Indexes → Fields) and see
[Supported Index Field Names](#supported-index-field-names).

### Search query errors in logs

- Verify the search endpoint URL is correct and reachable
- Confirm the index name exists on that search service
- Check that `DefaultAzureCredential` can authenticate (run `az account show`)
