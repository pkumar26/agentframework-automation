"""Unit tests for code-helper agent tools."""

import pytest

from agents.code_helper.tools.sample_tool import greet_user

pytestmark = pytest.mark.code_helper


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
        """Should identify itself as Code Helper."""
        result = greet_user("Test")
        assert "Code Helper" in result
