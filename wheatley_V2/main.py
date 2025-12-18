"""Main application file for PlayfulHost agent using MCP tools."""

from __future__ import annotations

import asyncio
import os
import sys
import subprocess
import time
import platform
import atexit
import shutil
import signal
from pathlib import Path

from colorama import Fore, Style, init as color  # type: ignore[import-untyped]
from agent_framework import ChatAgent  # type: ignore[import-not-found]
from agent_framework import ChatMessageStore as Store  # type: ignore[import-not-found]
from agent_framework import MCPStreamableHTTPTool as Tool  # type: ignore[import-not-found]
from agent_framework.openai import OpenAIResponsesClient as OpenAI  # type: ignore[import-not-found]

from helper.config import load_config  # type: ignore[import-not-found]
from helper.tts_helper import TTSHandler  # type: ignore[import-not-found]

APP_NAME = "Wheatley"
AGENT_MCP_URL = "http://127.0.0.1:8765/mcp"

MCP_PROCESSES: list[subprocess.Popen] = []


def cleanup_mcp_processes():
    """Kill all started MCP processes."""
    if not MCP_PROCESSES:
        return

    print(f"\n{Fore.YELLOW}Shutting down MCP servers...{Style.RESET_ALL}")
    for p in MCP_PROCESSES:
        if p.poll() is None:  # If still running
            try:
                if platform.system() == "Windows":
                    p.terminate()
                else:
                    os.kill(p.pid, signal.SIGTERM)
            except Exception as e:
                print(f"{Fore.RED}Error killing process {p.pid}: {e}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}MCP Servers terminated.{Style.RESET_ALL}")


atexit.register(cleanup_mcp_processes)


def start_mcp_server(script_name: str):
    """Start an MCP server in a new terminal window."""
    script_path = Path(__file__).parent / "MCP" / script_name

    if not script_path.exists():
        print(
            f"{Fore.RED}Error: Could not find {script_name} at {script_path}{Style.RESET_ALL}"
        )
        return

    cmd = [sys.executable, str(script_path)]
    system = platform.system()
    process = None

    try:
        if system == "Windows":
            # CREATE_NEW_CONSOLE = 0x00000010
            # Use getattr to avoid mypy errors on non-Windows systems
            creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 16)
            process = subprocess.Popen(cmd, creationflags=creation_flags)
        elif system == "Linux":
            # Only use lxterminal as requested
            if shutil.which("lxterminal"):
                process = subprocess.Popen(
                    ["lxterminal", "-e", sys.executable, str(script_path)]
                )
            else:
                print(
                    f"{Fore.YELLOW}lxterminal not found. Running {script_name} in background.{Style.RESET_ALL}"
                )
                process = subprocess.Popen(cmd)

        if process:
            MCP_PROCESSES.append(process)
            print(f"{Fore.GREEN}Started {script_name} (PID: {process.pid}){Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}Failed to start {script_name}: {e}{Style.RESET_ALL}")


def log(msg: str) -> None:
    """Log a message with agent name prefix."""
    print(f"{Style.BRIGHT}{Fore.YELLOW}[{APP_NAME}]{Style.RESET_ALL} {msg}", flush=True)


def build_instructions() -> str:
    """Build agent instructions for Wheatley."""
    return (
        "You are Wheatley — a helpful AI assistant.\n"
        "You have access to 'SpotifyAgent' and 'GoogleCalendarAgent' via the 'agent_tools' MCP tool.\n"
        "Use them to help the user with music and scheduling.\n"
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
            print(f"\n{Fore.GREEN}{Style.BRIGHT}User:{Style.RESET_ALL} ", end="", flush=True)
            user = await asyncio.to_thread(input)
            user = (user or "").strip()
            if not user:
                continue

            reply = agent.run_stream(
                user, tools=tools, thread=thread, max_tokens=max_tokens
            )
            print(f"{Fore.CYAN}{Style.BRIGHT}Wheatley:{Style.RESET_ALL} ", end="", flush=True)
            async for chunk in reply:
                if chunk.text:
                    print(f"{Fore.CYAN}{chunk.text}{Style.RESET_ALL}", end="", flush=True)
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
