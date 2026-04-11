"""Scaffold a new agent for the Agent Framework Platform.

Generates agent directory, test stubs, and registry entry from a name.
Uses only Python standard library — no external dependencies.
"""

from __future__ import annotations

import argparse
import keyword
import re
import sys
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "agents" / "registry.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
AGENTS_DIR = REPO_ROOT / "agents"
TESTS_DIR = REPO_ROOT / "tests"

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
MAX_NAME_LENGTH = 50

PREFIX = "[scaffold]"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def validate_name(name: str) -> str | None:
    """Validate an agent name.

    Returns None on success, or an error message string on failure.
    """
    if not name:
        return "Agent name is required."
    if len(name) > MAX_NAME_LENGTH:
        return "Agent name exceeds maximum length of 50 characters."
    if not NAME_PATTERN.match(name):
        return f"Invalid agent name '{name}'. Must be lowercase kebab-case (e.g., my-agent)."
    module = name.replace("-", "_")
    if keyword.iskeyword(module):
        return f"Agent name '{name}' is a Python reserved word."
    return None


# ---------------------------------------------------------------------------
# Name derivation helpers
# ---------------------------------------------------------------------------
def _parse_yaml_config(filepath: str) -> dict[str, str]:
    """Parse a simple key-value YAML config file (name, model).

    Supports only top-level scalar key: value pairs and comments.
    Uses no external dependencies.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")

    config: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        config[key.strip()] = value.strip().strip('"').strip("'")
    return config


def to_module_name(name: str) -> str:
    """Convert kebab-case name to snake_case module name."""
    return name.replace("-", "_")


def to_class_prefix(name: str) -> str:
    """Convert kebab-case name to PascalCase class prefix."""
    return "".join(part.capitalize() for part in name.split("-"))


def to_config_class_name(name: str) -> str:
    """Convert kebab-case name to PascalCase config class name."""
    return to_class_prefix(name) + "Config"


def to_display_name(name: str) -> str:
    """Convert kebab-case name to human-readable display name."""
    return name.replace("-", " ").title()


# ---------------------------------------------------------------------------
# Existence checks
# ---------------------------------------------------------------------------
def check_existence(
    name: str,
    module_name: str,
    agents_dir: Path | None = None,
    tests_dir: Path | None = None,
    registry_path: Path | None = None,
) -> str | None:
    """Check that the agent does not already exist.

    Returns None on success, or an error message string on failure.
    """
    _agents_dir = agents_dir or AGENTS_DIR
    _tests_dir = tests_dir or TESTS_DIR
    _registry_path = registry_path or REGISTRY_PATH

    agent_dir = _agents_dir / module_name
    if agent_dir.exists():
        try:
            rel = agent_dir.relative_to(REPO_ROOT)
        except ValueError:
            rel = agent_dir
        return f"Agent '{name}' already exists at {rel}"

    test_dir = _tests_dir / module_name
    if test_dir.exists():
        try:
            rel = test_dir.relative_to(REPO_ROOT)
        except ValueError:
            rel = test_dir
        return f"Test directory already exists at {rel}"

    if _registry_path.exists():
        content = _registry_path.read_text(encoding="utf-8")
        if f'name="{name}"' in content:
            try:
                rel = _registry_path.relative_to(REPO_ROOT)
            except ValueError:
                rel = _registry_path
            return f"Agent '{name}' is already registered in {rel}"

    return None


# ---------------------------------------------------------------------------
# File writing utility
# ---------------------------------------------------------------------------
def _write_file(path: Path, content: str) -> None:
    """Write *content* to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Agent file templates
