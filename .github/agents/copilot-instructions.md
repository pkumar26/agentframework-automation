# agentframework-automation Development Guidelines

## Active Technologies
- Python 3.11+ with `agent-framework>=1.0.0rc5`, `azure-identity>=1.15.0`, `pydantic-settings>=2.0.0`
- Microsoft Agent Framework for local/container agent orchestration
- Azure AI Foundry for model inference (GPT-4o, GPT-4.1, custom deployments)
- Azure Container Apps for production hosting via `azure-ai-agentserver-agentframework`
- Agent scaffolding: Python standard library only (argparse, pathlib, textwrap, re); pydantic-settings (for generated config classes)

## Project Structure

```text
agents/          # Agent packages (_base/, code_helper/, doc_assistant/, etc.)
tests/           # Unit + integration tests mirroring agents/ structure
scripts/         # CLI tools (run_agent, create_agent, delete_agent)
docs/            # Guides: deployment, scaffolding, custom tools
app.py           # Hosting adapter for ACA / local HTTP server (:8088)
Dockerfile       # Container image
docker-compose.yml
```

## Commands

```bash
pip install -e ".[dev]"                           # Install dependencies
pytest tests/ -m "not integration" -v             # Unit tests
pytest tests/ -m integration -v                   # Integration tests (requires AZURE_AI_PROJECT_ENDPOINT)
python scripts/run_agent.py --name <agent>        # Run agent interactively
python scripts/run_agent.py --name <agent> --prompt "..."  # Single prompt
AGENT_NAME=<agent> python app.py                  # Start HTTP service on :8088
python scripts/create_agent.py --name <agent>     # Scaffold a new agent
python scripts/delete_agent.py --name <agent>     # Remove an agent
docker compose up --build                         # Run in Docker
```

## Code Style

Python 3.11+: black (line-length=100), isort (profile=black), flake8

## Architecture

- **Models** run in Azure AI Foundry (inference only) — accessed via `AzureOpenAIResponsesClient`
- **Agent runtime** runs locally or in Azure Container Apps — orchestration, tools, instructions all in-process
- **Tools** are plain Python functions with `Annotated` type hints — auto-wrapped by Agent Framework
- **Hosting** via `azure-ai-agentserver-agentframework` exposes `/responses` endpoint on port 8088

## Key Patterns

- Each agent has: `config.py` (pydantic-settings), `instructions.md`, `tools/` (TOOLS list), `integrations/`
- `agents/registry.py` maps agent names → config classes and factory functions
- `agents/_base/agent_factory.py` loads instructions + tools and calls `client.as_agent()`
- `agents/_base/run.py` provides async `run_agent_async()` and sync `run_agent()` wrappers

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
