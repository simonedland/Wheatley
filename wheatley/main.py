"""
Main entry point for the Wheatley assistant.

Wires together:
- STT engine
- LLM client
- TTS engine
- Arduino interface

Provides an asynchronous event loop reacting to user input and controlling servos
and LED animations. External behavior and CLI entrypoints preserved.
"""

from __future__ import annotations

# =================== Imports: Standard Libraries ===================
import atexit
import asyncio
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from glob import glob
from queue import Queue
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import threading

import re
import requests
import yaml
from colorama import Fore, Style, init as colorama_init

# =================== Imports: Local Modules ===================
from hardware.arduino_interface import ArduinoInterface
from assistant.assistant import ConversationManager
from llm.llm_client import GPTClient, Functions
from tts.tts_engine import TextToSpeechEngine
from stt.stt_engine import SpeechToTextEngine
from utils.timing_logger import export_timings, clear_timings, record_timing
from utils.main_helpers import feature_summary, authenticate_and_update_features

# =================== Initialization ===================
colorama_init(autoreset=True)

# =================== Helper Constants ===================

# Sentence parsing (kept; not currently used but preserved for compatibility)
PUNCT_RE = re.compile(r"[.!?]\s+")
ABBREVS = {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st"}

MAX_TTS_WORKERS = 2
QUEUE_MAXSIZE = 100
MAX_CHAIN_RETRY = 10

# =================== Logging Setup ===================


class ColorConsoleFormatter(logging.Formatter):
    """Render log records with colorful, compact formatting for the terminal."""

    LEVEL_STYLES = {
        logging.DEBUG: ("🔍", Fore.LIGHTBLACK_EX, Style.NORMAL),
        logging.INFO: ("✨", Fore.CYAN, Style.NORMAL),
        logging.WARNING: ("⚠", Fore.YELLOW, Style.BRIGHT),
        logging.ERROR: ("✖", Fore.RED, Style.BRIGHT),
        logging.CRITICAL: ("🔥", Fore.RED, Style.BRIGHT),
    }

    def __init__(self) -> None:
        """Initialise the formatter with the compact message template."""
        super().__init__("%(message)s")

    def format(self, record: logging.LogRecord) -> str:
        """Return the formatted log record string with colour and icon."""
        icon, colour, intensity = self.LEVEL_STYLES.get(
            record.levelno, ("•", Fore.WHITE, Style.NORMAL)
        )
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        message = super().format(record)
        source = record.name or "root"
        level = f"{icon} {record.levelname:<7}"
        return (
            f"{Style.DIM}{timestamp}{Style.RESET_ALL} "
            f"{intensity}{colour}{level}{Style.RESET_ALL} "
            f"{Style.DIM}[{source}] {Style.RESET_ALL}{message}"
        )


def _configure_logging() -> logging.Logger:
    """Idempotent, file+console logging setup."""
    logger = logging.getLogger("wheatley")
    if getattr(_configure_logging, "_configured", False):
        return logger

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Remove pre-existing handlers to prevent duplicates in re-runs
    for h in root.handlers[:]:
        root.removeHandler(h)

    log_formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

    file_handler = logging.FileHandler("assistant.log", mode="w", encoding="utf-8")
    file_handler.setFormatter(log_formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColorConsoleFormatter())
    console_handler.setLevel(logging.DEBUG)
    root.addHandler(console_handler)

    # Suppress verbose HTTP logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    _configure_logging._configured = True  # type: ignore[attr-defined]
    return logger


logger = _configure_logging()

# =================== Configuration Loader ===================


def load_config() -> Dict[str, Any]:
    """Load and return YAML config from config/config.yaml."""
    config_path = Path(__file__).parent / "config" / "config.yaml"
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# =================== Welcome Banner ===================


def print_welcome() -> None:
    """Print a retro ASCII art welcome banner."""
    reset = "\033[0m"
    retro_color = "\033[95m"
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
    print(f"{retro_color}Welcome to the AI Assistant!{reset}")


# ────────────────────────── PRIVATE HELPERS ──────────────────────────── #


def _detect_serial_port() -> Tuple[Optional[str], bool]:
    """
    Return (best_port, dry_run_flag) based on OS and availability.

    Behavior preserved; shell `ls` replaced with safe glob listing.
    """
    dry_run, port = False, None

    if sys.platform.startswith(("linux", "darwin")):
        ports = sorted(p for p in glob("/dev/tty*"))
        logger.info("Available ports:")
        for p in ports:
            logger.info("  %s", p)
        port = "/dev/ttyACM0"

    elif sys.platform.startswith("win"):
        from serial.tools import list_ports  # type: ignore

        ports = list(list_ports.comports())
        logger.info("Available ports:")
        for p in ports:
            logger.info("  %s", p.device)

        port = next((p.device for p in ports if p.device == "COM7"), None)
        dry_run = not bool(port)
        if dry_run:
            logger.warning("No serial ports found. Running in dry-run mode.")

    return port, dry_run


def _init_arduino(
    port: Optional[str],
    dry_run: bool,
    stt_engine: Optional[SpeechToTextEngine],
) -> ArduinoInterface:
    """Create (or stub) ArduinoInterface and wire it to the STT engine."""
    if not port or dry_run:
        arduino = ArduinoInterface(port="dryrun", dry_run=True)
    else:
        try:
            arduino = ArduinoInterface(port=port)
            arduino.connect()
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "Could not connect to Arduino on %s: %s. Falling back to dry-run.",
                port,
                exc,
            )
            arduino = ArduinoInterface(port=port, dry_run=True)

    if stt_engine:
        stt_engine.arduino_interface = arduino
    return arduino


