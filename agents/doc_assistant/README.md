# Doc Assistant Agent

![Agent](https://img.shields.io/badge/agent-doc--assistant-blue)
![Model](https://img.shields.io/badge/model-gpt--4o-green)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![Agent Framework](https://img.shields.io/badge/Microsoft-Agent%20Framework-0078D4?logo=microsoft&logoColor=white)

An instruction-only documentation assistant built on the Agent Framework Platform.

## Capabilities

| Capability | Description |
|---|---|
| Documentation Q&A | Answers questions about docs and technical writing |
| Content Drafting | Helps draft and improve documentation |

## Configuration

| Setting | config.py Property | Default | Description |
|---|---|---|---|
| Agent name | `agent_name` | `doc-assistant` | Registry identifier |
| Model deployment | `agent_deployment_name` | `gpt-4o` | Azure AI Foundry deployment |

## File Structure

```
agents/doc_assistant/
├── __init__.py
├── config.py              # DocAssistantConfig (extends AgentBaseConfig)
├── instructions.md        # System prompt
├── README.md              # This file
├── integrations/
│   └── __init__.py
└── tools/
    └── __init__.py
```

## Quick Start

```bash
# Run locally
python scripts/run_agent.py --name doc-assistant

# Run as hosted service
AGENT_NAME=doc-assistant python app.py
```
