"""Client factory for Microsoft Agent Framework chat clients.

Creates AzureOpenAIResponsesClient instances that talk to Foundry-deployed
models for inference while running agent orchestration locally.
"""

import logging
import os
import ssl
import threading

import httpx
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_credential = None


def get_credential():
    """Get or create a shared DefaultAzureCredential.

    Respects the AZURE_AUTHORITY_HOST environment variable so that
    Azure Government (https://login.microsoftonline.us/) and other
    sovereign clouds work without code changes.
    """
    global _credential
    with _lock:
        if _credential is None:
            authority = os.environ.get("AZURE_AUTHORITY_HOST")
            kwargs = {"authority": authority} if authority else {}
            logger.info("Creating DefaultAzureCredential (authority=%s)", authority or "default")
            _credential = DefaultAzureCredential(**kwargs)
        return _credential


def _is_gov_cloud() -> bool:
    """Return True if AZURE_AUTHORITY_HOST points to Azure Government."""
    authority = os.environ.get("AZURE_AUTHORITY_HOST", "")
    return "microsoftonline.us" in authority


def _get_httpx_client() -> httpx.AsyncClient | None:
    """Return an httpx client with custom SSL settings if needed.

    When DISABLE_SSL_VERIFY=true (for corporate proxy / Zscaler environments
    where the root CA is not installed), creates an httpx client that skips
    TLS certificate verification.  Only use this for local development.
    """
    if os.environ.get("DISABLE_SSL_VERIFY", "").lower() in ("true", "1", "yes"):
        logger.warning(
            "SSL verification disabled (DISABLE_SSL_VERIFY=true). "
            "Do NOT use this in production."
        )
        return httpx.AsyncClient(verify=False)
    return None


def get_chat_client(endpoint: str, deployment_name: str) -> AzureOpenAIResponsesClient:
    """Create an AzureOpenAIResponsesClient for the given endpoint and deployment.

    For Azure Government the ``AIProjectClient.get_openai_client()`` hardcodes
    scope ``https://ai.azure.com/.default`` which does not exist in sovereign
    clouds.  We work around this by constructing the ``AIProjectClient`` with
    the correct scope *and* passing ``api_key`` to ``get_openai_client()`` so
    the hardcoded scope is bypassed.

    Args:
        endpoint: Azure AI Foundry project endpoint URL.
        deployment_name: Model deployment name (e.g., "gpt-4o").

    Returns:
        A configured AzureOpenAIResponsesClient.
    """
    credential = get_credential()
    http_client = _get_httpx_client()

    if _is_gov_cloud():
        from azure.ai.projects.aio import AIProjectClient
        from azure.identity.aio import get_bearer_token_provider

        gov_scope = "https://cognitiveservices.azure.us/.default"

        # Build AIProjectClient with correct gov scope
        project_client = AIProjectClient(
            endpoint=endpoint,
            credential=credential,
            credential_scopes=[gov_scope],
        )

        # get_openai_client() hardcodes "https://ai.azure.com/.default" for the
        # api_key token provider.  Override it by passing api_key ourselves.
        client_kwargs = {
            "api_key": get_bearer_token_provider(credential, gov_scope),
        }
        if http_client:
            client_kwargs["http_client"] = http_client
        openai_client = project_client.get_openai_client(**client_kwargs)

        return AzureOpenAIResponsesClient(
            async_client=openai_client,
            deployment_name=deployment_name,
            token_endpoint=gov_scope,
            credential=credential,
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
