"""Configuration for the code-helper agent."""

from pydantic import Field

from agents._base.config import AgentBaseConfig, _IDENTITY_ALIAS

_SKIP = _IDENTITY_ALIAS


class CodeHelperConfig(AgentBaseConfig):
    """Code-helper agent configuration.

    Extends the base config with agent-specific settings and defaults.
    """

    agent_name: str = Field(default="code-helper", validation_alias=_SKIP)
    agent_deployment_name: str = Field(default="gpt-4o", validation_alias=_SKIP)
    agent_instructions_path: str = Field(default="agents/code_helper/instructions.md", validation_alias=_SKIP)
