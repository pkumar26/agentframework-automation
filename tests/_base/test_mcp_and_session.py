"""Unit tests for _build_mcp_tools and agent_session in agent_factory."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents._base.agent_factory import _build_mcp_tools, agent_session
from agents._base.config import MCPServerConfig


# ---------------------------------------------------------------------------
# _build_mcp_tools
# ---------------------------------------------------------------------------

@pytest.fixture
def base_config(tmp_path):
    """Config for MCP tests with a real instructions file."""
    instructions_file = tmp_path / "instructions.md"
    instructions_file.write_text("You are a helpful agent.")

    config = MagicMock()
    config.mcp_servers = None
    config.azure_ai_project_endpoint = "https://test.services.ai.azure.com/api/projects/test"
    config.agent_name = "test-agent"
    config.agent_deployment_name = "gpt-4o"
    config.agent_instructions_path = str(instructions_file)
    config.azure_ai_search_endpoint = None
    config.azure_ai_search_index_name = None
    config.azure_ai_search_semantic_config = None
    config.azure_ai_search_knowledge_base = None
    config.azure_ai_search_indexes = None
    config.azure_authority_host = None
    config.azure_openai_token_scope = None
    return config


class TestBuildMcpTools:
    """Tests for _build_mcp_tools."""

    def test_returns_empty_when_no_servers(self, base_config):
        """Should return empty list when mcp_servers is None."""
        result = _build_mcp_tools(base_config)
        assert result == []

    def test_returns_empty_for_empty_list(self, base_config):
        """Should return empty list when mcp_servers is empty."""
        base_config.mcp_servers = []
        result = _build_mcp_tools(base_config)
        assert result == []

    @patch("agent_framework.MCPStdioTool")
    def test_stdio_transport(self, mock_stdio_cls, base_config):
        """Should create MCPStdioTool for stdio transport."""
        base_config.mcp_servers = [
            MCPServerConfig(
                name="my-stdio",
                transport="stdio",
                command="python",
                args=["-m", "server"],
                env={"KEY": "val"},
                description="A stdio server",
            ),
        ]

        result = _build_mcp_tools(base_config)

        assert len(result) == 1
        mock_stdio_cls.assert_called_once_with(
            name="my-stdio",
            command="python",
            args=["-m", "server"],
            env={"KEY": "val"},
            description="A stdio server",
        )

    @patch("agent_framework.MCPStreamableHTTPTool")
    def test_http_transport(self, mock_http_cls, base_config):
        """Should create MCPStreamableHTTPTool for http transport."""
        base_config.mcp_servers = [
            MCPServerConfig(
                name="my-http",
                transport="http",
                url="https://mcp.example.com/api",
                description="An HTTP server",
            ),
        ]

        result = _build_mcp_tools(base_config)

        assert len(result) == 1
        mock_http_cls.assert_called_once_with(
            name="my-http",
            url="https://mcp.example.com/api",
            description="An HTTP server",
        )

    @patch("agent_framework.MCPWebsocketTool")
    def test_websocket_transport(self, mock_ws_cls, base_config):
        """Should create MCPWebsocketTool for websocket transport."""
        base_config.mcp_servers = [
            MCPServerConfig(
                name="my-ws",
                transport="websocket",
                url="wss://mcp.example.com/ws",
                description="A WS server",
            ),
        ]

        result = _build_mcp_tools(base_config)

        assert len(result) == 1
        mock_ws_cls.assert_called_once_with(
            name="my-ws",
            url="wss://mcp.example.com/ws",
            description="A WS server",
        )

    @patch("agent_framework.MCPStdioTool")
    def test_stdio_missing_command_skipped(self, mock_stdio_cls, base_config):
        """Should skip stdio server when command is missing."""
        base_config.mcp_servers = [
            MCPServerConfig(name="bad-stdio", transport="stdio"),
        ]

        result = _build_mcp_tools(base_config)

        assert result == []
        mock_stdio_cls.assert_not_called()

    @patch("agent_framework.MCPStreamableHTTPTool")
    def test_http_missing_url_skipped(self, mock_http_cls, base_config):
        """Should skip http server when url is missing."""
        base_config.mcp_servers = [
            MCPServerConfig(name="bad-http", transport="http"),
        ]

        result = _build_mcp_tools(base_config)

        assert result == []
        mock_http_cls.assert_not_called()

    @patch("agent_framework.MCPWebsocketTool")
    def test_websocket_missing_url_skipped(self, mock_ws_cls, base_config):
        """Should skip websocket server when url is missing."""
        base_config.mcp_servers = [
            MCPServerConfig(name="bad-ws", transport="websocket"),
        ]

        result = _build_mcp_tools(base_config)

        assert result == []
        mock_ws_cls.assert_not_called()

    def test_unknown_transport_skipped(self, base_config):
        """Should skip servers with unknown transport type."""
        server = MagicMock()
        server.name = "bad-transport"
        server.transport = "grpc"
        base_config.mcp_servers = [server]

        result = _build_mcp_tools(base_config)

        assert result == []

    @patch("agent_framework.MCPWebsocketTool")
    @patch("agent_framework.MCPStreamableHTTPTool")
    @patch("agent_framework.MCPStdioTool")
    def test_mixed_transports(self, mock_stdio, mock_http, mock_ws, base_config):
        """Should create the correct tool type for each transport."""
        base_config.mcp_servers = [
            MCPServerConfig(name="s1", transport="stdio", command="cmd"),
            MCPServerConfig(name="s2", transport="http", url="https://a.com"),
            MCPServerConfig(name="s3", transport="websocket", url="wss://b.com"),
        ]

        result = _build_mcp_tools(base_config)

        assert len(result) == 3
        mock_stdio.assert_called_once()
        mock_http.assert_called_once()
        mock_ws.assert_called_once()

    @patch("agent_framework.MCPStdioTool")
    def test_stdio_none_args_defaults_to_empty_list(self, mock_stdio_cls, base_config):
        """Should pass empty list for args when None."""
        base_config.mcp_servers = [
            MCPServerConfig(name="s", transport="stdio", command="cmd"),
        ]

        _build_mcp_tools(base_config)

        call_kwargs = mock_stdio_cls.call_args.kwargs
        assert call_kwargs["args"] == []


# ---------------------------------------------------------------------------
# agent_session
# ---------------------------------------------------------------------------

class TestAgentSession:
    """Tests for the agent_session async context manager."""

    @patch("agents._base.agent_factory._collect_context_providers", return_value=[])
    @patch("agents._base.agent_factory._collect_agent_tools", return_value=[])
    @patch("agents._base.agent_factory.get_chat_client")
    @patch("agents._base.agent_factory._build_mcp_tools")
    async def test_yields_agent_with_mcp_tools(
        self, mock_build, mock_client, mock_tools, mock_providers, base_config
    ):
        """Should connect MCP tools and yield assembled agent."""
        mcp_tool = AsyncMock()
        mcp_tool.name = "test-mcp"
        mock_build.return_value = [mcp_tool]

        mock_agent = MagicMock()
        mock_chat = MagicMock()
        mock_chat.as_agent.return_value = mock_agent
        mock_client.return_value = mock_chat

        async with agent_session(base_config) as agent:
            assert agent is mock_agent
            mcp_tool.__aenter__.assert_awaited_once()

        mcp_tool.__aexit__.assert_awaited_once_with(None, None, None)

    @patch("agents._base.agent_factory._collect_context_providers", return_value=[])
    @patch("agents._base.agent_factory._collect_agent_tools", return_value=[])
    @patch("agents._base.agent_factory.get_chat_client")
    @patch("agents._base.agent_factory._build_mcp_tools", return_value=[])
    async def test_no_mcp_servers_still_yields_agent(
        self, mock_build, mock_client, mock_tools, mock_providers, base_config
    ):
        """Should work without MCP servers."""
        mock_agent = MagicMock()
        mock_chat = MagicMock()
        mock_chat.as_agent.return_value = mock_agent
        mock_client.return_value = mock_chat

        async with agent_session(base_config) as agent:
            assert agent is mock_agent

    @patch("agents._base.agent_factory._collect_context_providers", return_value=[])
    @patch("agents._base.agent_factory._collect_agent_tools")
    @patch("agents._base.agent_factory.get_chat_client")
    @patch("agents._base.agent_factory._build_mcp_tools")
    async def test_combines_function_and_mcp_tools(
        self, mock_build, mock_client, mock_fn_tools, mock_providers, base_config
    ):
        """Should combine function tools and MCP tools in the agent."""
        fn_tool = MagicMock()
        mock_fn_tools.return_value = [fn_tool]

        mcp_tool = AsyncMock()
        mcp_tool.name = "mcp-1"
        mock_build.return_value = [mcp_tool]

        mock_chat = MagicMock()
        mock_chat.as_agent.return_value = MagicMock()
        mock_client.return_value = mock_chat

        async with agent_session(base_config):
            pass

        call_kwargs = mock_chat.as_agent.call_args.kwargs
        assert call_kwargs["tools"] == [fn_tool, mcp_tool]

    @patch("agents._base.agent_factory._collect_context_providers", return_value=[])
    @patch("agents._base.agent_factory._collect_agent_tools", return_value=[])
    @patch("agents._base.agent_factory.get_chat_client")
    @patch("agents._base.agent_factory._build_mcp_tools")
    async def test_disconnects_on_exception(
        self, mock_build, mock_client, mock_tools, mock_providers, base_config
    ):
        """Should disconnect MCP tools even if the body raises."""
        mcp_tool = AsyncMock()
        mcp_tool.name = "test-mcp"
        mock_build.return_value = [mcp_tool]

        mock_chat = MagicMock()
        mock_chat.as_agent.return_value = MagicMock()
        mock_client.return_value = mock_chat

        with pytest.raises(RuntimeError, match="boom"):
            async with agent_session(base_config):
                raise RuntimeError("boom")

        mcp_tool.__aexit__.assert_awaited_once()

    @patch("agents._base.agent_factory._collect_context_providers", return_value=[])
    @patch("agents._base.agent_factory._collect_agent_tools", return_value=[])
    @patch("agents._base.agent_factory.get_chat_client")
    @patch("agents._base.agent_factory._build_mcp_tools")
    async def test_disconnect_error_is_suppressed(
        self, mock_build, mock_client, mock_tools, mock_providers, base_config
    ):
        """Should not raise if MCP disconnect fails."""
        mcp_tool = AsyncMock()
        mcp_tool.name = "test-mcp"
        mcp_tool.__aexit__.side_effect = Exception("disconnect failed")
        mock_build.return_value = [mcp_tool]

        mock_chat = MagicMock()
        mock_chat.as_agent.return_value = MagicMock()
        mock_client.return_value = mock_chat

        async with agent_session(base_config):
            pass
        # Should not raise

    @patch("agents._base.agent_factory._collect_context_providers", return_value=[])
    @patch("agents._base.agent_factory._collect_agent_tools", return_value=[])
    @patch("agents._base.agent_factory.get_chat_client")
    @patch("agents._base.agent_factory._build_mcp_tools")
    async def test_disconnects_in_reverse_order(
        self, mock_build, mock_client, mock_tools, mock_providers, base_config
    ):
        """Should disconnect MCP tools in reverse connection order."""
        tool1 = AsyncMock()
        tool1.name = "mcp-1"
        tool2 = AsyncMock()
        tool2.name = "mcp-2"
        mock_build.return_value = [tool1, tool2]

        mock_chat = MagicMock()
        mock_chat.as_agent.return_value = MagicMock()
        mock_client.return_value = mock_chat

        disconnect_order = []
        tool1.__aexit__.side_effect = lambda *a: disconnect_order.append("mcp-1")
        tool2.__aexit__.side_effect = lambda *a: disconnect_order.append("mcp-2")

        async with agent_session(base_config):
            pass

        assert disconnect_order == ["mcp-2", "mcp-1"]

    @patch("agents._base.agent_factory._collect_context_providers", return_value=[])
    @patch("agents._base.agent_factory._collect_agent_tools", return_value=[])
    @patch("agents._base.agent_factory.get_chat_client")
    @patch("agents._base.agent_factory._build_mcp_tools")
    async def test_partial_connect_disconnects_only_connected(
        self, mock_build, mock_client, mock_tools, mock_providers, base_config
    ):
        """Should only disconnect tools that were successfully connected."""
        tool1 = AsyncMock()
        tool1.name = "mcp-1"
        tool2 = AsyncMock()
        tool2.name = "mcp-2"
        tool2.__aenter__.side_effect = Exception("connect failed")
        mock_build.return_value = [tool1, tool2]

        with pytest.raises(Exception, match="connect failed"):
            async with agent_session(base_config):
                pass

        tool1.__aexit__.assert_awaited_once()
        tool2.__aexit__.assert_not_awaited()
