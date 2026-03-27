"""Unit tests for the create_agent scaffolding script."""

import pytest

from scripts.create_agent import (
    _parse_yaml_config,
    check_existence,
    to_class_prefix,
    to_config_class_name,
    to_display_name,
    to_module_name,
    validate_name,
)


class TestValidateName:
    """Tests for agent name validation."""

    def test_valid_simple_name(self):
        assert validate_name("my-agent") is None

    def test_valid_single_word(self):
        assert validate_name("agent") is None

    def test_valid_multi_segment(self):
        assert validate_name("my-cool-agent") is None

    def test_rejects_empty_name(self):
        assert validate_name("") is not None

    def test_rejects_uppercase(self):
        assert validate_name("MyAgent") is not None

    def test_rejects_underscore(self):
        assert validate_name("my_agent") is not None

    def test_rejects_leading_digit(self):
        assert validate_name("1agent") is not None

    def test_rejects_too_long(self):
        assert validate_name("a" * 51) is not None

    def test_rejects_python_keyword(self):
        assert validate_name("class") is not None


class TestNameConversions:
    """Tests for name derivation helpers."""

    def test_to_module_name(self):
        assert to_module_name("my-agent") == "my_agent"

    def test_to_class_prefix(self):
        assert to_class_prefix("my-agent") == "MyAgent"

    def test_to_config_class_name(self):
        assert to_config_class_name("my-agent") == "MyAgentConfig"

    def test_to_display_name(self):
        assert to_display_name("my-agent") == "My Agent"


class TestCheckExistence:
    """Tests for existence checking."""

    def test_no_conflict(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        registry = tmp_path / "registry.py"
        registry.write_text('name="other-agent"')

        result = check_existence(
            "new-agent", "new_agent", agents_dir, tests_dir, registry
        )
        assert result is None

    def test_agent_dir_exists(self, tmp_path):
        agents_dir = tmp_path / "agents"
        (agents_dir / "my_agent").mkdir(parents=True)
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        registry = tmp_path / "registry.py"
        registry.write_text("")

        result = check_existence(
            "my-agent", "my_agent", agents_dir, tests_dir, registry
        )
        assert result is not None
        assert "already exists" in result

    def test_registry_entry_exists(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        registry = tmp_path / "registry.py"
        registry.write_text('name="my-agent"')

        result = check_existence(
            "my-agent", "my_agent", agents_dir, tests_dir, registry
        )
        assert result is not None
        assert "already registered" in result


class TestParseYamlConfig:
    """Tests for YAML config file parsing."""

    def test_parses_name_and_model(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("name: my-agent\nmodel: gpt-4o-mini\n")
        result = _parse_yaml_config(str(cfg))
        assert result == {"name": "my-agent", "model": "gpt-4o-mini"}

    def test_ignores_comments_and_blanks(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("# comment\n\nname: my-agent\n")
        result = _parse_yaml_config(str(cfg))
        assert result == {"name": "my-agent"}

    def test_strips_quotes(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text('name: "my-agent"\nmodel: \'gpt-4o\'\n')
        result = _parse_yaml_config(str(cfg))
        assert result["name"] == "my-agent"
        assert result["model"] == "gpt-4o"

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            _parse_yaml_config("/nonexistent/config.yaml")
