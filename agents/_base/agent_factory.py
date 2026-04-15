"""Agent factory — assemble Agent instances from config, instructions, and tools.

Agents are assembled in-process (not deployed to a cloud service).
Models are called via Azure AI Foundry endpoints for inference.
"""

import importlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from agent_framework import Agent

from agents._base.client import get_chat_client
from agents._base.config import AgentBaseConfig
from agents._base.integrations.search import AzureAISearchContextProvider

logger = logging.getLogger(__name__)


def create_agent(config: AgentBaseConfig) -> Agent:
    """Create an Agent instance from config.

    Loads instructions from a markdown file, collects tool functions from
    the agent's tools module, and assembles an Agent that runs in-process.

    Args:
        config: An agent-specific config object (subclass of AgentBaseConfig).

    Returns:
        A fully assembled Agent ready to run.

    Raises:
        FileNotFoundError: If the instructions file does not exist.
        ValueError: If the instructions file is empty.
    """
    instructions = _load_instructions(config)
    tools = _collect_agent_tools(config)
    context_providers = _collect_context_providers(config)

    client = get_chat_client(
        endpoint=config.azure_ai_project_endpoint,
        deployment_name=config.agent_deployment_name,
        authority=config.azure_authority_host,
        token_scope=config.azure_openai_token_scope,
    )

    agent = client.as_agent(
        name=config.agent_name,
        instructions=instructions,
        tools=tools or None,
        context_providers=context_providers or None,
    )

    logger.info(
        "Assembled agent '%s' (model: %s)",
        config.agent_name,
        config.agent_deployment_name,
    )
    return agent


@asynccontextmanager
async def agent_session(config: AgentBaseConfig):
    """Async context manager that connects MCP servers and yields an Agent.

    Connects all configured MCP tools, assembles the agent with both
    function tools and MCP tools, and disconnects MCP tools on exit.
    Works transparently when no MCP servers are configured.

    Usage::

        async with agent_session(config) as agent:
            result = await agent.run("Hello!")

    Args:
        config: An agent-specific config object (subclass of AgentBaseConfig).

    Yields:
        A fully assembled Agent with MCP tools connected.
    """
    mcp_tools = _build_mcp_tools(config)
    connected = []
    try:
        for tool in mcp_tools:
            await tool.__aenter__()
            connected.append(tool)
            logger.info("Connected MCP server '%s'", tool.name)

        instructions = _load_instructions(config)
        function_tools = _collect_agent_tools(config)
        context_providers = _collect_context_providers(config)
        all_tools = function_tools + mcp_tools

        client = get_chat_client(
            endpoint=config.azure_ai_project_endpoint,
            deployment_name=config.agent_deployment_name,
            authority=config.azure_authority_host,
            token_scope=config.azure_openai_token_scope,
        )

        agent = client.as_agent(
            name=config.agent_name,
            instructions=instructions,
            tools=all_tools or None,
            context_providers=context_providers or None,
        )

        logger.info(
            "Assembled agent '%s' (model: %s, %d MCP server(s))",
            config.agent_name,
            config.agent_deployment_name,
            len(mcp_tools),
        )
        yield agent
    finally:
        for tool in reversed(connected):
            try:
                await tool.__aexit__(None, None, None)
                logger.info("Disconnected MCP server '%s'", tool.name)
            except Exception:
                logger.warning(
                    "Error disconnecting MCP server '%s'",
                    tool.name,
                    exc_info=True,
                )


def _load_instructions(config: AgentBaseConfig) -> str:
    """Load instructions from the configured markdown file."""
    instructions_path = Path(config.agent_instructions_path)
    if not instructions_path.is_absolute():
        project_root = Path(__file__).resolve().parent.parent.parent
        instructions_path = project_root / instructions_path
    if not instructions_path.exists():
        raise FileNotFoundError(f"Instructions file not found: {instructions_path}")
    instructions = instructions_path.read_text(encoding="utf-8").strip()
    if not instructions:
        raise ValueError(f"Instructions file is empty: {instructions_path}")
    return instructions


def _collect_agent_tools(config: AgentBaseConfig) -> list:
    """Collect tool functions from the agent's tools module.

    Looks for a TOOLS list in agents.{module_name}.tools.
    Agent Framework auto-wraps plain functions as function tools.
    """
    # Derive tools module from config class location when possible
    config_module = getattr(type(config), "__module__", "")
    if config_module.startswith("agents.") and config_module.endswith(".config"):
        agent_package = config_module.rsplit(".", 1)[0]
        tools_module_path = f"{agent_package}.tools"
    else:
        module_name = config.agent_name.replace("-", "_")
        tools_module_path = f"agents.{module_name}.tools"

    try:
        tools_module = importlib.import_module(tools_module_path)
    except ModuleNotFoundError:
        return []

    tools = []
    if hasattr(tools_module, "TOOLS"):
        tools.extend(tools_module.TOOLS)
    return tools


