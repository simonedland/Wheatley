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
import asyncio
from dataclasses import dataclass
from typing import Dict, Any, Optional
import sys
import argparse
import atexit

# =================== Imports: Third-Party Libraries ===================
import yaml  # For reading YAML config files
import openai  # For OpenAI API access
from colorama import init, Fore, Style  # For colored terminal output
import pathlib
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
import io
import re
import random

# =================== Imports: Local Modules ===================
from hardware.arduino_interface import ArduinoInterface  # Arduino hardware interface
from assistant.assistant import ConversationManager  # Manages conversation history
from llm.llm_client import GPTClient, Functions  # LLM client and function tools
from tts.tts_engine import TextToSpeechEngine  # Text-to-speech engine
from stt.stt_engine import SpeechToTextEngine  # Speech-to-text engine
from utils.timing_logger import export_timings, clear_timings, record_timing


# Initialize colorama for colored terminal output
init(autoreset=True)

# =================== Helper Functions ===================

# Sentence parsing and TTS streaming settings
PUNCT_RE = re.compile(r'[.!?]\s+')
ABBREVS = {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st"}
MAX_TTS_WORKERS = 2
QUEUE_MAXSIZE = 100
MAX_ATTEMPTS = 6

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
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

# Load configuration from YAML file
def load_config():
    """Return the YAML configuration as a dictionary."""

    config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

# Print ASCII art welcome message to the terminal
def print_welcome():
    """Display a retro style welcome banner."""

    RESET = "\033[0m"
    RETRO_COLOR = "\033[95m"
    print(r"""
⠀⠀⡀⠀⠀⠀⣀⣠⣤⣤⣤⣤⣤⣤⣤⣤⣤⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀
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
    print(f"{RETRO_COLOR}Welcome to the AI Assistant!{RESET}")

# =================== Assistant Initialization ===================
# Set up all assistant components (LLM, TTS, STT, Arduino, etc.)
def initialize_assistant(config, *, stt_enabled: bool | None = None, tts_enabled: bool | None = None):
    """Initialise and return all major subsystems."""

    start_time = time.time()  # Start timing initialization
    if stt_enabled is None:
        stt_enabled = config["stt"]["enabled"]  # Speech-to-text enabled
    if tts_enabled is None:
        tts_enabled = config["tts"]["enabled"]  # Text-to-speech enabled
    assistant_config = config.get("app")  # App-specific config
    max_memory = assistant_config.get("max_memory")  # Conversation memory size
    llm_config = config.get("llm")  # LLM config
    gpt_model = llm_config.get("model")  # LLM model name
    
    # Initialize core components
    manager = ConversationManager(max_memory=max_memory)
    gpt_client = GPTClient(model=gpt_model)
    # Fetch long term memory once at startup
    initial_memory = Functions().read_long_term_memory()
    manager.update_memory(f"LONG TERM MEMORY:\n{initial_memory}")
    stt_engine = SpeechToTextEngine() if stt_enabled else None
    tts_engine = TextToSpeechEngine() if tts_enabled else None
    import sys
    port = None
    dry_run = False
    # Detect available serial ports for Arduino (platform-specific)
    if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
        print("Available ports:")
        os.system("ls /dev/tty*")
        port = "/dev/ttyACM0"
    elif sys.platform.startswith("win"):
        from serial.tools import list_ports
        ports = list(list_ports.comports())
        print("Available ports:")
        for p in ports:
            print(p.device)
        # Try to use COM7 if available, else use first available port
        port = None
        for p in ports:
            if p.device == "COM7":
                port = "COM7"
        if not port:
            print("No serial ports found. Running in dry run mode.")
            dry_run = True
    # Initialize Arduino interface with error handling
    arduino_interface = None
    if port and not dry_run:
        try:
            arduino_interface = ArduinoInterface(port=port)
            arduino_interface.connect()
            if stt_engine:
                stt_engine.arduino_interface = arduino_interface
        except Exception as e:
            print(f"Could not connect to Arduino on {port}: {e}. Running in dry run mode.")
            arduino_interface = ArduinoInterface(port=port, dry_run=True)
            if stt_engine:
                stt_engine.arduino_interface = arduino_interface
    else:
        arduino_interface = ArduinoInterface(port="dryrun", dry_run=True)
        if stt_engine:
            stt_engine.arduino_interface = arduino_interface
    elapsed = time.time() - start_time
    # Return all initialized components and feature flags
    return manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled

# =================== Event Dataclass ===================
@dataclass
class Event:
    """Simple event container used by the async event loop."""

    source: str        # e.g. "user", "timer", "gpio", "webhook", etc.
    payload: str       # human-readable description
    metadata: Optional[Dict[str, Any]] = None

    def __str__(self):
        meta = f" {self.metadata}" if self.metadata else ""
        return f"[{self.source.upper()}] {self.payload}{meta}"

# =================== Async Event Handling ===================
async def user_input_producer(q: asyncio.Queue):
    """Asynchronously read user text input and push ``Event`` objects to ``q``."""
    loop = asyncio.get_event_loop()
    while True:
        text = await loop.run_in_executor(None, input, "You: ")
        await q.put(Event("user", text.strip(), {"input_type": "text"}))
        if text.strip().lower() == "exit":
            break
# Simple wrapper to print an event object
def print_event(event: Event):
    """Helper to display an ``Event`` on stdout."""
    print(event)


async def get_event(queue: asyncio.Queue):
    """Retrieve the next event from ``queue`` and normalise voice dicts."""
    incoming = await queue.get()
    if isinstance(incoming, dict) and incoming.get("type") == "voice":
        return Event("user", incoming.get("text", ""), {"input_type": "voice"})
    return incoming


# Insert system messages when events come from timers or reminders
def handle_non_user_event(event: Event, manager: ConversationManager):
    """Add system messages based on non-user events."""
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
def process_event(event: Event, manager: ConversationManager, last_input: str):
    """Update conversation with the event and determine if exit was requested."""
    if event.source == "user":
        last_input = event.metadata.get("input_type", "text") if event.metadata else "text"
        manager.add_text_to_conversation("user", event.payload)
        if event.payload.lower() == "exit":
            return True, last_input
    else:
        handle_non_user_event(event, manager)
    return False, last_input


# Execute tools suggested by the language model
def run_tool_workflow(manager: ConversationManager, gpt_client: GPTClient, queue: asyncio.Queue):
    """Get LLM proposed workflow and execute the associated tools."""
    chain_retry = 0
    while chain_retry < 3:
        try:
            workflow = gpt_client.get_workflow(manager.get_conversation())
        except Exception as e:
            logging.error(f"Error getting GPT workflow: {e}")
            chain_retry += 1
            continue

        if workflow:
            for call in workflow:
                print(f"Tool Name: {call.get('name', 'unknown')}")
                print(f"Arguments: {call.get('arguments', {})}")
            for item in workflow:
                if item.get("name") == "web_search_call_result":
                    context_text = item.get("arguments", {}).get("text", "")
                    if context_text:
                        manager.add_text_to_conversation("system", f"Info: {context_text}")
            workflow = [item for item in workflow if item.get("name") != "web_search_call_result"]

        # Always fetch memory before running tools and update memory message
        mem_result = Functions().read_long_term_memory()
        manager.update_memory(f"LONG TERM MEMORY:\n{mem_result}")

        if not workflow:
            return

        try:
            fn_results = Functions().execute_workflow(workflow, event_queue=queue) or []
        except Exception as e:
            logging.error(f"Error executing workflow tools: {e}")
            return
        for _, result in fn_results:
            manager.add_text_to_conversation("system", str(result))
        chain_retry += 1


# Ask the LLM for a textual reply and matching animation
def generate_assistant_reply(manager: ConversationManager, gpt_client: GPTClient):
    """Fetch assistant text and animation from the LLM."""
    gpt_text = gpt_client.get_text(manager.get_conversation())
    manager.add_text_to_conversation("assistant", gpt_text)
    manager.print_memory()
    animation = gpt_client.reply_with_animation(manager.get_conversation())
    return gpt_text, animation


# Play the assistant's speech and optionally capture a follow-up
async def handle_tts_and_follow_up(
    gpt_text: str,
    last_input_type: str,
    tts_engine: TextToSpeechEngine,
    stt_engine: SpeechToTextEngine,
    queue: asyncio.Queue,
    hotword_task: Optional[asyncio.Task],
    stt_enabled: bool,
    tts_enabled: bool,
):
    """Play TTS output and optionally listen for a follow-up voice response."""
    if not tts_enabled:
        return hotword_task

    if hotword_task:
        hotword_task.cancel()
        await asyncio.gather(hotword_task, return_exceptions=True)
        hotword_task = None

    if stt_enabled:
        stt_engine.pause_listening()
        print("[STT] Hotword listener paused.")
    tts_engine.generate_and_play_advanced(gpt_text)

    if stt_enabled:
        stt_engine.resume_listening()

    if stt_enabled and last_input_type == "voice":
        print("[STT] Listening for follow-up without hotword for 5 seconds...")
        loop = asyncio.get_event_loop()
        follow_up_future = loop.run_in_executor(None, lambda: stt_engine.record_and_transcribe(5))
        queue_get_task = asyncio.create_task(queue.get())
        done, _ = await asyncio.wait([follow_up_future, queue_get_task], return_when=asyncio.FIRST_COMPLETED)
        if follow_up_future in done:
            follow_up = follow_up_future.result()
            if follow_up and follow_up.strip():
                await queue.put(Event("user", follow_up.strip(), {"input_type": "voice"}))
            queue_get_task.cancel()
            await asyncio.gather(queue_get_task, return_exceptions=True)
        else:
            follow_up_future.cancel()
            await asyncio.gather(follow_up_future, return_exceptions=True)
            next_event = queue_get_task.result()
            await queue.put(next_event)

    if stt_enabled:
        stt_engine.resume_listening()
        hotword_task = asyncio.create_task(stt_engine.hotword_listener(queue))
        print("[STT] Hotword listener resumed.")

    return hotword_task

async def handle_follow_up_after_stream(
    last_input_type: str,
    stt_engine: SpeechToTextEngine,
    queue: asyncio.Queue,
    hotword_task: Optional[asyncio.Task],
    stt_enabled: bool,
) -> Optional[asyncio.Task]:
    """Handle follow-up recording after streaming TTS playback."""
    if not stt_enabled:
        return hotword_task

    if stt_engine:
        stt_engine.resume_listening()

    if last_input_type == "voice":
        print("[STT] Listening for follow-up without hotword for 5 seconds...")
        loop = asyncio.get_event_loop()
        follow_up_future = loop.run_in_executor(
            None, lambda: stt_engine.record_and_transcribe(5)
        )
        queue_get_task = asyncio.create_task(queue.get())
        done, _ = await asyncio.wait(
            [follow_up_future, queue_get_task], return_when=asyncio.FIRST_COMPLETED
        )
        if follow_up_future in done:
            follow_up = follow_up_future.result()
            if follow_up and follow_up.strip():
                await queue.put(
                    Event("user", follow_up.strip(), {"input_type": "voice"})
                )
            queue_get_task.cancel()
            await asyncio.gather(queue_get_task, return_exceptions=True)
        else:
            follow_up_future.cancel()
            await asyncio.gather(follow_up_future, return_exceptions=True)
            next_event = queue_get_task.result()
            await queue.put(next_event)

    hotword_task = asyncio.create_task(stt_engine.hotword_listener(queue))
    print("[STT] Hotword listener resumed.")
    return hotword_task

async def stream_assistant_reply(
    manager: ConversationManager,
    gpt_client: GPTClient,
    tts_engine: TextToSpeechEngine,
    last_input_type: str,
    stt_engine: SpeechToTextEngine,
    queue: asyncio.Queue,
    hotword_task: Optional[asyncio.Task],
    stt_enabled: bool,
) -> tuple[str, str, Optional[asyncio.Task]]:
    """Stream GPT reply and play TTS while generating."""

    stream_start_time = time.time()
    record_timing("streaming_start", stream_start_time)
    print(f"[Stream] Starting streaming with {MAX_TTS_WORKERS} TTS workers")

    if hotword_task:
        hotword_task.cancel()
        await asyncio.gather(hotword_task, return_exceptions=True)
        hotword_task = None

    if stt_enabled:
        stt_engine.pause_listening()
        print("[STT] Hotword listener paused.")

    sentences: list[str] = []
    q_sent: asyncio.Queue = asyncio.Queue(QUEUE_MAXSIZE)
    q_audio: asyncio.Queue = asyncio.Queue(QUEUE_MAXSIZE)
    loop = asyncio.get_running_loop()
    config = load_config()
    xi_key = config["secrets"]["elevenlabs_api_key"]
    voice_id = config["tts"].get("voice_id", "4Jtuv4wBvd95o1hzNloV")
    model_id = config["tts"].get("model_id", "eleven_flash_v2_5")
    output_format = config["tts"].get("output_format", "mp3_22050_32")
    api_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": xi_key, "Content-Type": "application/json"}

    def http_tts(text: str, prev: str, nxt: str, idx: float) -> bytes | None:
        def _post() -> requests.Response:
            return requests.post(
                api_url,
                headers=headers,
                params={"output_format": output_format},
                json={
                    "text": text,
                    "model_id": model_id,
                    "previous_text": prev or None,
                    "next_text": nxt or None,
                },
                timeout=60,
            )

        attempt, backoff = 1, 1
        while attempt <= MAX_ATTEMPTS:
            try:
                tts_start = time.time()
                resp = _post()
                resp.raise_for_status()
                tts_end = time.time()
                record_timing("tts_clip_generated", tts_start)
                return resp.content
            except Exception:
                if attempt == MAX_ATTEMPTS:
                    return None
                time.sleep(backoff + random.uniform(0, 0.5))
                backoff = min(backoff * 2, 32)
                attempt += 1

    def play_mp3(data: bytes | None, _idx: float) -> None:
        if data is None:
            return
        play_start = time.time()
        print(f"[Player] Playing clip {_idx}")
        tts_engine.play_mp3_bytes(data)
        play_end = time.time()
        record_timing("tts_clip_played", play_start)
        print(f"[Player] Finished clip {_idx}")

    def producer() -> None:
        idx = 0.0
        for sent, start_ts, end_ts in gpt_client.sentence_stream(manager.get_conversation()):
            sentences.append(sent)
            print(f"[Producer] Sentence {idx}: {sent}")
            record_timing(f"sentence_created", start_ts)
            asyncio.run_coroutine_threadsafe(q_sent.put((idx, sent)), loop)
            idx += 1.0
        asyncio.run_coroutine_threadsafe(q_sent.put(None), loop)

    threading.Thread(target=producer, daemon=True).start()

    async def tts_dispatch(sq: asyncio.Queue, aq: asyncio.Queue, pool):
        loop2 = asyncio.get_running_loop()
        sem = asyncio.Semaphore(MAX_TTS_WORKERS)
        prev_text = ""
        pending: list[asyncio.Task] = []

        async def handle(idx: float, cur: str, nxt: str, prev: str):
            async with sem:
                tts_clip_start = time.time()
                print(f"[TTS] Generating clip {idx}")
                data = await asyncio.wrap_future(
                    loop2.run_in_executor(pool, http_tts, cur, prev, nxt, idx)
                )
                tts_clip_end = time.time()
                await aq.put((idx, data))
                record_timing("tts_dispatch", tts_clip_end)
                print(f"[TTS] Done clip {idx}")

        item = await sq.get()
        while item:
            idx, cur = item
            nxt_item = await sq.get()
            nxt_txt = "" if nxt_item is None else nxt_item[1]
            pending.append(asyncio.create_task(handle(idx, cur, nxt_txt, prev_text)))
            prev_text, item = cur, nxt_item

        await asyncio.gather(*pending)
        await aq.put((-1, b""))

    async def sequencer(aq: asyncio.Queue):
        loop3, heap, expect = asyncio.get_running_loop(), {}, 0.0
        while True:
            idx, clip = await aq.get()
            if idx == -1:
                break
            heap[idx] = clip
            while expect in heap:
                play_clip_start = time.time()
                await loop3.run_in_executor(None, play_mp3, heap.pop(expect), expect)
                play_clip_end = time.time()
                expect += 1.0

    with ThreadPoolExecutor(MAX_TTS_WORKERS) as pool:
        await asyncio.gather(tts_dispatch(q_sent, q_audio, pool), sequencer(q_audio))

    gpt_text = " ".join(sentences)
    manager.add_text_to_conversation("assistant", gpt_text)
    manager.print_memory()
    animation = gpt_client.reply_with_animation(manager.get_conversation())

    stream_end_time = time.time()
    record_timing("streaming_end", stream_end_time)

    hotword_task = await handle_follow_up_after_stream(
        last_input_type, stt_engine, queue, hotword_task, stt_enabled
    )

    print("[Stream] Finished streaming")
    return gpt_text, animation, hotword_task


async def async_conversation_loop(manager,gpt_client,stt_engine,tts_engine,arduino_interface,stt_enabled,tts_enabled):
    """Main asynchronous interaction loop handling user events and tool calls."""
    import sys

    queue: asyncio.Queue = asyncio.Queue()

    # Start background producers
    user_task = asyncio.create_task(user_input_producer(queue))
    hotword_task = (
        asyncio.create_task(stt_engine.hotword_listener(queue)) if stt_enabled else None
    )

    last_input_type = "text"
    print("🤖 Assistant running. Type 'exit' to quit. Type or say hotword to speak.\n")
    try:
        while True:
            event = await get_event(queue)
            print_event(event)

            exit_requested, last_input_type = process_event(event, manager, last_input_type)
            if exit_requested:
                user_task.cancel()
                if hotword_task:
                    hotword_task.cancel()
                break

            run_tool_workflow(manager, gpt_client, queue)
            try:
                if tts_enabled:
                    gpt_text, animation, hotword_task = await stream_assistant_reply(
                        manager,
                        gpt_client,
                        tts_engine,
                        last_input_type,
                        stt_engine,
                        queue,
                        hotword_task,
                        stt_enabled,
                    )
                else:
                    gpt_text, animation = generate_assistant_reply(manager, gpt_client)
            except Exception as e:
                logging.error(f"Error generating assistant reply: {e}")
                continue

            print(f"[Animation chosen]: {animation}")
            arduino_interface.set_animation(animation)

            print_async_tasks()
            arduino_interface.servo_controller.print_servo_status()
            print(Fore.GREEN + Style.BRIGHT + f"\nAssistant: {gpt_text}" + Style.RESET_ALL)
            print(Fore.LIGHTBLACK_EX + Style.BRIGHT + "\n»»» Ready for your input! Type below..." + Style.RESET_ALL)

            if not tts_enabled:
                hotword_task = await handle_tts_and_follow_up(
                    gpt_text,
                    last_input_type,
                    tts_engine,
                    stt_engine,
                    queue,
                    hotword_task,
                    stt_enabled,
                    tts_enabled,
                )
    
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
            try:
                stt_engine.cleanup()
            except Exception as e:
                print(f"[Shutdown] Error during stt_engine cleanup: {e}")
        print("👋 Exiting…")
        return

def print_async_tasks():
    """Minimal async task list, one line per task, no table formatting."""
    tasks = []
    for t in asyncio.all_tasks():
        f = getattr(t.get_coro(), 'cr_frame', None)
        loc = f"{pathlib.Path(f.f_code.co_filename).name}:{f.f_lineno}" if f else ''
        tasks.append({
            "name": t.get_name(),
            "state": t._state,
            "coro": t.get_coro().__qualname__,
            "loc": loc
        })
    if tasks:
        print(Fore.CYAN + Style.BRIGHT + "\nAsync Tasks:")
        for t in tasks:
            name = f"{Fore.YELLOW}{t['name']}{Style.RESET_ALL}"
            state = f"{Fore.GREEN if t['state']=='PENDING' else Fore.RED}{t['state']}{Style.RESET_ALL}"
            print(f"  {name} | {state} | {t['coro']} | {t['loc']}")
    else:
        print(Fore.CYAN + Style.BRIGHT + "No async tasks running." + Style.RESET_ALL)

# =================== Main Code ===================
def main():
    """CLI entry point for launching the assistant."""


    parser = argparse.ArgumentParser(description="Launch the Wheatley assistant")
    parser.add_argument(
        "--export-timings",
        action="store_true",
        help="Write timing information to timings.json on exit",
    )
    args = parser.parse_args()

    # Start each run with a clean timing log
    clear_timings()

    if args.export_timings:
        atexit.register(export_timings)

    config = load_config()
    openai.api_key = config["secrets"]["openai_api_key"]

    # Print active/inactive features from config
    stt_enabled = config["stt"]["enabled"]
    tts_enabled = config["tts"]["enabled"]
    feature_summary = "\nFeature Status:\n"
    feature_summary += f" - Speech-to-Text (STT): {'Active' if stt_enabled else 'Inactive'}\n"
    feature_summary += f" - Text-to-Speech (TTS): {'Active' if tts_enabled else 'Inactive'}\n"
    print(feature_summary)

    # Dynamic import to prevent circular dependencies with service_auth
    from service_auth import authenticate_services
    service_status = authenticate_services()
    if not service_status.get("openai"):
        stt_enabled = False
    if not service_status.get("elevenlabs"):
        tts_enabled = False

    feature_summary = "\nFinal Feature Status:\n"
    feature_summary += f" - Speech-to-Text (STT): {'Active' if stt_enabled else 'Inactive'}\n"
    feature_summary += f" - Text-to-Speech (TTS): {'Active' if tts_enabled else 'Inactive'}\n"
    print(feature_summary)

    # Initialize assistant components
    manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled = initialize_assistant(
        config,
        stt_enabled=stt_enabled,
        tts_enabled=tts_enabled,
    )
    
    print_welcome()
    
    # Print the status of all servos
    arduino_interface.set_animation("neutral")  # Set initial animation to neutral
    arduino_interface.servo_controller.print_servo_status()
    
    # Get initial GPT response
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
