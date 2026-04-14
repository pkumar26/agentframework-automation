"""Client factory for Microsoft Agent Framework chat clients.

Creates AzureOpenAIResponsesClient instances that talk to Foundry-deployed
models for inference while running agent orchestration locally.
"""

import logging
import threading

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_credential = None

# Sovereign cloud default token scope (used when no explicit scope is configured).
_GOV_AUTHORITY_FRAGMENT = "login.microsoftonline.us"
_GOV_TOKEN_SCOPE = "https://cognitiveservices.azure.us/.default"


def get_credential(authority: str | None = None):
    """Get or create a shared DefaultAzureCredential.

    Args:
        authority: Azure authority host URL for sovereign clouds.
            Defaults to commercial cloud when not set.
    """
    global _credential
    with _lock:
        if _credential is None:
            kwargs = {}
            if authority:
                kwargs["authority"] = authority
            logger.info("Creating DefaultAzureCredential (authority=%s)", authority or "default")
            _credential = DefaultAzureCredential(**kwargs)
        return _credential


def get_chat_client(
    endpoint: str,
    deployment_name: str,
    authority: str | None = None,
    token_scope: str | None = None,
) -> AzureOpenAIResponsesClient:
    """Create an AzureOpenAIResponsesClient for the given endpoint and deployment.

    Args:
        endpoint: Azure OpenAI or Foundry project endpoint URL.
        deployment_name: Model deployment name (e.g., "gpt-4o").
        authority: Azure authority host URL for sovereign clouds.
        token_scope: Token scope override for sovereign clouds
            (e.g., "https://cognitiveservices.azure.us/.default").

    Returns:
        A configured AzureOpenAIResponsesClient.
    """
    credential = get_credential(authority=authority)

    # Sovereign clouds (e.g. Azure Government) typically use a direct Azure
    # OpenAI endpoint (https://xxx.openai.azure.us) instead of a Foundry
    # project endpoint.  The commercial path uses project_endpoint which
    # creates an AIProjectClient internally — that client hardcodes the
    # scope "https://ai.azure.com/.default" which is invalid in gov cloud.
    # For gov we pass the endpoint directly to AsyncAzureOpenAI with the
    # correct token scope.
    if authority and _GOV_AUTHORITY_FRAGMENT in authority:
        scope = token_scope or _GOV_TOKEN_SCOPE
        return AzureOpenAIResponsesClient(
            endpoint=endpoint.rstrip("/"),
            deployment_name=deployment_name,
            credential=credential,
            token_endpoint=scope,
            api_version="preview",
        )

    return AzureOpenAIResponsesClient(
        project_endpoint=endpoint,
        deployment_name=deployment_name,
        credential=credential,
    )


def reset_credential() -> None:
    """Reset the shared credential. Used for testing."""
    global _credential
    with _lock:
        _credential = None
