"""Unit tests for _collect_context_providers and agent-specific discovery."""

import types
from unittest.mock import MagicMock, patch

import pytest

from agents._base.agent_factory import (
    _build_base_context_providers,
    _collect_context_providers,
    _discover_agent_context_providers,
)
from agents._base.config import SearchIndexConfig


@pytest.fixture
def base_config():
    """Config with no search settings."""
    config = MagicMock()
    config.azure_ai_search_endpoint = None
    config.azure_ai_search_index_name = None
    config.azure_ai_search_semantic_config = None
    config.azure_ai_search_knowledge_base = None
    config.azure_ai_search_indexes = None
    config.azure_authority_host = None
    config.azure_ai_project_endpoint = "https://test.services.ai.azure.com/api/projects/test"
    return config


class TestCollectContextProviders:
    """Tests for _collect_context_providers."""

    @patch("agents._base.client.get_credential")
    def test_returns_empty_when_no_search_config(self, mock_cred, base_config):
        """Should return empty list when no search config is set."""
        mock_cred.return_value = MagicMock()
        result = _collect_context_providers(base_config)
        assert result == []

    @patch("agents._base.agent_factory.AzureAISearchContextProvider")
    @patch("agents._base.client.get_credential")
    def test_single_index_creates_one_provider(self, mock_cred, mock_provider_cls, base_config):
        """Should create one provider for explicit endpoint + index."""
        mock_cred.return_value = MagicMock()
        base_config.azure_ai_search_endpoint = "https://search.search.windows.net"
        base_config.azure_ai_search_index_name = "my-index"
        base_config.azure_ai_search_semantic_config = "my-semantic"

        result = _collect_context_providers(base_config)

        assert len(result) == 1
        mock_provider_cls.assert_called_once_with(
            endpoint="https://search.search.windows.net",
            index_name="my-index",
            semantic_config="my-semantic",
            credential=mock_cred.return_value,
        )

    @patch("agents._base.agent_factory.AzureAISearchContextProvider")
    @patch("agents._base.client.get_credential")
    def test_multi_index_creates_providers_per_entry(self, mock_cred, mock_provider_cls, base_config):
        """Should create one provider per entry in azure_ai_search_indexes."""
        mock_cred.return_value = MagicMock()
        base_config.azure_ai_search_indexes = [
            SearchIndexConfig(endpoint="https://s1.search.windows.net", index_name="idx1"),
            SearchIndexConfig(endpoint="https://s2.search.windows.net", index_name="idx2", semantic_config="sem"),
        ]

        result = _collect_context_providers(base_config)

        assert len(result) == 2
        calls = mock_provider_cls.call_args_list
        assert calls[0].kwargs["index_name"] == "idx1"
        assert calls[0].kwargs["semantic_config"] is None
        assert calls[1].kwargs["index_name"] == "idx2"
        assert calls[1].kwargs["semantic_config"] == "sem"

    @patch("agents._base.agent_factory.AzureAISearchContextProvider")
    @patch("agents._base.client.get_credential")
    def test_single_plus_multi_are_additive(self, mock_cred, mock_provider_cls, base_config):
        """Should combine single-index and multi-index providers."""
        mock_cred.return_value = MagicMock()
        base_config.azure_ai_search_endpoint = "https://primary.search.windows.net"
        base_config.azure_ai_search_index_name = "main"
        base_config.azure_ai_search_indexes = [
            SearchIndexConfig(endpoint="https://secondary.search.windows.net", index_name="extra"),
        ]

        result = _collect_context_providers(base_config)

        assert len(result) == 2

    @patch("agents._base.client.get_credential")
    def test_passes_authority_to_get_credential(self, mock_cred, base_config):
        """Should pass azure_authority_host to get_credential."""
        mock_cred.return_value = MagicMock()
        base_config.azure_authority_host = "https://login.microsoftonline.us"

        _collect_context_providers(base_config)

        mock_cred.assert_called_with(authority="https://login.microsoftonline.us")

    @patch("agents._base.agent_factory._resolve_knowledge_base")
    @patch("agents._base.agent_factory.AzureAISearchContextProvider")
    @patch("agents._base.client.get_credential")
    def test_knowledge_base_resolves_endpoint(self, mock_cred, mock_provider_cls, mock_resolve, base_config):
        """Should resolve knowledge base name to endpoint + index via Foundry API."""
        mock_cred.return_value = MagicMock()
        mock_resolve.return_value = ("https://resolved.search.windows.net", "resolved-index")
        base_config.azure_ai_search_knowledge_base = "my-kb"

        result = _collect_context_providers(base_config)

        assert len(result) == 1
        mock_resolve.assert_called_once_with(
            project_endpoint=base_config.azure_ai_project_endpoint,
            knowledge_base_name="my-kb",
            authority=None,
        )
        mock_provider_cls.assert_called_once_with(
            endpoint="https://resolved.search.windows.net",
            index_name="resolved-index",
            semantic_config=None,
            credential=mock_cred.return_value,
        )

    @patch("agents._base.agent_factory._resolve_knowledge_base")
    @patch("agents._base.client.get_credential")
    def test_knowledge_base_failure_returns_empty(self, mock_cred, mock_resolve, base_config):
        """Should gracefully degrade when knowledge base resolution fails."""
        mock_cred.return_value = MagicMock()
        mock_resolve.side_effect = Exception("API error")
        base_config.azure_ai_search_knowledge_base = "bad-kb"

        result = _collect_context_providers(base_config)

        assert result == []

    @patch("agents._base.agent_factory.AzureAISearchContextProvider")
    @patch("agents._base.client.get_credential")
    def test_explicit_endpoint_skips_knowledge_base(self, mock_cred, mock_provider_cls, base_config):
        """Should not resolve knowledge base when explicit endpoint + index are set."""
        mock_cred.return_value = MagicMock()
        base_config.azure_ai_search_endpoint = "https://explicit.search.windows.net"
        base_config.azure_ai_search_index_name = "explicit-idx"
        base_config.azure_ai_search_knowledge_base = "should-be-ignored"

        with patch("agents._base.agent_factory._resolve_knowledge_base") as mock_resolve:
            result = _collect_context_providers(base_config)
            mock_resolve.assert_not_called()

        assert len(result) == 1


