#!/usr/bin/env python3
"""CLI script for running agents locally.

Supports interactive (multi-turn) and single-prompt modes.
"""

import argparse
import asyncio
import logging
import sys

from agents.registry import REGISTRY


async def interactive_loop(agent_name: str) -> None:
    """Run an interactive conversation loop with an agent."""
    entry = REGISTRY.get_agent(agent_name)
    config = entry.config_class()
    agent = entry.factory(config)

    print(f"Agent '{agent_name}' ready. Type 'quit' to exit.\n")

    while True:
        try:
            prompt = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if prompt.lower() in ("quit", "exit", "bye"):
            print("Goodbye!")
            break

        if not prompt:
            continue

        result = await agent.run(prompt)
        text = result.text if hasattr(result, "text") else result
        print(f"Agent: {text}\n")


def main() -> int:
    """Run an agent via CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Run an agent locally",
        prog="run_agent.py",
    )
    parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="Agent name from registry (e.g., code-helper)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Single prompt (non-interactive mode)",
    )

    args = parser.parse_args()

    try:
        entry = REGISTRY.get_agent(args.name)
    except KeyError as e:
        print(f"[run] Error: {e}", file=sys.stderr)
        return 1

    if args.prompt:
        config = entry.config_class()
        agent = entry.factory(config)
        result = asyncio.run(agent.run(args.prompt))
        print(result.text if hasattr(result, "text") else result)
    else:
        asyncio.run(interactive_loop(args.name))

    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.exit(main())