# ---------------------------------------------------------------------------
def _template_config(
    class_prefix: str,
    agent_name: str,
    model: str,
    module_name: str,
) -> str:
    """Return config.py content for the scaffolded agent."""
    config_cls = f"{class_prefix}Config"
    instructions_path = f"agents/{module_name}/instructions.md"
    return textwrap.dedent(f'''\
        """Configuration for the {agent_name} agent."""

        from pydantic import Field

        from agents._base.config import AgentBaseConfig, _IDENTITY_ALIAS

        _SKIP = _IDENTITY_ALIAS


        class {config_cls}(AgentBaseConfig):
            """{class_prefix} agent configuration.

            Extends the base config with agent-specific settings and defaults.
            """

            agent_name: str = Field(default="{agent_name}", validation_alias=_SKIP)
            agent_deployment_name: str = Field(default="{model}", validation_alias=_SKIP)
            agent_instructions_path: str = Field(default="{instructions_path}", validation_alias=_SKIP)
    ''')


def _template_readme(
    name: str,
    display_name: str,
    module_name: str,
    class_prefix: str,
    model: str,
) -> str:
    """Return README.md content for the scaffolded agent."""
    config_cls = f"{class_prefix}Config"
    return textwrap.dedent(f"""\
        # {display_name} Agent

        ![Agent](https://img.shields.io/badge/agent-{name}-blue)
        ![Model](https://img.shields.io/badge/model-{model}-green)
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
        | `greet_user` | `agents/{module_name}/tools/sample_tool.py` | Sample greeting tool |

        ## Configuration

        | Setting | config.py Property | Default | Description |
        |---|---|---|---|
        | Agent name | `agent_name` | `{name}` | Registry identifier |
        | Model deployment | `agent_deployment_name` | `{model}` | Azure AI Foundry deployment |

        > **Note:** All settings are per-agent in `config.py`.
        > The `.env` file is for shared infrastructure only.

        ## File Structure

        ```
        agents/{module_name}/
        ├── __init__.py
        ├── config.py              # {config_cls} (extends AgentBaseConfig)
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
        python scripts/run_agent.py --name {name}

        # Run as hosted service
        AGENT_NAME={name} python app.py
        ```

        ## Testing

        ```bash
        # Unit tests
        pytest tests/{module_name}/ -v

        # Skip integration tests
        pytest tests/{module_name}/ -v -m "not integration"
        ```
    """)


def _template_instructions(display_name: str) -> str:
    """Return instructions.md content for the scaffolded agent."""
    return textwrap.dedent(f"""\
        # {display_name} Agent

        You are a helpful assistant called **{display_name}**.
        Your role is to assist users with their tasks.

        ## Capabilities

        - Answer questions clearly and concisely
        - Use available tools when they can help answer a question
        - Provide examples when appropriate

        ## Guidelines

        - Be concise and direct in your responses
        - If you're unsure about something, say so rather than guessing
        - Prioritise correctness and security in all suggestions
        - Follow established conventions and patterns
    """)


def _template_sample_tool(display_name: str) -> str:
    """Return sample_tool.py content for the scaffolded agent."""
    return textwrap.dedent(f'''\
        """Sample tool for the {display_name.lower()} agent — a greeting function."""

        from typing import Annotated

        from pydantic import Field


        def greet_user(
            name: Annotated[str, Field(description="The name of the user to greet.")],
        ) -> str:
            """Greet a user by name."""
            return f"Hello, {{name}}! I\'m the {display_name} agent. How can I assist you today?"


        # Exported tools list — consumed by agent_factory.
        # Agent Framework auto-wraps plain functions as function tools.
        TOOLS = [greet_user]
    ''')


def _template_tools_init(module_name: str) -> str:
    """Return tools/__init__.py content for the scaffolded agent."""
    return textwrap.dedent(f'''\
        """{module_name.replace("_", "-")} agent tools."""

        from agents.{module_name}.tools.sample_tool import TOOLS

        __all__ = ["TOOLS"]
    ''')


