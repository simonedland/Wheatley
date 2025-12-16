"""Main MCP agent server for SpotifyAgent and GoogleCalendarAgent."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

import uvicorn
import yaml
from colorama import Fore, Style, init as colorama_init
from fastmcp import FastMCP
from agent_framework import MCPStreamableHTTPTool as Tool
from agent_framework.openai import OpenAIResponsesClient as OpenAI


APP_NAME = "Agents_MCP"
CONFIG_PATH = Path(__file__).parent / ".." / "config" / "config.yaml"
SPOTIFY_MCP_URL = os.getenv("SPOTIFY_MCP_URL", "http://localhost:8766/mcp")
CALENDAR_MCP_URL = os.getenv("CALENDAR_MCP_URL", "http://localhost:8767/mcp")

colorama_init(autoreset=True)
logger = logging.getLogger(f"{APP_NAME}.tools")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter("%(message)s"))
logger.handlers[:] = [handler]
logger.propagate = False

def _require(cfg: Dict[str, Any], path: list[str]) -> Any:
    """Return nested config value or raise a clear error if missing."""
    cur: Any = cfg
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            joined = "/".join(path)
            raise KeyError(f"Missing required config key: {joined}")
        cur = cur[key]
    return cur


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    """Load config/config.yaml and require all referenced values."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)

    if not isinstance(loaded, dict):
        raise ValueError("Config file must contain a YAML mapping")

    _require(loaded, ["secrets", "openai_api_key"])
    _require(loaded, ["llm", "model"])

    return loaded


config = load_config()
openai_key = _require(config, ["secrets", "openai_api_key"])
llm_model = _require(config, ["llm", "model"])
os.environ["OPENAI_API_KEY"] = openai_key
os.environ["OPENAI_RESPONSES_MODEL_ID"] = llm_model


mcp = FastMCP(name=APP_NAME)
_openai = OpenAI()


spotify_agent = _openai.create_agent(
    name="SpotifyAgent",
    description="Answer questions about music and control playback by calling external Spotify tools (via MCP)."
)

calendar_agent = _openai.create_agent(
    name="GoogleCalendarAgent",
    description="Manages calendar events and schedules."
)


async def _run_agent_text(agent_obj, query: str, **kwargs) -> str:
    """Run an agent and return the text response."""
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