# =================== Event Dataclass ===================


@dataclass
class Event:
    """Simple event container used by the async event loop."""

    source: str  # e.g. "user", "timer", "gpio", "webhook"
    payload: str  # human-readable description
    metadata: Optional[Dict[str, Any]] = None
    ts: Optional[datetime] = None

    def __str__(self) -> str:
        """Return the event as a human readable string for logging/debugging."""
        meta = f" {self.metadata}" if self.metadata else ""
        ts = f" ({self.ts.isoformat()})" if self.ts else ""
        return f"[{self.source.upper()}] {self.payload}{meta}{ts}"


# =================== Async Event Handling ===================


async def user_input_producer(
    q: asyncio.Queue[Event],
    input_allowed_event: asyncio.Event,
) -> None:
    """
    Asynchronously read user text input and push Event objects to the queue.

    Waits for `input_allowed_event` to be set before returning input into the queue.
    """
    loop = asyncio.get_running_loop()
    while True:
        await input_allowed_event.wait()
        text = await loop.run_in_executor(None, input, "You: ")

        # If TTS started after prompting, wait here until allowed again.
        while not input_allowed_event.is_set():
            await input_allowed_event.wait()

        text_stripped = text.strip()
        await q.put(Event("user", text_stripped, {"input_type": "text"}))
        if text_stripped.lower() == "exit":
            break


async def get_event(queue: asyncio.Queue[Event | Dict[str, Any]]) -> Event:
    """Retrieve next event from the queue, normalizing voice dicts to Event objects."""
    incoming = await queue.get()
    if isinstance(incoming, dict) and incoming.get("type") == "voice":
        return Event("user", incoming.get("text", ""), {"input_type": "voice"})
    return incoming  # type: ignore[return-value]


# =================== System Event Handling ===================


def handle_non_user_event(event: Event, manager: ConversationManager) -> None:
    """Add system messages for timers/reminders/other events."""
    if event.source == "timer":
        label = event.payload
        duration = event.metadata.get("duration") if event.metadata else None
        timer_msg = (
            f"TIMER labeled {label} for {duration} is up inform the user."
            if duration
            else f"TIMER UP: {label}"
        )
        manager.add_text_to_conversation("system", timer_msg)
    elif event.source == "reminder":
        manager.add_text_to_conversation(
            "system",
            f"Reminder has triggered with the following text: {event.payload}",
        )
    else:
        manager.add_text_to_conversation("system", str(event))


