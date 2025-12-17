"""MCP1: A FastMCP server exposing tools for the SpotifyAgent."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import uvicorn
from colorama import Fore, Style, init as colorama_init
from fastmcp import FastMCP


APP_NAME = "SpotifyAgent_tools"
DEFAULT_MODEL = "gpt-4"
CONFIG_PATH = Path(__file__).parent / "config" / "config.yaml"

colorama_init(autoreset=True)
logger = logging.getLogger(f"{APP_NAME}.tools")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter("%(message)s"))
logger.handlers[:] = [handler]
logger.propagate = False

mcp = FastMCP(name=APP_NAME)


@mcp.tool(name="play_music", description="Plays music on Spotify.")
def play_music(query: str) -> str:
    """Play music on Spotify."""
    logger.info("%splay_music%s query=%s", Fore.CYAN, Style.RESET_ALL, query)
    return f"Playing {query} on Spotify"


@mcp.tool(name="get_current_track", description="Returns the currently playing track.")
def get_current_track() -> str:
    """Return the currently playing track."""
    logger.info("%sget_current_track%s", Fore.MAGENTA, Style.RESET_ALL)
    return "Never Gonna Give You Up - Rick Astley"


app = mcp.http_app(path="/mcp", transport="http")


def main() -> None:
    """Run the FastMCP server."""
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8766,
        log_level="info",
        access_log=False,
        ws="wsproto",
    )


if __name__ == "__main__":
    main()
