"""Configuration for the code-helper agent."""

from agents._base.config import AgentBaseConfig


class CodeHelperConfig(AgentBaseConfig):
    """Code-helper agent configuration.

    Extends the base config with agent-specific settings and defaults.
    """

    agent_name: str = "code-helper"
    agent_deployment_name: str = "gpt-4o"
    agent_instructions_path: str = "agents/code_helper/instructions.md"