def process_event(event: Event, manager: ConversationManager) -> bool:
    """
    Update conversation with the event and determine if exit was requested by the user.

    Returns True if exit requested, else False.
    """
    if event.source == "user":
        manager.add_text_to_conversation("user", event.payload)
        return event.payload.lower() == "exit"
    handle_non_user_event(event, manager)
    return False


# =================== Tool Workflow ===================


def run_tool_workflow(
    manager: ConversationManager,
    gpt_client: GPTClient,
    queue: asyncio.Queue[Any],
    *,
    stt_engine: Optional[SpeechToTextEngine] = None,
    tts_engine: Optional[TextToSpeechEngine] = None,
    hotword_task: Optional[asyncio.Task] = None,
) -> Optional[asyncio.Task]:
    """
    Ask GPT for a workflow, execute tools, add results.

    While tools run, pause STT and cancel hotword listener to prevent self-hearing,
    then resume/restart afterwards. Returns the possibly updated hotword_task.
    """
    # Pause listening and cancel hotword while executing tools
    if hotword_task:
        hotword_task.cancel()
        hotword_task = None
    if stt_engine:
        stt_engine.pause_listening()

    executed_workflows = 0
    seen_signatures: set[Tuple[str, ...]] = set()

    for attempt in range(1, MAX_CHAIN_RETRY + 1):
        conv = manager.get_conversation()
        workflow = gpt_client.get_workflow(conv)
        if not workflow:
            return _resume_hotword_listener(stt_engine, queue, tts_engine)

        # Preprocess once: inject web search info and remove those calls (preserve order)
        new_calls: List[Dict[str, Any]] = []
        for item in workflow:
            if item.get("name") == "web_search_call_result":
                text = item.get("arguments", {}).get("text", "")
                if text:
                    manager.add_text_to_conversation("system", f"Info: {text}")
            else:
                new_calls.append(item)
        # Mutate in place to preserve external expectations
        workflow[:] = new_calls

        if not workflow:
            logging.info(
                "Tool workflow attempt %d had no executable calls after preprocessing.",
                attempt,
            )
            continue

        # Signature to prevent loops
        signature = tuple(
            sorted(
                json.dumps(
                    {"name": c.get("name"), "arguments": c.get("arguments", {})},
                    sort_keys=True,
                )
                for c in workflow
            )
        )
        if signature in seen_signatures:
            logging.info(
                "Duplicate workflow signature detected on attempt %d; stopping to avoid loops.",
                attempt,
            )
            break
        seen_signatures.add(signature)

        mem = Functions().read_long_term_memory()
        manager.update_memory(f"LONG TERM MEMORY:\n{mem}")

        _execute_workflow(workflow, queue, manager)
        executed_workflows += 1

    return _resume_hotword_listener(stt_engine, queue, tts_engine)


def _resume_hotword_listener(
    stt_engine: Optional[SpeechToTextEngine],
    queue: asyncio.Queue[Any],
    tts_engine: Optional[TextToSpeechEngine],
) -> Optional[asyncio.Task]:
    """Resume listening and restart the hotword listener if needed."""
    if stt_engine:
        stt_engine.resume_listening()
        loop = asyncio.get_running_loop()
        return loop.create_task(
            stt_engine.hotword_listener(queue, tts_engine=tts_engine)
        )
    return None


