# Code Helper Agent

![Agent](https://img.shields.io/badge/agent-code--helper-blue)
![Model](https://img.shields.io/badge/model-gpt--4o-green)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![Agent Framework](https://img.shields.io/badge/Microsoft-Agent%20Framework-0078D4?logo=microsoft&logoColor=white)

A tool-augmented coding assistant built on the Agent Framework Platform.

## Capabilities

| Capability | Description |
|---|---|
| General Q&A | Answers coding questions and provides guidance |
| Code Generation | Writes code based on requirements |
| Code Review | Reviews and suggests improvements |

## Tools

| Tool | Function | Description |
|---|---|---|
| `greet_user` | `agents/code_helper/tools/sample_tool.py` | Sample greeting tool |

## Configuration

| Setting | config.py Property | Default | Description |
|---|---|---|---|
| Agent name | `agent_name` | `code-helper` | Registry identifier |
| Model deployment | `agent_deployment_name` | `gpt-4o` | Azure AI Foundry deployment |

> **Note:** All settings are per-agent in `config.py`.
> The `.env` file is for shared infrastructure only.

### Per-Agent Knowledge Base

Set agent-specific search indexes via env vars (overrides shared `AZURE_AI_SEARCH_*`):

```bash
CODE_HELPER_SEARCH_ENDPOINT=https://<search>.search.windows.net
CODE_HELPER_SEARCH_INDEX_NAME=<index-name>
CODE_HELPER_SEARCH_SEMANTIC_CONFIG=<semantic-config>   # optional
```

See `integrations/knowledge.py` and the [Knowledge & Search Guide](../../docs/knowledge-search-guide.md#option-d-agent-specific-knowledge-per-agent-indexes).

### Per-Agent MCP Servers

Give this agent its own MCP tools (overrides shared `MCP_SERVERS`):

```bash
CODE_HELPER_MCP_SERVERS='[{"name":"github","transport":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-github"]}]'
```

See the [Custom Tools Guide](../../docs/custom-tools-guide.md#mcp-servers).

## File Structure

```
agents/code_helper/
├── __init__.py
├── config.py              # CodeHelperConfig (extends AgentBaseConfig)
├── instructions.md        # System prompt
├── README.md              # This file
├── integrations/
│   ├── __init__.py
│   └── knowledge.py       # Per-agent search config
└── tools/
    ├── __init__.py
    └── sample_tool.py     # greet_user function
```

## Quick Start

```bash
# Run locally
python scripts/run_agent.py --name code-helper

# Run as hosted service
AGENT_NAME=code-helper python app.py
```

## Testing

```bash
# Unit tests
pytest tests/code_helper/ -v

# Skip integration tests
pytest tests/code_helper/ -v -m "not integration"
```
