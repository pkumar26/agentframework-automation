"""Knowledge source integration stub for the code-helper agent."""

from agents._base.config import AgentBaseConfig


def get_knowledge_tool(config: AgentBaseConfig):
    """Return a knowledge source tool definition, or None if disabled.

    Args:
        config: Agent configuration with knowledge_source_enabled flag.

    Returns:
        Tool definition when enabled (future implementation), None when disabled.
    """
    if not getattr(config, "knowledge_source_enabled", False):
        return None
    raise NotImplementedError(
        "Knowledge source integration is not yet implemented. "
        "Set 'knowledge_source_enabled = False' in your agent's config.py to disable."
    )
