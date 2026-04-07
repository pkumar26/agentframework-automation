"""Unit tests for create_agent factory."""

from unittest.mock import MagicMock, patch

import pytest

from agents._base.agent_factory import create_agent


@pytest.fixture
def agent_config(tmp_path):
    """Create a mock config with a real instructions file."""
    instructions_file = tmp_path / "instructions.md"
    instructions_file.write_text("You are a helpful agent.")

    config = MagicMock()
    config.azure_ai_project_endpoint = "https://test.services.ai.azure.com/api/projects/test"
    config.agent_name = "test-agent"
    config.agent_deployment_name = "gpt-4o"
    config.agent_instructions_path = str(instructions_file)
    config.azure_ai_search_endpoint = None
    config.azure_ai_search_index_name = None
    config.azure_ai_search_semantic_config = None
    config.azure_ai_search_knowledge_base = None
    config.azure_authority_host = None
    config.mcp_servers = None
    return config


class TestCreateAgent:
    """Tests for the agent factory function."""

    @patch("agents._base.agent_factory._collect_agent_tools", return_value=[])
    @patch("agents._base.agent_factory.get_chat_client")
    def test_creates_agent_via_as_agent(self, mock_get_client, mock_tools, agent_config):
        """Should create an agent via the client's as_agent method."""
        mock_client = MagicMock()
        mock_agent = MagicMock()
        mock_client.as_agent.return_value = mock_agent
        mock_get_client.return_value = mock_client

        result = create_agent(agent_config)

        mock_client.as_agent.assert_called_once()
        call_kwargs = mock_client.as_agent.call_args
        assert call_kwargs.kwargs["name"] == "test-agent"
        assert call_kwargs.kwargs["instructions"] == "You are a helpful agent."
        assert result is mock_agent

    @patch("agents._base.agent_factory._collect_agent_tools", return_value=[])
    @patch("agents._base.agent_factory.get_chat_client")
    def test_passes_correct_deployment(self, mock_get_client, mock_tools, agent_config):
        """Should create chat client with correct endpoint and deployment."""
        mock_client = MagicMock()
        mock_client.as_agent.return_value = MagicMock()
        mock_get_client.return_value = mock_client

        create_agent(agent_config)

        mock_get_client.assert_called_once_with(
            endpoint="https://test.services.ai.azure.com/api/projects/test",
            deployment_name="gpt-4o",
            authority=None,
        )

    def test_missing_instructions_raises_file_not_found(self, agent_config):
        """Should raise FileNotFoundError when instructions file doesn't exist."""
        agent_config.agent_instructions_path = "/nonexistent/path/instructions.md"

        with pytest.raises(FileNotFoundError, match="Instructions file not found"):
            create_agent(agent_config)

    def test_empty_instructions_raises_value_error(self, agent_config, tmp_path):
        """Should raise ValueError when instructions file is empty."""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("   ")
        agent_config.agent_instructions_path = str(empty_file)

        with pytest.raises(ValueError, match="Instructions file is empty"):
            create_agent(agent_config)

    @patch("agents._base.agent_factory._collect_agent_tools", return_value=[])
    @patch("agents._base.agent_factory.get_chat_client")
    def test_passes_none_tools_when_empty(self, mock_get_client, mock_tools, agent_config):
        """Should pass tools=None when no tools are found."""
        mock_client = MagicMock()
        mock_client.as_agent.return_value = MagicMock()
        mock_get_client.return_value = mock_client

        create_agent(agent_config)

        call_kwargs = mock_client.as_agent.call_args
        assert call_kwargs.kwargs["tools"] is None

    @patch("agents._base.agent_factory._collect_agent_tools")
    @patch("agents._base.agent_factory.get_chat_client")
    def test_passes_tools_when_present(self, mock_get_client, mock_tools, agent_config):
        """Should pass tools list when tools are found."""
        mock_tool = MagicMock()
        mock_tools.return_value = [mock_tool]
        mock_client = MagicMock()
        mock_client.as_agent.return_value = MagicMock()
        mock_get_client.return_value = mock_client

        create_agent(agent_config)

        call_kwargs = mock_client.as_agent.call_args
        assert call_kwargs.kwargs["tools"] == [mock_tool]
