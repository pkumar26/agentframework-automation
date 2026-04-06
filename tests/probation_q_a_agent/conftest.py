"""Conftest for probation-q-a-agent agent tests."""

import pytest

from agents.probation_q_a_agent.config import ProbationQAAgentConfig

pytestmark = pytest.mark.probation_q_a_agent


@pytest.fixture
def probation_q_a_agent_config(tmp_path):
    """Create a ProbationQAAgentConfig with a temp instructions file."""
    instructions_file = tmp_path / "instructions.md"
    instructions_file.write_text("You are a probation-q-a-agent agent.")

    with pytest.MonkeyPatch.context() as m:
        m.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test.services.ai.azure.com/api/projects/test")
        config = ProbationQAAgentConfig(
            agent_instructions_path=str(instructions_file),
        )
    return config
