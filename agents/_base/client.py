"""Client factory for Microsoft Agent Framework chat clients.

Creates AzureOpenAIResponsesClient instances that talk to Foundry-deployed
models for inference while running agent orchestration locally.
"""

import logging
import os
import threading
from urllib.parse import urlparse

import httpx
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_credential = None

# Token scopes for Azure OpenAI by cloud environment
_GOV_TOKEN_ENDPOINT = "https://cognitiveservices.azure.us/.default"


def _is_direct_openai_endpoint(endpoint: str) -> bool:
    """Return True if the endpoint is a direct Azure OpenAI endpoint."""
    hostname = urlparse(endpoint).hostname or ""
    return hostname.endswith((".openai.azure.com", ".openai.azure.us"))


def _is_gov_cloud(endpoint: str) -> bool:
    """Return True if the endpoint belongs to Azure Government."""
    hostname = urlparse(endpoint).hostname or ""
    return hostname.endswith(".azure.us")


def _ssl_disabled() -> bool:
    """Return True if SSL verification should be disabled."""
    return os.environ.get("DISABLE_SSL_VERIFY", "").lower() in ("true", "1", "yes")


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

    Automatically detects direct Azure OpenAI endpoints (*.openai.azure.com
    or *.openai.azure.us) and uses the ``endpoint`` parameter with the
    correct token scope.  For Foundry project endpoints, uses ``project_endpoint``
    which delegates to the Azure AI Projects SDK.

    Args:
        endpoint: Azure OpenAI or Foundry project endpoint URL.
        deployment_name: Model deployment name (e.g., "gpt-4o").
        authority: Azure authority host URL for sovereign clouds.

    Returns:
        A configured AzureOpenAIResponsesClient.
    """
    credential = get_credential(authority=authority)
    extra_kwargs: dict = {}

    # If SSL verification is disabled, pass a custom httpx client
    if _ssl_disabled():
        from urllib.parse import urljoin

        from openai.lib.azure import AsyncAzureOpenAI
        from azure.identity.aio import get_bearer_token_provider as get_async_bearer_token_provider

        token_endpoint = _GOV_TOKEN_ENDPOINT if _is_gov_cloud(endpoint) else "https://cognitiveservices.azure.com/.default"
        ad_token_provider = get_async_bearer_token_provider(credential, token_endpoint)

        # Responses API requires /openai/v1/ as the base path
        base_url = urljoin(endpoint, "/openai/v1/")
        http_client = httpx.AsyncClient(verify=False)
        azure_client = AsyncAzureOpenAI(
            base_url=base_url,
            azure_ad_token_provider=ad_token_provider,
            api_version="preview",
            http_client=http_client,
        )
        return AzureOpenAIResponsesClient(
            async_client=azure_client,
            deployment_name=deployment_name,
            endpoint=endpoint,
        )

    if _is_direct_openai_endpoint(endpoint):
        kwargs: dict = {
            "endpoint": endpoint,
            "deployment_name": deployment_name,
            "credential": credential,
        }
        if _is_gov_cloud(endpoint):
            kwargs["token_endpoint"] = _GOV_TOKEN_ENDPOINT
        return AzureOpenAIResponsesClient(**kwargs)

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
