# Agent Scaffolding Guide

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?logo=python&logoColor=white)
![CLI Tool](https://img.shields.io/badge/CLI-create__agent.py-green?logo=gnubash&logoColor=white)
![Microsoft Agent Framework](https://img.shields.io/badge/Microsoft-Agent%20Framework-0078D4?logo=microsoft&logoColor=white)

## Overview

`scripts/create_agent.py` is a zero-dependency CLI tool that scaffolds a new agent in seconds. It generates the full agent directory, test stubs, and registry entry — matching the exact patterns used by existing agents like `code_helper` and `doc_assistant`.

## Prerequisites

- **Python 3.11+**
- The repository cloned and dependencies installed (`uv sync`)
- No additional packages required — the script uses only the Python standard library

## Quick Start

```bash
# Scaffold a new agent
python scripts/create_agent.py --name my-agent
```

Output:
```
[scaffold] Creating agent 'my-agent'...
[scaffold]   ✓ agents/my_agent/__init__.py
[scaffold]   ✓ agents/my_agent/config.py
[scaffold]   ✓ agents/my_agent/instructions.md
[scaffold]   ✓ agents/my_agent/README.md
[scaffold]   ✓ agents/my_agent/tools/__init__.py
[scaffold]   ✓ agents/my_agent/tools/sample_tool.py
[scaffold]   ✓ agents/my_agent/integrations/__init__.py
[scaffold]   ✓ agents/my_agent/integrations/knowledge.py
[scaffold]   ✓ tests/my_agent/__init__.py
[scaffold]   ✓ tests/my_agent/conftest.py
[scaffold]   ✓ tests/my_agent/test_tools.py
[scaffold]   ✓ tests/my_agent/test_agent_create.py
[scaffold]   ✓ tests/my_agent/test_agent_run.py
[scaffold]   ✓ agents/registry.py (entry added)
[scaffold]   ✓ pyproject.toml (marker added)

[scaffold] ✓ Agent 'my-agent' scaffolded successfully!

[scaffold] Next steps:
[scaffold]   1. Edit agents/my_agent/instructions.md
[scaffold]   2. Add tools in agents/my_agent/tools/
[scaffold]   3. Run: python scripts/run_agent.py --name my-agent
[scaffold]   4. Test: pytest tests/my_agent/ -v
```

## CLI Reference

```
usage: create_agent.py [-h] (--name NAME | --from-file FROM_FILE) [--model MODEL]
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--name` | Yes* | — | Agent name in kebab-case (e.g., `my-agent`) |
| `--from-file` | Yes* | — | Path to YAML config file |
| `--model` | No | `gpt-4o` | Model name for the agent |
| `--help` | No | — | Show help message |

\* `--name` and `--from-file` are mutually exclusive — exactly one is required.

### Name Validation Rules

- Lowercase kebab-case only: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`
- Maximum 50 characters
- Cannot be a Python reserved word (e.g., `class`, `import`, `return`)
- Must not conflict with an existing agent directory or registry entry

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Validation error (invalid name, agent exists) |

## YAML Input Reference

### Schema

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `name` | Yes | — | Agent name in kebab-case |
| `model` | No | `gpt-4o` | Model name |

### Example File

```yaml
# agent-config.yaml
name: my-agent
model: gpt-4o-mini
```

### Usage

```bash
python scripts/create_agent.py --from-file agent-config.yaml
```

When `--from-file` is used, the `model` value from the YAML file takes precedence over any `--model` CLI flag.

## What Gets Generated

```
agents/{module_name}/
├── __init__.py              # Package init
├── config.py                # Agent configuration (extends AgentBaseConfig)
├── instructions.md          # System instructions (markdown)
├── README.md                # Agent documentation with badges, config, and usage
├── tools/
│   ├── __init__.py          # Exports TOOLS list
│   └── sample_tool.py       # Sample greeting tool (plain function)
└── integrations/
    ├── __init__.py          # Package init
    └── knowledge.py         # Knowledge source stub (returns None when disabled)

tests/{module_name}/
├── __init__.py              # Package init
├── conftest.py              # Fixtures with MonkeyPatch for env vars
├── test_tools.py            # Unit tests for the sample tool
├── test_agent_create.py     # Integration test stub for agent assembly
└── test_agent_run.py        # Integration test stub for run lifecycle

agents/registry.py           # Updated with import + AgentRegistryEntry
```

**Total**: 13 files created + 1 file updated = 14 file operations

## Customise Your Agent

After scaffolding, follow these steps to build your agent:

### 1. Edit Instructions

Open `agents/{module_name}/instructions.md` and replace the placeholder content with your agent's system prompt — its role, capabilities, and behaviour guidelines.

### 2. Add Custom Tools

Edit `agents/{module_name}/tools/sample_tool.py` or create new tool files:

```python
# agents/my_agent/tools/my_tool.py
from typing import Annotated
from pydantic import Field


def search_docs(
    query: Annotated[str, Field(description="The search query string.")],
) -> str:
    """Search documentation for a query."""
    return f"Results for: {query}"


TOOLS = [search_docs]
```

Update `agents/{module_name}/tools/__init__.py` to import your new tools.

See the [Custom Tools Guide](custom-tools-guide.md) for full details on function requirements, testing, error handling, and a complete walkthrough.

### 3. Update Config

Edit `agents/{module_name}/config.py` to add agent-specific settings:

```python
from pydantic import Field
from agents._base.config import AgentBaseConfig, _IDENTITY_ALIAS

_SKIP = _IDENTITY_ALIAS

class MyAgentConfig(AgentBaseConfig):
    agent_name: str = Field(default="my-agent", validation_alias=_SKIP)
    agent_deployment_name: str = Field(default="gpt-4o", validation_alias=_SKIP)
    agent_instructions_path: str = Field(default="agents/my_agent/instructions.md", validation_alias=_SKIP)
    # Add custom fields (these CAN be set via env vars normally):
    max_results: int = 10
    api_endpoint: str = ""
```

> **Why `validation_alias`?**  The `.env` file sets `AGENT_NAME` for `app.py` to select
> which agent to serve.  Without `validation_alias`, pydantic-settings would map that
> env var to `agent_name` in every config class, overriding the per-agent default.
> The `_IDENTITY_ALIAS` sentinel prevents this for `agent_name`,
> `agent_deployment_name`, and `agent_instructions_path`.

### 4. Write Tests

Update the generated test stubs in `tests/{module_name}/` with real assertions:

```bash
# Run your agent's tests
pytest tests/my_agent/ -v
```

### 5. Run Your Agent

```bash
# Interactive CLI
python scripts/run_agent.py --name my-agent

# Single prompt
python scripts/run_agent.py --name my-agent --prompt "Hello"

# As a hosted HTTP service
AGENT_NAME=my-agent python app.py
```

## Delete an Agent

Use the deletion script:

```bash
# Delete a single agent
python scripts/delete_agent.py --name my-agent

# Delete all scaffolded agents (built-in agents are excluded)
python scripts/delete_agent.py --all
```

This removes: (1) the agent directory `agents/{module_name}/`, (2) the test directory `tests/{module_name}/`, (3) the import and `AgentRegistryEntry` in `agents/registry.py`.

> **Note:** This only removes the agent from the local codebase. If you've deployed to Azure Container Apps, you need to remove the ACA deployment separately.

## FAQ

**How do I rename an agent after scaffolding?**

There is no automated rename command. You need to: (1) rename the directory under `agents/` and `tests/`, (2) update all class names and imports, (3) update the `agent_name` in config, (4) update the registry entry. It's simpler to scaffold a new agent with the correct name and migrate your custom code.

**How do I add more tools to my agent?**

Create new Python files in `agents/{module_name}/tools/`, define functions and a `TOOLS` list, then update `agents/{module_name}/tools/__init__.py` to aggregate them into a combined `TOOLS` export. No decorator or factory wrapper needed — plain functions work.

**How do I change the model after creation?**

Edit `agents/{module_name}/config.py` and update the `agent_deployment_name` field's default value. Note that `agent_deployment_name` is shielded from env var override (via `validation_alias`) to prevent `.env` from leaking into every agent config.

**Can I scaffold multiple agents at once?**

Not directly. Run the script once per agent. Each invocation is independent and idempotent — it will refuse to overwrite an existing agent.

**Do I need to redeploy after adding a tool?**

No. Agents are assembled in-process — just restart the CLI or hosted service. Tools are picked up from the `TOOLS` list at startup.

## Troubleshooting

| Error Message | Cause | Resolution |
|---------------|-------|------------|
| `Invalid agent name '...' Must be lowercase kebab-case` | Name contains uppercase, underscores, spaces, or invalid characters | Use lowercase letters, numbers, and hyphens only: `my-agent-v2` |
| `Agent name exceeds maximum length of 50 characters` | Name is too long | Choose a shorter name (50 chars max) |
| `Agent name '...' is a Python reserved word` | Name maps to a Python keyword when converted to snake_case | Choose a different name that isn't a Python keyword |
| `Agent '...' already exists at agents/...` | Agent directory already exists | Choose a different name or delete the existing agent first |
| `Test directory already exists at tests/...` | Test directory conflicts | Remove the orphaned test directory or use a different name |
| `Agent '...' is already registered in agents/registry.py` | Registry already has an entry for this name | Remove the existing registry entry or use a different name |
| `Input file not found: ...` | The `--from-file` path doesn't exist | Check the file path and ensure the YAML file exists |
| `Input file missing required field: 'name'` | YAML file doesn't contain a `name:` line | Add `name: your-agent-name` to the YAML file |
| `Permission denied` | Write access to `agents/` or `tests/` is restricted | Check file permissions or run from the repository root |