def _template_knowledge(module_name: str) -> str:
    """Return integrations/knowledge.py content for the scaffolded agent."""
    agent_label = module_name.replace("_", "-")
    return textwrap.dedent(f'''\
        """Knowledge source integration stub for the {agent_label} agent."""

        from agents._base.config import AgentBaseConfig


        def get_knowledge_tool(config: AgentBaseConfig):
            """Return a knowledge source tool definition, or None if disabled.

            Args:
                config: Agent configuration with knowledge_source_enabled flag.

            Returns:
                Tool definition when enabled (future implementation), None when disabled.
            """
            if not getattr(config, "knowledge_source_enabled", False):
                return None
            raise NotImplementedError(
                "Knowledge source integration is not yet implemented. "
                "Set 'knowledge_source_enabled = False' in your agent's config.py to disable."
            )
    ''')


# ---------------------------------------------------------------------------
# Test file templates
# ---------------------------------------------------------------------------
def _template_conftest(module_name: str, config_class_name: str) -> str:
    """Return conftest.py content for the scaffolded agent's tests."""
    agent_label = module_name.replace("_", "-")
    marker = module_name
    return textwrap.dedent(f'''\
        """Conftest for {agent_label} agent tests."""

        import pytest

        from agents.{module_name}.config import {config_class_name}

        pytestmark = pytest.mark.{marker}


        @pytest.fixture
        def {module_name}_config(tmp_path):
            """Create a {config_class_name} with a temp instructions file."""
            instructions_file = tmp_path / "instructions.md"
            instructions_file.write_text("You are a {agent_label} agent.")

            with pytest.MonkeyPatch.context() as m:
                m.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test.services.ai.azure.com/api/projects/test")
                config = {config_class_name}()
            config.agent_instructions_path = str(instructions_file)
            return config
    ''')


def _template_test_tools(module_name: str, display_name: str) -> str:
    """Return test_tools.py content for the scaffolded agent's tests."""
    marker = module_name
    return textwrap.dedent(f'''\
        """Unit tests for {module_name.replace("_", "-")} agent tools."""

        import pytest

        from agents.{module_name}.tools.sample_tool import greet_user

        pytestmark = pytest.mark.{marker}


        class TestGreetUser:
            """Tests for the greet_user tool function."""

            def test_greets_with_name(self):
                """Should return a greeting with the given name."""
                result = greet_user("Alice")
                assert "Alice" in result
                assert "Hello" in result

            def test_greets_with_empty_name(self):
                """Should handle empty string name."""
                result = greet_user("")
                assert "Hello" in result

            def test_returns_string(self):
                """Should always return a string."""
                result = greet_user("Bob")
                assert isinstance(result, str)

            def test_contains_agent_identifier(self):
                """Should identify itself as {display_name}."""
                result = greet_user("Test")
                assert "{display_name}" in result
    ''')


def _template_test_agent_create(module_name: str, agent_name: str, config_class_name: str) -> str:
    """Return test_agent_create.py content for the scaffolded agent's tests."""
    marker = module_name
    return textwrap.dedent(f'''\
        """Integration tests for {agent_name} agent creation."""

        import os

        import pytest

        pytestmark = [pytest.mark.integration, pytest.mark.{marker}]

        # Skip all tests in this module if no endpoint
        ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
        if not ENDPOINT:
            pytest.skip(
                "AZURE_AI_PROJECT_ENDPOINT not set — skipping integration tests",
                allow_module_level=True,
            )


        class TestAgentCreateIntegration:
            """Integration tests for agent assembly."""

            def test_creates_agent_from_config(self):
                """Should assemble an agent from config."""
                from agents._base.agent_factory import create_agent
                from agents.{module_name}.config import {config_class_name}

                config = {config_class_name}()
                agent = create_agent(config)
                assert agent is not None
    ''')


