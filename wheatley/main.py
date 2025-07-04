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
from dataclasses import dataclass  # For Event container
from typing import Dict, Any, Optional  # For type hints
from datetime import datetime  # For timestamps
import sys
import atexit

# =================== Imports: Third-Party Libraries ===================
import yaml  # For reading YAML config files
import openai  # For OpenAI API access
from colorama import init, Fore, Style  # For colored terminal output
import pathlib
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
import re
import random

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


# =================== Assistant Initialization ===================
# Set up all assistant components (LLM, TTS, STT, Arduino, etc.)
def initialize_assistant(config, *, stt_enabled: bool | None = None, tts_enabled: bool | None = None):
    """Initialise and return all major subsystems (LLM, TTS, STT, Arduino, etc)."""

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
    # Return all initialized components and feature flags
    return manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled


# =================== Event Dataclass ===================
@dataclass
class Event:
    """Simple event container used by the async event loop."""

    source: str        # e.g. "user", "timer", "gpio", "webhook", etc.
    payload: str       # human-readable description
    metadata: Optional[Dict[str, Any]] = None
    ts: Optional[datetime] = None

    def __str__(self):
        meta = f" {self.metadata}" if self.metadata else ""
        ts = f" ({self.ts.isoformat()})" if self.ts else ""
        return f"[{self.source.upper()}] {self.payload}{meta}{ts}"


# =================== Async Event Handling ===================
async def user_input_producer(q: asyncio.Queue):
    """Asynchronously read user text input and push Event objects to the queue."""
    loop = asyncio.get_event_loop()
    while True:
        wait_start = time.time()
        text = await loop.run_in_executor(None, input, "You: ")
        record_timing("await_user_input", wait_start)
        await q.put(Event("user", text.strip(), {"input_type": "text"}))
        if text.strip().lower() == "exit":
            break
# Simple wrapper to print an event object
def print_event(event: Event):
    """Print an Event object to stdout in a readable format."""
    print(event)


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
def process_event(event: Event, manager: ConversationManager, last_input: str):
    """Update conversation with the event and determine if exit was requested by the user."""
    if event.source == "user":
        last_input = event.metadata.get("input_type", "text") if event.metadata else "text"
        manager.add_text_to_conversation("user", event.payload)
        if event.payload.lower() == "exit":
            return True, last_input
    else:
        handle_non_user_event(event, manager)
    return False, last_input


# =================== Tool Workflow Execution ===================
# Execute tools suggested by the language model
def run_tool_workflow(manager: ConversationManager, gpt_client: GPTClient, queue: asyncio.Queue):
    """Get LLM-proposed workflow and execute the associated tools, updating conversation history."""
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


# =================== Assistant Reply Generation ===================
# Ask the LLM for a textual reply and matching animation
def generate_assistant_reply(manager: ConversationManager, gpt_client: GPTClient):
    """Fetch assistant text and animation from the LLM and update conversation history."""
    gpt_text = gpt_client.get_text(manager.get_conversation())
    manager.add_text_to_conversation("assistant", gpt_text)
    manager.print_memory()
    animation = gpt_client.reply_with_animation(manager.get_conversation())
    return gpt_text, animation


