"""Agent factory — assemble Agent instances from config, instructions, and tools.

Agents are assembled in-process (not deployed to a cloud service).
Models are called via Azure AI Foundry endpoints for inference.
"""

import importlib
import logging
from pathlib import Path

from agent_framework import Agent

from agents._base.client import get_chat_client
from agents._base.config import AgentBaseConfig

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

    client = get_chat_client(
        endpoint=config.azure_ai_project_endpoint,
        deployment_name=config.agent_deployment_name,
    )

    agent = client.as_agent(
        name=config.agent_name,
        instructions=instructions,
        tools=tools or None,
    )

    logger.info(
        "Assembled agent '%s' (model: %s)",
        config.agent_name,
        config.agent_deployment_name,
    )
    return agent


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