def _execute_workflow(
    workflow: List[Dict[str, Any]],
    queue: asyncio.Queue[Any],
    manager: ConversationManager,
) -> None:
    """Run tools via Functions.execute_workflow and append results to conversation."""
    if not workflow:
        return

    logging.info(
        "Executing workflow with %d call(s): %s",
        len(workflow),
        ", ".join(call.get("name", "unknown") for call in workflow),
    )

    for call in workflow:
        call_name = call.get("name", "unknown")
        call_args = call.get("arguments", {})
        call_id = call.get("call_id")
        logger.info("Tool ▶ %s args=%s", call_name, call_args)
        if call_id:
            logger.info("         call_id=%s", call_id)

    start = time.time()
    fn_results: List[Dict[str, Any]] = (
        Functions().execute_workflow(workflow, event_queue=queue) or []
    )
    record_timing("workflow_execute", start)
    if not fn_results:
        logging.info("Workflow returned no results.")

    for result_payload in fn_results:
        name = result_payload.get("name", "unknown")
        call_id = result_payload.get("call_id")
        result_text = str(result_payload.get("result"))
        logging.info("Tool '%s' (call_id=%s) result: %s", name, call_id, result_text)
        manager.add_text_to_conversation("system", result_text)


# =================== Assistant Replies ===================


def generate_assistant_reply(
    manager: ConversationManager, gpt_client: GPTClient
) -> Tuple[str, Any]:
    """Fetch assistant text and animation from the LLM and update conversation history."""
    conv = manager.get_conversation()
    gpt_text = gpt_client.get_text(conv)
    manager.add_text_to_conversation("assistant", gpt_text)
    manager.print_memory()
    animation = gpt_client.reply_with_animation(conv)
    return gpt_text, animation


async def handle_follow_up_after_stream(
    stt_engine: SpeechToTextEngine,
    event_queue: asyncio.Queue[Any],
    hotword_task: Optional[asyncio.Task],
    stt_enabled: bool,
    tts_engine: Optional[TextToSpeechEngine] = None,
) -> Optional[asyncio.Task]:
    """Handle follow-up voice recording after streaming TTS playback."""
    stt_engine.resume_listening()

    # 5s follow-up without hotword
    logger.debug("STT follow-up listening window opened (5s, no hotword)")
    loop = asyncio.get_running_loop()
    follow_up_future = loop.run_in_executor(
        None, lambda: stt_engine.record_and_transcribe(5, tts_engine=tts_engine)
    )
    next_event_task = asyncio.create_task(event_queue.get())
    done, _ = await asyncio.wait(
        [follow_up_future, next_event_task], return_when=asyncio.FIRST_COMPLETED
    )
    if follow_up_future in done:
        follow_up = follow_up_future.result()
        if follow_up and follow_up.strip():
            await event_queue.put(
                Event("user", follow_up.strip(), {"input_type": "voice"})
            )
        next_event_task.cancel()
        await asyncio.gather(next_event_task, return_exceptions=True)
    else:
        follow_up_future.cancel()
        await asyncio.gather(follow_up_future, return_exceptions=True)
        next_event = next_event_task.result()
        await event_queue.put(next_event)

    hotword_task = asyncio.create_task(
        stt_engine.hotword_listener(event_queue, tts_engine=tts_engine)
    )
    logger.debug("Hotword listener resumed after follow-up window")
    return hotword_task


# ────────────────────────────── DATA STRUCTS ──────────────────────────── #


@dataclass
class _StreamContext:
    sentences: List[str] = field(default_factory=list)
    sentence_q: asyncio.Queue = field(
        default_factory=lambda: asyncio.Queue(QUEUE_MAXSIZE)
    )
    tts_futures: Dict[float, asyncio.Future] = field(default_factory=dict)
    playback_q: Queue = field(default_factory=lambda: Queue(QUEUE_MAXSIZE))
    timing: Dict[str, float] = field(default_factory=dict)
    loop: asyncio.AbstractEventLoop = field(default_factory=asyncio.get_running_loop)
    tts_executor: Optional[ThreadPoolExecutor] = None
    play_executor: Optional[ThreadPoolExecutor] = None
    cfg: Dict[str, Any] = field(default_factory=dict)
    total_sentences: int = 0


