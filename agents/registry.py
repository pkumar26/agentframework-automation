"""Agent registry — central mapping of agent names to their config and factory."""

from dataclasses import dataclass
from typing import Callable, Type

from agents._base.config import AgentBaseConfig


@dataclass(frozen=True)
class AgentRegistryEntry:
    """An entry in the agent registry."""

    name: str
    config_class: Type[AgentBaseConfig]
    factory: Callable


class AgentRegistry:
    """Central registry of all agents. Immutable after construction."""

    def __init__(self, entries: list[AgentRegistryEntry]) -> None:
        """Initialise and validate uniqueness."""
        self._entries = list(entries)
        self.validate()

    def list_agents(self) -> list[AgentRegistryEntry]:
        """Return all registered agent entries."""
        return list(self._entries)

    def get_agent(self, name: str) -> AgentRegistryEntry:
        """Return the entry for the given agent name.

        Raises:
            KeyError: If no agent with the given name is registered.
        """
        for entry in self._entries:
            if entry.name == name:
                return entry
        available = ", ".join(e.name for e in self._entries)
        raise KeyError(f"Agent '{name}' not found. Available agents: {available}")

    def validate(self) -> None:
        """Check all invariants.

        Raises:
            ValueError: If duplicate agent names are detected.
        """
        names = [e.name for e in self._entries]
        duplicates = [n for n in names if names.count(n) > 1]
        if duplicates:
            unique_dupes = sorted(set(duplicates))
            raise ValueError(
                f"Duplicate agent name(s) in registry: {', '.join(unique_dupes)}. "
                "Each agent must have a unique name."
            )


from agents._base.agent_factory import create_agent  # noqa: E402
from agents.code_helper.config import CodeHelperConfig  # noqa: E402
from agents.doc_assistant.config import DocAssistantConfig  # noqa: E402
from agents.probation_poc_agent.config import ProbationPocAgentConfig  # noqa: E402



REGISTRY = AgentRegistry(
    [
        AgentRegistryEntry(
            name="code-helper",
            config_class=CodeHelperConfig,
            factory=create_agent,
        ),
        AgentRegistryEntry(
            name="doc-assistant",
            config_class=DocAssistantConfig,
            factory=create_agent,
        ),
        AgentRegistryEntry(
            name="probation-poc-agent",
            config_class=ProbationPocAgentConfig,
            factory=create_agent,
        ),
    ]
)
