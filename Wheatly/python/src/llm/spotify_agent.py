"""
spotify_agent.py
================
Adds tools:
• search_tracks          – return top N song matches.
• queue_track_by_name    – find a song by text and queue it.
• get_recently_played    – latest listening history.
• list_devices           – show user's Spotify devices.
• transfer_playback      – switch playback to a specific device.
• play_album_by_name     – play an entire album by name (optional artist/device)
All previous tools remain.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict

import openai
import yaml

try:
    from spotify_ha_utils import SpotifyHA
except ImportError:
    from llm.spotify_ha_utils import SpotifyHA

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

# ── SpotifyAgent class ────────────────────────────────────────────────
class SpotifyAgent:
    @staticmethod
    def _load_config() -> Dict[str, Any]:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        with open(os.path.join(base_dir, "config", "config.yaml"), encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    def __init__(self):
        cfg = self._load_config()
        self.spotify = SpotifyHA.get_default()
        openai.api_key = cfg["secrets"]["openai_api_key"]
        self.model = cfg["llm"]["model"]
        self.tools = SPOTIFY_TOOLS

    # ── dispatch mapping ──────────────────────────────────────────────
    def _dispatch(self, name: str, arguments: Dict[str, Any]):
        print(f"dispatching {name} with {arguments}")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}

        # basic casts
        limit = int(arguments.get("limit", 10)) if isinstance(arguments, dict) else 10

        if name == "get_current_track":
            track = self.spotify.get_current_track(simple=True)
            if track:
                return f"Now playing '{track.get('name')}' by {track.get('artists')} from the album '{track.get('album')}'."
            return "No track is currently playing."

        if name == "get_queue":
            queue_lim = arguments.get("limit", 10)
            q = self.spotify._queue_wait_times()[:queue_lim]
            lines = []
            if q:
                #currently playing track
                current_track = self.spotify.get_current_track(simple=True)
                if current_track:
                    lines.append(f"Now playing '{current_track.get('name')}' by {current_track.get('artists')} from the album '{current_track.get('album')}'.")
                lines.append("Upcoming Queue:")
                for idx, (track, eta) in enumerate(q, start=1):
                    eta_str = self.spotify._ms_to_mmss(eta)
                    name = track.get("name", "Unknown")
                    artists = track.get("artists", "Unknown")
                    album = track.get("album", "Unknown")
                    lines.append(f"{idx}. {name} by {artists} from '{album}' (ETA: {eta_str})")
            else:
                lines.append("No upcoming tracks in the queue.")
            return "\n".join(lines)

        if name == "toggle_play_pause":
            self.spotify.toggle_play_pause()
            return "toggled play/pause"

        if name == "skip_next_track":
            self.spotify.skip_next()
            return "skipped to next track"

        if name == "search_tracks":
            return self.spotify.search_tracks(arguments["query"], limit=limit, simple=True)

        if name == "queue_track_by_name":
            return self.spotify.search_and_queue_track(arguments["query"], limit=limit)

        if name == "queue_artist_top_track":
            return self.spotify.artist_top_track(
                arguments["artist_name"],
                pick_random=arguments.get("random", True),
                country="NO",
                add=True,
                simple=True,
            )

        if name == "remove_queue_item":
            self.spotify.remove_from_queue(arguments["count"])
            return f"{arguments['count']} queue item removed"

        if name == "list_devices":
            devices = self.spotify.list_devices()
            if not devices:
              return "No available devices."
            pretty_lines = []
            #add "available devices" header
            pretty_lines.append("Available devices:")
            for idx, device in enumerate(devices, start=1):
              pretty_lines.append(f"Device {idx}:")
              for key, value in device.items():
                pretty_lines.append(f"  {key}: {value}")
              pretty_lines.append("")  # add a blank line after each device
            return "\n".join(pretty_lines) + "\n"

        if name == "transfer_playback":
            self.spotify.transfer_playback(
                arguments["device_id"], force_play=arguments.get("force_play", True)
            )
            return f"playback transferred to device {arguments['device_id']}"

        if name == "get_recently_played":
            return self.spotify.get_recently_played(limit=limit, simple=True)

        if name == "play_album_by_name":
            return self.spotify.play_album_by_name(
                arguments["album_name"],
                artist=arguments.get("artist"),
                device_id=arguments.get("device_id"),
            )

        raise NotImplementedError(f"No handler for tool {name}")

    # ── main interface ────────────────────────────────────────────────
    def llm_decide_and_dispatch(self, user_request: str, arguments: Dict[str, Any] | None = None):
        now = datetime.now()
        tool_list = "\n".join(f"- {t['name']}: {t['description']}" for t in self.tools)

        #user request and arguments are passed to the LLM
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
    if obj is None:
        print("could not find anything")
        return

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
