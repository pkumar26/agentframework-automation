"""Configuration for the doc-assistant agent."""

from pydantic import Field

from agents._base.config import AgentBaseConfig, _IDENTITY_ALIAS

_SKIP = _IDENTITY_ALIAS


class DocAssistantConfig(AgentBaseConfig):
    """Doc-assistant agent configuration.

    Extends the base config with agent-specific settings and defaults.
    """

    agent_name: str = Field(default="doc-assistant", validation_alias=_SKIP)
    agent_deployment_name: str = Field(default="gpt-4o", validation_alias=_SKIP)
    agent_instructions_path: str = Field(default="agents/doc_assistant/instructions.md", validation_alias=_SKIP)
