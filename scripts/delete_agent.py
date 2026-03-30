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

BUILTIN_AGENTS = {"code-helper", "doc-assistant"}

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
        help="Delete all registered agents (except built-in ones)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip the confirmation prompt",
    )
    return parser


def delete_agent(
    name: str,
    agents_dir: Path | None = None,
    tests_dir: Path | None = None,
    registry_path: Path | None = None,
    pyproject_path: Path | None = None,
) -> int:
    """Delete agent artifacts (directories, registry, pyproject marker).

    This is the low-level deletion helper called after confirmation.
    Returns 0 on success, 1 on failure.
    """
    _agents_dir = agents_dir or AGENTS_DIR
    _tests_dir = tests_dir or TESTS_DIR

    module_name = to_module_name(name)
    config_class_name = to_config_class_name(name)

    removed_count = 0

    # Remove directories
    agent_dir = _agents_dir / module_name
    if remove_directory(agent_dir):
        try:
            rel = agent_dir.relative_to(REPO_ROOT)
        except ValueError:
            rel = agent_dir
        _success(f"Removed {rel}")
        removed_count += 1

    test_dir = _tests_dir / module_name
    if remove_directory(test_dir):
        try:
            rel = test_dir.relative_to(REPO_ROOT)
        except ValueError:
            rel = test_dir
        _success(f"Removed {rel}")
        removed_count += 1

    # Remove registry entry
    if remove_registry_entry(name, module_name, config_class_name, registry_path):
        _success("Updated agents/registry.py")
        removed_count += 1

    # Remove pyproject marker
    if remove_pyproject_marker(module_name, pyproject_path):
        _success("Removed pytest marker from pyproject.toml")

    _success(f"Agent '{name}' deleted ({removed_count} operations)")
    return 0


def _delete_single(
    name: str,
    force: bool,
    agents_dir: Path | None = None,
    tests_dir: Path | None = None,
    registry_path: Path | None = None,
    pyproject_path: Path | None = None,
) -> int:
    """Delete a single agent by name.

    Returns 0 on success, 1 on error or cancellation.
    """
    _agents_dir = agents_dir or AGENTS_DIR
    _tests_dir = tests_dir or TESTS_DIR

    module_name = to_module_name(name)

    agent_exists, test_exists, registry_exists = check_agent_exists(
        name, module_name, _agents_dir, _tests_dir, registry_path
    )

    if not any([agent_exists, test_exists, registry_exists]):
        _error(f"Agent '{name}' not found in the codebase.")
        return 1

    # Show what will be deleted
    _info(f"The following will be removed for agent '{name}':")
    if agent_exists:
        _info(f"  agents/{module_name}/")
    if test_exists:
        _info(f"  tests/{module_name}/")
    if registry_exists:
        _info("  Registry entry in agents/registry.py")

    # Confirm unless --force
    if not force:
        try:
            answer = input(f"{PREFIX} Continue? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            _info("Cancelled.")
            return 1
        if answer not in ("y", "yes"):
            _info("Cancelled.")
            return 1

    return delete_agent(
        name,
        agents_dir=_agents_dir,
        tests_dir=_tests_dir,
        registry_path=registry_path,
        pyproject_path=pyproject_path,
    )


def _delete_all(
    force: bool,
    registry_path: Path | None = None,
) -> int:
    """Delete all registered agents (except built-in ones).

    Returns 0 if all succeed, 1 if any fail or none found.
    """
    _registry_path = registry_path or REGISTRY_PATH

    names = _get_all_agent_names()
    names = [n for n in names if n not in BUILTIN_AGENTS]
    if not names:
        _error("No scaffolded agents found in registry (built-in agents are excluded)")
        return 1

    _info(f"Will delete {len(names)} agent(s): {', '.join(names)}")
    if not force:
        try:
            answer = input(f"{PREFIX} Continue? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            _info("Cancelled.")
            return 1
        if answer not in ("y", "yes"):
            _info("Cancelled.")
            return 1

    results: list[tuple[str, bool]] = []
    for name in names:
        exit_code = delete_agent(name, registry_path=registry_path)
        results.append((name, exit_code == 0))

    # Summary
    success_count = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n{PREFIX} Summary: {success_count}/{total} agents deleted successfully")
    for name, ok in results:
        if ok:
            print(f"{PREFIX}   \u2713 {name}")
        else:
            print(f"{PREFIX}   \u2717 {name}")

    return 0 if success_count == total else 1


def main(argv: list[str] | None = None) -> int:
    """Entry point for the deletion script.

    Returns 0 on success, 1 on error (agent not found or user cancelled).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.delete_all:
        return _delete_all(force=args.force)

    return _delete_single(args.name, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
