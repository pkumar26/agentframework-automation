"""Sample tool for the probation q a agent agent — a greeting function."""

from typing import Annotated

from pydantic import Field


def greet_user(
    name: Annotated[str, Field(description="The name of the user to greet.")],
) -> str:
    """Greet a user by name."""
    return f"Hello, {name}! I'm the Probation Q A Agent agent. How can I assist you today?"


# Exported tools list — consumed by agent_factory.
# Agent Framework auto-wraps plain functions as function tools.
TOOLS = [greet_user]
