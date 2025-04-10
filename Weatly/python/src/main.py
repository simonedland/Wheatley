import os
import time
from datetime import datetime, timezone
import textwrap
import logging
import requests
import openai
import matplotlib.pyplot as plt
import yaml

def check_prerequisites():
    # Check if essential configuration and secret values are set
    if not openai.api_key:
        logging.error("Prerequisite check failed: OpenAI API key not set!")
        return False
    # ... add additional prerequisite checks as needed ...
    logging.info("All prerequisites satisfied.")
    return True

# Load configuration from config folder
config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

# Set secrets from config
openai.api_key = config["secrets"]["openai_api_key"]

# Configure ElevenLabs client using our utils module (overwrite client api key)
APPINSIGHTS_IKEY = config["secrets"]["appinsights_ikey"]

# ...existing code for Timer, rate_limit, etc. are now moved to utils modules ...
from utils.rate_limit import rate_limit
from assistant import ConversationManager, Assistant

def main():
    plt.ion()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    # Run prerequisite tests
    if not check_prerequisites():
        print("Missing prerequisites. Please ensure all required dependencies and configuration values are set.")
        return

    instructions = """You are the Sorting Hat from Harry Potter.
    You must answer the user’s questions and engage in natural conversation, including interjections such as “hmms” and other verbalizations as needed. 
    Feel free to add <break time="X.Xs" /> where it fits with as long of a wait that fits the context.
    Try to add as many pauses as needed, with natural short pauses ranging from 0.1s to 1.5s.
    """
    # Initialize ConversationManager and Assistant using the new file structure.
    from stt.stt_engine import SpeechToTextEngine
    from tts.tts_engine import TextToSpeechEngine
    from llm.llm_client import LLMClient

    conversation_manager = ConversationManager(
        max_memory=10,
        instructions=instructions,
        bot_name="Assistant",
        user_name="User"
    )
    assistant = Assistant(
        create_audio=True,
        play_audio=True,
        conversation_memory=10,
        instructions=instructions,
        bot_name="Assistant",
        user_name="User",
        manager=conversation_manager
    )

    # Generate a greeting using GPT.
    assistant.manager.add_text("user", "Create an engaging greeting to start this chat.")
    greeting, tokens_used = assistant.get_response()
    if greeting:
        assistant.manager.add_text("assistant", greeting)
        print("Assistant Greeting:\n", greeting)
        assistant.generate_and_play_audio(greeting)

    print(r"""
            .
           /:\
          /;:.\ 
         //;:. \     
        ///;:.. \
  __--''////;:... \''--__
--__   ''--_____--''   __--
    ''--_______--''
    """)
    print("\033[95mWelcome to the AI Assistant!\033[0m")

    while True:
        user_input = input("User: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            break
        assistant.send_message(user_input)
        gpt_response, tokens_used = assistant.get_response()
        if not gpt_response:
            break
        assistant.manager.add_text("assistant", gpt_response)
        assistant.generate_and_play_audio(gpt_response)
        assistant.manager.print_memory()
        print("Average Timing Details so far:")
        # ...existing code to print timings...
        rate_limit(tokens_used, elapsed_seconds=1, cap_per_minute=40000)
        print("Estimated tokens per minute:", (60 / 1) * tokens_used)

    logging.info("Assistant finished.")

if __name__ == "__main__":
    main()