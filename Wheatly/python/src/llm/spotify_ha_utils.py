"""
spotify_ha_utils.py – v5.3
==========================
Adds `search_and_queue_track()` plus all previous features:
• pretty CLI demo (Rich optional) with ETA,
• auto artist selection,
• precise remove_from_queue().
"""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import spotipy
import yaml
from spotipy.oauth2 import SpotifyOAuth

try:
    from rich.console import Console
    from rich.table import Table

    _RICH_AVAILABLE = True
except ModuleNotFoundError:
    _RICH_AVAILABLE = False


_READ = (
    "user-read-playback-state user-read-currently-playing user-read-recently-played"
)
_WRITE = (
    _READ
    + " user-modify-playback-state playlist-modify-public playlist-modify-private"
)


def _load_cfg(path: str | Path | None = None) -> Dict[str, Any]:
    base = Path(__file__).resolve().parent.parent
    cfg_path = Path(path) if path else base / "config" / "config.yaml"
    with open(cfg_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class SpotifyHA:  # ─────────────────────────────────────────────────────────
    """Tiny OO wrapper around *spotipy* focused on queue & playback."""

    _default: "SpotifyHA" | None = None

    # ── construction ──────────────────────────────────────────────────
    def __init__(
        self,
        *,
        scopes: str = _WRITE,
        config_path: str | Path | None = None,
        redirect_uri: str = "http://127.0.0.1:5000/callback",
        open_browser: bool = False,
    ):
        try:
            cfg = _load_cfg(config_path)["secrets"]
            self._sp = spotipy.Spotify(
                auth_manager=SpotifyOAuth(
                    client_id=cfg["spotify_client_id"],
                    client_secret=cfg["spotify_client_secret"],
                    redirect_uri=redirect_uri,
                    scope=scopes,
                    open_browser=open_browser,
                )
            )
        except Exception as e:
            print("❌ ERROR: Authentication failed for Spotify! Please check your credentials or login again.")
            raise

    @classmethod
    def get_default(cls) -> "SpotifyHA":
        if cls._default is None:
            cls._default = cls()
        return cls._default

    # ── tiny helpers ──────────────────────────────────────────────────
    @staticmethod
    def _flat(track: Dict[str, Any] | None) -> Optional[Dict[str, Any]]:
        if not track:
            return None
        alb = track["album"]
        return {
            "id": track["id"],
            "uri": track["uri"],
            "name": track["name"],
            "artists": ", ".join(a["name"] for a in track["artists"]),
            "album": alb["name"],
            "image": alb["images"][0]["url"] if alb.get("images") else None,
            "duration_ms": track["duration_ms"],
        }

    @staticmethod
    def _ms_to_mmss(ms: int) -> str:
        m, s = divmod(ms // 1000, 60)
        h, m = divmod(m, 60)
        return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    @classmethod
    def _fmt_track(cls, t: Dict[str, Any] | None) -> str:
        return "∅" if t is None else f"{t['name']} – {t['artists']}  ({cls._ms_to_mmss(t['duration_ms'])})"

    # ── playback – read ───────────────────────────────────────────────
    def get_current_playback(self):
        return self._sp.current_playback()

    def get_current_track(self, *, simple: bool = True):
        pb = self.get_current_playback()
        return self._flat(pb["item"]) if pb and pb.get("item") and simple else pb

    def is_playing(self) -> bool:
        pb = self.get_current_playback()
        return bool(pb and pb.get("is_playing"))

    def get_queue(self, *, simple: bool = True):
        q = self._sp.queue().get("queue", [])
        return [self._flat(t) for t in q] if simple else q

    def _queue_wait_times(self) -> List[tuple[Dict[str, Any], int]]:
        pb = self.get_current_playback()
        rem_ms = (
            pb["item"]["duration_ms"] - pb.get("progress_ms", 0)
            if pb and pb.get("is_playing")
            else 0
        )
        times: list[tuple[Dict[str, Any], int]] = []
        for t in self.get_queue(simple=True):
            times.append((t, rem_ms))
            rem_ms += t["duration_ms"]
        return times

    # ── device helpers ────────────────────────────────────────────────
    def list_devices(self):
        return self._sp.devices()["devices"]

    def get_active_device(self):
        pb = self.get_current_playback()
        return pb.get("device") if pb else None

    def _with_device(self, device_id: str | None):
        if device_id:
            return device_id
        dev = self.get_active_device()
        if not dev:
            raise RuntimeError("No active device – start playback somewhere.")
        return dev["id"]

    # ── playback – control ────────────────────────────────────────────
    def play(self, device_id: str | None = None):
        self._sp.start_playback(device_id=self._with_device(device_id))

    def pause(self, device_id: str | None = None):
        self._sp.pause_playback(device_id=self._with_device(device_id))

    def skip_next(self, device_id: str | None = None):
        self._sp.next_track(device_id=self._with_device(device_id))

    def skip_previous(self, device_id: str | None = None):
        self._sp.previous_track(device_id=self._with_device(device_id))

    def toggle_play_pause(self, device_id: str | None = None):
        (self.pause if self.is_playing() else self.play)(device_id)

    def transfer_playback(self, device_id: str, *, force_play: bool = True):
        self._sp.transfer_playback(device_id, force_play=force_play)

    def start_playback(
        self,
        *,
        device_id: str | None = None,
        context_uri: str | None = None,
        uris: List[str] | None = None,
        offset: Dict[str, Any] | None = None,
        position_ms: int | None = None,
    ):
        self._sp.start_playback(
            device_id=self._with_device(device_id),
            context_uri=context_uri,
            uris=uris,
            offset=offset,
            position_ms=position_ms,
        )

    # ── search & queue helpers ────────────────────────────────────────
    def search_tracks(self, query: str, *, limit: int = 10, simple: bool = True):
        items = self._sp.search(q=query, type="track", limit=limit)["tracks"]["items"]
        #return nicely formated track description and action
        return [self._flat(t) for t in items] if simple else items

    def add_to_queue(
        self,
        uri: str,
        *,
        device_id: str | None = None,
        verify: bool = False,
        retries: int = 2,
        delay: float = 0.5,
    ):
        self._sp.add_to_queue(uri, device_id=self._with_device(device_id))
        if verify:
            for _ in range(retries + 1):
                if any(t["uri"] == uri for t in self.get_queue(simple=False)):
                    return
                time.sleep(delay)
            raise RuntimeError("Track did not appear in queue.")

    def play_track(self, uri: str, *, device_id: str | None = None):
        self.start_playback(device_id=device_id, uris=[uri])

    def search_and_queue_track(
        self,
        query: str,
        *,
        limit: int = 10,
        pick_first: bool = True,
        device_id: str | None = None,
        simple: bool = True,
    ):
        """Find track(s) by free-text *query* and queue one."""
        tracks = self.search_tracks(query, limit=limit, simple=False)
        if not tracks:
            return None
        track = tracks[0] if pick_first else random.choice(tracks)
        self.add_to_queue(track["uri"], device_id=device_id, verify=True)
        result = f"Queued: {track['name']} – {track['artists'][0]['name']}"
        return result

    # ── queue removal (precise) ───────────────────────────────────────
    def remove_from_queue(self, pos: int = 1) -> Optional[Dict[str, Any]]:
        queue = self.get_queue(simple=True)
        if not 1 <= pos <= len(queue):
            return None
        removed = queue[pos - 1]
        ahead = queue[: pos - 1]
        for _ in range(pos - 1):
            self.skip_next()
        self.skip_next()
        for t in reversed(ahead):
            self.add_to_queue(t["uri"])
        return removed

    # ── artist helper (auto pick) ─────────────────────────────────────
    @staticmethod
    def _best_artist(artists: list[Dict[str, Any]], query: str):
        if not artists:
            return None
        q = query.lower()
        for a in artists:
            if a["name"].lower() == q:
                return a
        return max(artists, key=lambda a: a["followers"]["total"])

    def artist_top_track(
        self,
        artist_name: str,
        *,
        country: str = "NO",
        pick_random: bool = True,
        device_id: str | None = None,
        add: bool = True,
        simple: bool = True,
    ):
        artists = self._sp.search(q=artist_name, type="artist", limit=10)["artists"][
            "items"
        ]
        artist = self._best_artist(artists, artist_name)
        if not artist:
            return None
        tracks = self._sp.artist_top_tracks(artist["id"], country=country)["tracks"]
        if not tracks:
            return None
        track = random.choice(tracks) if pick_random else tracks[0]
        if add:
            self.add_to_queue(track["uri"], device_id=device_id, verify=True)
        return self._flat(track) if simple else track

    # ── playlists & history ────────────────────────────────────────────
    def save_current_track_to_playlist(self, playlist_id: str, *, simple: bool = True):
        track = self.get_current_track(simple=False)
        if not track:
            return None
        self._sp.playlist_add_items(playlist_id, [track["uri"]])
        return self._flat(track) if simple else track

    def get_recently_played(self, *, limit: int = 20, simple: bool = True):
        items = self._sp.current_user_recently_played(limit=limit)["items"]
        tracks = [it["track"] for it in items]
        return [self._flat(t) for t in tracks] if simple else tracks

    # ── album playback ────────────────────────────────────────────────
    def play_album_by_name(self, album_name: str, artist: str = None, device_id: str | None = None) -> str:
        """Search for an album by name (and optional artist) and start playback of that album."""
        query = album_name
        if artist:
            query += f" artist:{artist}"
        results = self._sp.search(q=query, type="album", limit=5)
        albums = results.get("albums", {}).get("items", [])
        if not albums:
            return f"No album found for '{album_name}'" + (f" by {artist}" if artist else "")
        album = albums[0]
        album_uri = album["uri"]
        self.start_playback(device_id=device_id, context_uri=album_uri)
        return f"Started album: {album['name']} by {', '.join(a['name'] for a in album['artists'])}"

    # ── CLI demo remains unchanged (rich table) ────────────────────────
    def demo(self, artist: str = "Kaizers"):
        track = self.artist_top_track(artist, pick_random=True, add=True)
        queue_eta = self._queue_wait_times()

        if _RICH_AVAILABLE:
            console = Console()
            console.print(f":musical_note: Queued [bold]{self._fmt_track(track)}[/]\n")
            if not queue_eta:
                console.print("[dim](Queue is empty)")
                return
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", justify="right", width=3)
            table.add_column("Title")
            table.add_column("Artist(s)")
            table.add_column("▶ in", justify="right", width=7)
            for idx, (t, wait) in enumerate(queue_eta, 1):
                table.add_row(str(idx), t["name"], t["artists"], self._ms_to_mmss(wait))
            console.print(table)
        else:
            print(f"🎶 Queued: {self._fmt_track(track)}\n")
            for idx, (t, wait) in enumerate(queue_eta, 1):
                print(f"{idx:2}. {t['name']} – {t['artists']}  ▶ in {self._ms_to_mmss(wait)}")


if __name__ == "__main__":
    SpotifyHA.get_default().demo("Kaizers Orchestra")
