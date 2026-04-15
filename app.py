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
from agents._base.client import get_credential
from agents.registry import REGISTRY

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_GOV_AUTHORITY_FRAGMENT = "login.microsoftonline.us"


def _hide_project_endpoint_for_gov(config) -> None:
    """Prevent the agentserver from using ``ai.azure.com`` scope in sovereign clouds.

    The agentserver's FoundryToolClient hardcodes
    ``https://ai.azure.com/.default`` for tool-runtime and conversation
    storage.  That resource principal does not exist in Azure Government
    tenants, so the managed-identity token request fails with
    ``invalid_scope 400``.

    Removing ``AZURE_AI_PROJECT_ENDPOINT`` from the environment before the
    agentserver initialises causes it to fall back to a no-op tool runtime
    (``ThrowingFoundryToolRuntime``) that never requests the bad scope.
    Our own agent code already has the endpoint via the config object.

    SDK bug: azure-ai-agentserver hardcodes ``ai.azure.com/.default`` in
    FoundryToolClientConfiguration and _create_openai_client (base.py lines
    ~106, ~285).  Remove this workaround once the SDK accepts a
    ``credential_scopes`` parameter or adds sovereign cloud support.

    Disabled gov features (unavailable without Foundry):
    - Foundry tool runtime (connected tools, hosted MCP)
    - Conversation storage (store=true)
    """
    authority = config.azure_authority_host or ""
    if _GOV_AUTHORITY_FRAGMENT in authority:
        removed = os.environ.pop("AZURE_AI_PROJECT_ENDPOINT", None)
        if removed:
            logger.info(
                "Gov cloud: removed AZURE_AI_PROJECT_ENDPOINT from env "
                "to prevent agentserver ai.azure.com token request"
            )


async def _serve_with_mcp(agent_name: str) -> None:
    """Start the hosted server with MCP tools connected."""
    entry = REGISTRY.get_agent(agent_name)
    config = entry.config_class()
    credential = get_credential(authority=config.azure_authority_host)
    _hide_project_endpoint_for_gov(config)

    async with agent_session(config) as agent:
        logger.info("Starting hosted agent (with MCP): %s", agent_name)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: from_agent_framework(agent, credentials=credential).run()
        )


def main():
    agent_name = os.environ.get("AGENT_NAME", "code-helper")
    logger.info("Starting hosted agent: %s", agent_name)

    entry = REGISTRY.get_agent(agent_name)
    config = entry.config_class()
    credential = get_credential(authority=config.azure_authority_host)
    _hide_project_endpoint_for_gov(config)

    if config.mcp_servers:
        asyncio.run(_serve_with_mcp(agent_name))
    else:
        agent = entry.factory(config)
        from_agent_framework(agent, credentials=credential).run()


if __name__ == "__main__":
    main()
