
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict

import yaml
from colorama import Fore as C, Style as S, init as color
from agent_framework import ChatAgent
from agent_framework import ChatMessageStore as Store
from agent_framework import MCPStreamableHTTPTool as Tool
from agent_framework.openai import OpenAIResponsesClient as OpenAI

# ───────────────────────── constants ─────────────────────────
APP_NAME = "PlayfulHost"
DEFAULT_MODEL = "gpt-4"
CONFIG_PATH = Path(__file__).parent / "config" / "config.yaml"
MINI_TOOLS_URL = os.getenv("MINI_TOOLS_URL", "http://127.0.0.1:8765/mcp")

# ───────────────────────── utils ─────────────────────────
def log(msg: str) -> None:
    print(f"{S.BRIGHT}{C.YELLOW}[{APP_NAME}]{S.RESET_ALL} {msg}", flush=True)

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

# ───────────────────────── main ─────────────────────────
async def main() -> None:
    color(autoreset=True)
    config = load_config()
    os.environ["OPENAI_API_KEY"] = config["secrets"]["openai_api_key"]
    os.environ["OPENAI_RESPONSES_MODEL_ID"] = config["llm"]["model"]

    log(f"Model: {C.CYAN}{config['llm']['model']}{S.RESET_ALL}")
    log(f"MCP endpoint: {C.CYAN}{MINI_TOOLS_URL}{S.RESET_ALL}")

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
        print(f"{S.BRIGHT}{C.GREEN}Connected to {APP_NAME}. Type '/quit' to exit.{S.RESET_ALL}")
        thread = agent.get_new_thread()

        while True:
            # Non-blocking input so the event loop can breathe
            user = await asyncio.to_thread(input, "User: ")
            user = (user or "").strip()
            if not user:
                continue

            lower = user.lower()
            if lower in {"/quit", "quit", "exit"}:
                print(f"{C.MAGENTA}Bye!{S.RESET_ALL}")
                break
            if lower in {"/help", "help"}:
                print(
                    f"{C.CYAN}Commands:{S.RESET_ALL} /help, /quit\n"
                    "Ask me to roll dice, add numbers, or check the weather.\n"
                )
                continue
            if lower in {"/new", "/clear"}:
                thread = agent.get_new_thread()
                print(f"{C.BLUE}Started a new thread.{S.RESET_ALL}")
                continue

            try:
                reply = await agent.run(user, tools=tools, thread=thread)
            except Exception as e:  # noqa: BLE001
                print(f"{C.RED}Error:{S.RESET_ALL} {e}\n")
                continue

            # agent.run may return an object; print text or fallback to str
            text = getattr(reply, "text", None)
            print((text if text is not None else str(reply)))
            print()

# ───────────────────────── entrypoint ─────────────────────────
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()  # clean newline
        sys.exit(0)
