"""Main entry point for the Wheatley assistant.

This module wires together the speech-to-text engine, large language
model client, text-to-speech engine and Arduino hardware interface. It
provides an asynchronous event loop that reacts to user input and
controls the servos and LED animations on the robot.
"""

# =================== Imports: Standard Libraries ===================
import os  # For file and path operations
import logging  # For logging events and timings
import time  # For timing actions
import asyncio  # For async event loop
from typing import Any, List, Tuple, Dict, Optional  # For type hints
from datetime import datetime  # For timestamps
import sys
import atexit
from queue import Queue
import requests
import json

# =================== Imports: Third-Party Libraries ===================
import yaml  # For reading YAML config files
from colorama import init, Fore, Style  # For colored terminal output
import threading  # already imported, but safe to repeat
from concurrent.futures import ThreadPoolExecutor
import re
from dataclasses import dataclass, field

# =================== Imports: Local Modules ===================
from hardware.arduino_interface import ArduinoInterface  # Arduino hardware interface
from assistant.assistant import ConversationManager  # Manages conversation history
from llm.llm_client import GPTClient, Functions  # LLM client and function tools
from tts.tts_engine import TextToSpeechEngine  # Text-to-speech engine
from stt.stt_engine import SpeechToTextEngine  # Speech-to-text engine
from utils.timing_logger import export_timings, clear_timings, record_timing
from utils.main_helpers import feature_summary, authenticate_and_update_features

# =================== Initialization ===================
# Initialize colorama for colored terminal output
init(autoreset=True)

# =================== Helper Functions and Constants ===================

# Sentence parsing and TTS streaming settings
PUNCT_RE = re.compile(r'[.!?]\s+')
ABBREVS = {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st"}
MAX_TTS_WORKERS = 2
QUEUE_MAXSIZE = 100
MAX_ATTEMPTS = 6
MAX_CHAIN_RETRY = 10

# Robust logging setup: always log to file only
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remove all handlers associated with the root logger object (prevents duplicate logs)
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

file_handler = logging.FileHandler('assistant.log', mode='w', encoding='utf-8')
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

# Suppress verbose HTTP logs from openai, httpx, and requests
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)