class TestDiscoverAgentContextProviders:
    """Tests for _discover_agent_context_providers."""

    def test_returns_none_when_no_module(self, base_config):
        """Should return None when the knowledge module doesn't exist."""
        base_config.agent_name = "nonexistent-agent"
        result = _discover_agent_context_providers(base_config)
        assert result is None

    def test_returns_none_when_no_function(self, base_config):
        """Should return None when module exists but lacks get_context_providers."""
        mod = types.ModuleType("agents.fake.integrations.knowledge")
        # Module has no get_context_providers function
        with patch("importlib.import_module", return_value=mod):
            base_config.agent_name = "fake"
            result = _discover_agent_context_providers(base_config)
        assert result is None

    def test_returns_none_when_function_returns_none(self, base_config):
        """Should return None when get_context_providers returns None (defer)."""
        mod = types.ModuleType("agents.fake.integrations.knowledge")
        mod.get_context_providers = lambda config: None
        with patch("importlib.import_module", return_value=mod):
            base_config.agent_name = "fake"
            result = _discover_agent_context_providers(base_config)
        assert result is None

    def test_returns_list_from_function(self, base_config):
        """Should return the list from get_context_providers."""
        provider = MagicMock()
        mod = types.ModuleType("agents.fake.integrations.knowledge")
        mod.get_context_providers = lambda config: [provider]
        with patch("importlib.import_module", return_value=mod):
            base_config.agent_name = "fake"
            result = _discover_agent_context_providers(base_config)
        assert result == [provider]

    def test_returns_empty_list_as_override(self, base_config):
        """Should return empty list (agent explicitly has no search)."""
        mod = types.ModuleType("agents.fake.integrations.knowledge")
        mod.get_context_providers = lambda config: []
        with patch("importlib.import_module", return_value=mod):
            base_config.agent_name = "fake"
            result = _discover_agent_context_providers(base_config)
        assert result == []

    def test_returns_none_for_non_list_return(self, base_config):
        """Should return None and warn when function returns non-list."""
        mod = types.ModuleType("agents.fake.integrations.knowledge")
        mod.get_context_providers = lambda config: "bad"
        with patch("importlib.import_module", return_value=mod):
            base_config.agent_name = "fake"
            result = _discover_agent_context_providers(base_config)
        assert result is None

    def test_derives_module_from_config_class(self):
        """Should use config class __module__ to derive knowledge module path."""
        provider = MagicMock()
        mod = types.ModuleType("agents.my_agent.integrations.knowledge")
        mod.get_context_providers = lambda config: [provider]

        config = MagicMock()
        type(config).__module__ = "agents.my_agent.config"

        with patch("importlib.import_module", return_value=mod) as mock_import:
            result = _discover_agent_context_providers(config)

        mock_import.assert_called_with("agents.my_agent.integrations.knowledge")
        assert result == [provider]


class TestCollectWithDiscovery:
    """Tests for _collect_context_providers with discovery integration."""

    @patch("agents._base.agent_factory._discover_agent_context_providers")
    def test_uses_agent_providers_when_returned(self, mock_discover, base_config):
        """Should use agent-specific providers and skip base config."""
        agent_provider = MagicMock()
        mock_discover.return_value = [agent_provider]

        result = _collect_context_providers(base_config)

        assert result == [agent_provider]

    @patch("agents._base.agent_factory._build_base_context_providers")
    @patch("agents._base.agent_factory._discover_agent_context_providers")
    def test_falls_back_to_base_when_discovery_returns_none(
        self, mock_discover, mock_base, base_config
    ):
        """Should fall back to base config when discovery returns None."""
        mock_discover.return_value = None
        base_provider = MagicMock()
        mock_base.return_value = [base_provider]

        result = _collect_context_providers(base_config)

        mock_base.assert_called_once_with(base_config)
        assert result == [base_provider]

    @patch("agents._base.agent_factory._discover_agent_context_providers")
    def test_empty_list_overrides_base(self, mock_discover, base_config):
        """Empty list from discovery should override base (no search)."""
        mock_discover.return_value = []
        base_config.azure_ai_search_endpoint = "https://should-be-skipped.search.windows.net"
        base_config.azure_ai_search_index_name = "skipped"

        result = _collect_context_providers(base_config)

        assert result == []
