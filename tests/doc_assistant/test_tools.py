"""Unit tests for doc-assistant agent tools."""

import pytest

pytestmark = pytest.mark.doc_assistant


class TestDocAssistantTools:
    """Tests for the doc-assistant tools module."""

    def test_tools_list_is_empty(self):
        """Doc-assistant has no tools; TOOLS should be empty."""
        from agents.doc_assistant.tools import TOOLS

        assert TOOLS == []