# ────────────────────────────── SET-UP HELPERS ────────────────────────── #


def _prepare_stream(
    stt_enabled: bool,
    stt_engine: Optional[SpeechToTextEngine],
    hotword_task: Optional[asyncio.Task],
) -> Dict[str, Any]:
    """Pause hot-word + STT and return config with possibly canceled hotword_task."""
    if hotword_task:
        hotword_task.cancel()
    if stt_enabled and stt_engine:
        stt_engine.pause_listening()
    return {"hotword_task": hotword_task}


def _make_context(cfg: Dict[str, Any], manager: ConversationManager) -> _StreamContext:
    conf = load_config()
    ctx = _StreamContext(
        cfg={
            "api_url": (
                "https://api.elevenlabs.io/v1/text-to-speech/"
                f"{conf['tts'].get('voice_id', '4Jtuv4wBvd95o1hzNloV')}"
            ),
            "api_key": conf["secrets"]["elevenlabs_api_key"],
            "model": conf["tts"].get("model_id", "eleven_v3"),
            "fmt": conf["tts"].get("output_format", "mp3_22050_32"),
            "tts_engine": cfg.get("tts_engine"),
        }
    )
    ctx.tts_executor = ThreadPoolExecutor(
        max_workers=MAX_TTS_WORKERS, thread_name_prefix="TTS"
    )
    ctx.play_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="PLAY")
    return ctx


def _playback_worker(
    ctx: _StreamContext, playback_done_event: Optional[threading.Event] = None
) -> None:
    """Playback worker runs in its own thread; plays clips in FIFO order. Signals when done."""
    q = ctx.playback_q
    tts_engine: TextToSpeechEngine = ctx.cfg["tts_engine"]
    while True:
        idx, audio = q.get()
        if idx is None:  # sentinel ⇒ shutdown
            break
        if audio is None:
            continue
        start = time.time()
        total = ctx.total_sentences or max(len(ctx.sentences), int(idx) + 1)
        clip_number = int(idx) + 1
        logger.info("Playing sentence %d/%s", clip_number, total or "?")
        tts_engine.play_mp3_bytes(audio)
        record_timing("tts_clip_played", start)
        logger.info("Finished sentence %d/%s", clip_number, total or "?")

    if playback_done_event is not None and isinstance(
        playback_done_event, threading.Event
    ):
        playback_done_event.set()


# ────────────────────────────── PRODUCER ──────────────────────────────── #


def _sentence_producer(
    gpt_client: GPTClient,
    manager: ConversationManager,
    loop: asyncio.AbstractEventLoop,
    q: asyncio.Queue,
) -> None:
    """Stream sentences from GPT, push to queue, and launch TTS jobs immediately."""
    idx = 0.0
    ctx: Optional[_StreamContext] = getattr(q, "ctx", None)

    conv = manager.get_conversation()
    for sentence, ts_start, _ in gpt_client.sentence_stream(conv):
        if (
            ctx is not None
            and "stream_start" in ctx.timing
            and not ctx.timing.get("first_sentence_logged")
        ):
            record_timing("time_to_first_sentence", ctx.timing["stream_start"])
            ctx.timing["first_sentence_logged"] = True

        record_timing("sentence_created", ts_start)

        if ctx is not None:
            ctx.sentences.append(sentence)
            fut = asyncio.run_coroutine_threadsafe(
                _tts_job(idx, sentence, ctx, ctx.sentences), ctx.loop
            )
            ctx.tts_futures[idx] = fut

        asyncio.run_coroutine_threadsafe(q.put((idx, sentence)), loop)
        idx += 1

    if ctx is not None:
        ctx.total_sentences = len(ctx.sentences)

    asyncio.run_coroutine_threadsafe(q.put(None), loop)  # sentinel


