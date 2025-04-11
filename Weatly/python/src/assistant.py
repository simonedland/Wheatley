import os
import time
import textwrap
import logging
from datetime import datetime, timezone
import matplotlib.pyplot as plt

# ...existing or shared logic can be placed here if needed...

class ConversationManager:
    def __init__(self, max_memory=5, instructions=None, bot_name="Assistant", user_name="User"):
        self.max_memory = max_memory
        self.bot_name = bot_name
        self.user_name = user_name
        self.messages = [{
            "role": "system",
            "content": instructions or (f"I am {self.bot_name}, wise and witty. Let's chat briefly and meaningfully.")
        }]
    def add_text(self, role, text):
        self.messages.append({"role": role, "content": text})
        while len(self.messages) > self.max_memory + 1:
            self.messages.pop(1)
    def get_history(self):
        return self.messages
    def print_memory(self):
        colors = {"system": "\033[94m", "user": "\033[92m", "assistant": "\033[91m"}
        reset = "\033[0m"
        max_width = 70
        print(f"\n{colors['system']}╔{'═'*60}╗{reset}")
        for idx, msg in enumerate(self.messages):
            role = msg["role"]
            color = colors.get(role, colors["system"])
            name = (self.bot_name if role == "assistant" 
                    else self.user_name if role == "user" 
                    else role)
            print(f"{color}║ [{idx}] {name}:{reset}")
            for line in textwrap.wrap(msg["content"], width=max_width):
                print(f"{color}║     {line}{reset}")
            print(f"{color}║{'-'*max_width}{reset}")
        print(f"{colors['system']}╚{'═'*60}╝{reset}\n")

class Assistant:
    def __init__(self, create_audio=True, play_audio=True, conversation_memory=5, instructions=None, bot_name="Assistant", user_name="User", gpt_client=None, manager=None):
        self.create_audio = create_audio
        self.play_audio = play_audio
        self.bot_name = bot_name
        self.user_name = user_name
        self.manager = manager or ConversationManager(max_memory=conversation_memory,
                                                       instructions=instructions,
                                                       bot_name=bot_name,
                                                       user_name=user_name)
        if gpt_client is not None:
            self.gpt_client = gpt_client
        else:
            from llm.llm_client import GPTClient
            # NOTE: Set a valid API key from configuration here.
            self.gpt_client = GPTClient(api_key="")  # TODO: update the API key

    def send_message(self, user_input):
        self.manager.add_text("user", user_input)
    def get_response(self):
        try:
            gpt_text = self.gpt_client.get_text(self.manager.get_history())
            tokens_used = 0  # Token usage not tracked with the new client
            return gpt_text, tokens_used
        except Exception as e:
            logging.error(f"Error getting GPT response: {e}")
            return None, 0
    def generate_and_play_audio(self, gpt_text):
        from utils.audio import generate_audio, play_audio_from_file
        try:
            previous = self.manager.get_history()[-2]["content"] if len(self.manager.get_history()) >= 2 else None
            audio_chunks = list(generate_audio(gpt_text, previous_text=previous))
        except Exception as e:
            logging.error(f"Error generating audio: {e}")
            return {}
        if self.create_audio:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            file_path = f"OUT_{timestamp}.mp3"
            try:
                with open(file_path, "wb") as f:
                    for chunk in audio_chunks:
                        f.write(chunk)
            except Exception as e:
                logging.error(f"Error saving audio file: {e}")
                return {}
            logging.info(f"Audio saved: {file_path}")
            if self.play_audio:
                try:
                    play_audio_from_file(file_path)
                except Exception as e:
                    logging.error(f"Error playing audio file: {e}")
            try:
                os.remove(file_path)
            except Exception as e:
                logging.error(f"Error deleting audio file: {e}")
        return {}
    def summarize_time(self, time_gpt, tokens_used):
        conversation_length = len(self.manager.get_history()) - 1
        summary = (
            f"\nTime Summary:\n"
            f"  GPT response time: {time_gpt:.2f} sec\n"
            f"  Tokens used: {tokens_used}\n"
            f"  Conversation length: {conversation_length} messages"
        )
        print(summary)
        push_custom_event_to_appinsights("ResponseTime", tokens_used, time_gpt)

def push_custom_event_to_appinsights(event_name, tokens_used, response_time):
    import requests
    url = "https://dc.services.visualstudio.com/v2/track"
    payload = {
        "name": "Microsoft.ApplicationInsights.Event",
        "time": datetime.now(timezone.utc).isoformat(),
        "iKey": "",  # To be set from configuration in main.py
        "data": {
            "baseType": "EventData",
            "baseData": {
                "name": event_name,
                "properties": {
                    "totalTokens": tokens_used,
                    "responseTime": response_time
                }
            }
        }
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code != 200:
            logging.error(f"Failed to post custom event: {response.status_code} - {response.text}")
        else:
            logging.info(f"Posted custom event: {event_name}")
    except Exception as e:
        logging.error(f"Error sending custom event: {e}")
