# Copyright (c) Microsoft. All rights reserved.

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

# ───────────────────────── constants ─────────────────────────
APP_NAME = "RestaurantAgent"
DEFAULT_MODEL = "gpt-4"
CONFIG_PATH = Path(__file__).parent / "config" / "config.yaml"
RESTAURANT_MCP_URL = os.getenv("RESTAURANT_MCP_URL", "http://localhost:8766/mcp")
SOMMELIER_MCP_URL = os.getenv("SOMMELIER_MCP_URL", "http://localhost:8767/mcp")

# ───────────────────────── logging ─────────────────────────
def setup_logging() -> logging.Logger:
    colorama_init(autoreset=True)
    logger = logging.getLogger(f"{APP_NAME}.tools")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.handlers[:] = [handler]
    logger.propagate = False
    return logger

logger = setup_logging()

# ───────────────────────── config ─────────────────────────
def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    """
    Load config/config.yaml with safe defaults.
    env OPENAI_API_KEY / OPENAI_RESPONSES_MODEL_ID override file values if present.
    """
    cfg: Dict[str, Any] = {"llm": {"model": DEFAULT_MODEL}, "secrets": {"openai_api_key": ""}}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
            if isinstance(loaded, dict):
                cfg = {**cfg, **loaded}

    # env overrides
    key_env = os.getenv("OPENAI_API_KEY") or cfg["secrets"].get("openai_api_key", "")
    model_env = os.getenv("OPENAI_RESPONSES_MODEL_ID") or cfg["llm"].get("model", DEFAULT_MODEL)

    if not key_env:
        raise RuntimeError("Missing OpenAI API key (set OPENAI_API_KEY or configure config.yaml).")

    cfg["secrets"]["openai_api_key"] = key_env
    cfg["llm"]["model"] = model_env
    return cfg

config = load_config()
# Also export for any downstream libs that look in env
os.environ["OPENAI_API_KEY"] = config["secrets"]["openai_api_key"]
os.environ["OPENAI_RESPONSES_MODEL_ID"] = config["llm"]["model"]

# ───────────────────────── mcp & agents ─────────────────────────
mcp = FastMCP(name=APP_NAME)
_openai = OpenAI()  # reuse one client


# ===== Create Agents =====
# Important: DO NOT embed an MCP tool here. We'll attach it per-call with an async context.
restaurant_agent = _openai.create_agent(
    name="RestaurantAgent",
    description="Answer questions about the menu by calling external Restaurant tools (via MCP)."
)

sommelier_agent = _openai.create_agent(
    name="SommelierAgent",
    description="Suggests wine and beverage pairings, and explains why."
)

# Shared runner util (awaits coroutines or handles sync)
async def _run_agent_text(agent_obj, query: str, **kwargs) -> str:
    resp = agent_obj.run(query, **kwargs)
    if hasattr(resp, "__await__"):  # coroutine → await
        resp = await resp  # type: ignore[func-returns-value]
    return getattr(resp, "text", str(resp))

# ── MCP tools exposed by THIS server ──
@mcp.tool(name="RestaurantAgent", description="Answers questions about the restaurant menu.")
async def RestaurantAgent(query: str) -> str:
    logger.info("%sRestaurantAgent%s query=%s", Fore.GREEN, Style.RESET_ALL, query)
    try:
        # Open a fresh MCP session to the Restaurant tools server for this single call.
        async with Tool(
                name="restaurant_mcp",
                url=RESTAURANT_MCP_URL,
                request_timeout=60,
            ) as restaurant_tools:

            return await _run_agent_text(restaurant_agent, query, tools=restaurant_tools)
    except Exception as e:  # noqa: BLE001
        logger.exception("RestaurantAgent run failed")
        return f"Error: {e}"

@mcp.tool(name="SommelierAgent", description="Recommends wine/drink pairings and explains the choice. it also has overview of the wine list.")
async def SommelierAgent(query: str) -> str:
    logger.info("%sSommelierAgent%s query=%s", Fore.GREEN, Style.RESET_ALL, query)
    try:
        async with Tool(
                name="sommelier_mcp",
                url=SOMMELIER_MCP_URL,
                request_timeout=60,
            ) as sommelier_tools:
            return await _run_agent_text(sommelier_agent, query, tools=sommelier_tools)
    except Exception as e:  # noqa: BLE001
        logger.exception("SommelierAgent run failed")
        return f"Error: {e}"

# ───────────────────────── server glue ─────────────────────────
app = mcp.http_app(path="/mcp", transport="http")

def create_server() -> FastMCP:
    """Factory used by FastMCP CLI when importing this module."""
    return mcp

server = mcp

def main() -> None:
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
