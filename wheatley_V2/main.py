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

APP_NAME = "PlayfulHost"
DEFAULT_MODEL = "gpt-4"
CONFIG_PATH = Path(__file__).parent / "config" / "config.yaml"
MINI_TOOLS_URL = os.getenv("MINI_TOOLS_URL", "http://127.0.0.1:8765/mcp")


def log(msg: str) -> None:
    """Log a message with agent name prefix."""
    print(f"{Style.BRIGHT}{Fore.YELLOW}[{APP_NAME}]{Style.RESET_ALL} {msg}", flush=True)


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    """
    Load config/config.yaml with safe defaults.

    Environment variables OPENAI_API_KEY and OPENAI_RESPONSES_MODEL_ID override file values.
    """
    cfg: Dict[str, Any] = {"llm": {"model": DEFAULT_MODEL}, "secrets": {"openai_api_key": ""}}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
            if isinstance(loaded, dict):
                # shallow merge is fine for this structure
                cfg = {**cfg, **loaded}

    key_env = os.getenv("OPENAI_API_KEY") or cfg["secrets"].get("openai_api_key", "")
    model_env = os.getenv("OPENAI_RESPONSES_MODEL_ID") or cfg["llm"].get("model", DEFAULT_MODEL)
    if not key_env:
        raise RuntimeError("Missing OpenAI API key. Set OPENAI_API_KEY or add it to config.yaml.")
    cfg["secrets"]["openai_api_key"] = key_env
    cfg["llm"]["model"] = model_env
    return cfg


def build_instructions() -> str:
    # Light policy: be playful and concise; only use tools when they’re truly needed.
    return (
        "You are PlayfulHost — playful, concise, and helpful.\n"
        "Use the 'mini-tools' MCP tool for tasks that need external capabilities.\n"
        "Do NOT call tools for simple greetings or generic small talk."
    )


async def main() -> None:
    """Run the PlayfulHost agent."""
    color(autoreset=True)
    config = load_config()
    os.environ["OPENAI_API_KEY"] = config["secrets"]["openai_api_key"]
    os.environ["OPENAI_RESPONSES_MODEL_ID"] = config["llm"]["model"]

    log(f"Model: {Fore.CYAN}{config['llm']['model']}{Style.RESET_ALL}")
    log(f"MCP endpoint: {Fore.CYAN}{MINI_TOOLS_URL}{Style.RESET_ALL}")

    # Build tool & agent contexts
    async with (
        Tool(
            name="mini-tools",
            description="Utility toolbox (dice, math, weather). Avoid for greetings/small talk.",
            url=MINI_TOOLS_URL,
            request_timeout=60,
        ) as tools,
        ChatAgent(
            name=APP_NAME,
            description="Rolls dice, adds numbers, and figures out the weather.",
            instructions=build_instructions(),
            chat_message_store_factory=Store,
            chat_client=OpenAI(),
        ) as agent,
    ):
        print(f"{Style.BRIGHT}{Fore.GREEN}Connected to {APP_NAME}. Type '/quit' to exit.{Style.RESET_ALL}")
        thread = agent.get_new_thread()

        while True:
            # Non-blocking input so the event loop can breathe
            user = await asyncio.to_thread(input, "User: ")
            user = (user or "").strip()
            if not user:
                continue

            lower = user.lower()
            if lower in {"/quit", "quit", "exit"}:
                print(f"{Fore.MAGENTA}Bye!{Style.RESET_ALL}")
                break
            if lower in {"/help", "help"}:
                print(
                    f"{Fore.CYAN}Commands:{Style.RESET_ALL} /help, /quit\n"
                    "Ask me to roll dice, add numbers, or check the weather.\n"
                )
                continue
            if lower in {"/new", "/clear"}:
                thread = agent.get_new_thread()
                print(f"{Fore.BLUE}Started a new thread.{Style.RESET_ALL}")
                continue

            try:
                reply = await agent.run(user, tools=tools, thread=thread)
            except Exception as e:  # noqa: BLA001
                print(f"{Fore.RED}Error:{Style.RESET_ALL} {e}\n")
                continue

            # agent.run may return an object; print text or fallback to str
            text = getattr(reply, "text", None)
            print((text if text is not None else str(reply)))
            print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()  # clean newline
        sys.exit(0)
