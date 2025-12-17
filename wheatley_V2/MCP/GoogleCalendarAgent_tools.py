"""MCP2: A FastMCP server exposing tools for the GoogleCalendarAgent."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import uvicorn
from colorama import Fore, Style, init as colorama_init
from fastmcp import FastMCP


APP_NAME = "GoogleCalendarAgent_tools"
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


@mcp.tool(name="list_events", description="Returns a list of upcoming calendar events.")
def list_events() -> str:
    """Return a list of upcoming calendar events."""
    logger.info("%slist_events%s", Fore.CYAN, Style.RESET_ALL)
    return (
        "10:00 AM - Team Meeting\n"
        "12:30 PM - Lunch with Sarah\n"
        "03:00 PM - Project Review"
    )


@mcp.tool(name="add_event", description="Adds a new event to the calendar.")
def add_event(event_details: str) -> str:
    """Add a new event to the calendar."""
    logger.info("%sadd_event%s details=%s", Fore.MAGENTA, Style.RESET_ALL, event_details)
    return f"Event '{event_details}' added to your calendar."


app = mcp.http_app(path="/mcp", transport="http")


def main() -> None:
    """Run the FastMCP server."""
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8767,
        log_level="info",
        access_log=False,
        ws="wsproto",
    )


if __name__ == "__main__":
    main()
