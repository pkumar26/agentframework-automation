"""Integration tests for doc-assistant agent creation."""

import os

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.doc_assistant]

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
        from agents.doc_assistant.config import DocAssistantConfig

        config = DocAssistantConfig()
        agent = create_agent(config)
        assert agent is not None
