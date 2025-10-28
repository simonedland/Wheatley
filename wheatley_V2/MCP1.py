"""MCP1: A FastMCP server exposing tools for the RestaurantAgent."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import uvicorn
from colorama import Fore, Style, init as colorama_init
from fastmcp import FastMCP


APP_NAME = "RestaurantAgent_tools"
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


@mcp.tool(name="get_specials", description="Returns the specials from the menu.")
def get_specials() -> str:
    """Return the specials from the menu."""
    logger.info("%sget_specials%s", Fore.CYAN, Style.RESET_ALL)
    return (
        "Special Soup: Clam Chowder\n"
        "Special Salad: Cobb Salad\n"
        "Special Drink: Chai Tea"
    )


@mcp.tool(name="get_item_price", description="Returns the price of the menu item.")
def get_item_price(menu_item: str) -> str:
    """Return the price of the menu item."""
    logger.info("%sget_item_price%s item=%s", Fore.MAGENTA, Style.RESET_ALL, menu_item)
    return "$9.99"


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
