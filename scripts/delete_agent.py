"""Remove a scaffolded agent from the codebase.

Deletes the agent directory, test directory, and registry entry locally.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "agents" / "registry.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
AGENTS_DIR = REPO_ROOT / "agents"
TESTS_DIR = REPO_ROOT / "tests"

PREFIX = "[delete]"


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
def _info(msg: str) -> None:
    """Print an informational message."""
    print(f"{PREFIX} {msg}")


def _error(msg: str) -> None:
    """Print an error message to stderr."""
    print(f"{PREFIX} \u2717 {msg}", file=sys.stderr)


def _success(msg: str) -> None:
    """Print a success message."""
    print(f"{PREFIX} \u2713 {msg}")


# ---------------------------------------------------------------------------
# Name helpers
# ---------------------------------------------------------------------------
def to_module_name(name: str) -> str:
    """Convert kebab-case name to snake_case module name."""
    return name.replace("-", "_")


def to_config_class_name(name: str) -> str:
    """Convert kebab-case name to PascalCase config class name."""
    parts = name.split("-")
    return "".join(part.capitalize() for part in parts) + "Config"


# ---------------------------------------------------------------------------
# Existence checks
# ---------------------------------------------------------------------------
def check_agent_exists(
    name: str,
    module_name: str,
    agents_dir: Path | None = None,
    tests_dir: Path | None = None,
    registry_path: Path | None = None,
) -> tuple[bool, bool, bool]:
    """Check what artifacts exist for the given agent.

    Returns a tuple of (agent_dir_exists, test_dir_exists, registry_entry_exists).
    """
    _agents_dir = agents_dir or AGENTS_DIR
    _tests_dir = tests_dir or TESTS_DIR
    _registry_path = registry_path or REGISTRY_PATH

    agent_dir = _agents_dir / module_name
    test_dir = _tests_dir / module_name

    registry_exists = False
    if _registry_path.exists():
        content = _registry_path.read_text(encoding="utf-8")
        if f'name="{name}"' in content:
            registry_exists = True

    return agent_dir.exists(), test_dir.exists(), registry_exists


# ---------------------------------------------------------------------------
# Registry cleanup
# ---------------------------------------------------------------------------
def remove_registry_entry(
    name: str,
    module_name: str,
    config_class_name: str,
    registry_path: Path | None = None,
) -> bool:
    """Remove the agent's import and AgentRegistryEntry from registry.py.

    Returns True if the registry was modified, False otherwise.
    """
    path = registry_path or REGISTRY_PATH
    if not path.exists():
        return False

    content = path.read_text(encoding="utf-8")
    original = content

    # Remove the import line
    import_pattern = re.compile(
        rf"^from agents\.{re.escape(module_name)}\.config "
        rf"import {re.escape(config_class_name)}.*\n",
        re.MULTILINE,
    )
    content = import_pattern.sub("", content)

    # Remove the AgentRegistryEntry block
    entry_pattern = re.compile(
        rf"[ ]*AgentRegistryEntry\(\s*\n"
        rf"[ ]*name=\"{re.escape(name)}\",\s*\n"
        rf"[ ]*config_class={re.escape(config_class_name)},\s*\n"
        rf"[ ]*factory=create_agent,\s*\n"
        rf"[ ]*\),?\s*\n",
        re.MULTILINE,
    )
    content = entry_pattern.sub("", content)

    if content != original:
        path.write_text(content, encoding="utf-8")
        return True

    return False


# ---------------------------------------------------------------------------
# Directory removal
# ---------------------------------------------------------------------------
def remove_directory(dir_path: Path) -> bool:
    """Remove a directory and all its contents.

    Returns True if the directory was removed, False if it didn't exist.
    """
    if dir_path.exists():
        shutil.rmtree(dir_path)
        return True
    return False


def remove_pyproject_marker(
    module_name: str,
    pyproject_path: Path | None = None,
) -> bool:
    """Remove the pytest marker for this agent from pyproject.toml.

    Returns True if the marker was removed, False otherwise.
    """
    path = pyproject_path or PYPROJECT_PATH
    if not path.exists():
        return False

    content = path.read_text(encoding="utf-8")
    marker_pattern = re.compile(
        rf'^\s*"{re.escape(module_name)}:.*",?\n',
        re.MULTILINE,
    )
    new_content = marker_pattern.sub("", content)
    if new_content != content:
        path.write_text(new_content, encoding="utf-8")
        return True
    return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _get_all_agent_names() -> list[str]:
    """Return all agent names found in registry.py."""
    if not REGISTRY_PATH.exists():
        return []
    content = REGISTRY_PATH.read_text(encoding="utf-8")
    return re.findall(r'name="([^"]+)"', content)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Remove a scaffolded agent from the codebase.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--name",
        type=str,
        help="Agent name in kebab-case (e.g., my-agent)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        dest="delete_all",
        help="Delete all scaffolded agents (except built-in ones)",
    )
    return parser


def delete_agent(
    name: str,
    agents_dir: Path | None = None,
    tests_dir: Path | None = None,
    registry_path: Path | None = None,
    pyproject_path: Path | None = None,
) -> int:
    """Delete a single agent by name. Returns 0 on success, 1 on failure."""
    _agents_dir = agents_dir or AGENTS_DIR
    _tests_dir = tests_dir or TESTS_DIR

    module_name = to_module_name(name)
    config_class_name = to_config_class_name(name)

    agent_exists, test_exists, registry_exists = check_agent_exists(
        name, module_name, _agents_dir, _tests_dir, registry_path
    )

    if not any([agent_exists, test_exists, registry_exists]):
        _error(f"No artifacts found for agent '{name}'")
        return 1

    _info(f"Deleting agent '{name}'...")

    # Remove directories
    agent_dir = _agents_dir / module_name
    if remove_directory(agent_dir):
        _success(f"Removed {agent_dir.relative_to(REPO_ROOT)}")

    test_dir = _tests_dir / module_name
    if remove_directory(test_dir):
        _success(f"Removed {test_dir.relative_to(REPO_ROOT)}")

    # Remove registry entry
    if remove_registry_entry(name, module_name, config_class_name, registry_path):
        _success("Removed registry entry")

    # Remove pyproject marker
    if remove_pyproject_marker(module_name, pyproject_path):
        _success("Removed pyproject.toml marker")

    _success(f"Agent '{name}' deleted successfully")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.delete_all:
        names = _get_all_agent_names()
        if not names:
            _error("No agents found in registry")
            return 1
        results = []
        for name in names:
            results.append(delete_agent(name))
        return 0 if all(r == 0 for r in results) else 1

    return delete_agent(args.name)


if __name__ == "__main__":
    sys.exit(main())
