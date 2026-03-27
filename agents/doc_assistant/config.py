"""Configuration for the doc-assistant agent."""

from agents._base.config import AgentBaseConfig


class DocAssistantConfig(AgentBaseConfig):
    """Doc-assistant agent configuration.

    Extends the base config with agent-specific settings and defaults.
    """

    agent_name: str = "doc-assistant"
    agent_deployment_name: str = "gpt-4o"
    agent_instructions_path: str = "agents/doc_assistant/instructions.md"
