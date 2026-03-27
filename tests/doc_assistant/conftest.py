"""Conftest for doc-assistant agent tests."""

import pytest

from agents.doc_assistant.config import DocAssistantConfig

pytestmark = pytest.mark.doc_assistant


@pytest.fixture
def doc_assistant_config(tmp_path):
    """Create a DocAssistantConfig with a temp instructions file."""
    instructions_file = tmp_path / "instructions.md"
    instructions_file.write_text("You are a doc assistant agent.")

    with pytest.MonkeyPatch.context() as m:
        m.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test.services.ai.azure.com/api/projects/test")
        config = DocAssistantConfig(
            agent_instructions_path=str(instructions_file),
        )
    return config
