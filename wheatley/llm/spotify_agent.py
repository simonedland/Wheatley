"""
Adds tools.

• search_tracks          – return top N song matches.
• queue_track_by_name    – find a song by text and queue it.
• get_recently_played    – latest listening history.
• list_devices           – show user's Spotify devices.
• transfer_playback      – switch playback to a specific device.
• play_album_by_name     – play an entire album by name (optional artist/device)
All previous tools remain.

This module provides a Spotify agent with LLM-powered tool selection and playback control.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import openai  # type: ignore[import-not-found]
import yaml

from typing import Any, Dict, Callable, List, Tuple

try:
    from .spotify_ha_utils import SpotifyHA
except ImportError:
    from spotify_ha_utils import SpotifyHA  # type: ignore[import-not-found, no-redef]


# ── tools visible to the LLM ──────────────────────────────────────────
SPOTIFY_TOOLS = [
    {
        "type": "function",
        "name": "get_current_track",
        "description": "Return info about the track currently playing.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "function",
        "name": "get_queue",
        "description": "Return the upcoming queue with ETA for each item.",
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "toggle_play_pause",
        "description": "Toggle between play and pause.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "function",
        "name": "skip_next_track",
        "description": "Skip to the next track.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    # ── search for songs ─────────────────────────────────────────
    {
        "type": "function",
        "name": "search_tracks",
        "description": "Search Spotify for tracks by free-text query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "queue_track_by_name",
        "description": "Find the best matching track by name (and optional artist) and add it to the queue.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    # ── existing artist helper (NO region) ────────────────────────────
    {
        "type": "function",
        "name": "queue_artist_top_track",
        "description": "Queue one of the top tracks by the specified artist (market NO).",
        "parameters": {
            "type": "object",
            "properties": {
                "artist_name": {"type": "string"},
                "random": {"type": "boolean", "default": True},
            },
            "required": ["artist_name"],
        },
    },
    # ── queue removal ────────────────────────────────────────────────
    {
        "type": "function",
        "name": "remove_queue_item",
        "description": "Remove the N-1 upcoming track (1 = current). this will skip the current track and remove next n-1 tracks from queue.",
        "parameters": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "default": 1},
            },
            "required": ["count"],
        },
    },
    # ── playback devices helpers ────────────────────────────────
    {
        "type": "function",
        "name": "list_devices",
        "description": "List the user's Spotify devices.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "function",
        "name": "transfer_playback",
        "description": "Transfer playback to a given device id.",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
                "force_play": {"type": "boolean", "default": True},
            },
            "required": ["device_id"],
        },
    },
    # ── recently played ─────────────────────────────────────────
    {
        "type": "function",
        "name": "get_recently_played",
        "description": "Return the user's last N tracks.",
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 10}},
            "required": [],
        },
    },
    # ── play album by name ──────────────────────────────────────
    {
        "type": "function",
        "name": "play_album_by_name",
        "description": "Search for an album by name (and optional artist) and start playback of that album.",
        "parameters": {
            "type": "object",
            "properties": {
                "album_name": {"type": "string"},
                "artist": {"type": "string"},
                "device_id": {"type": "string"},
            },
            "required": ["album_name"],
        },
    },
]


_HANDLER_REGISTRY: dict[str, Callable[["SpotifyHA", Dict[str, Any], int], str]] = {}


def handles(name: str) -> Callable:
    """
    Register a function as a handler for a given name.

    This decorator returns a new decorator that, when applied, registers the decorated
    function in the handler registry under the provided name. Use it to quickly bind a
    handler to a specific tool identifier.
    """

    def decorator(func: Callable[["SpotifyHA", Dict[str, Any], int], str]):
        """Register a function as a handler for a specific tool name."""
        _HANDLER_REGISTRY[name] = func
        return func

    return decorator


# ── SpotifyAgent class ────────────────────────────────────────────────
class SpotifyAgent:
    """SpotifyAgent provides an interface to interact with Spotify using LLM tool selection and playback control."""

    @staticmethod
    def _load_config():
        base_dir = os.path.dirname(os.path.dirname(__file__))
        with open(
            os.path.join(base_dir, "config", "config.yaml"), encoding="utf-8"
        ) as fh:
            return yaml.safe_load(fh)

    def __init__(self):
        """Initialize the SpotifyAgent, loading configuration and authenticating with Spotify."""
        try:
            cfg = self._load_config()
            self.spotify = SpotifyHA.get_default()
        except Exception:
            print(
                "❌ ERROR: Authentication failed for Spotify! Please check your credentials or login again."
            )
            raise
        openai.api_key = cfg["secrets"]["openai_api_key"]
        self.model = cfg["llm"]["model"]
        self.tools = SPOTIFY_TOOLS

    # ── dispatch mapping ──────────────────────────────────────────────
    def _dispatch(self, name: str, arguments: Dict[str, Any] | str) -> str:
        """Route a tool call to the correct @handles handler."""
        args = self._coerce(arguments)
        limit = int(args.get("limit", 10))

        try:
            return _HANDLER_REGISTRY[name](self, args, limit)  # type: ignore[arg-type]
        except KeyError as exc:
            raise NotImplementedError(f"No handler for tool {name}") from exc

    # ────────────── Utilities ────────────── #

    @staticmethod
    def _coerce(arguments: Dict[str, Any] | str | None) -> Dict[str, Any]:
        if isinstance(arguments, str):
            try:
                return json.loads(arguments)
            except json.JSONDecodeError:
                return {}
        return arguments or {}

    # ────────────── Handlers (each gets its own decorator) ────────────── #
    @handles("get_current_track")
    def _get_current_track(self, _a: Dict[str, Any], _l: int) -> str:
        track = self.spotify.get_current_track(simple=True)
        if not track:
            return "No track is currently playing."
        return (
            f"Now playing '{track.get('name')}' by {track.get('artists')} "
            f"from the album '{track.get('album')}'."
        )

    @handles("get_queue")
    def _get_queue(self, args: Dict[str, Any], _l: int) -> str:
        queue_lim = args.get("limit", 10)
        q: List[Tuple[dict, int]] = self.spotify._queue_wait_times()[:queue_lim]

        if not q:
            return "No upcoming tracks in the queue."

        lines: list[str] = []
        current = self.spotify.get_current_track(simple=True)
        if current:
            lines.append(
                f"Now playing '{current.get('name')}' by {current.get('artists')} "
                f"from the album '{current.get('album')}'."
            )

        lines.append("Upcoming Queue:")
        for idx, (track, eta) in enumerate(q, start=1):
            lines.append(
                f"{idx}. {track.get('name', 'Unknown')} by {track.get('artists', 'Unknown')} "
                f"from '{track.get('album', 'Unknown')}' "
                f"(ETA: {self.spotify._ms_to_mmss(eta)})"
            )
        return "\n".join(lines)

    @handles("toggle_play_pause")
    def _toggle_play_pause(self, _a: Dict[str, Any], _l: int) -> str:
        self.spotify.toggle_play_pause()
        return "toggled play/pause"

    @handles("skip_next_track")
    def _skip_next_track(self, _a: Dict[str, Any], _l: int) -> str:
        self.spotify.skip_next()
        return "skipped to next track"

    @handles("search_tracks")
    def _search_tracks(self, args: Dict[str, Any], limit: int) -> str:
        return self.spotify.search_tracks(args["query"], limit=limit, simple=True)

    @handles("queue_track_by_name")
    def _queue_track_by_name(self, args: Dict[str, Any], limit: int) -> str:
        return self.spotify.search_and_queue_track(args["query"], limit=limit)

    @handles("queue_artist_top_track")
    def _queue_artist_top_track(self, args: Dict[str, Any], _l: int) -> str:
        return self.spotify.artist_top_track(
            args["artist_name"],
            pick_random=args.get("random", True),
            country="NO",
            add=True,
            simple=True,
        )

    @handles("remove_queue_item")
    def _remove_queue_item(self, args: Dict[str, Any], _l: int) -> str:
        self.spotify.remove_from_queue(args["count"])
        return f"{args['count']} queue item removed"

    @handles("list_devices")
    def _list_devices(self, _a: Dict[str, Any], _l: int) -> str:
        devices = self.spotify.list_devices()
        if not devices:
            return "No available devices."

        pretty: list[str] = ["Available devices:"]
        for idx, device in enumerate(devices, start=1):
            pretty.append(f"Device {idx}:")
            pretty.extend(f"  {k}: {v}" for k, v in device.items())
            pretty.append("")
        return "\n".join(pretty) + "\n"

    @handles("transfer_playback")
    def _transfer_playback(self, args: Dict[str, Any], _l: int) -> str:
        self.spotify.transfer_playback(
            args["device_id"], force_play=args.get("force_play", True)
        )
        return f"playback transferred to device {args['device_id']}"

    @handles("get_recently_played")
    def _get_recently_played(self, _a: Dict[str, Any], limit: int) -> str:
        return self.spotify.get_recently_played(limit=limit, simple=True)

    @handles("play_album_by_name")
    def _play_album_by_name(self, args: Dict[str, Any], _l: int) -> str:
        return self.spotify.play_album_by_name(
            args["album_name"],
            artist=args.get("artist"),
            device_id=args.get("device_id"),
        )

    # ── main interface ────────────────────────────────────────────────
    def llm_decide_and_dispatch(
        self, user_request: str, arguments: Dict[str, Any] | None = None
    ):
        """Given a user request, select and dispatch the appropriate tool using the LLM."""
        now = datetime.now()
        tool_list = "\n".join(f"- {t['name']}: {t['description']}" for t in self.tools)

        # user request and arguments are passed to the LLM
        if arguments:
            user_request = f"{user_request} {json.dumps(arguments)}"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a Spotify Agent for a Norwegian user (market NO). "
                    "Pick EXACTLY one tool from below and respond with its "
                    "function call:\n"
                    f"{tool_list}\n\n"
                    f"current_time: {now:%Y-%m-%d %H:%M:%S}, current_day: {now:%A}"
                ),
            },
            {"role": "user", "content": user_request},
        ]

        completion = openai.responses.create(
            model=self.model,
            input=messages,
            tools=self.tools,
            tool_choice="required",
            parallel_tool_calls=False,
        )

        for msg in completion.output:
            if msg.type == "function_call":
                return self._dispatch(msg.name, msg.arguments)

        raise RuntimeError("LLM did not return a function_call.")


def _pretty(obj):
    """Pretty-print the result of a SpotifyAgent operation."""
    if isinstance(obj, dict) and {"name", "artists"} <= obj.keys():
        eta = obj.get("eta_hms")
        line = f"🎵  {obj['name']} – {obj['artists']}"
        if eta:
            line += f"  ▶ in {eta}"
        print(line)
        return

    if isinstance(obj, dict) and "status" in obj:
        track = obj.get("track")
        if isinstance(track, dict):
            print(f"✔️  {obj['status']}: {track['name']} – {track['artists']}")
        else:
            print(f"✔️  {obj['status']}")
        return

    if isinstance(obj, list):
        for idx, item in enumerate(obj, 1):
            if isinstance(item, dict) and {"name", "artists"} <= item.keys():
                eta = item.get("eta_hms")
                line = f"{idx:2}. {item['name']} – {item['artists']}"
                if eta:
                    line += f"  ▶ in {eta}"
                print(line)
            elif isinstance(item, dict) and {"id", "name"} <= item.keys():
                print(f"{idx:2}. {item.get('name', item['id'])}")
            else:
                print(item)
        return

    print(obj)


if __name__ == "__main__":
    agent = SpotifyAgent()
    print("🎙  Spotify chat – Ctrl-C to quit")
    while True:
        try:
            user = input("You ➜ ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user:
            continue
        try:
            _pretty(agent.llm_decide_and_dispatch(user))
            print()
        except Exception as e:
            print("⚠️ ", e, "\n")