def _template_test_agent_run(module_name: str, agent_name: str, config_class_name: str) -> str:
    """Return test_agent_run.py content for the scaffolded agent's tests."""
    marker = module_name
    return textwrap.dedent(f'''\
        """Integration tests for {agent_name} agent run lifecycle."""

        import asyncio
        import os

        import pytest

        pytestmark = [pytest.mark.integration, pytest.mark.{marker}]

        # Skip all tests in this module if no endpoint
        ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
        if not ENDPOINT:
            pytest.skip(
                "AZURE_AI_PROJECT_ENDPOINT not set — skipping integration tests",
                allow_module_level=True,
            )


        class TestAgentRunIntegration:
            """Integration tests for the agent run lifecycle."""

            def test_agent_responds_to_prompt(self):
                """Should run the agent and get a response."""
                from agents._base.agent_factory import create_agent
                from agents.{module_name}.config import {config_class_name}

                config = {config_class_name}()
                agent = create_agent(config)
                result = asyncio.run(agent.run("Say 'Test OK' and nothing else."))
                assert result is not None
                assert len(str(result)) > 0
    ''')


# ---------------------------------------------------------------------------
# File generation
# ---------------------------------------------------------------------------
def _generate_agent_files(
    name: str,
    module_name: str,
    class_prefix: str,
    model: str,
    display_name: str,
    agents_dir: Path | None = None,
) -> list[Path]:
    """Generate all agent files under agents/{module_name}/."""
    base = (agents_dir or AGENTS_DIR) / module_name

    files: list[tuple[Path, str]] = [
        (base / "__init__.py", ""),
        (base / "config.py", _template_config(class_prefix, name, model, module_name)),
        (base / "instructions.md", _template_instructions(display_name)),
        (
            base / "README.md",
            _template_readme(name, display_name, module_name, class_prefix, model),
        ),
        (base / "tools" / "__init__.py", _template_tools_init(module_name)),
        (base / "tools" / "sample_tool.py", _template_sample_tool(display_name)),
        (base / "integrations" / "__init__.py", ""),
        (base / "integrations" / "knowledge.py", _template_knowledge(module_name)),
    ]

    created: list[Path] = []
    for path, content in files:
        _write_file(path, content)
        created.append(path)
    return created


def _generate_test_files(
    name: str,
    module_name: str,
    class_prefix: str,
    display_name: str,
    tests_dir: Path | None = None,
) -> list[Path]:
    """Generate all test files under tests/{module_name}/."""
    base = (tests_dir or TESTS_DIR) / module_name
    config_cls = to_config_class_name(name)

    files: list[tuple[Path, str]] = [
        (base / "__init__.py", ""),
        (base / "conftest.py", _template_conftest(module_name, config_cls)),
        (base / "test_tools.py", _template_test_tools(module_name, display_name)),
        (
            base / "test_agent_create.py",
            _template_test_agent_create(module_name, name, config_cls),
        ),
        (base / "test_agent_run.py", _template_test_agent_run(module_name, name, config_cls)),
    ]

    created: list[Path] = []
    for path, content in files:
        _write_file(path, content)
        created.append(path)
    return created


# ---------------------------------------------------------------------------
# Registry update
# ---------------------------------------------------------------------------
def _update_registry(
    name: str,
    module_name: str,
    config_class_name: str,
    registry_path: Path | None = None,
) -> None:
    """Append a new agent entry to agents/registry.py."""
    path = registry_path or REGISTRY_PATH
    content = path.read_text(encoding="utf-8")

    # Insert import after the last `from agents.*.config import *Config` line
    import_line = f"from agents.{module_name}.config import " f"{config_class_name}  # noqa: E402\n"
    last_import_pos = -1
    for match in re.finditer(r"^from agents\.\w+\.config import \w+.*$", content, re.MULTILINE):
        last_import_pos = match.end()

    if last_import_pos == -1:
        print(f"{PREFIX} ✗ Could not find config imports in {path}", file=sys.stderr)
        return

    content = content[:last_import_pos] + "\n" + import_line + content[last_import_pos:]

    # Insert new AgentRegistryEntry before the closing    ]\n)
    entry = textwrap.dedent(f"""\
        AgentRegistryEntry(
            name="{name}",
            config_class={config_class_name},
            factory=create_agent,
        ),
""")

    closing = "    ]\n)\n"
    closing_pos = content.rfind(closing)
    if closing_pos == -1:
        closing = "    ]\n)"
        closing_pos = content.rfind(closing)
    if closing_pos == -1:
        print(f"{PREFIX} ✗ Could not find REGISTRY closing in {path}", file=sys.stderr)
        return

    indented_entry = textwrap.indent(entry, "        ")
    content = content[:closing_pos] + indented_entry + content[closing_pos:]

    path.write_text(content, encoding="utf-8")


