"""Main application file for PlayfulHost agent using MCP tools."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime

from colorama import Fore, Style, init as color  # type: ignore[import-untyped]
from agent_framework import ChatAgent  # type: ignore[import-not-found]
from agent_framework import ChatMessageStore as Store  # type: ignore[import-not-found]
from agent_framework import MCPStreamableHTTPTool as Tool  # type: ignore[import-not-found]
from agent_framework.openai import OpenAIResponsesClient as OpenAI  # type: ignore[import-not-found]

from helper.config import load_config  # type: ignore[import-not-found]
from helper.tts_helper import TTSHandler  # type: ignore[import-not-found]
from helper.mcp_bootstrapper import start_mcp_server  # type: ignore[import-not-found]

APP_NAME = "Wheatley"
AGENT_MCP_URL = "http://127.0.0.1:8765/mcp"


def log(msg: str) -> None:
    """Log a message with agent name prefix."""
    print(f"{Style.BRIGHT}{Fore.YELLOW}[{APP_NAME}]{Style.RESET_ALL} {msg}", flush=True)


def build_instructions() -> str:
    """Build agent instructions for Wheatley."""
    now = datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
    return (
        f"Current Date and Time: {now}\n"
        "You are Wheatley — a helpful AI assistant.\n"
        "You have access to 'SpotifyAgent', 'GoogleCalendarAgent', and 'ResearcherAgent' via the 'agent_tools' MCP tool.\n"
        "Use them to help the user with music, scheduling, and web research.\n"
        "you have TTS capabilities to speak your responses aloud. this happens automatically.\n"
        "To implement vocal sounds or sound effects, use square brackets, e.g., [sarcastically], [giggles], [whispers]. Only use sound effects that would come from a mouth like [laughs], [sighs], [whispers] and so on.\n"
        "try to implement vocal sounds and sound effects naturally in your responses. Only make vocal sounds for things that actually makes sound. Examples of vocal sounds that does not make sound is [nods] [softly] and [thinks].\n"
        "Never add a vocal sounds by itself after '.' place it within the sentence you want it to affect. Add it to ALL the sentences you want to affect like: [whispers] Quiet now... [whispers] so quiet... [whispers] so lonely...\n"
        "Do not use vocal sounds for actions that do not produce sound, such as [looks around] or [thinks] [smiles].\n"
        "Place the vocal sounds within the sentences they are meant to affect, rather than at the end of sentences.\n"
        "NEVER place vocal sounds at the end of your response after punctuation. for example 'Hello there! [cheerfully] How can I assist you today? [cheerfully]' is incorrect.\n"
        "a example of correct usage is: '[cheerfully] Hello there! How can I assist you today?'\n"
    )


async def main() -> None:
    """Run the Wheatley agent."""
    color(autoreset=True)

    # Print Banner
    print(f"{Fore.CYAN}{Style.BRIGHT}")
    print(r"""
 __      __  __                    __   __
/  \    /  \|  |__    ____ _____ _/  |_|  |   ____ ___.__.
\   \/\/   /|  |  \ _/ __ \\__  \\   __\  | _/ __ <   |  |
 \        / |   Y  \\  ___/ / __ \|  | |  |_\  ___/\___  |
  \__/\  /  |___|  / \___  >____  /__| |____/\___  > ____|
       \/        \/      \/     \/               \/\/
    """)
    print(f"{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Initializing Wheatley V2...{Style.RESET_ALL}")

    # Bootstrap MCP Servers
    print(f"{Fore.YELLOW}Bootstrapping MCP Servers...{Style.RESET_ALL}")
    start_mcp_server("SpotifyAgent_tools.py")
    start_mcp_server("GoogleCalendarAgent_tools.py")

    print(f"{Fore.YELLOW}Waiting for sub-agents to initialize...{Style.RESET_ALL}")
    time.sleep(2)

    start_mcp_server("agent_MCP.py")
    print(f"{Fore.YELLOW}Waiting for main agent to initialize...{Style.RESET_ALL}")
    time.sleep(3)

    config = load_config()
    openai_key = config["secrets"]["openai_api_key"]
    llm_model = config["llm"]["model"]
    max_tokens = config["llm"].get("max_tokens", 1000)
    os.environ["OPENAI_API_KEY"] = openai_key
    os.environ["OPENAI_RESPONSES_MODEL_ID"] = llm_model

    log(f"Model: {Fore.CYAN}{llm_model}{Style.RESET_ALL}")
    log(f"MCP endpoint: {Fore.CYAN}{AGENT_MCP_URL}{Style.RESET_ALL}")

    xi_key = config["secrets"]["elevenlabs_api_key"]
    tts_cfg = config["tts"]
    voice_id = tts_cfg["voice_id"]
    model_id = tts_cfg["model_id"]
    tts_enabled = tts_cfg["enabled"]

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
        thread = agent.get_new_thread()

        tts = (
            TTSHandler(xi_key, voice_id=voice_id, model_id=model_id)
            if xi_key and tts_enabled
            else None
        )
        if tts:
            tts.start()

        # Main interaction loop
        while True:
            print(
                f"\n{Fore.GREEN}{Style.BRIGHT}User:{Style.RESET_ALL} ",
                end="",
                flush=True,
            )
            user = await asyncio.to_thread(input)
            user = (user or "").strip()
            if not user:
                continue

            reply = agent.run_stream(
                user, tools=tools, thread=thread, max_tokens=max_tokens
            )
            print(
                f"{Fore.CYAN}{Style.BRIGHT}Wheatley:{Style.RESET_ALL} ",
                end="",
                flush=True,
            )
            async for chunk in reply:
                if chunk.text:
                    print(
                        f"{Fore.CYAN}{chunk.text}{Style.RESET_ALL}", end="", flush=True
                    )
                    if tts:
                        tts.process_text(chunk.text)
            print()

            if tts:
                await tts.flush_pending()
                await tts.wait_idle()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        sys.exit(0)
