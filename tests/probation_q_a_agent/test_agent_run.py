"""Integration tests for probation-q-a-agent agent run lifecycle."""

import asyncio
import os

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.probation_q_a_agent]

# Skip all tests in this module if no endpoint
ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
if not ENDPOINT:
    pytest.skip(
        "AZURE_AI_PROJECT_ENDPOINT not set — skipping integration tests",
        allow_module_level=True,
    )


class TestAgentRunIntegration:
    """Integration tests for the agent run lifecycle."""

    def test_agent_responds_to_prompt(self):
        """Should run the agent and get a response."""
        from agents._base.agent_factory import create_agent
        from agents.probation_q_a_agent.config import ProbationQAAgentConfig

        config = ProbationQAAgentConfig()
        agent = create_agent(config)
        result = asyncio.run(agent.run("Say 'Test OK' and nothing else."))
        assert result is not None
        assert len(str(result)) > 0
