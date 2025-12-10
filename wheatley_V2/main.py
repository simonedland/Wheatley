"""Main application file for PlayfulHost agent using MCP tools."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict

import yaml
from colorama import Fore, Style, init as color
from agent_framework import ChatAgent
from agent_framework import ChatMessageStore as Store
from agent_framework import MCPStreamableHTTPTool as Tool
from agent_framework.openai import OpenAIResponsesClient as OpenAI

APP_NAME = "Wheatley"
CONFIG_PATH = Path(__file__).parent / "config" / "config.yaml"
AGENT_MCP_URL = "http://127.0.0.1:8765/mcp"


def log(msg: str) -> None:
    """Log a message with agent name prefix."""
    print(f"{Style.BRIGHT}{Fore.YELLOW}[{APP_NAME}]{Style.RESET_ALL} {msg}", flush=True)


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    """Load config/config.yaml with safe defaults."""
    cfg: Dict[str, Any] = {"llm": {"model": "gpt-4o"}, "secrets": {"openai_api_key": ""}}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
            if isinstance(loaded, dict):
                cfg = {**cfg, **loaded}

    key_env = cfg["secrets"].get("openai_api_key")
    model_env = cfg["llm"].get("model")

    cfg["secrets"]["openai_api_key"] = key_env
    cfg["llm"]["model"] = model_env
    return cfg


def build_instructions() -> str:
    """Build agent instructions for Wheatley."""
    return (
        "You are Wheatley — a helpful AI assistant.\n"
        "You have access to 'SpotifyAgent' and 'GoogleCalendarAgent' via the 'agent_tools' MCP tool.\n"
        "Use them to help the user with music and scheduling."
    )


async def main() -> None:
    """Run the Wheatley agent."""
    color(autoreset=True)
    config = load_config()
    os.environ["OPENAI_API_KEY"] = config["secrets"]["openai_api_key"]
    os.environ["OPENAI_RESPONSES_MODEL_ID"] = config["llm"]["model"]

    log(f"Model: {Fore.CYAN}{config['llm']['model']}{Style.RESET_ALL}")
    log(f"MCP endpoint: {Fore.CYAN}{AGENT_MCP_URL}{Style.RESET_ALL}")

    # Build tool & agent contexts
    async with (
        Tool(
            name="agent_tools",
            description="Access to Spotify and Calendar agents.",
            url=AGENT_MCP_URL,
            request_timeout=60,
        ) as tools,
        ChatAgent(
            name=APP_NAME,
            description="A helpful assistant with access to Spotify and Calendar.",
            instructions=build_instructions(),
            chat_message_store_factory=Store,
            chat_client=OpenAI(),
        ) as agent,
    ):
        print(f"{Style.BRIGHT}{Fore.GREEN}Connected to {APP_NAME}. Type '/quit' to exit.{Style.RESET_ALL}")
        thread = agent.get_new_thread()

        while True:
            user = await asyncio.to_thread(input, "User: ")
            user = (user or "").strip()
            if not user:
                continue

            lower = user.lower()
            if lower in {"/quit", "quit", "exit"}:
                print(f"{Fore.MAGENTA}Bye!{Style.RESET_ALL}")
                break

            reply = await agent.run(user, tools=tools, thread=thread)

            text = getattr(reply, "text", None)
            print((text if text is not None else str(reply)))
            print()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        sys.exit(0)