async def _tts_job(
    idx: float, sent: str, ctx: _StreamContext, sentences: List[str]
) -> Optional[bytes]:
    """Submit blocking TTS fetch to executor."""
    prev = sentences[int(idx - 1)] if idx >= 1 else ""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        ctx.tts_executor,
        _fetch_tts_clip,
        sent,
        prev,
        ctx.cfg,
    )


def _fetch_tts_clip(text: str, prev: str, cfg: Dict[str, Any]) -> Optional[bytes]:
    """Blocking call to ElevenLabs (behavior preserved; no retries added)."""
    t0 = time.time()
    resp = requests.post(
        cfg["api_url"],
        headers={"xi-api-key": cfg["api_key"], "Content-Type": "application/json"},
        params={"output_format": cfg["fmt"]},
        json={"text": text, "model_id": cfg["model"]},  # "previous_text": prev or None
        timeout=60,
    )
    resp.raise_for_status()
    record_timing("tts_clip_generated", t0)
    return resp.content


# ────────────────────────────── SEQUENCER ──────────────────────────────── #


async def _sequencer(ctx: _StreamContext) -> None:
    """Deliver clips to the playback thread in original order."""
    expected = 0.0
    buffer: Dict[float, Optional[bytes]] = {}

    while True:
        item = await ctx.sentence_q.get()
        if item is None:  # producer sentinel
            break
        idx, _ = item

        result = ctx.tts_futures.get(idx)
        if result is None:
            continue
        try:
            audio = await asyncio.wrap_future(result)
        except Exception as exc:
            logging.error("TTS future %s failed: %s", idx, exc)
            audio = None

        buffer[idx] = audio

        # Flush in order
        while expected in buffer:
            ctx.playback_q.put_nowait((expected, buffer.pop(expected)))
            expected += 1.0

    # Flush any remainder, then signal playback worker to exit
    for k in sorted(buffer):
        ctx.playback_q.put_nowait((k, buffer[k]))
    ctx.playback_q.put_nowait((None, None))  # sentinel


# ────────────────────────────── TEAR-DOWN HELPERS ──────────────────────── #


def _finalise_conversation(manager: ConversationManager, sentences: List[str]) -> str:
    gpt_text = " ".join(sentences)
    manager.add_text_to_conversation("assistant", gpt_text)
    manager.print_memory()
    return gpt_text


def _handle_animation(
    gpt_client: GPTClient, manager: ConversationManager, arduino: ArduinoInterface
) -> Any:
    anim = gpt_client.reply_with_animation(manager.get_conversation())
    arduino.set_animation(anim)
    return anim


# =================== Main Async Conversation Loop ===================


