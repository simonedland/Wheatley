"""Offline tests for the Wheatley V2 orchestrator (``wheatley_V2.main``).

The sibling modules (config, openrouter, tts, stt, conversation, memory,
personality, tools, integrations, hardware) are written in parallel by other
agents and are not present in this isolated worktree. So before importing
``wheatley_V2.main`` we install lightweight fake modules into ``sys.modules`` that
honour the interface contract. Everything here is deterministic and offline.
"""

from __future__ import annotations

import sys
import pathlib
import types
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))


# ---------------------------------------------------------------------------
# Fake sibling modules installed into sys.modules BEFORE importing main.
# ---------------------------------------------------------------------------


def _install_fake_siblings() -> dict[str, Any]:
    """Install fake ``wheatley_V2.*`` sibling modules and return shared handles.

    Returns:
        A dict of objects the tests reach into to assert behaviour (e.g. the
        record lists each fake ``dispatch`` appends to).
    """
    records: dict[str, Any] = {
        "tools_calls": [],
        "memory_calls": [],
        "personality_calls": [],
        "integrations_calls": [],
        "hardware_calls": [],
        "set_voice_calls": [],
        "switched": [],
    }

    pkg = "wheatley_V2"

    # --- config -------------------------------------------------------------
    config_mod = types.ModuleType(f"{pkg}.config")

    class _Settings:
        def __init__(self) -> None:
            self.openrouter_api_key = "or-key"
            self.elevenlabs_api_key = "xi-key"
            self.llm = {
                "default": "openai/gpt-4o-mini",
                "fast": "openai/gpt-4o-mini",
                "max_tokens": 1234,
                "max_memory": 10,
                "providers": {"openai/gpt-4o-mini": {"order": ["openai"]}},
            }
            self.stt = {
                "enabled": False,
                "model": "whisper-1",
                "language": "en",
                "provider": None,
            }
            self.tts = {
                "enabled": True,
                "voice_id": "voice-a",
                "model_id": "eleven_flash_v2_5",
            }
            self.wake_word = {"enabled": False}
            self.personalities = {
                "default": {
                    "system_message": "You are Wheatley (default).",
                    "tts": {"voice_id": "voice-a"},
                },
                "spooky": {
                    "system_message": "You are Wheatley (spooky).",
                    "tts": {"voice_id": "voice-b", "stability": 0.3},
                },
            }
            self.current_personality = "default"
            self.hardware = {"port": "dryrun", "baud_rate": 115200, "dry_run": True}
            self.integrations = {}

    config_mod.load_settings = lambda: _Settings()  # type: ignore[attr-defined]

    # --- openrouter ---------------------------------------------------------
    openrouter_mod = types.ModuleType(f"{pkg}.openrouter")

    class _Chunk:
        def __init__(self, text: str = "", tool_calls: Any = None) -> None:
            self.text = text
            self.tool_calls = tool_calls

    class _OpenRouterClient:
        #: Class-level script the fake stream replays; tests override per-call.
        stream_script: list[Any] = []

        def __init__(self, api_key: str, *, referer: str = "", title: str = "Wheatley"):
            self.api_key = api_key

        def chat_stream(
            self, messages, *, model, tools=None, max_tokens=2000, provider=None
        ):
            for item in _OpenRouterClient.stream_script:
                yield item

        def transcribe(
            self,
            audio: bytes,
            *,
            fmt="wav",
            model="whisper-1",
            language="en",
            provider=None,
        ) -> str:
            return "transcribed"

    openrouter_mod.OpenRouterClient = _OpenRouterClient  # type: ignore[attr-defined]
    openrouter_mod.ChatChunk = _Chunk  # type: ignore[attr-defined]

    # --- tts ----------------------------------------------------------------
    tts_mod = types.ModuleType(f"{pkg}.tts")

    class _TTSHandler:
        def __init__(self, api_key, voice_id, model_id="eleven_flash_v2_5"):
            self.api_key = api_key
            self.voice_id = voice_id
            self.model_id = model_id
            self.is_playing = False
            self.tasks: list = []
            self.processed: list[str] = []
            self.started = False
            self.flushed = 0
            self.waited = 0

        def start(self) -> None:
            self.started = True

        def process_text(self, chunk: str) -> None:
            self.processed.append(chunk)

        async def flush_pending(self) -> None:
            self.flushed += 1

        async def wait_idle(self) -> None:
            self.waited += 1

        def set_voice(self, voice_id, settings) -> None:
            records["set_voice_calls"].append((voice_id, settings))
            self.voice_id = voice_id

        def cleanup(self) -> None:
            self.cleaned = True

    tts_mod.TTSHandler = _TTSHandler  # type: ignore[attr-defined]

    # --- stt ----------------------------------------------------------------
    stt_mod = types.ModuleType(f"{pkg}.stt")

    class _VoiceListener:
        def __init__(self, transcribe_fn, *, wake_cfg, audio_cfg, greeting_dir=None):
            self.transcribe_fn = transcribe_fn

        async def hotword_listener(self, queue, tts_engine=None) -> None:
            # Idle forever until cancelled.
            import asyncio as _a

            await _a.Event().wait()

        def cleanup(self) -> None:
            pass

    stt_mod.VoiceListener = _VoiceListener  # type: ignore[attr-defined]

    # --- conversation -------------------------------------------------------
    conversation_mod = types.ModuleType(f"{pkg}.conversation")

    class _ConversationManager:
        def __init__(self, system_message, max_memory=10):
            self.system_message = system_message
            self.max_memory = max_memory
            self.messages: list[dict] = []
            self.long_term = ""

        def add(self, role: str, text: str) -> None:
            self.messages.append({"role": role, "content": text})

        def update_memory(self, text: str) -> None:
            self.long_term = text

        def set_system(self, text: str) -> None:
            self.system_message = text

        def get(self) -> list[dict]:
            return [{"role": "system", "content": self.system_message}, *self.messages]

    conversation_mod.ConversationManager = _ConversationManager  # type: ignore[attr-defined]

    # --- memory -------------------------------------------------------------
    memory_mod = types.ModuleType(f"{pkg}.memory")
    memory_mod.MEMORY_TOOLS = [{"function": {"name": "remember"}}]  # type: ignore[attr-defined]

    def _memory_dispatch(name, args):
        records["memory_calls"].append((name, args))
        if name == "remember":
            return "remembered"
        return None

    memory_mod.dispatch = _memory_dispatch  # type: ignore[attr-defined]
    memory_mod.as_context = lambda: "LONG TERM MEMORY: none"  # type: ignore[attr-defined]

    # --- personality --------------------------------------------------------
    personality_mod = types.ModuleType(f"{pkg}.personality")

    class _PersonalityManager:
        def __init__(self, personalities, current):
            self.personalities = personalities
            self._current = current

        @property
        def current(self) -> str:
            return self._current

        def get_personality(self, name) -> dict:
            return self.personalities.get(name, {})

        def switch(self, name) -> dict:
            self._current = name
            return self.personalities.get(name, {})

    def _personality_dispatch(name, args, *, on_switch):
        records["personality_calls"].append((name, args))
        if name == "set_personality":
            mode = args.get("mode")
            on_switch(mode, args)
            return f"switched to {mode}"
        return None

    personality_mod.PersonalityManager = _PersonalityManager  # type: ignore[attr-defined]
    personality_mod.dispatch = _personality_dispatch  # type: ignore[attr-defined]
    personality_mod.PERSONALITY_TOOLS = [  # type: ignore[attr-defined]
        {"function": {"name": "set_personality"}}
    ]

    # --- tools --------------------------------------------------------------
    tools_mod = types.ModuleType(f"{pkg}.tools")
    tools_mod.SIMPLE_TOOLS = [{"function": {"name": "get_time"}}]  # type: ignore[attr-defined]

    def _tools_dispatch(name, args, *, api_ninjas_key="", event_queue=None):
        records["tools_calls"].append((name, args, api_ninjas_key))
        if name == "get_time":
            return "12:00"
        return None

    tools_mod.dispatch = _tools_dispatch  # type: ignore[attr-defined]

    # --- integrations -------------------------------------------------------
    integrations_mod = types.ModuleType(f"{pkg}.integrations")
    integrations_mod.available_tools = (  # type: ignore[attr-defined]
        lambda creds: [{"function": {"name": "play_song"}}]
    )

    def _integrations_dispatch(name, args, *, spotify=None, google=None):
        records["integrations_calls"].append((name, args))
        if name == "play_song":
            return "playing"
        return None

    integrations_mod.dispatch = _integrations_dispatch  # type: ignore[attr-defined]

    # --- hardware -----------------------------------------------------------
    hardware_mod = types.ModuleType(f"{pkg}.hardware")

    class _HardwareInterface:
        def __init__(self, port="dryrun", baud_rate=115200, dry_run=True):
            self.port = port
            self.baud_rate = baud_rate
            self.dry_run = dry_run
            self.closed = False

        def close(self) -> None:
            self.closed = True

    hardware_mod.HardwareInterface = _HardwareInterface  # type: ignore[attr-defined]
    hardware_mod.ANIMATION_TOOLS = [{"function": {"name": "set_animation"}}]  # type: ignore[attr-defined]

    def _hardware_dispatch(name, args, *, hw=None):
        records["hardware_calls"].append((name, args))
        if name == "set_animation":
            return "animated"
        return None

    hardware_mod.dispatch = _hardware_dispatch  # type: ignore[attr-defined]

    import importlib

    pkg_obj = importlib.import_module(pkg)

    fakes: dict[str, Any] = {}
    saved: dict[str, Any] = {}
    saved_attrs: dict[str, Any] = {}
    _MISSING = object()
    for mod in (
        config_mod,
        openrouter_mod,
        tts_mod,
        stt_mod,
        conversation_mod,
        memory_mod,
        personality_mod,
        tools_mod,
        integrations_mod,
        hardware_mod,
    ):
        short = mod.__name__.split(".", 1)[1]
        fakes[short] = mod
        if mod.__name__ in sys.modules:
            saved[mod.__name__] = sys.modules[mod.__name__]
        sys.modules[mod.__name__] = mod
        # ``from wheatley_V2 import <short>`` resolves via ``getattr`` on the
        # package object first, so if a sibling test already imported the real
        # submodule (setting the attribute), our fake in sys.modules would be
        # bypassed. Set the attribute too, and remember the original.
        saved_attrs[short] = getattr(pkg_obj, short, _MISSING)
        setattr(pkg_obj, short, mod)

    records["Chunk"] = _Chunk
    records["OpenRouterClient"] = _OpenRouterClient
    records["_fakes"] = fakes
    records["_saved"] = saved
    records["_saved_attrs"] = saved_attrs
    records["_pkg"] = pkg_obj
    records["_missing"] = _MISSING
    return records


