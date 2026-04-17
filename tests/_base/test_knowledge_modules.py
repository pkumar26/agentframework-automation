"""Unit tests for agent-specific knowledge.py modules."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.code_helper.integrations.knowledge import (
    get_context_providers as code_helper_get,
)
from agents.doc_assistant.integrations.knowledge import (
    get_context_providers as doc_assistant_get,
)


@pytest.fixture
def config():
    config = MagicMock()
    config.azure_authority_host = None
    return config


class TestCodeHelperKnowledge:
    """Tests for code_helper knowledge.py."""

    def test_returns_none_when_no_env_vars(self, config, monkeypatch):
        """Should return None (defer to base) when agent env vars not set."""
        monkeypatch.delenv("CODE_HELPER_SEARCH_ENDPOINT", raising=False)
        monkeypatch.delenv("CODE_HELPER_SEARCH_INDEX_NAME", raising=False)
        monkeypatch.delenv("CODE_HELPER_SEARCH_INDEXES", raising=False)
        assert code_helper_get(config) is None

    def test_returns_none_when_only_endpoint(self, config, monkeypatch):
        """Should return None when only endpoint is set (index missing)."""
        monkeypatch.setenv("CODE_HELPER_SEARCH_ENDPOINT", "https://s.search.windows.net")
        monkeypatch.delenv("CODE_HELPER_SEARCH_INDEX_NAME", raising=False)
        monkeypatch.delenv("CODE_HELPER_SEARCH_INDEXES", raising=False)
        assert code_helper_get(config) is None

    @patch("agents._base.integrations.search.AzureAISearchContextProvider")
    @patch("agents._base.client.get_credential")
    def test_creates_provider_when_configured(self, mock_cred, mock_provider, config, monkeypatch):
        """Should create a provider when both env vars are set."""
        mock_cred.return_value = MagicMock()
        monkeypatch.setenv("CODE_HELPER_SEARCH_ENDPOINT", "https://code.search.windows.net")
        monkeypatch.setenv("CODE_HELPER_SEARCH_INDEX_NAME", "code-index")
        monkeypatch.setenv("CODE_HELPER_SEARCH_SEMANTIC_CONFIG", "my-sem")

        result = code_helper_get(config)

        assert len(result) == 1
        mock_provider.assert_called_once_with(
            endpoint="https://code.search.windows.net",
            index_name="code-index",
            semantic_config="my-sem",
            credential=mock_cred.return_value,
        )

    @patch("agents._base.integrations.search.AzureAISearchContextProvider")
    @patch("agents._base.client.get_credential")
    def test_passes_authority_to_credential(self, mock_cred, mock_provider, config, monkeypatch):
        """Should pass authority from config to get_credential."""
        mock_cred.return_value = MagicMock()
        config.azure_authority_host = "https://login.microsoftonline.us"
        monkeypatch.setenv("CODE_HELPER_SEARCH_ENDPOINT", "https://code.search.azure.us")
        monkeypatch.setenv("CODE_HELPER_SEARCH_INDEX_NAME", "code-index")

        code_helper_get(config)

        mock_cred.assert_called_once_with(authority="https://login.microsoftonline.us")

    @patch("agents._base.integrations.search.AzureAISearchContextProvider")
    @patch("agents._base.client.get_credential")
    def test_semantic_config_optional(self, mock_cred, mock_provider, config, monkeypatch):
        """Should pass None for semantic_config when not set."""
        mock_cred.return_value = MagicMock()
        monkeypatch.setenv("CODE_HELPER_SEARCH_ENDPOINT", "https://code.search.windows.net")
        monkeypatch.setenv("CODE_HELPER_SEARCH_INDEX_NAME", "code-index")
        monkeypatch.delenv("CODE_HELPER_SEARCH_SEMANTIC_CONFIG", raising=False)

        code_helper_get(config)

        assert mock_provider.call_args.kwargs["semantic_config"] is None

    @patch("agents._base.integrations.search.AzureAISearchContextProvider")
    @patch("agents._base.client.get_credential")
    def test_multi_index_from_json(self, mock_cred, mock_provider, config, monkeypatch):
        """Should create providers from JSON array env var."""
        mock_cred.return_value = MagicMock()
        monkeypatch.delenv("CODE_HELPER_SEARCH_ENDPOINT", raising=False)
        monkeypatch.delenv("CODE_HELPER_SEARCH_INDEX_NAME", raising=False)
        indexes = [
            {"endpoint": "https://s1.search.windows.net", "index_name": "idx1"},
            {"endpoint": "https://s2.search.windows.net", "index_name": "idx2", "semantic_config": "sem2"},
        ]
        monkeypatch.setenv("CODE_HELPER_SEARCH_INDEXES", json.dumps(indexes))

        result = code_helper_get(config)

        assert len(result) == 2
        calls = mock_provider.call_args_list
        assert calls[0].kwargs["index_name"] == "idx1"
        assert calls[0].kwargs["semantic_config"] is None
        assert calls[1].kwargs["index_name"] == "idx2"
        assert calls[1].kwargs["semantic_config"] == "sem2"

    @patch("agents._base.integrations.search.AzureAISearchContextProvider")
    @patch("agents._base.client.get_credential")
    def test_single_plus_multi_are_additive(self, mock_cred, mock_provider, config, monkeypatch):
        """Should combine single-index and multi-index providers."""
        mock_cred.return_value = MagicMock()
        monkeypatch.setenv("CODE_HELPER_SEARCH_ENDPOINT", "https://primary.search.windows.net")
        monkeypatch.setenv("CODE_HELPER_SEARCH_INDEX_NAME", "main-idx")
        indexes = [{"endpoint": "https://s2.search.windows.net", "index_name": "extra-idx"}]
        monkeypatch.setenv("CODE_HELPER_SEARCH_INDEXES", json.dumps(indexes))

        result = code_helper_get(config)

        assert len(result) == 2
        calls = mock_provider.call_args_list
        assert calls[0].kwargs["index_name"] == "main-idx"
        assert calls[1].kwargs["index_name"] == "extra-idx"

    @patch("agents._base.integrations.search.AzureAISearchContextProvider")
    @patch("agents._base.client.get_credential")
    def test_invalid_json_returns_empty(self, mock_cred, mock_provider, config, monkeypatch):
        """Should return empty list when JSON is invalid (not defer to base)."""
        mock_cred.return_value = MagicMock()
        monkeypatch.delenv("CODE_HELPER_SEARCH_ENDPOINT", raising=False)
        monkeypatch.delenv("CODE_HELPER_SEARCH_INDEX_NAME", raising=False)
        monkeypatch.setenv("CODE_HELPER_SEARCH_INDEXES", "not-json")

        result = code_helper_get(config)

        assert result == []
        mock_provider.assert_not_called()


class TestDocAssistantKnowledge:
    """Tests for doc_assistant knowledge.py."""

    def test_returns_none_when_no_env_vars(self, config, monkeypatch):
        """Should return None (defer to base) when agent env vars not set."""
        monkeypatch.delenv("DOC_ASSISTANT_SEARCH_ENDPOINT", raising=False)
        monkeypatch.delenv("DOC_ASSISTANT_SEARCH_INDEX_NAME", raising=False)
        monkeypatch.delenv("DOC_ASSISTANT_SEARCH_INDEXES", raising=False)
        assert doc_assistant_get(config) is None

    @patch("agents._base.integrations.search.AzureAISearchContextProvider")
    @patch("agents._base.client.get_credential")
    def test_creates_provider_when_configured(self, mock_cred, mock_provider, config, monkeypatch):
        """Should create a provider when both env vars are set."""
        mock_cred.return_value = MagicMock()
        monkeypatch.setenv("DOC_ASSISTANT_SEARCH_ENDPOINT", "https://docs.search.windows.net")
        monkeypatch.setenv("DOC_ASSISTANT_SEARCH_INDEX_NAME", "docs-index")

        result = doc_assistant_get(config)

        assert len(result) == 1
        mock_provider.assert_called_once_with(
            endpoint="https://docs.search.windows.net",
            index_name="docs-index",
            semantic_config=None,
            credential=mock_cred.return_value,
        )

    @patch("agents._base.integrations.search.AzureAISearchContextProvider")
    @patch("agents._base.client.get_credential")
    def test_reads_doc_assistant_prefixed_env_vars(self, mock_cred, mock_provider, config, monkeypatch):
        """Should read DOC_ASSISTANT_ prefixed env vars, not CODE_HELPER_."""
        mock_cred.return_value = MagicMock()
        monkeypatch.setenv("DOC_ASSISTANT_SEARCH_ENDPOINT", "https://docs.search.windows.net")
        monkeypatch.setenv("DOC_ASSISTANT_SEARCH_INDEX_NAME", "docs-idx")
        monkeypatch.setenv("DOC_ASSISTANT_SEARCH_SEMANTIC_CONFIG", "doc-sem")
        # These should NOT be picked up by doc_assistant
        monkeypatch.setenv("CODE_HELPER_SEARCH_ENDPOINT", "https://wrong.search.windows.net")

        doc_assistant_get(config)

        assert mock_provider.call_args.kwargs["endpoint"] == "https://docs.search.windows.net"
        assert mock_provider.call_args.kwargs["semantic_config"] == "doc-sem"

    @patch("agents._base.integrations.search.AzureAISearchContextProvider")
    @patch("agents._base.client.get_credential")
    def test_multi_index_from_json(self, mock_cred, mock_provider, config, monkeypatch):
        """Should create providers from JSON array env var."""
        mock_cred.return_value = MagicMock()
        monkeypatch.delenv("DOC_ASSISTANT_SEARCH_ENDPOINT", raising=False)
        monkeypatch.delenv("DOC_ASSISTANT_SEARCH_INDEX_NAME", raising=False)
        indexes = [
            {"endpoint": "https://s1.search.windows.net", "index_name": "docs1"},
            {"endpoint": "https://s2.search.windows.net", "index_name": "docs2"},
        ]
        monkeypatch.setenv("DOC_ASSISTANT_SEARCH_INDEXES", json.dumps(indexes))

        result = doc_assistant_get(config)

        assert len(result) == 2
        calls = mock_provider.call_args_list
        assert calls[0].kwargs["index_name"] == "docs1"
        assert calls[1].kwargs["index_name"] == "docs2"