def _update_pyproject_markers(
    module_name: str,
    agent_name: str,
    pyproject_path: Path | None = None,
) -> None:
    """Register a pytest marker for the new agent in pyproject.toml."""
    path = pyproject_path or PYPROJECT_PATH
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    marker_entry = f'    "{module_name}: marks tests for the {agent_name} agent",\n'

    if f'"{module_name}:' in content:
        return

    markers_start = content.find("markers = [")
    if markers_start == -1:
        return

    markers_end = content.find("]", markers_start)
    if markers_end == -1:
        return

    content = content[:markers_end] + marker_entry + content[markers_end:]
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Scaffold a new agent for the Agent Framework Platform",
        prog="create_agent.py",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--name",
        type=str,
        help="Agent name in kebab-case (e.g., my-agent)",
    )
    group.add_argument(
        "--from-file",
        type=str,
        dest="from_file",
        help="Path to a YAML config file with 'name' and optional 'model' keys",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o",
        help="Model deployment name (default: gpt-4o)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Scaffold a new agent."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.from_file:
        file_config = _parse_yaml_config(args.from_file)
        name = file_config.get("name", "")
        model = file_config.get("model", args.model)
    else:
        name = args.name
        model = args.model

    # Validate name
    error = validate_name(name)
    if error:
        print(f"{PREFIX} ✗ {error}", file=sys.stderr)
        return 1

    module_name = to_module_name(name)
    class_prefix = to_class_prefix(name)
    config_class_name = to_config_class_name(name)
    display_name = to_display_name(name)

    # Check existence
    error = check_existence(name, module_name)
    if error:
        print(f"{PREFIX} ✗ {error}", file=sys.stderr)
        return 1

    print(f"{PREFIX} Creating agent '{name}'...")

    # Generate agent files
    agent_files = _generate_agent_files(name, module_name, class_prefix, model, display_name)
    for f in agent_files:
        try:
            rel = f.relative_to(REPO_ROOT)
        except ValueError:
            rel = f
        print(f"{PREFIX}   ✓ {rel}")

    # Generate test files
    test_files = _generate_test_files(name, module_name, class_prefix, display_name)
    for f in test_files:
        try:
            rel = f.relative_to(REPO_ROOT)
        except ValueError:
            rel = f
        print(f"{PREFIX}   ✓ {rel}")

    # Update registry
    _update_registry(name, module_name, config_class_name)
    print(f"{PREFIX}   ✓ agents/registry.py (entry added)")

    # Update pyproject markers
    _update_pyproject_markers(module_name, name)
    print(f"{PREFIX}   ✓ pyproject.toml (marker added)")

    print(f"\n{PREFIX} ✓ Agent '{name}' scaffolded successfully!")
    print(f"\n{PREFIX} Next steps:")
    print(f"{PREFIX}   1. Edit agents/{module_name}/instructions.md")
    print(f"{PREFIX}   2. Add tools in agents/{module_name}/tools/")
    print(f"{PREFIX}   3. Run: python scripts/run_agent.py --name {name}")
    print(f"{PREFIX}   4. Test: pytest tests/{module_name}/ -v")

    return 0


if __name__ == "__main__":
    sys.exit(main())