RECORDS = _install_fake_siblings()

# Import AFTER the fakes are installed. ``main`` binds its references to the
# fakes at import time, so we can immediately restore ``sys.modules`` (and the
# package attributes) to avoid leaking these fakes into the rest of the test
# suite's collection (sibling test modules import the *real* wheatley_V2.*).
from wheatley_V2 import main  # noqa: E402

for _name, _mod in list(RECORDS["_fakes"].items()):
    _full = f"wheatley_V2.{_name}"
    if _full in RECORDS["_saved"]:
        sys.modules[_full] = RECORDS["_saved"][_full]
    else:
        sys.modules.pop(_full, None)
    _orig = RECORDS["_saved_attrs"][_name]
    if _orig is RECORDS["_missing"]:
        if hasattr(RECORDS["_pkg"], _name):
            delattr(RECORDS["_pkg"], _name)
    else:
        setattr(RECORDS["_pkg"], _name, _orig)

# Convenience handle for tests that need the fake sibling modules directly.
FAKES = RECORDS["_fakes"]


# ---------------------------------------------------------------------------
# dispatch_tool routing tests
# ---------------------------------------------------------------------------


def _make_dispatcher():
    """Build a ``dispatch_tool`` wired to the fake personality + hardware."""
    personality = FAKES["personality"].PersonalityManager(
        {
            "default": {"system_message": "d", "tts": {"voice_id": "voice-a"}},
            "spooky": {"system_message": "s", "tts": {"voice_id": "voice-b"}},
        },
        "default",
    )

    def _on_switch(mode, args):
        personality.switch(mode)
        RECORDS["switched"].append(mode)

    hardware = FAKES["hardware"].HardwareInterface()
    return (
        main.build_dispatcher(
            creds={"api_ninjas_key": "nk"},
            spotify=None,
            google=None,
            hardware=hardware,
            on_switch=_on_switch,
        ),
        personality,
    )


