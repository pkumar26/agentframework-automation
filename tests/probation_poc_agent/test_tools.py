"""Unit tests for probation-poc-agent agent tools."""

import pytest

from agents.probation_poc_agent.tools.sample_tool import greet_user

pytestmark = pytest.mark.probation_poc_agent


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
        """Should identify itself as Probation Poc Agent."""
        result = greet_user("Test")
        assert "Probation Poc Agent" in result
