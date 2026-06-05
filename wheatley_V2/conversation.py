"""Bounded conversation history for Wheatley V2.

A tiny, dependency-injected port of ``wheatley/assistant/assistant.py``. The
system message is passed in by the caller; this module never reads config files
from disk and imports only the standard library.
"""

from __future__ import annotations

from datetime import datetime


class ConversationManager:
    """Maintain a bounded chat history ready for an OpenRouter request.

    The message list always begins with two reserved system slots:

    * slot 0 -- the primary system message (persona / instructions).
    * slot 1 -- the long-term-memory context (initially empty).

    User and assistant turns are appended after these slots and trimmed so that
    only the most recent ``max_memory`` non-system turns are retained.
    """

    def __init__(self, system_message: str, max_memory: int = 10) -> None:
        """Initialize the conversation buffer.

        Args:
            system_message: The primary system message (injected by the caller).
            max_memory: Maximum number of non-system turns to retain.
        """
        self.max_memory = max_memory
        self.messages: list[dict] = [
            {"role": "system", "content": system_message},
            {"role": "system", "content": ""},  # reserved: long-term memory
        ]

    def add(self, role: str, text: str) -> None:
        """Append a turn and trim to the last ``max_memory`` non-system turns.

        Args:
            role: The message role (``"user"`` or ``"assistant"``).
            text: The message content.
        """
        self.messages.append({"role": role, "content": text})
        # Keep the two reserved system slots plus the latest max_memory turns.
        while len(self.messages) > self.max_memory + 2:
            self.messages.pop(2)

    def set_system(self, text: str) -> None:
        """Replace the primary system message (slot 0).

        Args:
            text: The new system message content.
        """
        self.messages[0]["content"] = text

    def update_memory(self, text: str) -> None:
        """Set or replace the long-term-memory system message (slot 1).

        Args:
            text: The long-term-memory context.
        """
        self.messages[1]["content"] = text

    def get(self) -> list[dict]:
        """Return the full message list, ready for an OpenRouter chat request."""
        return self.messages

    @staticmethod
    def render(template: str) -> str:
        """Substitute ``<current_time>`` / ``<current_day>`` placeholders.

        Args:
            template: A string that may contain the placeholders.

        Returns:
            The template with placeholders replaced using ``datetime.now()``.
        """
        now = datetime.now()
        return template.replace(
            "<current_time>", now.strftime("%Y-%m-%d %H:%M:%S")
        ).replace("<current_day>", now.strftime("%A"))