def test_dispatch_routes_to_tools_module():
    dispatch_tool, _ = _make_dispatcher()
    assert dispatch_tool("get_time", {}) == "12:00"
    assert RECORDS["tools_calls"][-1] == ("get_time", {}, "nk")


def test_dispatch_routes_to_memory_module():
    dispatch_tool, _ = _make_dispatcher()
    assert dispatch_tool("remember", {"x": 1}) == "remembered"


def test_dispatch_routes_to_integrations_module():
    dispatch_tool, _ = _make_dispatcher()
    assert dispatch_tool("play_song", {"q": "song"}) == "playing"


def test_dispatch_routes_to_hardware_module():
    dispatch_tool, _ = _make_dispatcher()
    assert dispatch_tool("set_animation", {"name": "wave"}) == "animated"


def test_dispatch_returns_first_non_none_and_personality_on_switch():
    dispatch_tool, personality = _make_dispatcher()
    result = dispatch_tool("set_personality", {"mode": "spooky"})
    assert result == "switched to spooky"
    assert personality.current == "spooky"
    assert RECORDS["switched"][-1] == "spooky"


def test_dispatch_unknown_tool_reports_unavailable():
    dispatch_tool, _ = _make_dispatcher()
    assert "not available" in dispatch_tool("does_not_exist", {})


