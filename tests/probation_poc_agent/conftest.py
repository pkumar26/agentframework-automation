"""Conftest for probation-poc-agent agent tests."""

import pytest

from agents.probation_poc_agent.config import ProbationPocAgentConfig

pytestmark = pytest.mark.probation_poc_agent


@pytest.fixture
def probation_poc_agent_config(tmp_path):
    """Create a ProbationPocAgentConfig with a temp instructions file."""
    instructions_file = tmp_path / "instructions.md"
    instructions_file.write_text("You are a probation-poc-agent agent.")

    with pytest.MonkeyPatch.context() as m:
        m.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test.services.ai.azure.com/api/projects/test")
        config = ProbationPocAgentConfig(
            agent_instructions_path=str(instructions_file),
        )
    return config
