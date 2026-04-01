"""Configuration for the probation-poc-agent agent."""

from agents._base.config import AgentBaseConfig


class ProbationPocAgentConfig(AgentBaseConfig):
    """ProbationPocAgent agent configuration.

    Extends the base config with agent-specific settings and defaults.
    """

    agent_name: str = "probation-poc-agent"
    agent_deployment_name: str = "gpt-4o"
    agent_instructions_path: str = "agents/probation_poc_agent/instructions.md"
