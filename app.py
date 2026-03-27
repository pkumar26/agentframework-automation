"""Hosting adapter for Azure Container Apps deployment.

Wraps an agent with azure-ai-agentserver-agentframework to expose
a Foundry-compatible /responses endpoint on port 8088.

Usage:
    AGENT_NAME=code-helper python app.py
"""

import logging
import os

from azure.ai.agentserver.agentframework import from_agent_framework

from agents.registry import REGISTRY

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    agent_name = os.environ.get("AGENT_NAME", "code-helper")
    logger.info("Starting hosted agent: %s", agent_name)

    entry = REGISTRY.get_agent(agent_name)
    config = entry.config_class()
    agent = entry.factory(config)

    from_agent_framework(agent).run()


if __name__ == "__main__":
    main()
