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
import datetime
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

# Try to import RPi.GPIO for Raspberry Pi GPIO control; disable if not available
try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
    print("RPi.GPIO module not found; GPIO functionality will be disabled.")

# =================== Imports: Local Modules ===================
from hardware.arduino_interface import ArduinoInterface  # Arduino hardware interface
from assistant.assistant import ConversationManager  # Manages conversation history
from llm.llm_client import GPTClient, Functions  # LLM client and function tools
from tts.tts_engine import TextToSpeechEngine  # Text-to-speech engine
from stt.stt_engine import SpeechToTextEngine  # Speech-to-text engine
from utils.timing_logger import record_timing, export_timings, clear_timings


# Initialize colorama for colored terminal output
init(autoreset=True)

# =================== Helper Functions ===================

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

    start_time = time.time()
    try:
        config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    finally:
        record_timing("load_config", start_time)

# Print ASCII art welcome message to the terminal
def print_welcome():
    """Display a retro style welcome banner."""

    start_time = time.time()
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
    record_timing("print_welcome", start_time)

# =================== Assistant Initialization ===================
# Set up all assistant components (LLM, TTS, STT, Arduino, etc.)
def initialize_assistant(config):
    """Initialise and return all major subsystems."""

    start_time = time.time()  # Start timing initialization
    stt_enabled = config["stt"]["enabled"]  # Speech-to-text enabled
    tts_enabled = config["tts"]["enabled"]  # Text-to-speech enabled
    assistant_config = config.get("app")  # App-specific config
    max_memory = assistant_config.get("max_memory")  # Conversation memory size
    llm_config = config.get("llm")  # LLM config
    gpt_model = llm_config.get("model")  # LLM model name
    
    # Initialize core components
    manager = ConversationManager(max_memory=max_memory)
    gpt_client = GPTClient(model=gpt_model)
    stt_engine = SpeechToTextEngine()
    tts_engine = TextToSpeechEngine()
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
            stt_engine.arduino_interface = arduino_interface
        except Exception as e:
            print(f"Could not connect to Arduino on {port}: {e}. Running in dry run mode.")
            arduino_interface = ArduinoInterface(port=port, dry_run=True)
            stt_engine.arduino_interface = arduino_interface
    else:
        arduino_interface = ArduinoInterface(port="dryrun", dry_run=True)
        stt_engine.arduino_interface = arduino_interface
    elapsed = time.time() - start_time
    logging.info(f"initialize_assistant completed in {elapsed:.3f} seconds.")
    record_timing("initialize_assistant", start_time)
    # Return all initialized components and feature flags
    return manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled

# =================== Event Dataclass ===================
@dataclass
class Event:
    """Simple event container used by the async event loop."""

    source: str        # e.g. "user", "timer", "gpio", "webhook", etc.
    payload: str       # human-readable description
    metadata: Optional[Dict[str, Any]] = None
    ts: datetime.datetime = datetime.datetime.utcnow()

    def __str__(self):
        meta = f" {self.metadata}" if self.metadata else ""
        return f"[{self.source.upper()}] {self.payload}{meta}"

# =================== Async Event Handling ===================
async def user_input_producer(q: asyncio.Queue):
    """Asynchronously read user text input and push ``Event`` objects to ``q``."""
    loop = asyncio.get_event_loop()
    while True:
        start_time = time.time()
        text = await loop.run_in_executor(None, input, "You: ")
        record_timing("user_input", start_time)
        await q.put(Event("user", text.strip(), {"input_type": "text"}))
        if text.strip().lower() == "exit":
            break
# Simple wrapper to print an event object
def print_event(event: Event):
    """Helper to display an ``Event`` on stdout."""
    start_time = time.time()
    print(event)
    record_timing("output_event", start_time)


async def get_event(queue: asyncio.Queue):
    """Retrieve the next event from ``queue`` and normalise voice dicts."""
    start_time = time.time()
    incoming = await queue.get()
    record_timing("get_event", start_time)
    if isinstance(incoming, dict) and incoming.get("type") == "voice":
        return Event("user", incoming.get("text", ""), {"input_type": "voice"})
    return incoming


# Insert system messages when events come from timers or reminders
def handle_non_user_event(event: Event, manager: ConversationManager):
    """Add system messages based on non-user events."""
    start_time = time.time()
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
    record_timing("handle_non_user_event", start_time)


# Update conversation history and return True if user requested to exit
def process_event(event: Event, manager: ConversationManager, last_input: str):
    """Update conversation with the event and determine if exit was requested."""
    start_time = time.time()
    try:
        if event.source == "user":
            last_input = event.metadata.get("input_type", "text") if event.metadata else "text"
            manager.add_text_to_conversation("user", event.payload)
            if event.payload.lower() == "exit":
                return True, last_input
        else:
            handle_non_user_event(event, manager)
        return False, last_input
    finally:
        record_timing("process_event", start_time)


# Execute tools suggested by the language model
def run_tool_workflow(manager: ConversationManager, gpt_client: GPTClient, queue: asyncio.Queue):
    """Get LLM proposed workflow and execute the associated tools."""
    start_time = time.time()
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

        # Always fetch memory before running tools
        mem_result = Functions().read_long_term_memory()
        manager.add_text_to_conversation("system", str(mem_result))

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
    record_timing("run_tool_workflow", start_time)


# Ask the LLM for a textual reply and matching animation
def generate_assistant_reply(manager: ConversationManager, gpt_client: GPTClient):
    """Fetch assistant text and animation from the LLM."""
    start_time = time.time()
    gpt_text = gpt_client.get_text(manager.get_conversation())
    manager.add_text_to_conversation("assistant", gpt_text)
    manager.print_memory()
    animation = gpt_client.reply_with_animation(manager.get_conversation())
    record_timing("generate_assistant_reply", start_time)
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
    start_time = time.time()
    if not tts_enabled:
        record_timing("handle_tts_and_follow_up", start_time)
        return hotword_task

    if hotword_task:
        hotword_task.cancel()
        await asyncio.gather(hotword_task, return_exceptions=True)
        hotword_task = None

    stt_engine.pause_listening()
    print("[STT] Hotword listener paused.")
    tts_engine.generate_and_play_advanced(gpt_text)

    if stt_enabled:
        stt_engine.resume_listening()

    if stt_enabled and last_input_type == "voice":
        print("[STT] Listening for follow-up without hotword for 10 seconds...")
        loop = asyncio.get_event_loop()
        follow_up_future = loop.run_in_executor(None, lambda: stt_engine.record_and_transcribe(10))
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

    record_timing("handle_tts_and_follow_up", start_time)
    return hotword_task


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
    start_time = time.time()
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

            hotword_task = await handle_tts_and_follow_up(gpt_text,last_input_type,tts_engine,stt_engine,queue,hotword_task,stt_enabled,tts_enabled)
    
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
        print("👋 Exiting… (forced exit)")
        sys.exit(0)

def print_async_tasks():
    """Minimal async task list, one line per task, no table formatting."""
    start_time = time.time()
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
    record_timing("print_async_tasks", start_time)

# =================== Main Code ===================
def main():
    """CLI entry point for launching the assistant."""
    start_time = time.time()

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

    # Initialize assistant components
    manager, gpt_client, stt_engine, tts_engine, arduino_interface, stt_enabled, tts_enabled = initialize_assistant(config)
    
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
    logging.info("Assistant finished.")
    record_timing("main", start_time)

if __name__ == "__main__":
    main()
