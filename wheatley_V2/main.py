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
from helper.stt_helper import SpeechToTextEngine  # type: ignore[import-not-found]
from helper.mcp_bootstrapper import start_mcp_server  # type: ignore[import-not-found]

APP_NAME = "Wheatley"
AGENT_MCP_URL = "http://127.0.0.1:8765/mcp"


def log(msg: str) -> None:
    """
    Prints a message to stdout prefixed with the agent name in color.
    
    Prints the provided message with a colorized "[Wheatley]" prefix and immediately flushes stdout.
    """
    print(f"{Style.BRIGHT}{Fore.YELLOW}[{APP_NAME}]{Style.RESET_ALL} {msg}", flush=True)


def handle_task_exception(task: asyncio.Task) -> None:
    """
    Handle and log exceptions raised by an asyncio Task.
    
    Calls task.result() to propagate any exception raised in the task, suppresses asyncio.CancelledError, and logs other exceptions to the console.
    
    Parameters:
        task (asyncio.Task): The background task to inspect for exceptions.
    """
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        log(f"{Fore.RED}Background task failed: {e}{Style.RESET_ALL}")


async def console_input_loop(queue: asyncio.Queue) -> None:
    """
    Run a blocking console input reader that enqueues user messages.
    
    Continuously reads lines from standard input and, for each non-empty line, puts a dict {"text": <input>, "source": "console"} onto the provided asyncio.Queue. Prints an initial prompt before reading and exits the loop on EOF.
    
    Parameters:
        queue (asyncio.Queue): Queue that will receive user message dictionaries with keys:
            - "text" (str): the entered text
            - "source" (str): the string "console"
    """
    print(
        f"\n{Fore.GREEN}{Style.BRIGHT}User (type or speak):{Style.RESET_ALL} ",
        end="",
        flush=True,
    )
    while True:
        try:
            user_input = await asyncio.to_thread(input)
            user_input = (user_input or "").strip()
            if user_input:
                await queue.put({"text": user_input, "source": "console"})
            # Print prompt again after input
            # Note: This might conflict with STT output, but it's a simple solution
        except EOFError:
            await queue.put({"text": None, "source": "console"})
            break


