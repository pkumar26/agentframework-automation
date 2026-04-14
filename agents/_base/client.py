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

# Sovereign cloud credential scopes.
# The azure-ai-projects SDK defaults to "https://ai.azure.com/.default" which
# is only valid in the commercial cloud.  For sovereign clouds the token
# audience must match the cloud-specific Cognitive Services resource ID.
_GOV_AUTHORITY_FRAGMENT = "login.microsoftonline.us"
_GOV_CREDENTIAL_SCOPES = ["https://cognitiveservices.azure.us/.default"]


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

    # Sovereign clouds: the default credential_scopes in AIProjectClient
    # ("https://ai.azure.com/.default") are invalid outside commercial Azure.
    # Create the project client ourselves with the correct scopes.
    if authority and _GOV_AUTHORITY_FRAGMENT in authority:
        from azure.ai.projects.aio import AIProjectClient

        project_client = AIProjectClient(
            endpoint=endpoint,
            credential=credential,
            credential_scopes=_GOV_CREDENTIAL_SCOPES,
        )
        return AzureOpenAIResponsesClient(
            project_client=project_client,
            deployment_name=deployment_name,
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
