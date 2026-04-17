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

Search grounding is configured entirely through environment variables (`.env`
file locally, container env vars in ACA). Choose the option that fits your
setup:

| Scenario | Option | What you set |
|----------|--------|--------------|
| You have a search service URL and index name | [Option A](#option-a-explicit-endpoint--index-name) | `AZURE_AI_SEARCH_ENDPOINT` + `AZURE_AI_SEARCH_INDEX_NAME` |
| Your index is registered in Azure AI Foundry | [Option B](#option-b-foundry-knowledge-base-name) | `AZURE_AI_SEARCH_KNOWLEDGE_BASE` |
| You need to search **multiple** indexes | [Option C](#option-c-multiple-search-indexes) | `AZURE_AI_SEARCH_INDEXES` (JSON array) |
| Each agent needs its **own** index(es) | [Option D](#option-d-agent-specific-knowledge-per-agent-indexes) | `{AGENT}_SEARCH_ENDPOINT` + `{AGENT}_SEARCH_INDEX_NAME` (+ optional `{AGENT}_SEARCH_INDEXES` JSON array) |

> **Tip:** Options A/B/C are additive shared config. Option D overrides
> A/B/C per-agent — if an agent's `knowledge.py` returns providers,
> the shared config is skipped for that agent.

### Option A: Explicit Endpoint + Index Name

Set both values directly:

```bash
# .env (commercial cloud)
AZURE_AI_SEARCH_ENDPOINT=https://<search-service>.search.windows.net
AZURE_AI_SEARCH_INDEX_NAME=<index-name>

# .env (US Government)
AZURE_AI_SEARCH_ENDPOINT=https://<search-service>.search.azure.us
AZURE_AI_SEARCH_INDEX_NAME=<index-name>
```

Use this when you know the exact search service URL and index name.

> **Gov cloud:** The provider auto-detects `.azure.us` endpoints and sets the
> correct token audience (`https://search.azure.us`) on the `SearchClient`
> automatically. No extra configuration is needed beyond using the correct
> endpoint URL.

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

### Option C: Multiple Search Indexes

To ground an agent on **multiple knowledge bases** simultaneously, set
`AZURE_AI_SEARCH_INDEXES` as a JSON array:

```bash
# .env
AZURE_AI_SEARCH_INDEXES='[
  {"endpoint": "https://search1.search.windows.net", "index_name": "products"},
  {"endpoint": "https://search2.search.windows.net", "index_name": "support-docs", "semantic_config": "my-semantic-config"}
]'
```

Each entry requires `endpoint` and `index_name`. The `semantic_config` field
is optional per index.

**When to use this:**

- Agent needs to answer from both product docs and support articles
- Different data lives in separate search services or indexes
- You want to combine internal knowledge with external documentation

**How it combines with other options:**

Option C is **additive**. If you also set Option A or B, those indexes are
searched alongside the ones in the list. For example:

```bash
# .env — searches 3 indexes total (1 from Option A + 2 from Option C)
AZURE_AI_SEARCH_ENDPOINT=https://primary.search.windows.net
AZURE_AI_SEARCH_INDEX_NAME=main-docs
AZURE_AI_SEARCH_INDEXES='[
  {"endpoint": "https://secondary.search.windows.net", "index_name": "faq"},
  {"endpoint": "https://secondary.search.windows.net", "index_name": "tutorials"}
]'
```

All results from all indexes are injected into the agent's context before
each turn. The agent sees them as a single merged set of search results.

> **Note:** Each search service used in the list needs the **Search Index Data
> Reader** RBAC role assigned to the running identity. See
> [RBAC / Permissions](#rbac--permissions).

### Option D: Agent-Specific Knowledge (Per-Agent Indexes)

When deploying **multiple agents** together, each agent can have its own
search index via agent-prefixed environment variables. This is configured
in each agent's `integrations/knowledge.py` file.

**How it works:**

Each agent's `knowledge.py` exports a `get_context_providers(config)` function.
The factory calls it before falling back to the shared base-config env vars:

1. If the function returns a **list** → those providers are used (agent takes control)
2. If the function returns **`None`** → falls back to base-config Options A/B/C
3. If the module doesn't exist → falls back to base-config Options A/B/C

**Example — give each agent its own index:**

```bash
# .env — each agent searches a different index
CODE_HELPER_SEARCH_ENDPOINT=https://search.search.windows.net
CODE_HELPER_SEARCH_INDEX_NAME=code-docs
CODE_HELPER_SEARCH_SEMANTIC_CONFIG=code-semantic

DOC_ASSISTANT_SEARCH_ENDPOINT=https://search.search.windows.net
DOC_ASSISTANT_SEARCH_INDEX_NAME=product-docs
DOC_ASSISTANT_SEARCH_SEMANTIC_CONFIG=docs-semantic
```

**Example — give one agent multiple indexes:**

Like Option C for shared config, each agent also supports a JSON array of
indexes via `{AGENT}_SEARCH_INDEXES`. Single and multi are additive:

```bash
# .env — code-helper searches 3 indexes total (1 single + 2 from JSON)
CODE_HELPER_SEARCH_ENDPOINT=https://search.search.windows.net
CODE_HELPER_SEARCH_INDEX_NAME=code-docs
CODE_HELPER_SEARCH_INDEXES=[{"endpoint":"https://search.search.windows.net","index_name":"api-ref"},{"endpoint":"https://s2.search.windows.net","index_name":"samples","semantic_config":"samples-sem"}]
```

The env var prefix is derived from the agent's module name in UPPER_SNAKE_CASE:

| Agent Name | Module | Env Var Prefix |
|-----------|--------|----------------|
| `code-helper` | `code_helper` | `CODE_HELPER_` |
| `doc-assistant` | `doc_assistant` | `DOC_ASSISTANT_` |
| `my-new-agent` | `my_new_agent` | `MY_NEW_AGENT_` |

**When to use this:**

- Multiple agents deployed in the same container, each needing different data
- You want per-agent search config without separate deployments
- Agent needs a knowledge base that other agents shouldn't see

**How it combines with base config:**

Agent-specific config **overrides** base config — it does NOT combine with it.
If `CODE_HELPER_SEARCH_ENDPOINT` and `CODE_HELPER_SEARCH_INDEX_NAME` are set,
the `code-helper` agent uses only that index. The shared `AZURE_AI_SEARCH_*`
vars are ignored for that agent (but still apply to any agent whose
`knowledge.py` returns `None`).

**Customising `knowledge.py`:**

The scaffolded `knowledge.py` supports both a single index and a JSON array
of multiple indexes out of the box. For fully custom logic (e.g. hardcoded
indexes or conditional logic), edit the function directly:

```python
# agents/my_agent/integrations/knowledge.py
def get_context_providers(config):
    """Return agent-specific context providers."""
    from agents._base.client import get_credential
    from agents._base.integrations.search import AzureAISearchContextProvider

    credential = get_credential(authority=config.azure_authority_host)
    return [
        AzureAISearchContextProvider(
            endpoint="https://search.search.windows.net",
            index_name="primary-index",
            credential=credential,
        ),
        AzureAISearchContextProvider(
            endpoint="https://search.search.windows.net",
            index_name="secondary-index",
            semantic_config="my-semantic",
            credential=credential,
        ),
    ]
```

## RBAC / Permissions

![RBAC](https://img.shields.io/badge/RBAC-Search%20Index%20Data%20Reader-green?logo=microsoftazure&logoColor=white)

The identity running the agent needs the **Search Index Data Reader** role on
**every** Azure AI Search service referenced in your config (Options A, B, C, or D).

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
| `AZURE_AI_SEARCH_INDEXES` | JSON array of `{endpoint, index_name, semantic_config}` objects *(optional, for multiple indexes)* |

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
| `AZURE_AI_SEARCH_INDEXES` | `azure_ai_search_indexes` | Option C | JSON array of `{endpoint, index_name, semantic_config}` objects |
| `{AGENT}_SEARCH_ENDPOINT` | — | Option D | Per-agent search endpoint (e.g. `CODE_HELPER_SEARCH_ENDPOINT`) |
| `{AGENT}_SEARCH_INDEX_NAME` | — | Option D | Per-agent index name |
| `{AGENT}_SEARCH_SEMANTIC_CONFIG` | — | Option D | Per-agent semantic config (optional) |
| `{AGENT}_SEARCH_INDEXES` | — | Option D | Per-agent JSON array of indexes (additive with single) |
| `AZURE_AUTHORITY_HOST` | `azure_authority_host` | Gov cloud | Authority URL — affects how the search credential authenticates (see [Gov Cloud](#sovereign--government-clouds)) |

If none of these are set, agents run without search grounding (model-only).

## Architecture

The integration is built from two components:

### `AzureAISearchContextProvider` ([agents/_base/integrations/search.py](../agents/_base/integrations/search.py))

A `BaseContextProvider` subclass that:

- Accepts a `credential` parameter (a `DefaultAzureCredential` instance
  created by `agent_factory.py` with the correct authority for your cloud)
- Auto-detects government cloud endpoints (`.azure.us`) and sets the
  `SearchClient` audience to `https://search.azure.us` so token requests
  use the correct scope
- In `before_run()`, extracts the user query and calls `SearchClient.search()`
- Looks for content in fields named `content`, `chunk`, or `snippet`
  (falls back to the first long string field)
- Extracts source titles from `title` or `doc_url` fields
- Injects results via `context.extend_instructions()` with a strict
  grounding prompt

### `_collect_context_providers()` ([agents/_base/agent_factory.py](../agents/_base/agent_factory.py))

Called by `create_agent()` to wire up providers at assembly time:

1. Calls `_discover_agent_context_providers(config)` to check for an
   agent-specific `knowledge.py` module (Option D)
2. If discovery returns a list (even empty), uses it — **skips base config**
3. If discovery returns `None`, falls back to base config:
   a. Creates a `DefaultAzureCredential` with the configured `authority`
   b. Checks for explicit `endpoint` + `index_name` in config (Option A)
   c. If not found, tries to resolve `knowledge_base` via the Foundry API (Option B)
   d. Iterates `azure_ai_search_indexes` and creates a provider per entry (Option C)
4. Returns the combined providers list passed to `client.as_agent(context_providers=...)`

All providers run independently — each queries its own index and injects
results into the agent's context.

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

## Sovereign / Government Clouds

[![US Government](https://img.shields.io/badge/Azure-US%20Government-003366?logo=microsoftazure&logoColor=white)](https://learn.microsoft.com/azure/azure-government/)

Search grounding works on sovereign clouds (US Government, China) with no
extra code changes. The platform handles two gov-specific requirements
automatically:

### Credential Authority

When `AZURE_AUTHORITY_HOST` is set (e.g., `https://login.microsoftonline.us`),
`agent_factory.py` creates a `DefaultAzureCredential` with the matching
`authority` and passes it to every search provider. This ensures managed
identity / CLI tokens are requested from the correct login endpoint.

### Search Token Audience

The `SearchClient` SDK defaults to commercial Azure scope
(`https://search.windows.net`). On government cloud this produces an
`invalid_scope 400` error. The provider auto-detects `.azure.us` in the
endpoint URL and overrides the audience to `https://search.azure.us`.

### What You Need to Set

| Cloud | Search Endpoint | Additional Env Vars |
|-------|----------------|---------------------|
| Commercial (default) | `https://<name>.search.windows.net` | None |
| US Government | `https://<name>.search.azure.us` | `AZURE_AUTHORITY_HOST=https://login.microsoftonline.us` |
| China (21Vianet) | `https://<name>.search.azure.cn` | `AZURE_AUTHORITY_HOST=https://login.chinacloudapi.cn` |

All other search configuration (Options A, B, C, D, RBAC, semantic config)
works identically across clouds.

---

## Troubleshooting

### Agent answers from general knowledge, not the knowledge base

- Verify `.env` has the search config (Option A, B, C, or D)
- Check agent logs for `Enabled Azure AI Search context provider`
  (one line per index when using Option C)
- Check for `Injected N search results` in logs during conversations
- If you see `No search results`, the index may be empty or the query
  didn't match — try a broader question

### 403 Forbidden on search queries

Your identity lacks the **Search Index Data Reader** role. See
[RBAC / Permissions](#rbac--permissions) above.

### `invalid_scope 400` on search queries (gov cloud)

The `SearchClient` is requesting a token for the wrong audience. This
happens when:

- Your endpoint is `.search.azure.us` but the SDK uses the default
  commercial audience — the provider handles this automatically, so
  ensure you're on the latest code
- `AZURE_AUTHORITY_HOST` is not set — the credential authenticates
  against commercial Azure and the resulting token is rejected by gov
  cloud search. Set `AZURE_AUTHORITY_HOST=https://login.microsoftonline.us`

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
- For gov cloud: ensure `AZURE_AUTHORITY_HOST` is set correctly

### Multiple indexes: some work, some don't

- Each search service needs its own **Search Index Data Reader** role assignment
- Verify each endpoint URL and index name independently
- A failing index logs a warning but does not block other indexes from working
