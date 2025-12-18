"""Main MCP agent server for SpotifyAgent and GoogleCalendarAgent."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

import uvicorn  # type: ignore[import-not-found]
import yaml
from colorama import Fore, Style, init as colorama_init  # type: ignore[import-untyped]
from fastmcp import FastMCP  # type: ignore[import-not-found]
from agent_framework import MCPStreamableHTTPTool as Tool  # type: ignore[import-not-found]
from agent_framework.openai import OpenAIResponsesClient as OpenAI  # type: ignore[import-not-found]

# Add parent directory to path to allow importing helper
sys.path.append(str(Path(__file__).parent.parent))
from helper.config import load_config

APP_NAME = "Agents_MCP"
SPOTIFY_MCP_URL = os.getenv("SPOTIFY_MCP_URL", "http://localhost:8766/mcp")
CALENDAR_MCP_URL = os.getenv("CALENDAR_MCP_URL", "http://localhost:8767/mcp")

colorama_init(autoreset=True)
logger = logging.getLogger(f"{APP_NAME}.tools")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter("%(message)s"))
logger.handlers[:] = [handler]
logger.propagate = False


config = load_config()
openai_key = config["secrets"]["openai_api_key"]
llm_model = config["llm"]["model"]
max_tokens = config["llm"].get("max_tokens", 1000)
os.environ["OPENAI_API_KEY"] = openai_key
os.environ["OPENAI_RESPONSES_MODEL_ID"] = llm_model


mcp = FastMCP(name=APP_NAME)
_openai = OpenAI()


spotify_agent = _openai.create_agent(
    name="SpotifyAgent",
    description="Answer questions about music and control playback by calling external Spotify tools (via MCP).",
)

calendar_agent = _openai.create_agent(
    name="GoogleCalendarAgent", description="Manages calendar events and schedules."
)


async def _run_agent_text(agent_obj, query: str, **kwargs) -> str:
    """Run an agent and return the text response."""
    # Ensure max_tokens is passed if not already in kwargs
    if "max_tokens" not in kwargs:
        kwargs["max_tokens"] = max_tokens
    
    resp = agent_obj.run(query, **kwargs)
    if hasattr(resp, "__await__"):
        resp = await resp
    return getattr(resp, "text", str(resp))


@mcp.tool(name="SpotifyAgent", description="Controls Spotify music playback.")
async def spotify_agent_tool(query: str) -> str:
    """Run the SpotifyAgent and return the response."""
    logger.info("%sSpotifyAgent%s query=%s", Fore.GREEN, Style.RESET_ALL, query)
    async with Tool(
        name="spotify_mcp",
        url=SPOTIFY_MCP_URL,
        request_timeout=60,
    ) as spotify_tools:
        return await _run_agent_text(spotify_agent, query, tools=spotify_tools)


@mcp.tool(name="GoogleCalendarAgent", description="Manages Google Calendar events.")
async def calendar_agent_tool(query: str) -> str:
    """Run the GoogleCalendarAgent and return the response."""
    logger.info("%sGoogleCalendarAgent%s query=%s", Fore.GREEN, Style.RESET_ALL, query)
    async with Tool(
        name="calendar_mcp",
        url=CALENDAR_MCP_URL,
        request_timeout=60,
    ) as calendar_tools:
        return await _run_agent_text(calendar_agent, query, tools=calendar_tools)


app = mcp.http_app(path="/mcp", transport="http")
server = mcp


def main() -> None:
    """Run the FastMCP server."""
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8765,
        log_level="info",
        access_log=False,
        ws="wsproto",
    )


if __name__ == "__main__":
    main()