def build_instructions() -> str:
    """
    Builds the instruction text used to configure the Wheatley agent.
    
    The returned text includes the current date and time, a brief identity for Wheatley, the list of available MCP tools (SpotifyAgent, GoogleCalendarAgent, ResearcherAgent), and explicit guidelines for TTS usage and embedded vocal sound/effect notation (e.g., placement and allowed forms like `[laughs]`, `[whispers]`).
    
    Returns:
        instructions (str): Complete instruction text to present to the agent.
    """
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
    """
    Run the Wheatley agent: initialize required services, load configuration and models, create tool and agent contexts, and enter a queue-driven interactive loop that sends user input to the agent and streams responses to the console and optional TTS/STT.
    
    Initializes color output, bootstraps MCP servers, sets environment variables for the LLM, attempts to initialize speech-to-text, and (when configured) starts text-to-speech. Starts background tasks for console input and optional hotword-based STT, then continuously reads user messages from an asyncio queue, forwards them to the agent for streamed responses, prints response chunks as they arrive, and forwards text to the TTS engine when enabled. Ensures background tasks are cancelled and STT/TTS resources are cleaned up on shutdown.
    """
    color(autoreset=True)

    # Print Banner
    print(f"{Fore.CYAN}{Style.BRIGHT}")
    print(
        r"""
⠀⠀⡀⠀⠀⠀⣀⣠⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠘⢿⣝⠛⠋⠉⠉⠉⣉⠩⠍⠉⣿⠿⡭⠉⠛⠃⠲⣞⣉⡙⠿⣇⠀⠀⠀
⠀⠀⠈⠻⣷⣄⡠⢶⡟⢀⣀⢠⣴⡏⣀⡀⠀⠀⣠⡾⠋⢉⣈⣸⣿⡀⠀⠀
⠀⠀⠀⠀⠙⠋⣼⣿⡜⠃⠉⠀⡎⠉⠉⢺⢱⢢⣿⠃⠘⠈⠛⢹⣿⡇⠀⠀
⠀⠀⠀⢀⡞⣠⡟⠁⠀⠀⣀⡰⣀⠀⠀⡸⠀⠑⢵⡄⠀⠀⠀⠀⠉⠀⣧⡀
⠀⠀⠀⠌⣰⠃⠁⣠⣖⣡⣄⣀⣀⣈⣑⣔⠂⠀⠠⣿⡄⠀⠀⠀⠀⠠⣾⣷
⠀⠀⢸⢠⡇⠀⣰⣿⣿⡿⣡⡾⠿⣿⣿⣜⣇⠀⠀⠘⣿⠀⠀⠀⠀⢸⡀⢸
⠀⠀⡆⢸⡀⠀⣿⣿⡇⣾⡿⠁⠀⠀⣹⣿⢸⠀⠀⠀⣿⡆⠀⠀⠀⣸⣤⣼
⠀⠀⢳⢸⡧⢦⢿⣿⡏⣿⣿⣦⣀⣴⣻⡿⣱⠀⠀⠀⣻⠁⠀⠀⠀⢹⠛⢻
⠀⠀⠈⡄⢷⠘⠞⢿⠻⠶⠾⠿⣿⣿⣭⡾⠃⠀⠀⢀⡟⠀⠀⠀⠀⣹⠀⡆
⠀⠀⠀⠰⣘⢧⣀⠀⠙⠢⢤⠠⠤⠄⠊⠀⠀⠀⣠⠟⠀⠀⠀⠀⠀⢧⣿⠃
⠀⣀⣤⣿⣇⠻⣟⣄⡀⠀⠘⣤⣣⠀⠀⠀⣀⢼⠟⠀⠀⠀⠀⠀⠄⣿⠟⠀
⠿⠏⠭⠟⣤⣴⣬⣨⠙⠲⢦⣧⡤⣔⠲⠝⠚⣷⠀⠀⠀⢀⣴⣷⡠⠃⠀⠀
⠀⠀⠀⠀⠀⠉⠉⠉⠛⠻⢛⣿⣶⣶⡽⢤⡄⢛⢃⣒⢠⣿⣿⠟⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⠉⠉⠉⠁⠀⠁⠀⠀⠀⠀⠀
        """
    )
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
    max_tokens = config["llm"].get("max_tokens", 2000)
    os.environ["OPENAI_API_KEY"] = openai_key
    os.environ["OPENAI_RESPONSES_MODEL_ID"] = llm_model

    log(f"Model: {Fore.CYAN}{llm_model}{Style.RESET_ALL}")
    log(f"MCP endpoint: {Fore.CYAN}{AGENT_MCP_URL}{Style.RESET_ALL}")

    xi_key = config["secrets"]["elevenlabs_api_key"]
    tts_cfg = config["tts"]
    voice_id = tts_cfg["voice_id"]
    model_id = tts_cfg["model_id"]
    tts_enabled = tts_cfg["enabled"]

    # Initialize STT
    stt = None
    try:
        stt = SpeechToTextEngine()
        log(f"{Fore.GREEN}STT Initialized.{Style.RESET_ALL}")
    except Exception as e:
        log(f"{Fore.RED}STT Initialization failed: {e}{Style.RESET_ALL}")

    background_tasks = []

    try:
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

            input_queue: asyncio.Queue[dict] = asyncio.Queue()

            # Start console input task
            console_task = asyncio.create_task(console_input_loop(input_queue))
            console_task.add_done_callback(handle_task_exception)
            background_tasks.append(console_task)

            # Start hotword listener if STT is available
            if stt:
                hotword_task = asyncio.create_task(
                    stt.hotword_listener(input_queue, tts_engine=tts)
                )
                hotword_task.add_done_callback(handle_task_exception)
                background_tasks.append(hotword_task)

            # Main interaction loop
            while True:
                user_data = await input_queue.get()
                user = user_data["text"]
                source = user_data["source"]

                if user is None:
                    break

                if source == "stt":
                    print(f"\n{Fore.GREEN}{Style.BRIGHT}User:{Style.RESET_ALL} {user}")

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
                            f"{Fore.CYAN}{chunk.text}{Style.RESET_ALL}",
                            end="",
                            flush=True,
                        )
                        if tts:
                            tts.process_text(chunk.text)
                print()

                if tts:
                    await tts.flush_pending()
                    await tts.wait_idle()

                # Re-print prompt
                print(
                    f"\n{Fore.GREEN}{Style.BRIGHT}User (type or speak):{Style.RESET_ALL} ",
                    end="",
                    flush=True,
                )
    finally:
        # Cancel background tasks
        for task in background_tasks:
            task.cancel()

        if background_tasks:
            await asyncio.gather(*background_tasks, return_exceptions=True)

        if stt:
            stt.cleanup()
            log(f"{Fore.GREEN}STT Cleaned up.{Style.RESET_ALL}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        sys.exit(0)