async def async_conversation_loop(
    manager: ConversationManager,
    gpt_client: GPTClient,
    stt_engine: Optional[SpeechToTextEngine],
    tts_engine: Optional[TextToSpeechEngine],
    arduino_interface: ArduinoInterface,
    stt_enabled: bool,
    tts_enabled: bool,
) -> None:
    """Run the asynchronous interaction loop handling events, tools, and replies."""
    queue: asyncio.Queue[Any] = asyncio.Queue()
    input_allowed_event = asyncio.Event()
    input_allowed_event.set()  # Allow input initially

    # Start background producers
    user_task = asyncio.create_task(user_input_producer(queue, input_allowed_event))
    hotword_task: Optional[asyncio.Task] = (
        asyncio.create_task(stt_engine.hotword_listener(queue, tts_engine=tts_engine))
        if stt_enabled and stt_engine
        else None
    )

    print("🤖 Assistant running. Type 'exit' to quit. Type or say hotword to speak.\n")
    try:
        while True:
            event = await get_event(queue)
            turn_start = time.time()

            if process_event(event, manager):
                user_task.cancel()
                if hotword_task:
                    hotword_task.cancel()
                break

            workflow_start = time.time()
            workflow_hotword = run_tool_workflow(
                manager,
                gpt_client,
                queue,
                stt_engine=stt_engine,
                tts_engine=tts_engine,
                hotword_task=hotword_task,
            )
            if workflow_hotword is not None:
                hotword_task = workflow_hotword
            record_timing("tool_workflow", workflow_start)

            # ✅ Allow TTS to stream even when STT is disabled
            if tts_enabled and tts_engine:
                input_allowed_event.clear()  # Block input while TTS is playing
                playback_done_event = threading.Event()

                response_start = time.time()
                gpt_text, animation, hotword_task = await stream_assistant_reply(
                    manager,
                    gpt_client,
                    tts_engine,
                    stt_engine,  # may be None
                    queue,
                    hotword_task,
                    stt_enabled,
                    arduino_interface,
                    playback_done_event=playback_done_event,
                )
                record_timing("stream_assistant_reply", response_start)

                # Allow input immediately after playback (already awaited inside)
                input_allowed_event.set()
            else:
                response_start = time.time()
                gpt_text, animation = generate_assistant_reply(manager, gpt_client)
                record_timing("generate_assistant_reply", response_start)

            logger.info("Animation selected: %s", animation)
            print(
                Fore.GREEN + Style.BRIGHT + f"\nAssistant: {gpt_text}" + Style.RESET_ALL
            )
            print(
                f"{Fore.LIGHTBLACK_EX}{Style.BRIGHT}\n"
                f"»»» Ready for your input! Type below...{Style.RESET_ALL}"
            )

            record_timing("user_turn_total", turn_start)

    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.warning("KeyboardInterrupt or cancellation received; shutting down loop")
    finally:
        logger.info("Cleaning up resources...")
        export_timings()

        # Cancel any remaining tasks (except current)
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        if stt_engine and hasattr(stt_engine, "cleanup"):
            stt_engine.cleanup()

        print("👋 Exiting…")


# =================== Streaming Reply ===================


async def stream_assistant_reply(
    manager: ConversationManager,
    gpt_client: GPTClient,
    tts_engine: TextToSpeechEngine,
    stt_engine: Optional[SpeechToTextEngine],  # <- now Optional
    queue: asyncio.Queue[Any],
    hotword_task: Optional[asyncio.Task],
    stt_enabled: bool,
    arduino_interface: ArduinoInterface,
    playback_done_event: Optional[threading.Event] = None,
) -> Tuple[str, Any, Optional[asyncio.Task]]:
    """Stream GPT sentences to TTS playback and resume the hot-word listener."""
    stream_start = time.time()

    if stt_enabled and stt_engine:
        stt_engine.pause_listening()

    cfg = _prepare_stream(stt_enabled, stt_engine, hotword_task)
    cfg["tts_engine"] = tts_engine
    ctx = _make_context(cfg, manager)
    ctx.timing["stream_start"] = stream_start
    ctx.play_executor.submit(_playback_worker, ctx, playback_done_event)
    ctx.sentence_q.ctx = ctx  # type: ignore[attr-defined]

    # Start the sentence producer in a thread
    producer_thread = threading.Thread(
        target=_sentence_producer,
        args=(gpt_client, manager, ctx.loop, ctx.sentence_q),
        daemon=True,
    )
    producer_thread.start()

    await _sequencer(ctx)

    gpt_text = _finalise_conversation(manager, ctx.sentences)
    logger.debug("Full assistant reply captured: %s", gpt_text)
    logger.info("Reply sentences: %d", len(ctx.sentences))
    animation = _handle_animation(gpt_client, manager, arduino_interface)

    # Wait for playback to fully finish before resuming listening
    if playback_done_event is not None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, playback_done_event.wait)

    if stt_enabled and stt_engine:
        stt_engine.resume_listening()
        follow_start = time.time()
        hotword_task = await handle_follow_up_after_stream(
            stt_engine, queue, hotword_task, stt_enabled, tts_engine
        )
        record_timing("post_stream_follow_up", follow_start)

    logger.info("Reply streaming complete")
    return gpt_text, animation, hotword_task


