"""Unit tests for AzureAISearchContextProvider."""

from unittest.mock import MagicMock, patch

import pytest

from agents._base.integrations.search import AzureAISearchContextProvider


class TestSearchProviderInit:
    """Tests for AzureAISearchContextProvider constructor."""

    @patch("agents._base.integrations.search.SearchClient")
    def test_creates_search_client_commercial(self, mock_search_cls):
        """Should create SearchClient without audience for commercial endpoints."""
        cred = MagicMock()
        AzureAISearchContextProvider(
            endpoint="https://my-search.search.windows.net",
            index_name="my-index",
            credential=cred,
        )
        mock_search_cls.assert_called_once_with(
            endpoint="https://my-search.search.windows.net",
            index_name="my-index",
            credential=cred,
        )

    @patch("agents._base.integrations.search.SearchClient")
    def test_creates_search_client_gov_with_audience(self, mock_search_cls):
        """Should set gov audience for .azure.us endpoints."""
        cred = MagicMock()
        AzureAISearchContextProvider(
            endpoint="https://my-search.search.azure.us",
            index_name="my-index",
            credential=cred,
        )
        mock_search_cls.assert_called_once_with(
            endpoint="https://my-search.search.azure.us",
            index_name="my-index",
            credential=cred,
            audience="https://search.azure.us",
        )

    @patch("agents._base.integrations.search.SearchClient")
    def test_stores_semantic_config(self, mock_search_cls):
        """Should store semantic_config for use in search queries."""
        cred = MagicMock()
        provider = AzureAISearchContextProvider(
            endpoint="https://my-search.search.windows.net",
            index_name="my-index",
            credential=cred,
            semantic_config="my-semantic",
        )
        assert provider._semantic_config == "my-semantic"

    @patch("agents._base.integrations.search.SearchClient")
    def test_default_top_k(self, mock_search_cls):
        """Should default to top_k=5."""
        cred = MagicMock()
        provider = AzureAISearchContextProvider(
            endpoint="https://my-search.search.windows.net",
            index_name="my-index",
            credential=cred,
        )
        assert provider._top_k == 5

    @patch("agents._base.integrations.search.SearchClient")
    def test_custom_top_k(self, mock_search_cls):
        """Should accept custom top_k."""
        cred = MagicMock()
        provider = AzureAISearchContextProvider(
            endpoint="https://my-search.search.windows.net",
            index_name="my-index",
            credential=cred,
            top_k=10,
        )
        assert provider._top_k == 10


class TestExtractQuery:
    """Tests for the _extract_query static method."""

    def test_returns_none_for_empty_messages(self):
        """Should return None when no input messages."""
        context = MagicMock()
        context.input_messages = []
        assert AzureAISearchContextProvider._extract_query(context) is None

    def test_returns_none_for_no_user_messages(self):
        """Should return None when no user-role messages exist."""
        msg = MagicMock()
        msg.role = "assistant"
        context = MagicMock()
        context.input_messages = [msg]
        assert AzureAISearchContextProvider._extract_query(context) is None

    def test_extracts_latest_user_message(self):
        """Should return text from the most recent user message."""
        msg1 = MagicMock()
        msg1.role = "user"
        msg1.text = "first question"
        msg2 = MagicMock()
        msg2.role = "user"
        msg2.text = "second question"
        context = MagicMock()
        context.input_messages = [msg1, msg2]
        assert AzureAISearchContextProvider._extract_query(context) == "second question"

    def test_truncates_long_queries(self):
        """Should truncate queries longer than 500 chars."""
        msg = MagicMock()
        msg.role = "user"
        msg.text = "x" * 600
        context = MagicMock()
        context.input_messages = [msg]
        result = AzureAISearchContextProvider._extract_query(context)
        assert len(result) == 500

    def test_falls_back_to_str_when_no_text_attr(self):
        """Should use str(msg) when .text is None."""
        msg = MagicMock()
        msg.role = "user"
        msg.text = None
        msg.__str__ = lambda self: "fallback text"
        context = MagicMock()
        context.input_messages = [msg]
        result = AzureAISearchContextProvider._extract_query(context)
        assert "fallback" in result


