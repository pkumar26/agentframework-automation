"""Shared tool utilities for all agents.

Microsoft Agent Framework auto-wraps plain Python functions as tools
when passed to an agent's `tools` parameter. Use the @tool decorator
for explicit control over name, description, or schema.

Usage:
    from agents._base.tools import tool

    @tool
    def my_tool(param: str) -> str:
        \"\"\"Tool description.\"\"\"
        return f"Result: {param}"
"""

from agent_framework import tool

__all__ = ["tool"]
