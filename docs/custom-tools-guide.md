# Custom Tools Guide

[![Microsoft Agent Framework](https://img.shields.io/badge/Microsoft-Agent%20Framework-0078D4?logo=microsoft&logoColor=white)](https://learn.microsoft.com/agent-framework/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)

This guide walks you through adding custom tools to any agent in the platform — from writing your first tool function to testing and deploying it.

## How Tools Work

Tools let your agent call Python functions during a conversation. When the agent decides it needs a tool, the Agent Framework:

1. Pauses the agent's response
2. Calls your Python function with the arguments the agent chose
3. Sends the function's return value back to the agent
4. The agent incorporates the result into its response

The Agent Framework **auto-wraps plain Python functions** as tools — no manual schema writing or factory calls needed. It generates a JSON schema from your function's signature, type annotations, and `Annotated` metadata.

## Quick Start: Add a Tool in 3 Steps

### 1. Write the Function

Create a new file in your agent's `tools/` directory:

```python
# agents/code_helper/tools/calculator.py
from typing import Annotated
from pydantic import Field


def add_numbers(
    a: Annotated[int, Field(description="The first number.")],
    b: Annotated[int, Field(description="The second number.")],
) -> str:
    """Add two numbers together."""
    return str(a + b)


# Export the tool — agent_factory picks this up automatically
TOOLS = [add_numbers]
```

### 2. Register in `__init__.py`

Update the agent's tools `__init__.py` to include your new tool:

```python
# agents/code_helper/tools/__init__.py
"""Code-helper agent tools."""

from agents.code_helper.tools.sample_tool import TOOLS as SAMPLE_TOOLS
from agents.code_helper.tools.calculator import TOOLS as CALC_TOOLS

TOOLS = SAMPLE_TOOLS + CALC_TOOLS

__all__ = ["TOOLS"]
```

### 3. Restart Your Agent

```bash
# Local CLI
python scripts/run_agent.py --name code-helper

# Or hosted service
AGENT_NAME=code-helper python app.py
```

The factory detects the updated `TOOLS` list and passes all tools to the agent at assembly time.

## Function Requirements

Tool functions must follow these rules for the Agent Framework to generate correct schemas:

| Requirement | Why |
|-------------|-----|
| **`Annotated` type hints with `Field(description=...)`** | Framework uses these for the JSON schema |
| **Docstring** | Used as the tool description shown to the model |
| **Return a string** | The return value is sent back to the agent as text |
| **No `*args` or `**kwargs`** | Framework cannot generate schemas for variadic params |

### Good Example

```python
from typing import Annotated
from pydantic import Field


def search_docs(
    query: Annotated[str, Field(description="The search query string.")],
    max_results: Annotated[int, Field(description="Maximum number of results.")] = 5,
) -> str:
    """Search the documentation for relevant articles."""
    results = do_search(query, max_results)
    return "\n".join(f"- {r.title}: {r.snippet}" for r in results)
```

### Using the `@tool` Decorator

For explicit control over the tool name or description, use the `@tool` decorator:

```python
from agents._base.tools import tool
from typing import Annotated
from pydantic import Field


@tool
def search_docs(
    query: Annotated[str, Field(description="The search query string.")],
) -> str:
    """Search the documentation for relevant articles."""
    return do_search(query)
```

Both approaches (plain function and `@tool` decorator) produce the same result — the decorator is optional.

### What to Avoid

```python
# BAD: No Annotated types — agent sees no parameter descriptions
def search_docs(query: str, max_results: int = 5) -> str:
    ...

# BAD: Returns dict — agent receives repr() which is messy
def search_docs(query: str) -> dict:
    return {"results": [...]}

# BAD: No docstring — agent sees no tool description
def search_docs(
    query: Annotated[str, Field(description="The search query.")],
) -> str:
    return do_search(query)
```

## Registering Multiple Functions

Each function becomes its own tool. Register them in the `TOOLS` list:

```python
# agents/code_helper/tools/math_tools.py
from typing import Annotated
from pydantic import Field


def add(
    a: Annotated[int, Field(description="First number.")],
    b: Annotated[int, Field(description="Second number.")],
) -> str:
    """Add two numbers."""
    return str(a + b)


def multiply(
    a: Annotated[int, Field(description="First number.")],
    b: Annotated[int, Field(description="Second number.")],
) -> str:
    """Multiply two numbers."""
    return str(a * b)


# Both functions registered as separate tools
TOOLS = [add, multiply]
```

Or combine tools from different files:

```python
TOOLS = [add, subtract, search_docs]
```

## Handling Errors

If your tool function raises an exception, the framework sends the error message back to the agent, which may retry or respond with an error explanation. For predictable behaviour, catch exceptions and return error strings:

```python
from typing import Annotated
from pydantic import Field


def fetch_weather(
    city: Annotated[str, Field(description="City name (e.g., 'Seattle').")],
) -> str:
    """Get current weather for a city."""
    try:
        data = weather_api.get(city)
        return f"Weather in {city}: {data['temp']}°F, {data['condition']}"
    except Exception as e:
        return f"Could not fetch weather for {city}: {e}"
```

## Optional Parameters

Use default values for optional parameters. The framework marks parameters without defaults as `required` in the schema:

```python
def search(
    query: Annotated[str, Field(description="Search query (required).")],
    language: Annotated[str, Field(description="Language code to filter by.")] = "en",
    max_results: Annotated[int, Field(description="Maximum results to return.")] = 10,
) -> str:
    """Search with optional filters."""
    ...
```

The agent sees `query` as required and `language`/`max_results` as optional.

## Testing Your Tools

### Unit Tests

Write unit tests alongside your tools. The existing pattern in the repo:

```python
# tests/code_helper/test_calculator.py
import pytest
from agents.code_helper.tools.calculator import add_numbers

pytestmark = pytest.mark.code_helper


class TestAddNumbers:
    def test_adds_positive_numbers(self):
        assert add_numbers(2, 3) == "5"

    def test_adds_negative_numbers(self):
        assert add_numbers(-1, -2) == "-3"

    def test_returns_string(self):
        assert isinstance(add_numbers(1, 1), str)
```

Run with:

```bash
pytest tests/code_helper/test_calculator.py -v
```

### Interactive Testing

Test the tool end-to-end by running the agent locally:

```bash
python scripts/run_agent.py --name code-helper --prompt "What is 42 + 58?"
```

Or via the hosted service:

```bash
AGENT_NAME=code-helper python app.py

# In another terminal:
curl -X POST http://localhost:8088/responses \
  -H "Content-Type: application/json" \
  -d '{"input": "What is 42 + 58?"}'
```

## Complete Walkthrough: Adding a File Reader Tool

Here's a full example — adding a tool that reads a file and returns its contents:

**1. Create the tool file:**

```python
# agents/code_helper/tools/file_reader.py
from pathlib import Path
from typing import Annotated

from pydantic import Field

ALLOWED_EXTENSIONS = {".py", ".md", ".txt", ".json", ".yaml", ".yml"}


def read_file(
    filepath: Annotated[str, Field(description="Relative path to the file to read.")],
) -> str:
    """Read the contents of a file."""
    path = Path(filepath)

    if not path.exists():
        return f"File not found: {filepath}"

    if path.suffix not in ALLOWED_EXTENSIONS:
        return f"File type not supported: {path.suffix}"

    try:
        content = path.read_text(encoding="utf-8")
        if len(content) > 4000:
            content = content[:4000] + "\n... (truncated)"
        return content
    except Exception as e:
        return f"Error reading file: {e}"


TOOLS = [read_file]
```

**2. Update `__init__.py`:**

```python
# agents/code_helper/tools/__init__.py
"""Code-helper agent tools."""

from agents.code_helper.tools.sample_tool import TOOLS as GREETING_TOOLS
from agents.code_helper.tools.file_reader import TOOLS as FILE_TOOLS

TOOLS = GREETING_TOOLS + FILE_TOOLS

__all__ = ["TOOLS"]
```

**3. Add tests:**

```python
# tests/code_helper/test_file_reader.py
import pytest
from agents.code_helper.tools.file_reader import read_file

pytestmark = pytest.mark.code_helper


class TestReadFile:
    def test_reads_existing_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        assert read_file(str(f)) == "hello world"

    def test_returns_error_for_missing_file(self):
        result = read_file("nonexistent.txt")
        assert "not found" in result.lower()

    def test_rejects_unsupported_extension(self, tmp_path):
        f = tmp_path / "binary.exe"
        f.write_bytes(b"\x00")
        result = read_file(str(f))
        assert "not supported" in result.lower()

    def test_truncates_large_files(self, tmp_path):
        f = tmp_path / "large.txt"
        f.write_text("x" * 5000)
        result = read_file(str(f))
        assert "truncated" in result
```

**4. Run tests and restart:**

```bash
pytest tests/code_helper/test_file_reader.py -v
python scripts/run_agent.py --name code-helper
```

## File Structure Reference

```
agents/code_helper/
├── tools/
│   ├── __init__.py          # Aggregates TOOLS from all tool files
│   ├── sample_tool.py       # greet_user (ships with scaffold)
│   ├── calculator.py        # Your new tool
│   └── file_reader.py       # Another new tool
```

The factory in `agents/_base/agent_factory.py` imports `agents.{agent_name}.tools` and collects the `TOOLS` list automatically — no other wiring needed.

## Key Differences from Azure AI Agent Service SDK

If you're migrating from the Foundry Agent Service SDK (`azure-ai-projects`), note these changes:

| Old (Agent Service SDK) | New (Agent Framework) |
|---|---|
| `create_function_tool(func)` wrapper | Plain function — auto-wrapped |
| Docstring `Args:` section for descriptions | `Annotated[type, Field(description=...)]` |
| `deploy_agent.py` pushes tools to Foundry | Tools run in-process — just restart |
| `FunctionTool` objects in TOOLS list | Plain function references in TOOLS list |

## MCP Servers

[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-8A2BE2)](https://modelcontextprotocol.io/)

In addition to Python function tools, agents can connect to external tools and services via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). MCP servers are discovered, connected, and exposed as tools automatically.

### How MCP Works

When an agent starts (via `app.py` or `agent_session()`):

1. The factory resolves MCP server configs (per-agent override → shared fallback)
2. Each MCP server is connected as an async context manager
3. The MCP tools are merged with the agent's Python function tools
4. On shutdown, all MCP connections are cleanly closed

### Configuration

MCP servers are configured via environment variables as JSON arrays:

| Scope | Env Var | Description |
|-------|---------|-------------|
| **Shared** | `MCP_SERVERS` | All agents connect to these MCP servers |
| **Per-agent** | `{AGENT}_MCP_SERVERS` | Override for a specific agent (e.g., `CODE_HELPER_MCP_SERVERS`) |

When a per-agent var is set, the agent uses **only** those servers — the shared `MCP_SERVERS` is ignored for that agent.

### Supported Transports

| Transport | Config Fields | Example |
|-----------|---------------|---------|
| `stdio` | `command`, `args`, `env` | Local CLI tools (npx, python) |
| `http` | `url` | Remote HTTP endpoints |
| `websocket` | `url` | WebSocket endpoints |

### Examples

**GitHub MCP server (stdio):**

```bash
MCP_SERVERS='[{"name":"github","transport":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-github"],"env":{"GITHUB_PERSONAL_ACCESS_TOKEN":"ghp_..."}}]'
```

**Azure MCP server (stdio):**

```bash
MCP_SERVERS='[{"name":"azure","transport":"stdio","command":"npx","args":["-y","@azure/mcp@latest","server","start"]}]'
```

**Remote HTTP MCP server:**

```bash
MCP_SERVERS='[{"name":"web-api","transport":"http","url":"https://api.example.com/mcp"}]'
```

**Multiple servers (JSON array):**

```bash
MCP_SERVERS='[{"name":"azure","transport":"stdio","command":"npx","args":["-y","@azure/mcp@latest","server","start"]},{"name":"github","transport":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-github"]}]'
```

### Per-Agent MCP Configuration

Give different agents different MCP tools:

```bash
# code-helper gets GitHub + filesystem MCP
CODE_HELPER_MCP_SERVERS='[{"name":"github","transport":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-github"]},{"name":"filesystem","transport":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","/workspace"]}]'

# doc-assistant gets a custom docs API
DOC_ASSISTANT_MCP_SERVERS='[{"name":"docs-api","transport":"http","url":"https://docs-api.example.com/mcp"}]'
```

The agent prefix is derived from the agent name: `code-helper` → `CODE_HELPER`, `doc-assistant` → `DOC_ASSISTANT`, `my-new-agent` → `MY_NEW_AGENT`.

### MCP Server Config Schema

Each server object in the JSON array supports these fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Server identifier |
| `transport` | string | no | `stdio` (default), `http`, or `websocket` |
| `command` | string | stdio only | Executable to run |
| `args` | string[] | no | Command arguments |
| `env` | object | no | Environment variables for the process |
| `url` | string | http/ws only | Server URL |
| `description` | string | no | Human-readable description |

### Deployment

For **local dev**, set MCP vars in `.env`. For **Container Apps**, set them as GitHub Actions vars (for the deploy workflow) or in the Bicep parameter files. See the [Deployment Guide](deployment-guide.md) for details.

> **Note:** Stdio-transport MCP servers require the executable (e.g., `npx`) to be available in the container image. The default `Dockerfile` includes Node.js for this purpose. HTTP/WebSocket MCP servers work without additional container dependencies.
