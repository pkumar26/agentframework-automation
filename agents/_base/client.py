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


def get_credential():
    """Get or create a shared DefaultAzureCredential."""
    global _credential
    with _lock:
        if _credential is None:
            logger.info("Creating DefaultAzureCredential")
            _credential = DefaultAzureCredential()
        return _credential


def get_chat_client(endpoint: str, deployment_name: str) -> AzureOpenAIResponsesClient:
    """Create an AzureOpenAIResponsesClient for the given endpoint and deployment.

    Args:
        endpoint: Azure AI Foundry project endpoint URL.
        deployment_name: Model deployment name (e.g., "gpt-4o").

    Returns:
        A configured AzureOpenAIResponsesClient.
    """
    return AzureOpenAIResponsesClient(
        project_endpoint=endpoint,
        deployment_name=deployment_name,
        credential=get_credential(),
    )


def reset_credential() -> None:
    """Reset the shared credential. Used for testing."""
    global _credential
    with _lock:
        _credential = None