# =================== Initialization / Main ===================


def initialize() -> Tuple[
    bool,
    bool,
    ConversationManager,
    GPTClient,
    Optional[SpeechToTextEngine],
    Optional[TextToSpeechEngine],
    ArduinoInterface,
]:
    """
    Initialize the assistant system and return core components.

    Returns:
        (stt_enabled, tts_enabled, manager, gpt_client, stt_engine, tts_engine, arduino_interface)
    """
    clear_timings()
    atexit.register(export_timings)
    config = load_config()

    stt_enabled = bool(config["stt"]["enabled"])
    tts_enabled = bool(config["tts"]["enabled"])

    print(feature_summary(stt_enabled, tts_enabled, "Feature Status"))

    # Authenticate external services and update feature flags accordingly
    stt_enabled, tts_enabled = authenticate_and_update_features(
        stt_enabled, tts_enabled
    )

    # Initialize core components
    max_mem = config["app"].get("max_memory")
    manager = ConversationManager(max_memory=max_mem)

    gpt_model = config["llm"].get("model")
    gpt_client = GPTClient(model=gpt_model)

    initial_mem = Functions().read_long_term_memory()
    manager.update_memory(f"LONG TERM MEMORY:\n{initial_mem}")

    stt_engine = SpeechToTextEngine() if stt_enabled else None
    tts_engine = TextToSpeechEngine() if tts_enabled else None

    port, dry_run = _detect_serial_port()
    arduino_interface = _init_arduino(port, dry_run, stt_engine)

    # Neutral pose on startup
    arduino_interface.set_animation("neutral")

    # Warm-up conversation
    manager.add_text_to_conversation("user", "Hello, please introduce yourself.")
    conv = manager.get_conversation()
    gpt_text = gpt_client.get_text(conv)
    manager.add_text_to_conversation("assistant", gpt_text)
    manager.print_memory()

    animation = gpt_client.reply_with_animation(conv)
    arduino_interface.set_animation(animation)

    if tts_enabled and tts_engine:
        tts_engine.generate_and_play_advanced(gpt_text)
    else:
        print("Assistant:", gpt_text)

    return (
        stt_enabled,
        tts_enabled,
        manager,
        gpt_client,
        stt_engine,
        tts_engine,
        arduino_interface,
    )


def main() -> None:
    """CLI entry point for launching the Wheatley assistant and starting the main event loop."""
    (
        stt_enabled,
        tts_enabled,
        manager,
        gpt_client,
        stt_engine,
        tts_engine,
        arduino_interface,
    ) = initialize()
    print_welcome()

    try:
        asyncio.run(
            async_conversation_loop(
                manager,
                gpt_client,
                stt_engine,
                tts_engine,
                arduino_interface,
                stt_enabled,
                tts_enabled,
            )
        )
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt received in main thread; exiting")
        if stt_engine and hasattr(stt_engine, "cleanup"):
            try:
                stt_engine.cleanup()
            except Exception as e:
                logger.error("Error during stt_engine cleanup: %s", e)
        sys.exit(0)


if __name__ == "__main__":
    main()


# ------------------------ Small Unit-Style Examples ------------------------
# These are comments/examples for quick sanity checks (not executed here).
#
# Example: Event stringification
# e = Event("timer", "tea", {"duration": "3m"})
# assert "TIMER" in str(e)
#
# Example: Sequencer ordering (conceptual)
# - Feed sentences (0, 1, 2) -> ensure playback_q receives in the same order.
#
# Example: Tool workflow preprocessing
# workflow = [
#     {"name": "web_search_call_result", "arguments": {"text": "foo"}},
#     {"name": "do_something", "arguments": {"x": 1}},
# ]
# manager = ConversationManager(max_memory=None)
# _execute_workflow(workflow, asyncio.Queue(), manager)  # preserves order for executable