# ---------------------------------------------------------------------------
# Streaming loop: text deltas go to tts.process_text + printed; tool calls run.
# ---------------------------------------------------------------------------


async def test_handle_turn_streams_text_to_tts_and_dispatches_tool(capsys):
    Chunk = RECORDS["Chunk"]
    OpenRouterClient = RECORDS["OpenRouterClient"]

    calls = {"n": 0}
    tool_call = {"function": {"name": "get_time", "arguments": "{}"}}

    def scripted_stream(
        self, messages, *, model, tools=None, max_tokens=2000, provider=None
    ):
        calls["n"] += 1
        if calls["n"] == 1:
            # First pass: emit text deltas then request a tool.
            yield Chunk(text="Hello")
            yield Chunk(text=" world")
            yield Chunk(tool_calls=[tool_call])
        else:
            # Second pass after tool result: finish plainly.
            yield Chunk(text="!")

    OpenRouterClient.chat_stream = scripted_stream  # type: ignore[assignment]

    client = OpenRouterClient("k")
    conversation = FAKES["conversation"].ConversationManager("sys")
    tts = FAKES["tts"].TTSHandler("k", "voice-a")

    dispatched: list = []

    def dispatch_tool(name, args):
        dispatched.append((name, args))
        return "12:00"

    await main.handle_turn(
        "what time is it",
        client=client,
        conversation=conversation,
        dispatch_tool=dispatch_tool,
        tts=tts,
        model="m",
        provider=None,
        tools=[],
        max_tokens=100,
    )

    # Text deltas were streamed straight into TTS (overlap), in order.
    assert tts.processed == ["Hello", " world", "!"]

    # And printed to the console.
    out = capsys.readouterr().out
    assert "Hello" in out and "world" in out

    # Tool was dispatched and its result appended to the conversation.
    assert dispatched == [("get_time", {})]
    contents = [m["content"] for m in conversation.messages]
    assert "what time is it" in contents
    assert "Hello world" in contents  # assistant text accumulated
    assert any("get_time: 12:00" in c for c in contents)  # tool result recorded

    # Flush + wait happened once the stream finished.
    assert tts.flushed >= 1 and tts.waited >= 1


async def test_handle_turn_without_tts_still_completes(capsys):
    Chunk = RECORDS["Chunk"]
    OpenRouterClient = RECORDS["OpenRouterClient"]

    def scripted_stream(
        self, messages, *, model, tools=None, max_tokens=2000, provider=None
    ):
        yield Chunk(text="Hi there")

    OpenRouterClient.chat_stream = scripted_stream  # type: ignore[assignment]

    client = OpenRouterClient("k")
    conversation = FAKES["conversation"].ConversationManager("sys")

    await main.handle_turn(
        "hi",
        client=client,
        conversation=conversation,
        dispatch_tool=lambda n, a: "x",
        tts=None,
        model="m",
        provider=None,
        tools=[],
        max_tokens=100,
    )

    out = capsys.readouterr().out
    assert "Hi there" in out
    contents = [m["content"] for m in conversation.messages]
    assert "Hi there" in contents


def test_parse_tool_call_handles_dict_and_object():
    name, args = main._parse_tool_call(
        {"function": {"name": "f", "arguments": '{"a": 1}'}}
    )
    assert name == "f" and args == {"a": 1}

    class _Fn:
        name = "g"
        arguments = {"b": 2}

    class _Call:
        function = _Fn()

    name, args = main._parse_tool_call(_Call())
    assert name == "g" and args == {"b": 2}

    # Bad JSON falls back to a raw wrapper rather than raising.
    name, args = main._parse_tool_call({"name": "h", "arguments": "not json"})
    assert name == "h" and args == {"_raw": "not json"}
