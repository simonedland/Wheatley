"""Personality management for Wheatley V2.

This module owns the switchable personality state (normal/western/skitsofrenic)
and the OpenAI-format tool surface for the ``set_personality`` tool.

It is intentionally decoupled: the personalities dictionary is *passed in* by the
caller (read from config), so this module never reads config itself and never
imports sibling ``wheatley_V2`` modules. Only stdlib is used here.
"""

from __future__ import annotations

from typing import Callable

# Canonical personality modes recognised by the ``set_personality`` tool.
PERSONALITY_MODES: list[str] = ["normal", "western", "skitsofrenic"]

# Default fallback personality name.
DEFAULT_PERSONALITY: str = "normal"


class PersonalityManager:
    """Hold and switch between Wheatley's personalities.

    Each personality maps a name to a dict shaped like::

        {
            "system_message": str,
            "tts": {
                "voice_id": str,
                "stability": float,
                "similarity_boost": float,
                "style": float,
                "use_speaker_boost": bool,
                "speed": float,
            },
        }

    The personalities mapping is supplied by the caller (dependency injection),
    keeping this class free of any config or I/O concerns.
    """

    def __init__(self, personalities: dict, current: str = "normal") -> None:
        """Initialise the manager.

        Args:
            personalities: Mapping of personality name to its definition dict.
            current: Name of the personality to start with. If it is not present
                in ``personalities`` it falls back to ``"normal"`` (or, failing
                that, the first available personality).

        Raises:
            ValueError: If ``personalities`` is empty.
        """
        if not personalities:
            raise ValueError("personalities mapping must not be empty")
        self._personalities: dict = dict(personalities)
        self._current: str = self._resolve_initial(current)

    def _resolve_initial(self, current: str) -> str:
        """Return a valid starting personality name.

        Args:
            current: Requested starting personality.

        Returns:
            ``current`` if known, else ``"normal"`` if present, else the first
            available personality name.
        """
        if current in self._personalities:
            return current
        if DEFAULT_PERSONALITY in self._personalities:
            return DEFAULT_PERSONALITY
        return next(iter(self._personalities))

    def list_personalities(self) -> list[str]:
        """Return the available personality names.

        Returns:
            A list of personality names in insertion order.
        """
        return list(self._personalities)

    def get_personality(self, name: str) -> dict:
        """Return the personality definition for ``name``.

        Falls back to the current personality, then to ``"normal"``, when the
        requested name is unknown.

        Args:
            name: The personality name to look up.

        Returns:
            The personality definition dict.

        Raises:
            KeyError: If neither ``name``, the current personality, nor
                ``"normal"`` can be resolved (should not happen for a
                non-empty manager).
        """
        if name in self._personalities:
            return self._personalities[name]
        if self._current in self._personalities:
            return self._personalities[self._current]
        if DEFAULT_PERSONALITY in self._personalities:
            return self._personalities[DEFAULT_PERSONALITY]
        raise KeyError(
            f"Unknown personality {name!r} and no fallback "
            f"({self._current!r}/{DEFAULT_PERSONALITY!r}) available"
        )

    @property
    def current(self) -> str:
        """Return the name of the currently active personality."""
        return self._current

    def switch(self, name: str) -> dict:
        """Switch the active personality and return its definition.

        Args:
            name: The personality name to switch to.

        Returns:
            The newly active personality definition dict.

        Raises:
            ValueError: If ``name`` is not a known personality.
        """
        if name not in self._personalities:
            raise ValueError(
                f"Unknown personality {name!r}; "
                f"available: {self.list_personalities()}"
            )
        self._current = name
        return self._personalities[name]


# OpenAI-format tool schema for the ``set_personality`` tool.
PERSONALITY_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "set_personality",
            "description": (
                "Switch Wheatley's personality and voice. Valid modes are "
                "'normal', 'western', and 'skitsofrenic'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": list(PERSONALITY_MODES),
                        "description": "Desired personality mode.",
                    }
                },
                "required": ["mode"],
                "additionalProperties": False,
            },
        },
    }
]


def dispatch(
    name: str,
    args: dict,
    *,
    on_switch: Callable[[str, dict], None],
) -> str | None:
    """Dispatch a tool call related to personality switching.

    For ``set_personality``, the requested mode is validated against the known
    personality modes, then ``on_switch`` is invoked. The caller owns the
    ``PersonalityManager`` and performs the actual state change inside
    ``on_switch`` — looking up the personality definition, updating the
    conversation system message and TTS voice. A short confirmation string is
    then returned.

    Args:
        name: The tool name being dispatched.
        args: The arguments for the tool call (expects ``{"mode": <str>}`` for
            ``set_personality``).
        on_switch: Callback invoked as ``on_switch(mode, args)`` to apply the
            switch. It receives the validated mode and the raw tool arguments;
            the caller's closure is responsible for resolving the personality
            definition and updating conversation/TTS state.

    Returns:
        A short confirmation string for ``set_personality``, or ``None`` for any
        other (non-personality) tool name.

    Raises:
        ValueError: If ``mode`` is missing or not one of the valid modes.
    """
    if name != "set_personality":
        return None

    mode = args.get("mode")
    if mode not in PERSONALITY_MODES:
        raise ValueError(
            f"Invalid personality mode {mode!r}; "
            f"valid modes: {PERSONALITY_MODES}"
        )

    on_switch(mode, args)
    return f"Personality switched to {mode}."
