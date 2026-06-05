"""Direct (no-MCP) integrations for Spotify and Google Calendar.

This module ports the essential Spotify and Google Calendar operations from
Wheatley v1 into plain, direct Python wrappers. There are no subprocess MCP
servers and no nested LLM agents — natural-language requests are mapped to
client calls with a pragmatic keyword/intent matcher.

Design notes:
    * Credentials are *injected* via a ``creds`` dict — nothing here reads a
      shared config module. A missing or invalid creds dict yields a disabled
      client (``enabled is False``) instead of raising at construction time.
    * Third-party imports (``spotipy`` / Google libraries) are lazy so the
      module always imports even when those packages are absent; tests mock
      the underlying client objects directly.

NL mapping limitation:
    ``call_spotify_agent`` / ``call_google_agent`` use a keyword/intent
    matcher rather than an LLM. This is intentional (simplicity is the #1
    goal). It handles representative phrasings ("play", "pause", "skip",
    "queue X", "what's playing", "calendar", "create event", ...) but is not a
    full natural-language understander. Callers needing richer parsing should
    pass structured requests or extend ``_match_spotify_intent`` /
    ``_match_google_intent``.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Spotify
# ─────────────────────────────────────────────────────────────────────────────
_SPOTIFY_SCOPE = (
    "user-read-playback-state user-read-currently-playing "
    "user-read-recently-played user-modify-playback-state "
    "playlist-modify-public playlist-modify-private"
)


class SpotifyClient:
    """Thin direct wrapper around a *spotipy* ``Spotify`` instance.

    Construct from an injected ``creds`` dict. If the required credentials are
    absent or authentication fails, the client is created in a *disabled*
    state (``enabled is False``) and every operation returns a friendly
    message instead of raising.

    Recognised creds keys:
        spotify_client_id, spotify_client_secret, and optionally
        spotify_redirect_uri (default ``https://127.0.0.1``).

    Args:
        creds: Mapping of credential values. May be ``None`` or empty.
        sp: Optional pre-built spotipy client (mainly for tests / DI). When
            provided the client is enabled regardless of ``creds``.
    """

    def __init__(self, creds: dict[str, Any] | None = None, *, sp: Any = None) -> None:
        """Build a Spotify client, disabling gracefully on missing creds."""
        self._sp: Any = None
        self.enabled: bool = False
        self.disabled_reason: str = ""

        if sp is not None:
            self._sp = sp
            self.enabled = True
            return

        creds = creds or {}
        client_id = creds.get("spotify_client_id")
        client_secret = creds.get("spotify_client_secret")
        if not client_id or not client_secret:
            self.disabled_reason = "Spotify credentials are missing."
            return

        try:
            import spotipy  # type: ignore[import-not-found, import-untyped]
            from spotipy.oauth2 import SpotifyOAuth  # type: ignore[import-not-found, import-untyped]

            self._sp = spotipy.Spotify(
                auth_manager=SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri=creds.get("spotify_redirect_uri", "https://127.0.0.1"),
                    scope=_SPOTIFY_SCOPE,
                    open_browser=False,
                )
            )
            self.enabled = True
        except Exception as exc:  # noqa: BLE001 - graceful disable
            self.disabled_reason = f"Spotify authentication failed: {exc}"
            self._sp = None
            self.enabled = False

    # ── tiny helpers ──────────────────────────────────────────────────
    @staticmethod
    def _flat(track: dict[str, Any] | None) -> dict[str, Any] | None:
        """Flatten a spotipy track object into a compact dict."""
        if not track:
            return None
        album = track.get("album", {})
        images = album.get("images") or []
        return {
            "id": track.get("id"),
            "uri": track.get("uri"),
            "name": track.get("name"),
            "artists": ", ".join(a["name"] for a in track.get("artists", [])),
            "album": album.get("name"),
            "image": images[0]["url"] if images else None,
            "duration_ms": track.get("duration_ms"),
        }

    def _active_device(self, device_id: str | None) -> str | None:
        """Return ``device_id`` or the currently active device id (or None)."""
        if device_id:
            return device_id
        pb = self._sp.current_playback()
        if pb and pb.get("device"):
            return pb["device"].get("id")
        return None

    # ── read ──────────────────────────────────────────────────────────
    def current_track(self) -> dict[str, Any] | None:
        """Return the currently playing track, flattened (or ``None``)."""
        pb = self._sp.current_playback()
        if pb and pb.get("item"):
            return self._flat(pb["item"])
        return None

    def is_playing(self) -> bool:
        """Return ``True`` when playback is currently active."""
        pb = self._sp.current_playback()
        return bool(pb and pb.get("is_playing"))

    def list_devices(self) -> list[dict[str, Any]]:
        """Return the user's available Spotify devices."""
        return self._sp.devices().get("devices", [])

    def get_queue(self) -> list[dict[str, Any] | None]:
        """Return the upcoming queue (flattened tracks)."""
        q = self._sp.queue().get("queue", [])
        return [self._flat(t) for t in q]

    # ── search ────────────────────────────────────────────────────────
    def search_tracks(
        self, query: str, *, limit: int = 5
    ) -> list[dict[str, Any] | None]:
        """Search Spotify for tracks matching ``query``."""
        items = (
            self._sp.search(q=query, type="track", limit=limit)
            .get("tracks", {})
            .get("items", [])
        )
        return [self._flat(t) for t in items]

    # ── control ───────────────────────────────────────────────────────
    def play(self, device_id: str | None = None) -> None:
        """Start/resume playback on the chosen or active device."""
        self._sp.start_playback(device_id=self._active_device(device_id))

    def pause(self, device_id: str | None = None) -> None:
        """Pause playback on the chosen or active device."""
        self._sp.pause_playback(device_id=self._active_device(device_id))

    def toggle_play_pause(self, device_id: str | None = None) -> None:
        """Toggle between play and pause on the chosen or active device."""
        if self.is_playing():
            self.pause(device_id)
        else:
            self.play(device_id)

    def skip_next(self, device_id: str | None = None) -> None:
        """Skip to the next track."""
        self._sp.next_track(device_id=self._active_device(device_id))

    def transfer_playback(self, device_id: str, *, force_play: bool = True) -> None:
        """Transfer playback to ``device_id``."""
        self._sp.transfer_playback(device_id, force_play=force_play)

    def queue_track_by_name(
        self, query: str, *, limit: int = 10, device_id: str | None = None
    ) -> str:
        """Find the best matching track by name and add it to the queue."""
        items = (
            self._sp.search(q=query, type="track", limit=limit)
            .get("tracks", {})
            .get("items", [])
        )
        if not items:
            return f"No track found for '{query}'."
        track = items[0]
        self._sp.add_to_queue(track["uri"], device_id=self._active_device(device_id))
        artists = ", ".join(a["name"] for a in track.get("artists", []))
        return f"Queued: {track['name']} - {artists}"


# ─────────────────────────────────────────────────────────────────────────────
# Google Calendar
# ─────────────────────────────────────────────────────────────────────────────
_GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarClient:
    """Thin direct wrapper around the Google Calendar v3 service.

    Construct from an injected ``creds`` dict. If credentials are absent or
    invalid the client is created in a *disabled* state and every operation
    returns a friendly message instead of raising.

    Recognised creds keys (any one of these enables construction):
        token / token_info: a mapping suitable for
            ``Credentials.from_authorized_user_info``.
        token_file: path to an authorized-user JSON token file.

    Args:
        creds: Mapping of credential values. May be ``None`` or empty.
        service: Optional pre-built Google Calendar service (for tests / DI).
            When provided the client is enabled regardless of ``creds``.
        calendar_id: Calendar to operate on. Defaults to ``"primary"``.
    """

    def __init__(
        self,
        creds: dict[str, Any] | None = None,
        *,
        service: Any = None,
        calendar_id: str = "primary",
    ) -> None:
        """Build a Calendar client, disabling gracefully on missing creds."""
        self._service: Any = None
        self.calendar_id = calendar_id
        self.enabled: bool = False
        self.disabled_reason: str = ""

        if service is not None:
            self._service = service
            self.enabled = True
            return

        creds = creds or {}
        token_info = creds.get("token") or creds.get("token_info")
        token_file = creds.get("token_file")
        if not token_info and not token_file:
            self.disabled_reason = "Google Calendar credentials are missing."
            return

        try:
            from google.oauth2.credentials import (  # type: ignore[import-not-found, import-untyped]
                Credentials,
            )
            from googleapiclient.discovery import build  # type: ignore[import-not-found, import-untyped]

            if token_info:
                google_creds = Credentials.from_authorized_user_info(
                    token_info, _GOOGLE_SCOPES
                )
            else:
                google_creds = Credentials.from_authorized_user_file(
                    token_file, _GOOGLE_SCOPES
                )
            self._service = build(
                "calendar", "v3", credentials=google_creds, cache_discovery=False
            )
            self.enabled = True
        except Exception as exc:  # noqa: BLE001 - graceful disable
            self.disabled_reason = f"Google Calendar authentication failed: {exc}"
            self._service = None
            self.enabled = False

    @staticmethod
    def _now_iso() -> str:
        """Return the current UTC time as an RFC3339 string."""
        return datetime.now(timezone.utc).isoformat()

    def list_events(
        self, days: int = 7, *, max_results: int = 25
    ) -> list[dict[str, Any]]:
        """List upcoming events in the next ``days`` days.

        Returns:
            A list of ``{"id", "start", "summary"}`` dicts.
        """
        time_min = self._now_iso()
        time_max = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        events = (
            self._service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                maxResults=max_results,
            )
            .execute()
            .get("items", [])
        )
        return [
            {
                "id": ev.get("id"),
                "start": ev.get("start", {}).get("dateTime")
                or ev.get("start", {}).get("date"),
                "summary": ev.get("summary", "(no title)"),
            }
            for ev in events
        ]

    def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        *,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a calendar event and return ``{"id", "summary", "htmlLink"}``."""
        body: dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time},
        }
        if description:
            body["description"] = description
        created = (
            self._service.events()
            .insert(calendarId=self.calendar_id, body=body)
            .execute()
        )
        return {
            "id": created.get("id"),
            "summary": created.get("summary", summary),
            "htmlLink": created.get("htmlLink"),
        }

    def delete_event(self, event_id: str) -> bool:
        """Delete the event with ``event_id``; returns ``True`` on success."""
        self._service.events().delete(
            calendarId=self.calendar_id, eventId=event_id
        ).execute()
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Natural-language → client-call mapping
# ─────────────────────────────────────────────────────────────────────────────
def _match_spotify_intent(request: str) -> tuple[str, dict[str, Any]]:
    """Map a free-text Spotify request to ``(intent, args)``.

    The matcher is deliberately simple (keyword/regex based). Unknown phrasings
    fall back to the ``"current_track"`` intent.
    """
    text = request.strip().lower()

    # queue X / add X to queue / play song X
    m = re.search(r"\bqueue\b\s+(?:the\s+song\s+|song\s+)?(.+)", text)
    if m:
        return "queue", {"query": m.group(1).strip()}
    m = re.search(r"\badd\b\s+(.+?)\s+to\s+(?:the\s+)?queue\b", text)
    if m:
        return "queue", {"query": m.group(1).strip()}

    if re.search(r"\b(pause|stop)\b", text):
        return "pause", {}
    if re.search(r"\b(skip|next)\b", text):
        return "skip", {}
    if re.search(r"\b(resume|unpause|play)\b", text) and "queue" not in text:
        return "play", {}
    if re.search(r"\b(device|devices)\b", text):
        return "devices", {}
    if re.search(r"\b(queue|upcoming)\b", text):
        return "get_queue", {}
    if re.search(r"\b(search|find|look up)\b", text):
        q = re.sub(r"\b(search|find|look up)\b(\s+for)?", "", text).strip()
        return "search", {"query": q or text}
    # "what's playing", "current song", "now playing"
    return "current_track", {}


def call_spotify_agent(
    user_request: str, device_id: str | None = None, *, client: SpotifyClient
) -> str:
    """Translate a natural-language Spotify request into client calls.

    Args:
        user_request: Free-text request (e.g. "pause", "queue Bohemian Rhapsody").
        device_id: Optional target device id.
        client: An injected :class:`SpotifyClient`.

    Returns:
        A human-readable result string. When the client is disabled a friendly
        "not configured" message is returned instead of raising.
    """
    if client is None or not getattr(client, "enabled", False):
        reason = getattr(client, "disabled_reason", "") if client else ""
        return f"Spotify integration is not configured. {reason}".strip()

    intent, args = _match_spotify_intent(user_request)

    try:
        if intent == "play":
            client.play(device_id)
            return "Playback started."
        if intent == "pause":
            client.pause(device_id)
            return "Playback paused."
        if intent == "skip":
            client.skip_next(device_id)
            return "Skipped to the next track."
        if intent == "queue":
            return client.queue_track_by_name(args["query"], device_id=device_id)
        if intent == "search":
            results = client.search_tracks(args["query"])
            if not results:
                return f"No tracks found for '{args['query']}'."
            lines = [
                f"{i}. {t['name']} - {t['artists']}"
                for i, t in enumerate(results, start=1)
                if t
            ]
            return "Search results:\n" + "\n".join(lines)
        if intent == "devices":
            devices = client.list_devices()
            if not devices:
                return "No available Spotify devices."
            return "Devices:\n" + "\n".join(
                f"- {d.get('name')} ({d.get('id')})" for d in devices
            )
        if intent == "get_queue":
            queue = client.get_queue()
            if not queue:
                return "The queue is empty."
            lines = [
                f"{i}. {t['name']} - {t['artists']}"
                for i, t in enumerate(queue, start=1)
                if t
            ]
            return "Upcoming queue:\n" + "\n".join(lines)
        # current_track
        track = client.current_track()
        if not track:
            return "No track is currently playing."
        return f"Now playing '{track['name']}' by {track['artists']}."
    except Exception as exc:  # noqa: BLE001 - surface as friendly text
        return f"Spotify request failed: {exc}"


_GOOGLE_DATE_RE = re.compile(r"\b(\d+)\s+day")


def _match_google_intent(request: str) -> tuple[str, dict[str, Any]]:
    """Map a free-text Calendar request to ``(intent, args)``.

    Only event *listing* can be reliably inferred from free text. Create/delete
    require structured arguments embedded in the request; when those are absent
    the matcher returns ``"need_args"`` for the caller to surface.
    """
    text = request.strip().lower()

    if re.search(r"\b(delete|remove|cancel)\b", text):
        # An event id must look id-like and must not be one of the request's
        # own words (verbs, articles, "event"/"id" hints). We require a token
        # that contains a digit OR mixed case OR an underscore/hyphen so plain
        # English words ("delete", "meeting", "standup") are not mistaken for
        # an id. Otherwise fall through to need_args.
        stop = {"delete", "remove", "cancel", "event", "events"}
        for tok in re.findall(r"\b([A-Za-z0-9_-]{6,})\b", request):
            if tok.lower() in stop:
                continue
            if (
                re.search(r"\d", tok)
                or "_" in tok
                or "-" in tok
                or (tok != tok.lower() and tok != tok.upper())
            ):
                return "delete", {"event_id": tok}
        return "need_args", {"action": "delete"}

    if re.search(r"\b(create|add|schedule|new)\b", text):
        return "need_args", {"action": "create"}

    # default: list events
    days = 7
    m = _GOOGLE_DATE_RE.search(text)
    if m:
        days = int(m.group(1))
    elif "tomorrow" in text:
        days = 1
    elif "week" in text:
        days = 7
    elif "month" in text:
        days = 30
    return "list", {"days": days}


def call_google_agent(user_request: str, *, client: GoogleCalendarClient) -> str:
    """Translate a natural-language Calendar request into client calls.

    Listing events is inferred from free text; creating/deleting events needs
    structured input. For creation, pass arguments via :func:`dispatch` with
    the ``create_google_calendar_event`` tool rather than free text.

    Args:
        user_request: Free-text request (e.g. "what's on my calendar this week").
        client: An injected :class:`GoogleCalendarClient`.

    Returns:
        A human-readable result string. When the client is disabled a friendly
        "not configured" message is returned instead of raising.
    """
    if client is None or not getattr(client, "enabled", False):
        reason = getattr(client, "disabled_reason", "") if client else ""
        return f"Google Calendar integration is not configured. {reason}".strip()

    intent, args = _match_google_intent(user_request)

    try:
        if intent == "delete":
            client.delete_event(args["event_id"])
            return f"Deleted event {args['event_id']}."
        if intent == "need_args":
            action = args.get("action", "that action")
            return (
                f"To {action} a calendar event I need structured details "
                "(summary, start time, end time). Please provide them explicitly."
            )
        # list
        events = client.list_events(days=args["days"])
        if not events:
            return f"No upcoming events in the next {args['days']} day(s)."
        lines = [f"- {ev['start']} — {ev['summary']}" for ev in events]
        return f"Upcoming events (next {args['days']} day(s)):\n" + "\n".join(lines)
    except Exception as exc:  # noqa: BLE001 - surface as friendly text
        return f"Google Calendar request failed: {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Tool surface (OpenAI chat tool schemas)
# ─────────────────────────────────────────────────────────────────────────────
_SPOTIFY_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "call_spotify_agent",
        "description": (
            "Control Spotify playback (play/pause/skip), search, queue tracks, "
            "list devices, transfer playback, or report the current track. Pass "
            "a natural-language request."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "Natural-language Spotify request.",
                },
                "device_id": {
                    "type": "string",
                    "description": "Optional target Spotify device id.",
                },
            },
            "required": ["user_request"],
        },
    },
}

_GOOGLE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "call_google_agent",
        "description": (
            "List, create, or delete Google Calendar events. Pass a "
            "natural-language request describing what you want."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "Natural-language Google Calendar request.",
                },
            },
            "required": ["user_request"],
        },
    },
}

INTEGRATION_TOOLS: list[dict[str, Any]] = [_SPOTIFY_TOOL, _GOOGLE_TOOL]


def _spotify_creds_present(creds: dict[str, Any]) -> bool:
    """Return ``True`` when minimally sufficient Spotify creds are present."""
    return bool(creds.get("spotify_client_id") and creds.get("spotify_client_secret"))


def _google_creds_present(creds: dict[str, Any]) -> bool:
    """Return ``True`` when minimally sufficient Google creds are present."""
    return bool(
        creds.get("token") or creds.get("token_info") or creds.get("token_file")
    )


def available_tools(creds: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return the integration tool schemas whose creds are present.

    A tool is omitted entirely when its credentials are absent, so a disabled
    integration is never advertised to the LLM.

    Args:
        creds: Injected credentials mapping (may be ``None`` or empty).

    Returns:
        A list of OpenAI chat tool schema dicts.
    """
    creds = creds or {}
    tools: list[dict[str, Any]] = []
    if _spotify_creds_present(creds):
        tools.append(_SPOTIFY_TOOL)
    if _google_creds_present(creds):
        tools.append(_GOOGLE_TOOL)
    return tools


def dispatch(
    name: str,
    args: dict[str, Any],
    *,
    spotify: SpotifyClient | None = None,
    google: GoogleCalendarClient | None = None,
) -> str | None:
    """Route a tool call by ``name`` to the injected clients.

    Args:
        name: Tool function name.
        args: Parsed tool arguments.
        spotify: Injected Spotify client (or ``None``).
        google: Injected Google Calendar client (or ``None``).

    Returns:
        The tool result string, or ``None`` when ``name`` is not owned by this
        integration module. When the relevant client is missing/disabled a
        friendly "not configured" message is returned.
    """
    args = args or {}
    if name == "call_spotify_agent":
        if spotify is None or not getattr(spotify, "enabled", False):
            reason = getattr(spotify, "disabled_reason", "") if spotify else ""
            return f"Spotify integration is not configured. {reason}".strip()
        return call_spotify_agent(
            args.get("user_request", ""),
            args.get("device_id"),
            client=spotify,
        )
    if name == "call_google_agent":
        if google is None or not getattr(google, "enabled", False):
            reason = getattr(google, "disabled_reason", "") if google else ""
            return f"Google Calendar integration is not configured. {reason}".strip()
        return call_google_agent(args.get("user_request", ""), client=google)
    return None
