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

# Sovereign cloud token scope.
# The azure-ai-projects SDK hardcodes "https://ai.azure.com/.default" in
# AIProjectClient.get_openai_client() which is only valid in commercial Azure.
# For US Government the token audience must be the gov-specific endpoint.
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
) -> AzureOpenAIResponsesClient:
    """Create an AzureOpenAIResponsesClient for the given endpoint and deployment.

    Args:
        endpoint: Azure AI Foundry project endpoint URL.
        deployment_name: Model deployment name (e.g., "gpt-4o").
        authority: Azure authority host URL for sovereign clouds.

    Returns:
        A configured AzureOpenAIResponsesClient.
    """
    credential = get_credential(authority=authority)

    # Sovereign clouds: AIProjectClient.get_openai_client() hardcodes the
    # commercial scope "https://ai.azure.com/.default" which causes
    # ManagedIdentityCredential to fail with invalid_scope in gov cloud.
    # Bypass the project client entirely and build the OpenAI client ourselves
    # with the correct gov token scope fed through token_endpoint.
    if authority and _GOV_AUTHORITY_FRAGMENT in authority:
        return AzureOpenAIResponsesClient(
            endpoint=endpoint.rstrip("/"),
            base_url=endpoint.rstrip("/") + "/openai/v1/",
            deployment_name=deployment_name,
            credential=credential,
            token_endpoint=_GOV_TOKEN_SCOPE,
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
