"""Unit tests for chat client factory."""

from unittest.mock import MagicMock, patch

import pytest

from agents._base.client import get_chat_client, get_credential, reset_credential


class TestGetChatClient:
    """Tests for the chat client factory."""

    def setup_method(self):
        """Reset credential cache before each test."""
        reset_credential()

    def teardown_method(self):
        """Reset credential cache after each test."""
        reset_credential()

    @patch("agents._base.client.DefaultAzureCredential")
    @patch("agents._base.client.AzureOpenAIResponsesClient")
    def test_creates_client_with_params(self, mock_client_cls, mock_cred_cls):
        """Client should be created with endpoint, deployment, and credential."""
        mock_cred = MagicMock()
        mock_cred_cls.return_value = mock_cred
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        result = get_chat_client(
            endpoint="https://test.services.ai.azure.com/api/projects/test",
            deployment_name="gpt-4o",
        )

        mock_cred_cls.assert_called_once_with()
        mock_client_cls.assert_called_once_with(
            project_endpoint="https://test.services.ai.azure.com/api/projects/test",
            deployment_name="gpt-4o",
            credential=mock_cred,
        )
        assert result is mock_client

    @patch("agents._base.client.DefaultAzureCredential")
    def test_credential_is_reused(self, mock_cred_cls):
        """Subsequent calls should reuse the same credential."""
        mock_cred = MagicMock()
        mock_cred_cls.return_value = mock_cred

        cred1 = get_credential()
        cred2 = get_credential()

        assert cred1 is cred2
        assert mock_cred_cls.call_count == 1

    def test_reset_credential_clears_cache(self):
        """reset_credential should clear the cached credential."""
        with patch("agents._base.client.DefaultAzureCredential") as mock_cls:
            mock_cls.return_value = MagicMock()
            get_credential()
            reset_credential()
            get_credential()
            assert mock_cls.call_count == 2

    @patch("agents._base.client.DefaultAzureCredential")
    def test_credential_with_authority(self, mock_cred_cls):
        """Credential should be created with authority for sovereign clouds."""
        mock_cred_cls.return_value = MagicMock()
        get_credential(authority="https://login.microsoftonline.us")
        mock_cred_cls.assert_called_once_with(
            authority="https://login.microsoftonline.us",
        )

    @patch("agents._base.client.DefaultAzureCredential")
    def test_credential_without_authority(self, mock_cred_cls):
        """Credential should be created without authority kwarg for commercial cloud."""
        mock_cred_cls.return_value = MagicMock()
        get_credential()
        mock_cred_cls.assert_called_once_with()

    @patch("agents._base.client.DefaultAzureCredential")
    @patch("agents._base.client.AzureOpenAIResponsesClient")
    def test_gov_cloud_bypasses_project_client(self, mock_client_cls, mock_cred_cls):
        """Gov cloud should bypass AIProjectClient and pass token_endpoint directly."""
        mock_cred = MagicMock()
        mock_cred_cls.return_value = mock_cred
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        result = get_chat_client(
            endpoint="https://test.services.ai.azure.us/api/projects/test",
            deployment_name="gpt-4o",
            authority="https://login.microsoftonline.us",
        )

        mock_client_cls.assert_called_once_with(
            endpoint="https://test.services.ai.azure.us/api/projects/test",
            base_url="https://test.services.ai.azure.us/api/projects/test/openai/v1/",
            deployment_name="gpt-4o",
            credential=mock_cred,
            token_endpoint="https://cognitiveservices.azure.us/.default",
            api_version="preview",
        )
        assert result is mock_client