# =================== TTS and Follow-up Handling ===================
# Play the assistant's speech and optionally capture a follow-up
async def handle_tts_and_follow_up(gpt_text, last_input_type, tts_engine, stt_engine, event_queue, hotword_task, stt_enabled, tts_enabled):
    """Play the assistant reply using TTS and optionally capture a quick follow-up from the user."""
    if not tts_enabled:
        return hotword_task

    # Stop hotword detection while speaking
    if hotword_task:
        hotword_task.cancel()
        await asyncio.gather(hotword_task, return_exceptions=True)
        hotword_task = None

    if stt_enabled:
        stt_engine.pause_listening()
        print("[STT] Hotword listener paused.")

    tts_engine.generate_and_play_advanced(gpt_text)

    if not stt_enabled:
        return hotword_task

    stt_engine.resume_listening()

    if last_input_type == "voice":
        print("[STT] Listening for follow-up without hotword for 5 seconds...")
        loop = asyncio.get_event_loop()
        follow_up_future = loop.run_in_executor(
            None, lambda: stt_engine.record_and_transcribe(5)
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

    hotword_task = asyncio.create_task(stt_engine.hotword_listener(event_queue))
    print("[STT] Hotword listener resumed.")

    return hotword_task


async def handle_follow_up_after_stream(last_input_type, stt_engine, event_queue, hotword_task, stt_enabled):
    """Handle follow-up voice recording after streaming TTS playback."""
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

    hotword_task = asyncio.create_task(stt_engine.hotword_listener(event_queue))
    print("[STT] Hotword listener resumed.")
    return hotword_task


# =================== Streaming Assistant Reply (Advanced) ===================
# Stream GPT reply and play TTS while generating.
async def stream_assistant_reply(
    manager, gpt_client, tts_engine, last_input_type, stt_engine, queue, hotword_task, stt_enabled, arduino_interface
):
    """
    Stream GPT reply and play TTS while generating.
    Streams sentences from the LLM, generates TTS audio for each sentence in parallel,
    and plays them in order, while handling hotword detection and follow-up.
    """

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
    sentence_queue: asyncio.Queue = asyncio.Queue(QUEUE_MAXSIZE)
    audio_queue: asyncio.Queue = asyncio.Queue(QUEUE_MAXSIZE)
    loop = asyncio.get_running_loop()
    config = load_config()
    xi_key = config["secrets"]["elevenlabs_api_key"]
    voice_id = config["tts"].get("voice_id", "4Jtuv4wBvd95o1hzNloV")
    model_id = config["tts"].get("model_id", "eleven_flash_v2_5")
    output_format = config["tts"].get("output_format", "mp3_22050_32")
    api_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": xi_key, "Content-Type": "application/json"}

    def fetch_tts_clip(text, previous_sentence, next_sentence, sentence_index):
        # Synchronously call ElevenLabs TTS API for a text segment.
        # Retries with exponential backoff on failure.
        # Returns MP3 bytes or None on failure.
        def _post():
            return requests.post(
                api_url,
                headers=headers,
                params={"output_format": output_format},
                json={
                    "text": text,
                    "model_id": model_id,
                    "previous_text": previous_sentence or None,
                    "next_text": next_sentence or None,
                },
                timeout=60,
            )

        attempt, backoff = 1, 1
        while attempt <= MAX_ATTEMPTS:
            try:
                tts_start = time.time()
                resp = _post()
                resp.raise_for_status()
                record_timing("tts_clip_generated", tts_start)
                return resp.content
            except Exception:
                if attempt == MAX_ATTEMPTS:
                    return None
                time.sleep(backoff + random.uniform(0, 0.5))
                backoff = min(backoff * 2, 32)
                attempt += 1

    def play_mp3_bytes(audio_bytes, sentence_index):
        # Play MP3 audio bytes using the TTS engine.
        # Logs timing and playback events.
        if audio_bytes is None:
            return
        play_start = time.time()
        print(f"[Player] Playing clip {sentence_index}")
        tts_engine.play_mp3_bytes(audio_bytes)
        record_timing("tts_clip_played", play_start)
        print(f"[Player] Finished clip {sentence_index}")

    def producer():
        """Stream sentences from GPT and enqueue them for TTS."""
        sentence_index = 0.0
        for sentence, start_timestamp, _ in gpt_client.sentence_stream(manager.get_conversation()):
            sentences.append(sentence)
            print(f"[Producer] Sentence {sentence_index}: {sentence}")
            record_timing("sentence_created", start_timestamp)
            asyncio.run_coroutine_threadsafe(sentence_queue.put((sentence_index, sentence)), loop)
            sentence_index += 1.0
        asyncio.run_coroutine_threadsafe(sentence_queue.put(None), loop)

    threading.Thread(target=producer, daemon=True).start()

    async def tts_dispatch(text_queue, audio_queue, thread_pool):
        """Generate TTS clips concurrently and enqueue them for playback."""
        dispatch_loop = asyncio.get_running_loop()
        semaphore = asyncio.Semaphore(MAX_TTS_WORKERS)
        previous_sentence = ""
        pending_tasks = []

        async def handle(sentence_index, current_sentence, next_sentence, previous_sentence_val):
            """Run a single TTS job."""
            async with semaphore:
                print(f"[TTS] Generating clip {sentence_index}")
                audio_bytes = await asyncio.wrap_future(
                    dispatch_loop.run_in_executor(thread_pool, fetch_tts_clip, current_sentence, previous_sentence_val, next_sentence, sentence_index)
                )
                tts_clip_end = time.time()
                await audio_queue.put((sentence_index, audio_bytes))
                record_timing("tts_dispatch", tts_clip_end)
                print(f"[TTS] Done clip {sentence_index}")

        item = await text_queue.get()
        while item:
            sentence_index, current_sentence = item
            next_item = await text_queue.get()
            next_sentence = "" if next_item is None else next_item[1]
            pending_tasks.append(
                asyncio.create_task(handle(sentence_index, current_sentence, next_sentence, previous_sentence))
            )
            previous_sentence, item = current_sentence, next_item

        await asyncio.gather(*pending_tasks)
        await audio_queue.put((-1, b""))

    async def sequencer(audio_queue):
        """Play audio clips in the original sentence order."""
        playback_loop, buffer, expected_index = asyncio.get_running_loop(), {}, 0.0
        while True:
            sentence_index, audio_bytes = await audio_queue.get()
            if sentence_index == -1:
                break
            buffer[sentence_index] = audio_bytes
            while expected_index in buffer:
                await playback_loop.run_in_executor(None, play_mp3_bytes, buffer.pop(expected_index), expected_index)
                expected_index += 1.0

    with ThreadPoolExecutor(MAX_TTS_WORKERS) as thread_pool:
        # Launch TTS generation and playback in parallel
        dispatch_task = asyncio.create_task(tts_dispatch(sentence_queue, audio_queue, thread_pool))
        seq_task = asyncio.create_task(sequencer(audio_queue))

        # Wait until all sentences have been processed by the TTS dispatcher
        await dispatch_task

    gpt_text = " ".join(sentences)
    manager.add_text_to_conversation("assistant", gpt_text)
    manager.print_memory()
    animation = gpt_client.reply_with_animation(manager.get_conversation())
    arduino_interface.set_animation(animation)

    # Wait for all audio to finish playing
    await seq_task

    stream_end_time = time.time()
    record_timing("streaming_end", stream_end_time)

    hotword_task = await handle_follow_up_after_stream(
        last_input_type, stt_engine, queue, hotword_task, stt_enabled
    )

    print("[Stream] Finished streaming")
    return gpt_text, animation, hotword_task


# =================== Main Async Conversation Loop ===================
async def async_conversation_loop(manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled):
    """Main asynchronous interaction loop handling user events, tool calls, and assistant responses."""

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
                        arduino_interface,
                    )
                else:
                    gpt_text, animation = generate_assistant_reply(manager, gpt_client)
            except Exception as e:
                logging.error(f"Error generating assistant reply: {e}")
                continue

            # The animation is applied during streaming so it matches the speech
            print(f"[Animation chosen]: {animation}")

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
    """Print a minimal list of currently running async tasks for debugging purposes."""
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
    """CLI entry point for launching the Wheatley assistant and starting the main event loop."""

    # --- Setup and configuration ---------------------------------------
    clear_timings()
    atexit.register(export_timings)

    config = load_config()
    openai.api_key = config["secrets"]["openai_api_key"]

    # Initial feature flags from configuration file
    stt_enabled = config["stt"]["enabled"]
    tts_enabled = config["tts"]["enabled"]
    print(feature_summary(stt_enabled, tts_enabled, "Feature Status"))

    # Authenticate external services and update feature flags accordingly
    stt_enabled, tts_enabled = authenticate_and_update_features(
        stt_enabled, tts_enabled
    )
    print(feature_summary(stt_enabled, tts_enabled, "Final Feature Status"))

    # --- Initialise core subsystems ------------------------------------
    manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled = initialize_assistant(
        config,
        stt_enabled=stt_enabled,
        tts_enabled=tts_enabled,
    )

    print_welcome()

    # Establish a neutral pose on startup and display servo status
    arduino_interface.set_animation("neutral")  # Set initial animation to neutral
    arduino_interface.servo_controller.print_servo_status()

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
