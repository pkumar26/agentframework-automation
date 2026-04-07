"""Hosting adapter for Azure Container Apps deployment.

Wraps an agent with azure-ai-agentserver-agentframework to expose
a Foundry-compatible /responses endpoint on port 8088.

Usage:
    AGENT_NAME=code-helper python app.py
"""

import asyncio
import logging
import os

from azure.ai.agentserver.agentframework import from_agent_framework

from agents._base.agent_factory import agent_session
from agents.registry import REGISTRY

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def _serve_with_mcp(agent_name: str) -> None:
    """Start the hosted server with MCP tools connected."""
    entry = REGISTRY.get_agent(agent_name)
    config = entry.config_class()

    async with agent_session(config) as agent:
        logger.info("Starting hosted agent (with MCP): %s", agent_name)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: from_agent_framework(agent).run())


def main():
    agent_name = os.environ.get("AGENT_NAME", "code-helper")
    logger.info("Starting hosted agent: %s", agent_name)

    entry = REGISTRY.get_agent(agent_name)
    config = entry.config_class()

    if config.mcp_servers:
        asyncio.run(_serve_with_mcp(agent_name))
    else:
        agent = entry.factory(config)
        from_agent_framework(agent).run()


if __name__ == "__main__":
    main()