# =================== Configuration Loader ===================
def load_config():
    """Load and return the YAML configuration as a dictionary from config/config.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# =================== Welcome Banner ===================
def print_welcome():
    """Print a retro ASCII art welcome banner to the terminal."""
    reset = "\033[0m"
    retro_color = "\033[95m"
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
    print(f"{retro_color}Welcome to the AI Assistant!{reset}")


# ────────────────────────── PRIVATE HELPERS ──────────────────────────── #

def _detect_serial_port() -> tuple[str | None, bool]:
    """Return (best_port, dry_run_flag) based on OS and availability."""
    dry_run, port = False, None

    if sys.platform.startswith(("linux", "darwin")):
        print("Available ports:")
        os.system("ls /dev/tty*")
        port = "/dev/ttyACM0"

    elif sys.platform.startswith("win"):
        from serial.tools import list_ports

        ports = list(list_ports.comports())
        print("Available ports:")
        for p in ports:
            print(p.device)

        port = next((p.device for p in ports if p.device == "COM7"), None)
        dry_run = not port
        if dry_run:
            print("No serial ports found. Running in dry-run mode.")

    return port, dry_run


def _init_arduino(port, dry_run, stt_engine):
    """Create (or stub) ArduinoInterface and wire it to the STT engine."""
    if not port or dry_run:
        arduino = ArduinoInterface(port="dryrun", dry_run=True)
    else:
        try:
            arduino = ArduinoInterface(port=port)
            arduino.connect()
        except Exception as exc:  # pragma: no cover
            print(f"Could not connect to Arduino on {port}: {exc}. Falling back to dry-run.")
            arduino = ArduinoInterface(port=port, dry_run=True)

    if stt_engine:
        stt_engine.arduino_interface = arduino
    return arduino


# =================== Event Dataclass ===================
@dataclass
class Event:
    """Simple event container used by the async event loop."""

    source: str        # e.g. "user", "timer", "gpio", "webhook", etc.
    payload: str       # human-readable description
    metadata: Optional[Dict[str, Any]] = None
    ts: Optional[datetime] = None

    def __str__(self):
        """Return a string representation of the event."""
        meta = f" {self.metadata}" if self.metadata else ""
        ts = f" ({self.ts.isoformat()})" if self.ts else ""
        return f"[{self.source.upper()}] {self.payload}{meta}{ts}"


# =================== Async Event Handling ===================
async def user_input_producer(q: asyncio.Queue, input_allowed_event: asyncio.Event):
    """Asynchronously read user text input and push Event objects to the queue. Waits for input_allowed_event to be set before pushing input."""
    loop = asyncio.get_event_loop()
    while True:
        await input_allowed_event.wait()  # Block input if not allowed
        text = await loop.run_in_executor(None, input, "You: ")
        # Wait here if TTS is still playing (input_allowed_event not set)
        print("Waiting for input to be allowed...")
        while not input_allowed_event.is_set():
            await input_allowed_event.wait()
        await q.put(Event("user", text.strip(), {"input_type": "text"}))
        if text.strip().lower() == "exit":
            break


async def get_event(queue: asyncio.Queue):
    """Retrieve the next event from the queue and normalize voice dicts to Event objects."""
    incoming = await queue.get()
    if isinstance(incoming, dict) and incoming.get("type") == "voice":
        return Event("user", incoming.get("text", ""), {"input_type": "voice"})
    return incoming


# =================== System Event Handling ===================
# Insert system messages when events come from timers or reminders
def handle_non_user_event(event: Event, manager: ConversationManager):
    """Add system messages to the conversation based on non-user events (timers, reminders, etc)."""
    if event.source == "timer":
        timer_label = event.payload
        timer_duration = event.metadata.get("duration") if event.metadata else None
        timer_msg = (
            f"TIMER labeled {timer_label} for {timer_duration} is up inform the user."
            if timer_duration
            else f"TIMER UP: {timer_label}"
        )
        manager.add_text_to_conversation("system", timer_msg)
    elif event.source == "reminder":
        reminder_text = event.payload
        manager.add_text_to_conversation(
            "system", f"Reminder has triggered with the following text: {reminder_text}"
        )
    else:
        manager.add_text_to_conversation("system", str(event))


# Update conversation history and return True if user requested to exit
def process_event(event: Event, manager: ConversationManager):
    """Update conversation with the event and determine if exit was requested by the user."""
    if event.source == "user":
        manager.add_text_to_conversation("user", event.payload)
        if event.payload.lower() == "exit":
            return True
    else:
        handle_non_user_event(event, manager)
    return False


def run_tool_workflow(
    manager: "ConversationManager",
    gpt_client: "GPTClient",
    queue: asyncio.Queue,
    *,
    stt_engine: Optional["SpeechToTextEngine"] = None,
    tts_engine: Optional["TextToSpeechEngine"] = None,
    hotword_task: Optional[asyncio.Task] = None,
) -> Optional[asyncio.Task]:
    """Ask GPT for a workflow, execute its tools, and add the results to the conversation.

    While tools run (and we narrate what we're doing), temporarily pause STT and stop the hotword listener,
    then resume and restart it afterward. Returns the possibly updated hotword_task.
    """
    # Pause listening and cancel hotword while executing tools to prevent self-hearing
    if hotword_task:
        hotword_task.cancel()
        hotword_task = None
    if stt_engine:
        stt_engine.pause_listening()

    executed_workflows = 0
    seen_signatures: set[tuple[str, ...]] = set()

    for attempt in range(1, MAX_CHAIN_RETRY + 1):
        workflow = gpt_client.get_workflow(manager.get_conversation())
        if not workflow:
            return _resume_hotword_listener(stt_engine, queue, tts_engine)

        # inject context from web search results into the conversation
        for item in list(workflow):  # iterate over a static copy
            if item.get("name") == "web_search_call_result":
                text = item.get("arguments", {}).get("text", "")
                if text:
                    manager.add_text_to_conversation("system", f"Info: {text}")
                workflow.remove(item)  # mutate original list

        if not workflow:
            logging.info("Tool workflow attempt %d had no executable calls after preprocessing.", attempt)
            continue

        signature = tuple(
            sorted(
                json.dumps({
                    "name": item.get("name"),
                    "arguments": item.get("arguments", {}),
                }, sort_keys=True)
                for item in workflow
            )
        )
        if signature in seen_signatures:
            logging.info("Duplicate workflow signature detected on attempt %d; stopping to avoid loops.", attempt)
            break
        seen_signatures.add(signature)
        print(f"Seen signatures: {seen_signatures}")

        mem = Functions().read_long_term_memory()
        manager.update_memory(f"LONG TERM MEMORY:\n{mem}")

        _execute_workflow(workflow, queue, manager)
        executed_workflows += 1

    return _resume_hotword_listener(stt_engine, queue, tts_engine)


# ────────────────────────────── Helpers ─────────────────────────────────── #

def _resume_hotword_listener(
    stt_engine: Optional["SpeechToTextEngine"],
    queue: asyncio.Queue,
    tts_engine: Optional["TextToSpeechEngine"],
) -> Optional[asyncio.Task]:
    """Resume listening and restart the hotword listener if needed."""
    if stt_engine:
        stt_engine.resume_listening()
        loop = asyncio.get_running_loop()
        return loop.create_task(stt_engine.hotword_listener(queue, tts_engine=tts_engine))
    return None


def _execute_workflow(
    workflow: List[Dict[str, Any]],
    queue: asyncio.Queue,
    manager,
) -> None:
    """Run tools via Functions.execute_workflow and append their results to the conversation history."""
    if not workflow:
        return

    logging.info(
        "Executing workflow with %d call(s): %s",
        len(workflow),
        ", ".join(call.get("name", "unknown") for call in workflow),
    )

    # Pretty-print the proposed calls for console visibility
    for call in workflow:
        print(f"Tool Name: {call.get('name', 'unknown')}")
        print(f"Arguments: {call.get('arguments', {})}")
        if call.get("call_id"):
            print(f"Call ID: {call.get('call_id')}")

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
        logging.info(
            "Tool '%s' (call_id=%s) result: %s",
            name,
            call_id,
            result_text,
        )
        manager.add_text_to_conversation("system", result_text)


# =================== Assistant Reply Generation ===================
# Ask the LLM for a textual reply and matching animation
def generate_assistant_reply(manager: ConversationManager, gpt_client: GPTClient):
    """Fetch assistant text and animation from the LLM and update conversation history."""
    gpt_text = gpt_client.get_text(manager.get_conversation())
    manager.add_text_to_conversation("assistant", gpt_text)
    manager.print_memory()
    animation = gpt_client.reply_with_animation(manager.get_conversation())
    return gpt_text, animation


async def handle_follow_up_after_stream(stt_engine, event_queue, hotword_task, stt_enabled, tts_engine=None):
    """Handle follow-up voice recording after streaming TTS playback."""
    stt_engine.resume_listening()

    # Always listen for follow-up without hotword for 5 seconds after TTS
    print("[STT] Listening for follow-up without hotword for 5 seconds...")
    loop = asyncio.get_event_loop()
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

    hotword_task = asyncio.create_task(stt_engine.hotword_listener(event_queue, tts_engine=tts_engine))
    print("[STT] Hotword listener resumed.")
    return hotword_task


async def stream_assistant_reply(
    manager,
    gpt_client,
    tts_engine,
    stt_engine,
    queue,
    hotword_task,
    stt_enabled: bool,
    arduino_interface,
    playback_done_event=None,  # new argument
) -> Tuple[str, Any, asyncio.Task]:
    """
    Stream GPT-generated sentences → TTS → audio output.

    It hands control back to the hot-word listener.
    """
    stream_start = time.time()
    # Always pause listening before streaming TTS
    if stt_enabled and stt_engine:
        stt_engine.pause_listening()

    cfg = _prepare_stream(stt_enabled, stt_engine, hotword_task)
    cfg['tts_engine'] = tts_engine
    ctx = _make_context(cfg, manager)
    ctx.timing["stream_start"] = stream_start
    ctx.play_executor.submit(_playback_worker, ctx.playback_q, ctx.cfg["tts_engine"], playback_done_event)
    ctx.sentence_q.ctx = ctx
    # Start the sentence producer in a thread (it will launch TTS jobs)
    producer_thread = threading.Thread(
        target=_sentence_producer,
        args=(gpt_client, manager, ctx.loop, ctx.sentence_q),
        daemon=True,
    )
    producer_thread.start()

    await _sequencer(ctx)

    gpt_text = _finalise_conversation(manager, ctx.sentences)
    print(f"[Conversation] Full assistant reply: {gpt_text}")
    animation = _handle_animation(gpt_client, manager, arduino_interface)
    # Wait for playback to fully finish before resuming listening
    if playback_done_event is not None and isinstance(playback_done_event, threading.Event):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, playback_done_event.wait)
    # Resume listening after playback; then run 5s no-hotword follow-up and restart hotword listener
    if stt_enabled and stt_engine:
        stt_engine.resume_listening()
        follow_start = time.time()
        hotword_task = await handle_follow_up_after_stream(
            stt_engine, queue, hotword_task, stt_enabled, tts_engine
        )
        record_timing("post_stream_follow_up", follow_start)

    print("[Stream] Finished streaming")
    return gpt_text, animation, hotword_task


# ────────────────────────────── DATA STRUCTS ──────────────────────────── #


@dataclass
class _StreamContext:
    sentences: list[str] = field(default_factory=list)
    sentence_q: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(QUEUE_MAXSIZE))
    tts_futures: dict[float, asyncio.Future] = field(default_factory=dict)
    playback_q: Queue = field(default_factory=lambda: Queue(QUEUE_MAXSIZE))
    timing: dict = field(default_factory=dict)
    loop: asyncio.AbstractEventLoop = field(default_factory=asyncio.get_running_loop)
    tts_executor: ThreadPoolExecutor | None = None      # set in _make_context
    play_executor: ThreadPoolExecutor | None = None     # ditto
    cfg: dict = field(default_factory=dict)


# ────────────────────────────── SET-UP HELPERS ────────────────────────── #

def _prepare_stream(stt_enabled: bool, stt_engine, hotword_task):
    """Pause hot-word + STT and return (possibly canceled) hotword_task."""
    # record_timing("streaming_start")
    if hotword_task:
        hotword_task.cancel()
    if stt_enabled:
        stt_engine.pause_listening()
    return {"hotword_task": hotword_task}


def _make_context(cfg: dict, manager) -> _StreamContext:
    conf = load_config()
    ctx = _StreamContext(
        cfg={
            "api_url": f"https://api.elevenlabs.io/v1/text-to-speech/"
                       f"{conf['tts'].get('voice_id', '4Jtuv4wBvd95o1hzNloV')}",
            "api_key": conf["secrets"]["elevenlabs_api_key"],
            "model": conf["tts"].get("model_id", "eleven_flash_v2_5"),
            "fmt": conf["tts"].get("output_format", "mp3_22050_32"),
            "tts_engine": cfg.get("tts_engine"),
        }
    )
    # Thread pools -------------------------------------------------------
    ctx.tts_executor = ThreadPoolExecutor(max_workers=MAX_TTS_WORKERS, thread_name_prefix="TTS")
    ctx.play_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="PLAY")
    return ctx


def _playback_worker(q: Queue, tts_engine, playback_done_event=None):
    """Playback worker runs in its own thread; plays clips in FIFO order. Signals when done."""
    while True:
        idx, audio = q.get()
        if idx is None:                      # sentinel ⇒ shutdown
            break
        if audio is None:
            continue
        start = time.time()
        print(f"[Player] Playing clip {idx}")
        tts_engine.play_mp3_bytes(audio)
        record_timing("tts_clip_played", start)
        print(f"[Player] Finished clip {idx}")
    if playback_done_event is not None:
        if isinstance(playback_done_event, threading.Event):
            playback_done_event.set()


# ────────────────────────────── PRODUCER ──────────────────────────────── #
def _sentence_producer(gpt_client, manager, loop, q: asyncio.Queue) -> None:
    """Stream sentences from GPT and push them to *q* from a thread. Also launch TTS jobs immediately."""
    idx = 0.0
    ctx = getattr(q, 'ctx', None)
    for sentence, ts_start, _ in gpt_client.sentence_stream(manager.get_conversation()):
        if ctx is not None and "stream_start" in ctx.timing and not ctx.timing.get("first_sentence_logged"):
            record_timing("time_to_first_sentence", ctx.timing["stream_start"])
            ctx.timing["first_sentence_logged"] = True
        print(f"[Producer] Sentence {idx} created: {sentence}")
        record_timing("sentence_created", ts_start)
        if ctx is not None:
            ctx.sentences.append(sentence)
            # Launch TTS job immediately for maximal concurrency
            fut = asyncio.run_coroutine_threadsafe(
                _tts_job(idx, sentence, ctx, ctx.sentences), ctx.loop
            )
            ctx.tts_futures[idx] = fut
        asyncio.run_coroutine_threadsafe(q.put((idx, sentence)), loop)
        idx += 1
    asyncio.run_coroutine_threadsafe(q.put(None), loop)    # sentinel


async def _tts_job(idx, sent, ctx, sentences):
    prev = sentences[int(idx - 1)] if idx >= 1 else ""
    nxt = ""                                # still unknown at launch
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        ctx.tts_executor,
        _fetch_tts_clip,
        sent, prev, nxt, ctx.cfg,
    )


def _fetch_tts_clip(
    text: str, prev: str, nxt: str, cfg: dict
) -> bytes | None:
    """Blocking call to ElevenLabs with retries."""
    t0 = time.time()
    resp = requests.post(
        cfg["api_url"],
        headers={"xi-api-key": cfg["api_key"], "Content-Type": "application/json"},
        params={"output_format": cfg["fmt"]},
        json={
            "text": text,
            "model_id": cfg["model"],
            "previous_text": prev or None,
            "next_text": nxt or None,
        },
        timeout=60,
    )
    resp.raise_for_status()
    record_timing("tts_clip_generated", t0)
    return resp.content


# ────────────────────────────── SEQUENCER ──────────────────────────────── #

async def _sequencer(ctx: _StreamContext) -> None:
    """Deliver clips to the playback thread in original order."""
    expected = 0.0
    buffer: dict[float, bytes] = {}

    while True:
        item = await ctx.sentence_q.get()
        if item is None:                             # producer sent sentinel
            break
        idx, _ = item
        # Fetch the TTS result for this index
        result = ctx.tts_futures.get(idx)
        if result is None:
            continue
        try:
            audio = await asyncio.wrap_future(result)   # wait only for TTS
        except Exception as exc:
            logging.error("TTS future %s failed: %s", idx, exc)
            audio = None
        buffer[idx] = audio

        while expected in buffer:                    # maintain order
            ctx.playback_q.put_nowait((expected, buffer.pop(expected)))
            expected += 1.0

    # flush any remainder, then signal playback worker to exit
    for k in sorted(buffer):
        ctx.playback_q.put_nowait((k, buffer[k]))
    ctx.playback_q.put_nowait((None, None))          # sentinel


# ────────────────────────────── TEAR-DOWN HELPERS ──────────────────────── #

def _finalise_conversation(manager, sentences: List[str]) -> str:
    gpt_text = " ".join(sentences)
    manager.add_text_to_conversation("assistant", gpt_text)
    manager.print_memory()
    return gpt_text


def _handle_animation(gpt_client, manager, arduino):
    anim = gpt_client.reply_with_animation(manager.get_conversation())
    arduino.set_animation(anim)
    return anim


# =================== Main Async Conversation Loop ===================
async def async_conversation_loop(manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled):
    """Run the main asynchronous interaction loop handling user events, tool calls, and assistant responses."""
    queue: asyncio.Queue = asyncio.Queue()
    input_allowed_event = asyncio.Event()
    input_allowed_event.set()  # Allow input initially

    # Start background producers
    user_task = asyncio.create_task(user_input_producer(queue, input_allowed_event))
    hotword_task = (
        asyncio.create_task(stt_engine.hotword_listener(queue, tts_engine=tts_engine)) if stt_enabled else None
    )

    print("🤖 Assistant running. Type 'exit' to quit. Type or say hotword to speak.\n")
    try:
        while True:
            event = await get_event(queue)
            # print(event)
            turn_start = time.time()

            exit_requested = process_event(event, manager)
            if exit_requested:
                user_task.cancel()
                if hotword_task:
                    hotword_task.cancel()
                break

            workflow_start = time.time()
            hotword_task = run_tool_workflow(
                manager, gpt_client, queue,
                stt_engine=stt_engine,
                tts_engine=tts_engine,
                hotword_task=hotword_task,
            ) or hotword_task
            record_timing("tool_workflow", workflow_start)
            if tts_enabled:
                input_allowed_event.clear()  # Block input while TTS is playing
                playback_done_event = threading.Event()
                response_start = time.time()
                gpt_text, animation, hotword_task = await stream_assistant_reply(
                    manager,
                    gpt_client,
                    tts_engine,
                    stt_engine,
                    queue,
                    hotword_task,
                    stt_enabled,
                    arduino_interface,
                    playback_done_event=playback_done_event,
                )
                record_timing("stream_assistant_reply", response_start)
                # Wait for playback to finish before allowing input
                while not playback_done_event.is_set():
                    await asyncio.sleep(0.2)
                input_allowed_event.set()  # Allow input after TTS is done
            else:
                response_start = time.time()
                gpt_text, animation = generate_assistant_reply(manager, gpt_client)
                record_timing("generate_assistant_reply", response_start)

            # The animation is applied during streaming so it matches the speech
            print(f"[Animation chosen]: {animation}")

            # arduino_interface.servo_controller.print_servo_status()
            print(Fore.GREEN + Style.BRIGHT + f"\nAssistant: {gpt_text}" + Style.RESET_ALL)
            print(Fore.LIGHTBLACK_EX + Style.BRIGHT + "\n»»» Ready for your input! Type below..." + Style.RESET_ALL)

            record_timing("user_turn_total", turn_start)
            # Follow-up after TTS is handled inside stream_assistant_reply

    except (asyncio.CancelledError, KeyboardInterrupt):
        print("\n[Main] KeyboardInterrupt or CancelledError received. Exiting...")
    finally:
        # --- CLEANUP SECTION ---
        print("[Shutdown] Cleaning up resources...")
        export_timings()
        # Cancel any remaining tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for t in tasks:
            t.cancel()
        # Await their cancellation
        await asyncio.gather(*tasks, return_exceptions=True)
        # Cleanup STT engine if it has a cleanup method
        if hasattr(stt_engine, "cleanup"):
            stt_engine.cleanup()
        print("👋 Exiting…")


def initialize():
    """Initialize the assistant system and return core components."""
    clear_timings()
    atexit.register(export_timings)
    config = load_config()

    # sett global TTS and STT booleans
    stt_enabled = config["stt"]["enabled"]
    tts_enabled = config["tts"]["enabled"]

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

    # Initialize STT and TTS engines if enabled
    stt_engine = SpeechToTextEngine() if stt_enabled else None
    tts_engine = TextToSpeechEngine() if tts_enabled else None

    port, dry_run = _detect_serial_port()
    arduino_interface = _init_arduino(port, dry_run, stt_engine)

    # Establish a neutral pose on startup and display servo status
    arduino_interface.set_animation("neutral")  # Set initial animation to neutral
    # arduino_interface.servo_controller.print_servo_status()

    # --- Warm-up conversation -----------------------------------------
    # Ask the assistant to introduce itself so we can verify everything works
    manager.add_text_to_conversation("user", "Hello, please introduce yourself.")
    gpt_text = gpt_client.get_text(manager.get_conversation())
    manager.add_text_to_conversation("assistant", gpt_text)
    manager.print_memory()

    animation = gpt_client.reply_with_animation(manager.get_conversation())
    arduino_interface.set_animation(animation)  # Set initial animation

    if tts_enabled:
        tts_engine.generate_and_play_advanced(gpt_text)
    else:
        print("Assistant:", gpt_text)

    return stt_enabled, tts_enabled, manager, gpt_client, stt_engine, tts_engine, arduino_interface


# =================== Main Code ===================
def main():
    """CLI entry point for launching the Wheatley assistant and starting the main event loop."""
    # --- Setup and configuration ---------------------------------------

    stt_enabled, tts_enabled, manager, gpt_client, stt_engine, tts_engine, arduino_interface = initialize()

    print_welcome()

    try:
        # Start the async event-based conversation loop
        asyncio.run(async_conversation_loop(manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled))
    except KeyboardInterrupt:
        print("\n[KeyboardInterrupt] Exiting...")
        if hasattr(stt_engine, "cleanup"):
            try:
                stt_engine.cleanup()
            except Exception as e:
                print(f"[Shutdown] Error during stt_engine cleanup: {e}")
        sys.exit(0)


if __name__ == "__main__":
    main()
