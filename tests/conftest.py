"""Root conftest — shared fixtures and marker registration."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_config():
    """Create a mock AgentBaseConfig-like object for testing."""
    config = MagicMock()
    config.azure_ai_project_endpoint = "https://test.services.ai.azure.com/api/projects/test"
    config.environment = "dev"
    config.agent_name = "test-agent"
    config.agent_deployment_name = "gpt-4o"
    config.agent_instructions_path = "agents/code_helper/instructions.md"
    return config


@pytest.fixture
def mock_chat_client():
    """Create a mock AzureOpenAIResponsesClient."""
    with patch("agents._base.client.AzureOpenAIResponsesClient") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        yield client
