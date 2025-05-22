"""
spotify_agent.py
================
Adds tools:
• search_tracks          – return top N song matches.
• queue_track_by_name    – find a song by text and queue it.
• get_recently_played    – latest listening history.
• list_devices           – show user's Spotify devices.
• transfer_playback      – switch playback to a specific device.
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
    # ── NEW: search for songs ─────────────────────────────────────────
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
        "description": "Remove the N-th upcoming track (1 = next).",
        "parameters": {
            "type": "object",
            "properties": {
                "position": {"type": "integer", "default": 1},
            },
            "required": ["position"],
        },
    },
    # ── NEW: playback devices helpers ────────────────────────────────
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
                "device_id": {"type": "string"},
                "force_play": {"type": "boolean", "default": True},
            },
            "required": ["device_id"],
        },
    },
    # ── NEW: recently played ─────────────────────────────────────────
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
              message = (
                  f"Now playing '{track.get('name')}' by {track.get('artists')}"
                  f" from the album '{track.get('album')}'."
              )
              return message
            else:
              return "No track is currently playing."

        if name == "get_queue":
            queue_lim = arguments.get("limit", 10)
            q = self.spotify._queue_wait_times()[: queue_lim]
            return [
                {**t, "eta_hms": self.spotify._ms_to_mmss(eta)}
                for t, eta in q
            ]

        if name == "toggle_play_pause":
            self.spotify.toggle_play_pause()
            return {"status": "toggled play/pause"}

        if name == "skip_next_track":
            self.spotify.skip_next()
            return {"status": "skipped to next track"}

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
            removed = self.spotify.remove_from_queue(arguments["position"])
            return (
                {"status": "queue item removed", "track": removed}
                if removed
                else {"status": "nothing removed"}
            )

        if name == "list_devices":
            return self.spotify.list_devices()

        if name == "transfer_playback":
            self.spotify.transfer_playback(
                arguments["device_id"], force_play=arguments.get("force_play", True)
            )
            return {"status": "playback transferred"}

        if name == "get_recently_played":
            return self.spotify.get_recently_played(limit=limit, simple=True)

        raise NotImplementedError(f"No handler for tool {name}")

    # ── main interface ────────────────────────────────────────────────
    def llm_decide_and_dispatch(self, user_request, arguments: dict = None):
        now = datetime.now()
        tool_list = "\n".join(f"- {t['name']}: {t['description']}" for t in self.tools)

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
