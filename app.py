"""Hosting adapter for Azure Container Apps deployment.

Serves a chat web UI on ``/`` and the Foundry-compatible ``/responses``
API on port 8088.  The ``/api/chat`` endpoint powers the browser UI.

Usage:
    AGENT_NAME=code-helper python app.py
"""

import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env before any Azure SDK imports so AZURE_AUTHORITY_HOST etc. are set
load_dotenv(Path(__file__).parent / ".env")

from azure.ai.agentserver.agentframework import from_agent_framework
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from agents.registry import REGISTRY

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

# ---------------------------------------------------------------------------
# Build agent once at startup
# ---------------------------------------------------------------------------
agent_name = os.environ.get("AGENT_NAME", "code-helper")
entry = REGISTRY.get_agent(agent_name)
config = entry.config_class()
agent = entry.factory(config)
logger.info("Agent assembled: %s", agent_name)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

async def index(request):
    """Serve the chat UI."""
    html = (STATIC_DIR / "index.html").read_text()
    return HTMLResponse(html)


async def api_info(request):
    """Return agent metadata for the UI."""
    return JSONResponse({"agent_name": agent_name})


async def api_chat(request):
    """Handle chat messages from the web UI."""
    try:
        body = await request.json()
        message = body.get("message", "").strip()
        if not message:
            return JSONResponse({"error": "Empty message"}, status_code=400)

        result = await agent.run(message)
        text = result.text if hasattr(result, "text") else str(result)
        return JSONResponse({"response": text})
    except Exception as e:
        logger.exception("Chat error")
        return JSONResponse({"error": str(e)}, status_code=500)


routes = [
    Route("/", index),
    Route("/api/info", api_info),
    Route("/api/chat", api_chat, methods=["POST"]),
    Mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static"),
]

app = Starlette(routes=routes)


# ---------------------------------------------------------------------------
# Main — run both the UI server and the Foundry /responses server
# ---------------------------------------------------------------------------

def main():
    import uvicorn

    port = int(os.environ.get("PORT", "8088"))
    logger.info("Starting agent '%s' on port %d (UI + API)", agent_name, port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
