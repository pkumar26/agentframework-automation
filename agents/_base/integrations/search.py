"""Azure AI Search context provider for RAG-grounded agents.

Queries an Azure AI Search index before each model invocation and injects
the top results as context so the agent can ground its answers on your data.
Uses DefaultAzureCredential — works locally (az login) and in Container Apps
(managed identity).
"""

import logging
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from agent_framework import (
    BaseContextProvider,
    SessionContext,
    SupportsAgentRun,
    AgentSession,
)

logger = logging.getLogger(__name__)


class AzureAISearchContextProvider(BaseContextProvider):
    """Injects Azure AI Search results into agent context before each turn."""

    def __init__(
        self,
        *,
        endpoint: str,
        index_name: str,
        top_k: int = 5,
        semantic_config: str | None = None,
        credential: DefaultAzureCredential | None = None,
        audience: str | None = None,
        connection_verify: bool = True,
    ):
        super().__init__(source_id="azure-ai-search")
        kwargs: dict[str, Any] = {}
        if audience:
            kwargs["audience"] = audience
        if not connection_verify:
            kwargs["connection_verify"] = False
        self._client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=credential or DefaultAzureCredential(),
            **kwargs,
        )
        self._top_k = top_k
        self._index_name = index_name
        self._semantic_config = semantic_config

    async def before_run(
        self,
        *,
        agent: SupportsAgentRun,
        session: AgentSession,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        """Search the index with the latest user message and inject results."""
        query = self._extract_query(context)
        if not query:
            return

        try:
            search_kwargs: dict[str, Any] = {
                "search_text": query,
                "top": self._top_k,
            }
            if self._semantic_config:
                search_kwargs["query_type"] = "semantic"
                search_kwargs["semantic_configuration_name"] = (
                    self._semantic_config
                )
            results = self._client.search(**search_kwargs)
            snippets = []
            for doc in results:
                # Try common content field names used by Azure AI Search indexes
                text = (
                    doc.get("content")
                    or doc.get("chunk")
                    or doc.get("snippet")
                    or ""
                )
                if not text:
                    for k, v in doc.items():
                        if k.startswith("@search.") or k.endswith("_vector"):
                            continue
                        if isinstance(v, str) and len(v) > 50:
                            text = v
                            break
                if text:
                    title = (
                        doc.get("title")
                        or doc.get("doc_url", "").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
                        or ""
                    )
                    prefix = f"[{title}] " if title else ""
                    snippets.append(f"{prefix}{text}")

            if snippets:
                grounding = (
                    "IMPORTANT: Answer ONLY based on the following "
                    "search results from the knowledge base. "
                    "Do NOT use prior knowledge or information from "
                    "the internet. If the search results do not "
                    "contain enough information to answer, say so "
                    "explicitly. Cite the source title for each "
                    "fact you reference.\n\n"
                    + "\n---\n".join(snippets)
                )
                context.extend_instructions(self.source_id, grounding)
                logger.info(
                    "Injected %d search results from index '%s'",
                    len(snippets),
                    self._index_name,
                )
            else:
                logger.info(
                    "No search results from index '%s' for query: %s",
                    self._index_name,
                    query[:100],
                )
        except Exception:
            logger.warning(
                "Azure AI Search query failed for index '%s'",
                self._index_name,
                exc_info=True,
            )

    @staticmethod
    def _extract_query(context: SessionContext) -> str | None:
        """Get the text of the most recent user input message."""
        if not context.input_messages:
            return None
        for msg in reversed(context.input_messages):
            if getattr(msg, "role", None) == "user":
                text = getattr(msg, "text", None) or str(msg)
                return text[:500]
        return None
