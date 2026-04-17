"""Agent-specific knowledge configuration for the code-helper agent.

Reads agent-prefixed env vars to give this agent its own search index(es),
independent of other agents sharing the same deployment. Return ``None``
to fall back to the shared base-config search settings.

Env vars (all optional — single index):
    CODE_HELPER_SEARCH_ENDPOINT        – Azure AI Search service URL
    CODE_HELPER_SEARCH_INDEX_NAME      – Index to query
    CODE_HELPER_SEARCH_SEMANTIC_CONFIG – Semantic ranking config name

Env vars (all optional — multiple indexes, additive with single):
    CODE_HELPER_SEARCH_INDEXES – JSON array of {endpoint, index_name, semantic_config}
"""

import json
import logging
import os

from agents._base.config import AgentBaseConfig

logger = logging.getLogger(__name__)


def get_context_providers(config: AgentBaseConfig):
    """Return agent-specific context providers, or None to use base config.

    Supports a single index via ``CODE_HELPER_SEARCH_ENDPOINT`` +
    ``CODE_HELPER_SEARCH_INDEX_NAME``, multiple indexes via
    ``CODE_HELPER_SEARCH_INDEXES`` (JSON array), or both combined.
    Returns None when no agent-specific vars are set so the factory
    falls back to the shared ``AZURE_AI_SEARCH_*`` env vars.
    """
    endpoint = os.environ.get("CODE_HELPER_SEARCH_ENDPOINT")
    index_name = os.environ.get("CODE_HELPER_SEARCH_INDEX_NAME")
    indexes_json = os.environ.get("CODE_HELPER_SEARCH_INDEXES")

    if not (endpoint and index_name) and not indexes_json:
        return None  # Defer to base config

    from agents._base.client import get_credential
    from agents._base.integrations.search import AzureAISearchContextProvider

    credential = get_credential(authority=config.azure_authority_host)
    providers = []

    # Single index
    if endpoint and index_name:
        semantic_config = os.environ.get("CODE_HELPER_SEARCH_SEMANTIC_CONFIG")
        providers.append(
            AzureAISearchContextProvider(
                endpoint=endpoint,
                index_name=index_name,
                semantic_config=semantic_config,
                credential=credential,
            )
        )

    # Multiple indexes (additive)
    if indexes_json:
        try:
            entries = json.loads(indexes_json)
            for entry in entries:
                providers.append(
                    AzureAISearchContextProvider(
                        endpoint=entry["endpoint"],
                        index_name=entry["index_name"],
                        semantic_config=entry.get("semantic_config"),
                        credential=credential,
                    )
                )
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.warning(
                "Invalid CODE_HELPER_SEARCH_INDEXES JSON — skipping multi-index config",
                exc_info=True,
            )

    return providers
