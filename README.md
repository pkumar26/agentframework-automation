# Agent Framework Automation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Agent Framework](https://img.shields.io/badge/Microsoft-Agent%20Framework-0078D4?logo=microsoft&logoColor=white)](https://learn.microsoft.com/agent-framework/)
[![Azure AI Foundry](https://img.shields.io/badge/Azure%20AI-Foundry-0089D6?logo=microsoftazure&logoColor=white)](https://ai.azure.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![GitHub stars](https://img.shields.io/github/stars/pkumar26/agentframework-automation?style=social)](https://github.com/pkumar26/agentframework-automation/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/pkumar26/agentframework-automation?style=social)](https://github.com/pkumar26/agentframework-automation/network/members)
[![GitHub issues](https://img.shields.io/github/issues/pkumar26/agentframework-automation)](https://github.com/pkumar26/agentframework-automation/issues)
[![Last commit](https://img.shields.io/github/last-commit/pkumar26/agentframework-automation)](https://github.com/pkumar26/agentframework-automation/commits/main)
[![Repo size](https://img.shields.io/github/repo-size/pkumar26/agentframework-automation)](https://github.com/pkumar26/agentframework-automation)

A multi-agent platform built on **Microsoft Agent Framework** with models inference from **Azure AI Foundry**. Agents run locally for development/testing and deploy to **Azure Container Apps** for production.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Azure AI Foundry (Model Inference)             │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │  GPT-4o  │ │ GPT-4.1  │ │ Custom Model │    │
│  └────▲─────┘ └────▲─────┘ └───────▲──────┘    │
└───────┼─────────────┼───────────────┼───────────┘
        │             │               │
┌───────┼─────────────┼───────────────┼───────────┐
│  Agent Runtime (Local / ACA Container)          │
│  ┌─────────────────────────────────────────┐    │
│  │  Microsoft Agent Framework              │    │
│  │  ┌─────────────┐  ┌─────────────────┐   │    │
│  │  │ code-helper │  │ doc-assistant    │   │    │
│  │  │ + tools     │  │ + instructions   │   │    │
│  │  └─────────────┘  └─────────────────┘   │    │
│  └─────────────────────────────────────────┘    │
│  Hosting: agentserver-agentframework → :8088    │
└─────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

![Azure CLI](https://img.shields.io/badge/Azure%20CLI-2.60+-0078D4?logo=microsoftazure&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)

- Azure subscription with an AI Foundry project
- Model deployment (e.g., `gpt-4o`) in Foundry
- Python 3.11+

### Setup

```bash
# Clone and install
git clone https://github.com/pkumar26/agentframework-automation.git
cd agentframework-automation
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your Foundry project endpoint

# Authenticate
az login
```

### Run an agent locally

```bash
# Interactive mode
python scripts/run_agent.py --name code-helper

# Single prompt
python scripts/run_agent.py --name code-helper --prompt "Write a Python fibonacci function"
```

### Run as a hosted service

```bash
# Local server on :8088
AGENT_NAME=code-helper python app.py

# Test with curl
curl -X POST http://localhost:8088/responses \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello!"}'
```

### Run in Docker

![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

```bash
docker compose up --build
```

## Project Structure

```
agentframework-automation/
├── app.py                     # Hosting adapter (ACA / local server)
├── Dockerfile                 # Container image
├── docker-compose.yml         # Local container orchestration
├── agents/
│   ├── __init__.py            # Public API
│   ├── registry.py            # Central agent registry
│   ├── _base/
│   │   ├── config.py          # AgentBaseConfig (pydantic-settings)
│   │   ├── client.py          # AzureOpenAIResponsesClient factory
│   │   ├── agent_factory.py   # create_agent() — assembles Agent in-process
│   │   ├── run.py             # run_agent() — async execution
│   │   ├── tools/             # @tool decorator utilities
│   │   └── integrations/      # Shared integration stubs
│   ├── code_helper/           # Example: tool-augmented agent
│   │   ├── config.py
│   │   ├── instructions.md
│   │   └── tools/
│   └── doc_assistant/         # Example: instruction-only agent
│       ├── config.py
│       └── instructions.md
├── scripts/
│   ├── run_agent.py           # CLI for local execution
│   ├── create_agent.py        # Scaffold a new agent
│   └── delete_agent.py        # Remove a scaffolded agent
└── tests/
```

## Scaffold a New Agent

![Scaffolding](https://img.shields.io/badge/CLI-Scaffolding-green?logo=gnubash&logoColor=white)

```bash
# Create a new agent with all files, tests, and registry entry
python scripts/create_agent.py --name my-agent

# Remove it
python scripts/delete_agent.py --name my-agent
```

## Deploy to Azure Container Apps

![Azure Container Apps](https://img.shields.io/badge/Azure-Container%20Apps-0078D4?logo=microsoftazure&logoColor=white)

```bash
# Build and push container image
az acr login --name <your-registry>
docker build -t <your-registry>.azurecr.io/code-helper:v1 .
docker push <your-registry>.azurecr.io/code-helper:v1

# Deploy to ACA
az containerapp create \
  --name code-helper \
  --resource-group <rg> \
  --environment <aca-env> \
  --image <your-registry>.azurecr.io/code-helper:v1 \
  --target-port 8088 \
  --ingress external \
  --env-vars AGENT_NAME=code-helper AZURE_AI_PROJECT_ENDPOINT=<endpoint>
```

See the [Deployment Guide](docs/deployment-guide.md) for full ACA setup, managed identity, multi-agent deployment, and troubleshooting.

## Agent Documentation

- **[Code Helper](agents/code_helper/README.md)** — Tool-augmented coding assistant for debugging, code review, and technical Q&A
- **[Doc Assistant](agents/doc_assistant/README.md)** — Instruction-only documentation specialist for READMEs, API docs, and technical writing

## Guides

- **[Deployment Guide](docs/deployment-guide.md)** — Local, Docker, and Azure Container Apps deployment (setup, authentication, multi-agent, troubleshooting)
- **[Scaffolding Guide](docs/scaffolding-guide.md)** — YAML format, customisation, and FAQ for agent scaffolding
- **[Custom Tools Guide](docs/custom-tools-guide.md)** — How to write, test, and run custom Python tool functions

## Testing

![pytest](https://img.shields.io/badge/pytest-8.0+-0A9EDC?logo=pytest&logoColor=white)

```bash
# Unit tests (no Azure credentials needed)
pytest tests/ -v -m "not integration"

# Integration tests (requires AZURE_AI_PROJECT_ENDPOINT)
pytest tests/ -v -m integration
```

## License

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
