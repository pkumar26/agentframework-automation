"""Unit tests for run_agent lifecycle."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents._base.run import run_agent


class TestRunAgent:
    """Tests for the run_agent function."""

    @patch("agents._base.run.create_agent")
    def test_returns_response_text(self, mock_create):
        """Should return the agent's response text on success."""
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.text = "Hello from agent"
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_create.return_value = mock_agent

        config = MagicMock()
        config.agent_name = "test-agent"

        result = run_agent(config, "Hello")

        assert result == "Hello from agent"
        mock_agent.run.assert_called_once_with("Hello")

    @patch("agents._base.run.create_agent")
    def test_handles_string_result(self, mock_create):
        """Should handle when result is a plain string."""
        mock_agent = MagicMock()
        mock_result = "Plain string result"
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_create.return_value = mock_agent

        config = MagicMock()
        config.agent_name = "test-agent"

        result = run_agent(config, "Hello")

        assert result == "Plain string result"

    @patch("agents._base.run.create_agent")
    def test_propagates_exceptions(self, mock_create):
        """Should propagate exceptions from agent.run()."""
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("API error"))
        mock_create.return_value = mock_agent

        config = MagicMock()
        config.agent_name = "test-agent"

        with pytest.raises(RuntimeError, match="API error"):
            run_agent(config, "Hello")
