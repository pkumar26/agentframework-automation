# Probation Poc Agent Agent

![Agent](https://img.shields.io/badge/agent-probation-poc-agent-blue)
![Model](https://img.shields.io/badge/model-gpt-4o-green)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![Agent Framework](https://img.shields.io/badge/Microsoft-Agent%20Framework-0078D4?logo=microsoft&logoColor=white)

A custom agent built on the Agent Framework Platform.

## Capabilities

| Capability | Description |
|---|---|
| General Q&A | Answers questions and provides guidance |

## Tools

| Tool | Function | Description |
|---|---|---|
| `greet_user` | `agents/probation_poc_agent/tools/sample_tool.py` | Sample greeting tool |

## Configuration

| Setting | config.py Property | Default | Description |
|---|---|---|---|
| Agent name | `agent_name` | `probation-poc-agent` | Registry identifier |
| Model deployment | `agent_deployment_name` | `gpt-4o` | Azure AI Foundry deployment |

> **Note:** All settings are per-agent in `config.py`.
> The `.env` file is for shared infrastructure only.

## File Structure

```
agents/probation_poc_agent/
├── __init__.py
├── config.py              # ProbationPocAgentConfig (extends AgentBaseConfig)
├── instructions.md        # System prompt
├── README.md              # This file
├── integrations/
│   ├── __init__.py
│   └── knowledge.py       # Knowledge integration stub
└── tools/
    ├── __init__.py
    └── sample_tool.py     # greet_user function
```

## Quick Start

```bash
# Run locally
python scripts/run_agent.py --name probation-poc-agent

# Run as hosted service
AGENT_NAME=probation-poc-agent python app.py
```

## Testing

```bash
# Unit tests
pytest tests/probation_poc_agent/ -v

# Skip integration tests
pytest tests/probation_poc_agent/ -v -m "not integration"
```
