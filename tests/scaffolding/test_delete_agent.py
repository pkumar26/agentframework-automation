"""Unit tests for the delete_agent script."""

import pytest

from scripts.delete_agent import (
    check_agent_exists,
    remove_directory,
    remove_registry_entry,
    to_config_class_name,
    to_module_name,
)


class TestNameHelpers:
    """Tests for name conversion helpers."""

    def test_to_module_name(self):
        assert to_module_name("my-agent") == "my_agent"

    def test_to_config_class_name(self):
        assert to_config_class_name("my-agent") == "MyAgentConfig"


class TestCheckAgentExists:
    """Tests for existence checking."""

    def test_nothing_exists(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        registry = tmp_path / "registry.py"
        registry.write_text("")

        result = check_agent_exists(
            "my-agent", "my_agent", agents_dir, tests_dir, registry
        )
        assert result == (False, False, False)

    def test_all_exist(self, tmp_path):
        agents_dir = tmp_path / "agents"
        (agents_dir / "my_agent").mkdir(parents=True)
        tests_dir = tmp_path / "tests"
        (tests_dir / "my_agent").mkdir(parents=True)
        registry = tmp_path / "registry.py"
        registry.write_text('name="my-agent"')

        result = check_agent_exists(
            "my-agent", "my_agent", agents_dir, tests_dir, registry
        )
        assert result == (True, True, True)


class TestRemoveDirectory:
    """Tests for directory removal."""

    def test_removes_existing_directory(self, tmp_path):
        target = tmp_path / "to_remove"
        target.mkdir()
        (target / "file.txt").write_text("content")

        assert remove_directory(target) is True
        assert not target.exists()

    def test_returns_false_for_nonexistent(self, tmp_path):
        target = tmp_path / "nonexistent"
        assert remove_directory(target) is False


class TestRemoveRegistryEntry:
    """Tests for registry cleanup."""

    def test_removes_entry(self, tmp_path):
        registry = tmp_path / "registry.py"
        registry.write_text(
            'from agents.my_agent.config import MyAgentConfig  # noqa: E402\n'
            "\n"
            "REGISTRY = AgentRegistry(\n"
            "    [\n"
            "        AgentRegistryEntry(\n"
            '            name="my-agent",\n'
            "            config_class=MyAgentConfig,\n"
            "            factory=create_agent,\n"
            "        ),\n"
            "    ]\n"
            ")\n"
        )

        result = remove_registry_entry(
            "my-agent", "my_agent", "MyAgentConfig", registry
        )
        assert result is True

        content = registry.read_text()
        assert "my-agent" not in content
        assert "MyAgentConfig" not in content

    def test_no_change_when_not_found(self, tmp_path):
        registry = tmp_path / "registry.py"
        registry.write_text("REGISTRY = AgentRegistry([])\n")

        result = remove_registry_entry(
            "nonexistent", "nonexistent", "NonexistentConfig", registry
        )
        assert result is False
