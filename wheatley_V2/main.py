"""Wheatley V2 orchestrator.

Wires the sibling modules (config, OpenRouter LLM/STT, ElevenLabs TTS, wake-word
listener, conversation memory, personalities, tools, integrations and hardware
animations) into one readable, latency-optimised async loop.

The single most important metric is latency from the user speaking/typing until a
reply starts. To that end the loop overlaps LLM token streaming with TTS
generation and playback: every text delta is forwarded to the TTS engine the
instant it arrives, so Wheatley begins speaking sentence one while the LLM is
still producing the rest of the response. No artificial buffering, no silence
padding.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Callable

from colorama import Fore, Style, init as color  # type: ignore[import-untyped]

from wheatley_V2.config import load_settings
from wheatley_V2.openrouter import OpenRouterClient
from wheatley_V2.tts import TTSHandler
from wheatley_V2.stt import VoiceListener
from wheatley_V2.conversation import ConversationManager
from wheatley_V2 import memory
from wheatley_V2.personality import (
    PersonalityManager,
    PERSONALITY_TOOLS,
    dispatch as personality_dispatch,
)
from wheatley_V2 import tools as simple_tools
from wheatley_V2 import integrations
from wheatley_V2.hardware import (
    HardwareInterface,
    ANIMATION_TOOLS,
    dispatch as hw_dispatch,
)

APP_NAME = "Wheatley"

#: Cap on consecutive LLM<->tool round trips for a single user turn. Prevents an
#: infinite tool-calling loop while still allowing multi-step workflows.
MAX_TOOL_ROUNDS = 8

#: Directory holding optional hot-word greeting clips played by the listener.
GREETING_DIR = Path(__file__).resolve().parent / "stt" / "hotword_greetings"


def log(msg: str) -> None:
    """Print a message prefixed with a colourised agent banner.

    Args:
        msg: Text to print after the ``[Wheatley]`` prefix.
    """
    print(f"{Style.BRIGHT}{Fore.YELLOW}[{APP_NAME}]{Style.RESET_ALL} {msg}", flush=True)


def print_banner() -> None:
    """Print the Wheatley ASCII-art startup banner."""
    print(f"{Fore.CYAN}{Style.BRIGHT}")
    print(r"""
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
        """)
    print(f"{Style.RESET_ALL}")


def handle_task_exception(task: asyncio.Task) -> None:
    """Log (but never raise) an exception from a finished background task.

    Args:
        task: The completed task to inspect.
    """
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as exc:  # noqa: BLE001 - background tasks must not crash the loop
        log(f"{Fore.RED}Background task failed: {exc}{Style.RESET_ALL}")


async def console_input_loop(queue: asyncio.Queue) -> None:
    """Read stdin lines and enqueue them as console user messages.

    Reads in a worker thread so the event loop stays free. Each non-empty line is
    enqueued as ``{"text": <line>, "source": "console"}``. On EOF a sentinel
    ``{"text": None, "source": "console"}`` is enqueued to stop the main loop.

    Args:
        queue: Queue receiving the user message dictionaries.
    """
    print(
        f"\n{Fore.GREEN}{Style.BRIGHT}User (type or speak):{Style.RESET_ALL} ",
        end="",
        flush=True,
    )
    while True:
        try:
            user_input = await asyncio.to_thread(input)
        except EOFError:
            await queue.put({"text": None, "source": "console"})
            break
        user_input = (user_input or "").strip()
        if user_input:
            await queue.put({"text": user_input, "source": "console"})


def build_dispatcher(
    *,
    creds: dict[str, Any],
    spotify: Any,
    google: Any,
    hardware: HardwareInterface,
    on_switch: Callable[[str, dict[str, Any]], None],
) -> Callable[[str, dict[str, Any]], str]:
    """Build the unified tool dispatcher.

    The returned callable tries each sibling module's ``dispatch`` in turn and
    returns the first non-``None`` result. Modules that do not own the tool are
    expected to return ``None`` so routing falls through to the next one.

    Args:
        creds: Credential mapping (for integration dispatch context).
        spotify: Optional Spotify client passed to integration dispatch.
        google: Optional Google client passed to integration dispatch.
        hardware: Hardware interface passed to animation dispatch.
        on_switch: Callback invoked by personality tools when the active
            personality changes; receives ``(mode, args)``.

    Returns:
        A ``dispatch_tool(name, args) -> str`` callable.
    """
    api_ninjas_key = str(creds.get("api_ninjas_key", "")) if creds else ""

    def dispatch_tool(name: str, args: dict[str, Any]) -> str:
        """Route a single tool call to whichever module owns it.

        Args:
            name: Tool name requested by the LLM.
            args: Parsed tool arguments.

        Returns:
            The first non-``None`` result string, or an error notice if no
            module handled the tool.
        """
        try:
            result = simple_tools.dispatch(
                name, args, api_ninjas_key=api_ninjas_key, event_queue=None
            )
            if result is not None:
                return result

            result = memory.dispatch(name, args)
            if result is not None:
                return result

            result = personality_dispatch(name, args, on_switch=on_switch)
            if result is not None:
                return result

            result = integrations.dispatch(name, args, spotify=spotify, google=google)
            if result is not None:
                return result

            result = hw_dispatch(name, args, hw=hardware)
            if result is not None:
                return result
        except Exception as exc:  # noqa: BLE001 - tool errors are fed back to the LLM
            return f"Tool '{name}' failed: {exc}"

        return f"Tool '{name}' is not available."

    return dispatch_tool


def _parse_tool_call(call: Any) -> tuple[str, dict[str, Any]]:
    """Normalise a tool call from a chunk into ``(name, args)``.

    Supports both dict-shaped calls (OpenAI/OpenRouter ``{"function": {...}}``)
    and simple objects exposing ``.name``/``.arguments`` (optionally nested
    behind a ``.function`` attribute).

    Args:
        call: A single tool-call entry from a stream chunk.

    Returns:
        Tuple of the tool name and a parsed argument dict.
    """
    name: str = ""
    raw_args: Any = {}

    if isinstance(call, dict):
        fn = call.get("function", call)
        name = fn.get("name", "") or call.get("name", "")
        raw_args = fn.get("arguments", call.get("arguments", {}))
    else:
        fn = getattr(call, "function", None)
        if fn is not None:
            name = getattr(fn, "name", "") or ""
            raw_args = getattr(fn, "arguments", {})
        else:
            name = getattr(call, "name", "") or ""
            raw_args = getattr(call, "arguments", {})

    if isinstance(raw_args, str):
        try:
            raw_args = json.loads(raw_args) if raw_args.strip() else {}
        except (ValueError, TypeError):
            raw_args = {"_raw": raw_args}
    if not isinstance(raw_args, dict):
        raw_args = {"_value": raw_args}

    return name, raw_args


def _drain_stream(
    client: OpenRouterClient,
    conversation: ConversationManager,
    *,
    model: str,
    tools: list[dict[str, Any]],
    max_tokens: int,
    provider: Any,
    tts: TTSHandler | None,
) -> tuple[str, list]:
    """Consume one LLM stream, printing and speaking text deltas as they arrive.

    Runs synchronously (the OpenRouter client is a blocking iterator); call it via
    a worker thread so the event loop keeps servicing TTS and input tasks.

    Args:
        client: OpenRouter client.
        conversation: Active conversation (read for the request messages).
        model: Model id to request.
        tools: Tool schema list offered to the model.
        max_tokens: Generation cap.
        provider: Provider routing value for this model (may be ``None``).
        tts: Optional TTS engine fed each text delta immediately.

    Returns:
        Tuple of ``(full_text, tool_calls)`` where ``tool_calls`` is the list of
        tool calls collected across the stream (possibly empty).
    """
    full_text_parts: list[str] = []
    tool_calls: list = []

    for chunk in client.chat_stream(
        conversation.get(),
        model=model,
        tools=tools,
        max_tokens=max_tokens,
        provider=provider,
    ):
        text = getattr(chunk, "text", "") or ""
        if text:
            print(f"{Fore.CYAN}{text}{Style.RESET_ALL}", end="", flush=True)
            full_text_parts.append(text)
            if tts is not None:
                tts.process_text(text)
        chunk_tools = getattr(chunk, "tool_calls", None)
        if chunk_tools:
            tool_calls.extend(chunk_tools)

    return "".join(full_text_parts), tool_calls


async def handle_turn(
    user_text: str,
    *,
    client: OpenRouterClient,
    conversation: ConversationManager,
    dispatch_tool: Callable[[str, dict[str, Any]], str],
    tts: TTSHandler | None,
    model: str,
    provider: Any,
    tools: list[dict[str, Any]],
    max_tokens: int,
) -> None:
    """Run one full user turn: stream the reply, run any tools, speak the result.

    Streams the LLM response while forwarding text deltas to TTS for minimal
    latency. If the model requests tools, they are dispatched, their results are
    appended to the conversation, and the LLM turn continues (bounded by
    :data:`MAX_TOOL_ROUNDS`).

    Args:
        user_text: The user's message for this turn.
        client: OpenRouter client.
        conversation: Conversation manager (mutated with user/assistant/tool turns).
        dispatch_tool: Unified tool dispatcher.
        tts: Optional TTS engine.
        model: Default model id.
        provider: Provider routing value for ``model``.
        tools: Aggregated tool schemas.
        max_tokens: Generation cap.
    """
    conversation.add("user", user_text)

    print(f"{Fore.CYAN}{Style.BRIGHT}{APP_NAME}:{Style.RESET_ALL} ", end="", flush=True)

    spoke = False
    for _ in range(MAX_TOOL_ROUNDS):
        full_text, tool_calls = await asyncio.to_thread(
            _drain_stream,
            client,
            conversation,
            model=model,
            tools=tools,
            max_tokens=max_tokens,
            provider=provider,
            tts=tts,
        )

        if full_text:
            conversation.add("assistant", full_text)
            if tts is not None:
                spoke = True

        if not tool_calls:
            break

        for call in tool_calls:
            name, args = _parse_tool_call(call)
            log(f"{Fore.MAGENTA}tool ▶ {name} {args}{Style.RESET_ALL}")
            result = dispatch_tool(name, args)
            conversation.add("tool", f"{name}: {result}")
    else:
        log(f"{Fore.YELLOW}Tool round limit reached; ending turn.{Style.RESET_ALL}")

    print()

    if tts is not None and spoke:
        await tts.flush_pending()
        await tts.wait_idle()


async def main() -> None:
    """Initialise every subsystem and run the latency-optimised interaction loop."""
    color(autoreset=True)
    print_banner()
    print(f"{Fore.GREEN}Initializing Wheatley V2...{Style.RESET_ALL}")

    settings = load_settings()
    client = OpenRouterClient(settings.openrouter_api_key)

    # --- Personality + conversation memory ---------------------------------
    personality = PersonalityManager(
        settings.personalities, settings.current_personality
    )
    system_message = personality.get_personality(personality.current).get(
        "system_message", ""
    )
    max_memory = int(settings.llm.get("max_memory", 10))
    conversation = ConversationManager(system_message, max_memory=max_memory)
    conversation.update_memory(memory.as_context())

    log(f"Model: {Fore.CYAN}{settings.llm.get('default')}{Style.RESET_ALL}")

    # --- TTS ----------------------------------------------------------------
    tts: TTSHandler | None = None
    if settings.tts.get("enabled"):
        tts = TTSHandler(
            settings.elevenlabs_api_key,
            settings.tts["voice_id"],
            settings.tts.get("model_id", "eleven_flash_v2_5"),
        )
        tts.start()
        log(f"{Fore.GREEN}TTS ready.{Style.RESET_ALL}")

    # --- Voice / wake-word listener ----------------------------------------
    voice: VoiceListener | None = None
    if settings.wake_word.get("enabled") or settings.stt.get("enabled"):
        voice = VoiceListener(
            transcribe_fn=lambda wav: client.transcribe(
                wav,
                model=settings.stt["model"],
                language=settings.stt.get("language", "en"),
                provider=settings.stt.get("provider"),
            ),
            wake_cfg=settings.wake_word,
            audio_cfg=settings.stt,
            greeting_dir=GREETING_DIR,
        )
        log(f"{Fore.GREEN}Voice listener ready.{Style.RESET_ALL}")

    # --- Hardware ----------------------------------------------------------
    hardware = HardwareInterface(**settings.hardware)

    # --- Tool aggregation + dispatcher -------------------------------------
    creds: dict[str, Any] = dict(getattr(settings, "integrations", {}) or {})

    def on_switch(mode: str, args: dict[str, Any]) -> None:
        """Apply a personality switch to the conversation system prompt and voice.

        Args:
            mode: The personality mode to switch to.
            args: The raw tool arguments (unused; present for the dispatch contract).
        """
        profile = personality.switch(mode)
        conversation.set_system(profile.get("system_message", ""))
        tts_cfg = profile.get("tts", {}) or {}
        voice_id = tts_cfg.get("voice_id")
        if tts is not None and voice_id:
            tts.set_voice(voice_id, tts_cfg)

    dispatch_tool = build_dispatcher(
        creds=creds,
        spotify=creds.get("spotify"),
        google=creds.get("google"),
        hardware=hardware,
        on_switch=on_switch,
    )

    all_tools: list[dict[str, Any]] = [
        *simple_tools.SIMPLE_TOOLS,
        *memory.MEMORY_TOOLS,
        *PERSONALITY_TOOLS,
        *integrations.available_tools(creds),
        *ANIMATION_TOOLS,
    ]

    model = settings.llm["default"]
    provider = settings.llm.get("providers", {}).get(model)
    max_tokens = int(settings.llm.get("max_tokens", 2000))

    # --- Input plumbing ----------------------------------------------------
    queue: asyncio.Queue[dict] = asyncio.Queue()
    background_tasks: list[asyncio.Task] = []

    console_task = asyncio.create_task(console_input_loop(queue))
    console_task.add_done_callback(handle_task_exception)
    background_tasks.append(console_task)

    if voice is not None:
        hotword_task = asyncio.create_task(
            voice.hotword_listener(queue, tts_engine=tts)
        )
        hotword_task.add_done_callback(handle_task_exception)
        background_tasks.append(hotword_task)

    print(
        f"{Fore.LIGHTBLACK_EX}Ready. Type a message, or say the wake word."
        f"{Style.RESET_ALL}"
    )

    # --- Main loop ---------------------------------------------------------
    try:
        while True:
            user_data = await queue.get()
            user_text = user_data.get("text")
            source = user_data.get("source", "console")

            if user_text is None:
                break

            if source != "console":
                print(f"\n{Fore.GREEN}{Style.BRIGHT}User:{Style.RESET_ALL} {user_text}")

            await handle_turn(
                user_text,
                client=client,
                conversation=conversation,
                dispatch_tool=dispatch_tool,
                tts=tts,
                model=model,
                provider=provider,
                tools=all_tools,
                max_tokens=max_tokens,
            )

            print(
                f"\n{Fore.GREEN}{Style.BRIGHT}User (type or speak):{Style.RESET_ALL} ",
                end="",
                flush=True,
            )
    finally:
        for task in background_tasks:
            task.cancel()
        if background_tasks:
            await asyncio.gather(*background_tasks, return_exceptions=True)

        if tts is not None:
            for task in getattr(tts, "tasks", []):
                task.cancel()
            if getattr(tts, "tasks", None):
                await asyncio.gather(*tts.tasks, return_exceptions=True)
            tts.cleanup()
            log(f"{Fore.GREEN}TTS cleaned up.{Style.RESET_ALL}")

        if voice is not None:
            voice.cleanup()
            log(f"{Fore.GREEN}Voice listener cleaned up.{Style.RESET_ALL}")

        close = getattr(hardware, "close", None)
        if callable(close):
            close()
        log(f"{Fore.GREEN}Hardware closed.{Style.RESET_ALL}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        sys.exit(0)
