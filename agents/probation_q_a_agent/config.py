"""Configuration for the probation-q-a-agent agent."""

from agents._base.config import AgentBaseConfig


class ProbationQAAgentConfig(AgentBaseConfig):
    """ProbationQAAgent agent configuration.

    Extends the base config with agent-specific settings and defaults.
    """

    agent_name: str = "probation-q-a-agent"
    agent_deployment_name: str = "gpt-5.1"
    agent_instructions_path: str = "agents/probation_q_a_agent/instructions.md"
