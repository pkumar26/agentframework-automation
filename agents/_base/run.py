"""Run lifecycle for agent interactions using Microsoft Agent Framework."""

import asyncio
import concurrent.futures
import logging

from agents._base.agent_factory import agent_session, create_agent
from agents._base.config import AgentBaseConfig

logger = logging.getLogger(__name__)


async def run_agent_async(config: AgentBaseConfig, prompt: str) -> str:
    """Execute a single-turn conversation with an agent (async).

    Creates the agent from config, runs it with the given prompt,
    and returns the response text. When MCP servers are configured,
    connects them for the duration of the call.

    Args:
        config: Agent configuration (subclass of AgentBaseConfig).
        prompt: The user message to send.

    Returns:
        The agent's response text.
    """
    if config.mcp_servers:
        async with agent_session(config) as agent:
            logger.info("Running agent '%s' with prompt: %s...", config.agent_name, prompt[:50])
            result = await agent.run(prompt)
            return result.text if hasattr(result, "text") else str(result)

    agent = create_agent(config)
    logger.info("Running agent '%s' with prompt: %s...", config.agent_name, prompt[:50])

    result = await agent.run(prompt)
    return result.text if hasattr(result, "text") else str(result)


def run_agent(config: AgentBaseConfig, prompt: str) -> str:
    """Execute a single-turn conversation with an agent (sync wrapper).

    Safe to call from both regular scripts and Jupyter notebooks.

    Args:
        config: Agent configuration (subclass of AgentBaseConfig).
        prompt: The user message to send.

    Returns:
        The agent's response text.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — use asyncio.run() directly
        return asyncio.run(run_agent_async(config, prompt))

    # Already inside a running loop (e.g. Jupyter) — run in a new thread
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, run_agent_async(config, prompt)).result()