def _collect_context_providers(config: AgentBaseConfig) -> list:
    """Build context providers based on config.

    Supports Azure AI Search via explicit endpoint + index, via a Foundry
    knowledge base name (resolved through the project connections API),
    and via a list of multiple search indexes.
    All sources are additive — providers from single-index config and
    the azure_ai_search_indexes list are combined.
    """
    providers = []

    # --- Single-index config (backward compatible) ---
    endpoint = config.azure_ai_search_endpoint
    index_name = config.azure_ai_search_index_name

    # Resolve knowledge base name → endpoint + index via Foundry project API
    if not (endpoint and index_name) and config.azure_ai_search_knowledge_base:
        try:
            endpoint, index_name = _resolve_knowledge_base(
                project_endpoint=config.azure_ai_project_endpoint,
                knowledge_base_name=config.azure_ai_search_knowledge_base,
                authority=config.azure_authority_host,
            )
        except Exception:
            logger.warning(
                "Failed to resolve knowledge base '%s' — "
                "search grounding disabled for this agent",
                config.azure_ai_search_knowledge_base,
                exc_info=True,
            )

    # Share the credential that already handles sovereign cloud authority
    from agents._base.client import get_credential

    credential = get_credential(authority=config.azure_authority_host)

    if endpoint and index_name:
        providers.append(
            AzureAISearchContextProvider(
                endpoint=endpoint,
                index_name=index_name,
                semantic_config=config.azure_ai_search_semantic_config,
                credential=credential,
            )
        )
        logger.info(
            "Enabled Azure AI Search context provider (index: %s)",
            index_name,
        )

    # --- Multiple indexes ---
    if config.azure_ai_search_indexes:
        for idx_cfg in config.azure_ai_search_indexes:
            providers.append(
                AzureAISearchContextProvider(
                    endpoint=idx_cfg.endpoint,
                    index_name=idx_cfg.index_name,
                    semantic_config=idx_cfg.semantic_config,
                    credential=credential,
                )
            )
            logger.info(
                "Enabled Azure AI Search context provider (index: %s)",
                idx_cfg.index_name,
            )

    return providers


def _resolve_knowledge_base(
    project_endpoint: str,
    knowledge_base_name: str,
    authority: str | None = None,
) -> tuple[str, str]:
    """Resolve a Foundry knowledge base name to (search_endpoint, index_name).

    Uses the project connections and indexes APIs to look up the underlying
    Azure AI Search service endpoint and index name.
    """
    from azure.ai.projects import AIProjectClient

    from agents._base.client import get_credential

    client = AIProjectClient(
        endpoint=project_endpoint,
        credential=get_credential(authority=authority),
    )
    # Get the latest version of the index
    versions = list(client.indexes.list_versions(knowledge_base_name))
    if not versions:
        raise ValueError(
            f"Knowledge base '{knowledge_base_name}' not found in project."
        )
    index = versions[-1]
    search_index_name = index.index_name
    connection_name = index.connection_name

    # Resolve connection → search endpoint
    connection = client.connections.get(connection_name)
    search_endpoint = connection.target

    logger.info(
        "Resolved knowledge base '%s' → endpoint=%s, index=%s",
        knowledge_base_name,
        search_endpoint,
        search_index_name,
    )
    return search_endpoint, search_index_name


def _build_mcp_tools(config: AgentBaseConfig) -> list:
    """Create MCP tool instances from config (unconnected).

    Supports stdio, HTTP, and WebSocket transports. The returned tools
    must be connected via ``async with`` before use — ``agent_session()``
    handles this automatically.
    """
    if not config.mcp_servers:
        return []

    from agent_framework import MCPStdioTool, MCPStreamableHTTPTool, MCPWebsocketTool

    tools = []
    for server in config.mcp_servers:
        if server.transport == "stdio":
            if not server.command:
                logger.warning(
                    "MCP server '%s': stdio transport requires 'command'",
                    server.name,
                )
                continue
            tools.append(
                MCPStdioTool(
                    name=server.name,
                    command=server.command,
                    args=server.args or [],
                    env=server.env,
                    description=server.description,
                )
            )
        elif server.transport == "http":
            if not server.url:
                logger.warning(
                    "MCP server '%s': http transport requires 'url'",
                    server.name,
                )
                continue
            tools.append(
                MCPStreamableHTTPTool(
                    name=server.name,
                    url=server.url,
                    description=server.description,
                )
            )
        elif server.transport == "websocket":
            if not server.url:
                logger.warning(
                    "MCP server '%s': websocket transport requires 'url'",
                    server.name,
                )
                continue
            tools.append(
                MCPWebsocketTool(
                    name=server.name,
                    url=server.url,
                    description=server.description,
                )
            )
        else:
            logger.warning(
                "MCP server '%s': unknown transport '%s'",
                server.name,
                server.transport,
            )
    return tools
