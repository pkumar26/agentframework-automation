# Probation Q A Agent Agent

![Agent](https://img.shields.io/badge/agent-probation-q-a-agent-blue)
![Model](https://img.shields.io/badge/model-gpt-5.1-green)
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
| `greet_user` | `agents/probation_q_a_agent/tools/sample_tool.py` | Sample greeting tool |

## Configuration

| Setting | config.py Property | Default | Description |
|---|---|---|---|
| Agent name | `agent_name` | `probation-q-a-agent` | Registry identifier |
| Model deployment | `agent_deployment_name` | `gpt-5.1` | Azure AI Foundry deployment |

> **Note:** All settings are per-agent in `config.py`.
> The `.env` file is for shared infrastructure only.

## File Structure

```
agents/probation_q_a_agent/
├── __init__.py
├── config.py              # ProbationQAAgentConfig (extends AgentBaseConfig)
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
python scripts/run_agent.py --name probation-q-a-agent

# Run as hosted service
AGENT_NAME=probation-q-a-agent python app.py
```

## Testing

```bash
# Unit tests
pytest tests/probation_q_a_agent/ -v

# Skip integration tests
pytest tests/probation_q_a_agent/ -v -m "not integration"
```