class TestBeforeRun:
    """Tests for the before_run hook."""

    @pytest.fixture
    def provider(self):
        with patch("agents._base.integrations.search.SearchClient"):
            p = AzureAISearchContextProvider(
                endpoint="https://my-search.search.windows.net",
                index_name="test-index",
                credential=MagicMock(),
            )
        return p

    @pytest.fixture
    def run_args(self):
        """Standard args for before_run."""
        agent = MagicMock()
        session = MagicMock()
        context = MagicMock()
        state = {}
        return {"agent": agent, "session": session, "context": context, "state": state}

    async def test_injects_search_results(self, provider, run_args):
        """Should inject search snippets via extend_instructions."""
        msg = MagicMock()
        msg.role = "user"
        msg.text = "what is probation?"
        run_args["context"].input_messages = [msg]

        provider._client.search.return_value = [
            {"content": "Probation is a period of supervision.", "title": "Overview"},
        ]

        await provider.before_run(**run_args)

        run_args["context"].extend_instructions.assert_called_once()
        call_args = run_args["context"].extend_instructions.call_args
        assert call_args[0][0] == "azure-ai-search"
        injected = call_args[0][1]
        assert "Probation is a period of supervision." in injected
        assert "[Overview]" in injected
        assert "Answer ONLY based on" in injected

    async def test_uses_chunk_field(self, provider, run_args):
        """Should extract content from 'chunk' field."""
        msg = MagicMock()
        msg.role = "user"
        msg.text = "query"
        run_args["context"].input_messages = [msg]

        provider._client.search.return_value = [
            {"chunk": "Chunk content here.", "title": "Doc1"},
        ]

        await provider.before_run(**run_args)

        injected = run_args["context"].extend_instructions.call_args[0][1]
        assert "Chunk content here." in injected

    async def test_uses_snippet_field(self, provider, run_args):
        """Should extract content from 'snippet' field."""
        msg = MagicMock()
        msg.role = "user"
        msg.text = "query"
        run_args["context"].input_messages = [msg]

        provider._client.search.return_value = [
            {"snippet": "Snippet content.", "title": "Doc1"},
        ]

        await provider.before_run(**run_args)

        injected = run_args["context"].extend_instructions.call_args[0][1]
        assert "Snippet content." in injected

    async def test_falls_back_to_long_string_field(self, provider, run_args):
        """Should use first long string field when standard fields missing."""
        msg = MagicMock()
        msg.role = "user"
        msg.text = "query"
        run_args["context"].input_messages = [msg]

        provider._client.search.return_value = [
            {"custom_field": "A" * 60, "@search.score": 0.9},
        ]

        await provider.before_run(**run_args)

        injected = run_args["context"].extend_instructions.call_args[0][1]
        assert "A" * 60 in injected

    async def test_skips_vector_and_search_metadata_fields(self, provider, run_args):
        """Should skip @search.* and *_vector fields in fallback."""
        msg = MagicMock()
        msg.role = "user"
        msg.text = "query"
        run_args["context"].input_messages = [msg]

        provider._client.search.return_value = [
            {
                "@search.score": 0.95,
                "content_vector": "B" * 100,
                "actual_content": "C" * 60,
            },
        ]

        await provider.before_run(**run_args)

        injected = run_args["context"].extend_instructions.call_args[0][1]
        assert "C" * 60 in injected
        assert "B" * 100 not in injected

    async def test_extracts_title_from_doc_url(self, provider, run_args):
        """Should extract filename from doc_url for citation."""
        msg = MagicMock()
        msg.role = "user"
        msg.text = "query"
        run_args["context"].input_messages = [msg]

        provider._client.search.return_value = [
            {"content": "Some text.", "doc_url": "https://example.com/docs/guide.pdf"},
        ]

        await provider.before_run(**run_args)

        injected = run_args["context"].extend_instructions.call_args[0][1]
        assert "[guide.pdf]" in injected

    async def test_no_results_does_not_inject(self, provider, run_args):
        """Should not call extend_instructions when no results."""
        msg = MagicMock()
        msg.role = "user"
        msg.text = "query"
        run_args["context"].input_messages = [msg]

        provider._client.search.return_value = []

        await provider.before_run(**run_args)

        run_args["context"].extend_instructions.assert_not_called()

    async def test_no_query_returns_early(self, provider, run_args):
        """Should return early when no user message found."""
        run_args["context"].input_messages = []

        await provider.before_run(**run_args)

        provider._client.search.assert_not_called()

    async def test_search_exception_is_caught(self, provider, run_args):
        """Should catch and log exceptions without re-raising."""
        msg = MagicMock()
        msg.role = "user"
        msg.text = "query"
        run_args["context"].input_messages = [msg]

        provider._client.search.side_effect = Exception("Connection refused")

        await provider.before_run(**run_args)

        run_args["context"].extend_instructions.assert_not_called()

    async def test_uses_semantic_config_when_set(self, provider, run_args):
        """Should pass semantic query params when semantic_config is set."""
        provider._semantic_config = "my-semantic"
        msg = MagicMock()
        msg.role = "user"
        msg.text = "query"
        run_args["context"].input_messages = [msg]

        provider._client.search.return_value = [
            {"content": "Result.", "title": "Doc"},
        ]

        await provider.before_run(**run_args)

        search_kwargs = provider._client.search.call_args[1]
        assert search_kwargs["query_type"] == "semantic"
        assert search_kwargs["semantic_configuration_name"] == "my-semantic"

    async def test_keyword_search_when_no_semantic_config(self, provider, run_args):
        """Should not pass semantic params when semantic_config is None."""
        msg = MagicMock()
        msg.role = "user"
        msg.text = "query"
        run_args["context"].input_messages = [msg]

        provider._client.search.return_value = [
            {"content": "Result.", "title": "Doc"},
        ]

        await provider.before_run(**run_args)

        search_kwargs = provider._client.search.call_args[1]
        assert "query_type" not in search_kwargs
        assert "semantic_configuration_name" not in search_kwargs
