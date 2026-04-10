"""Base configuration for all agents using pydantic-settings."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server connection."""

    name: str
    transport: Literal["stdio", "http", "websocket"] = "stdio"
    # stdio transport
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    # http / websocket transport
    url: str | None = None
    # common
    description: str | None = None


class AgentBaseConfig(BaseSettings):
    """Shared configuration base for all agents.

    Models are deployed in Azure AI Foundry; agents run locally or in ACA.
    Reads from environment variables and .env files.
    Each agent extends this class with agent-specific settings.
    """

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Azure AI Foundry project endpoint (for model inference)
    azure_ai_project_endpoint: str
    environment: Literal["dev", "qa", "prod"] = "dev"

    # Azure authority host (optional — set for sovereign clouds).
    # Commercial (default): https://login.microsoftonline.com
    # US Government:         https://login.microsoftonline.us
    # China (21Vianet):      https://login.chinacloudapi.cn
    azure_authority_host: str | None = None

    # Azure AI Search (optional — set endpoint + index to enable RAG grounding)
    azure_ai_search_endpoint: str | None = None
    azure_ai_search_index_name: str | None = None
    # Semantic configuration name (set to enable semantic/hybrid ranking).
    # Leave unset for simple keyword search.
    azure_ai_search_semantic_config: str | None = None

    # Foundry knowledge base (optional — alternative to setting
    # endpoint + index directly). Set the index name registered in your Foundry project; the
    # search endpoint and underlying index name are resolved automatically via
    # the project connections API.
    azure_ai_search_knowledge_base: str | None = None

    # Disable SSL certificate verification (optional — for corporate proxies
    # with SSL inspection). Defaults to False.
    disable_ssl_verify: bool = False

    # MCP servers (optional — JSON list of MCPServerConfig objects).
    # Set via env var: MCP_SERVERS='[{"name":"github","transport":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-github"]}]'
    mcp_servers: list[MCPServerConfig] | None = None
