import os
import time
import textwrap
import logging
from datetime import datetime
# ...other existing imports...

class ConversationManager:
    """
    Manages the conversation history with a fixed memory.
    """
    def __init__(self, max_memory=5):
        self.max_memory = max_memory
        self.messages = [{
            "role": "system",
            "content": (
                "you are Weatly, a helpful assistant. from portal 2, answer in a single short sentence"
            )
        }]

    def add_text_to_conversation(self, role, text):
        self.messages.append({"role": role, "content": text})
        # Keep only the latest max_memory messages (excluding system)
        while len(self.messages) > self.max_memory + 1:
            self.messages.pop(1)

    def get_conversation(self):
        return self.messages

    def print_memory(self):
        debug_color = "\033[94m"      # system
        user_color = "\033[92m"       # user
        assistant_color = "\033[93m"  # assistant
        reset_color = "\033[0m"
        max_width = 70
        
        print(f"\n{debug_color}+------------------------ Conversation Memory ------------------------+{reset_color}")
        for idx, msg in enumerate(self.messages):
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                role_color = debug_color; prefix = f"[{idx}] {role}: "
            elif role == "user":
                role_color = user_color; prefix = f"[{idx}] {role}:      "
            elif role == "assistant":
                role_color = assistant_color; prefix = f"[{idx}] {role}: "
            else:
                role_color = debug_color; prefix = f"[{idx}] {role}: "
            wrapped = textwrap.wrap(content, width=max_width-len(prefix))
            if wrapped:
                print(f"{role_color}{prefix}{wrapped[0]}{reset_color}")
                for line in wrapped[1:]:
                    print(f"{role_color}{' ' * len(prefix)}{line}{reset_color}")
            else:
                print(f"{role_color}{prefix}{reset_color}")
        print(f"{debug_color}+---------------------------------------------------------------------+{reset_color}\n")
