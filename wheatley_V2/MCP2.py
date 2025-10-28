"""MCP2: A FastMCP server exposing tools for the RestaurantAgent."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import uvicorn
from colorama import Fore, Style, init as colorama_init
from fastmcp import FastMCP


APP_NAME = "SommelierAgent_tools"
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


@mcp.tool(name="list_wines", description="Returns a short wine list with styles.")
def list_wines() -> str:
    """Return a short wine list with styles."""
    logger.info("%slist_wines%s", Fore.CYAN, Style.RESET_ALL)
    return (
        "Whites: Sauvignon Blanc, Chardonnay (oaked/unoaked)\n"
        "Reds: Pinot Noir, Merlot, Cabernet Sauvignon\n"
        "Sparkling: Prosecco, Champagne\n"
        "Non-alcoholic: Sparkling tea, Verjus spritz"
    )


@mcp.tool(name="suggest_pairing", description="Suggests a drink pairing for a dish.")
def suggest_pairing(dish: str) -> str:
    """Suggest a drink pairing for a dish."""
    logger.info("%ssuggest_pairing%s dish=%s", Fore.MAGENTA, Style.RESET_ALL, dish)
    base = "Try a Sauvignon Blanc for acidity and freshness." if any(
        k in dish.lower() for k in ["salad", "fish", "shellfish", "goat cheese"]
    ) else "Pinot Noir is a versatile red that won’t overpower most dishes."
    return base


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
