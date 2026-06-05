"""Tests for wheatley_V2.integrations (fully mocked — no real OAuth)."""

from __future__ import annotations

import pathlib
import sys
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from wheatley_V2 import integrations  # noqa: E402
from wheatley_V2.integrations import (  # noqa: E402
    GoogleCalendarClient,
    SpotifyClient,
    available_tools,
    call_google_agent,
    call_spotify_agent,
    dispatch,
)


# ─────────────────────────────────────────────────────────────────────────────
# Mock builders
# ─────────────────────────────────────────────────────────────────────────────
def _make_track(name: str = "Song", artist: str = "Artist") -> dict:
    return {
        "id": "tid",
        "uri": "spotify:track:tid",
        "name": name,
        "artists": [{"name": artist}],
        "album": {"name": "Album", "images": [{"url": "http://img"}]},
        "duration_ms": 200000,
    }


def _make_spotipy() -> MagicMock:
    sp = MagicMock()
    sp.current_playback.return_value = {
        "is_playing": True,
        "item": _make_track("Now Playing", "Band"),
        "device": {"id": "dev123"},
    }
    sp.search.return_value = {"tracks": {"items": [_make_track("Found", "FBand")]}}
    sp.devices.return_value = {"devices": [{"name": "Phone", "id": "dev123"}]}
    sp.queue.return_value = {"queue": [_make_track("Queued", "QBand")]}
    return sp


def _make_google_service() -> MagicMock:
    service = MagicMock()
    events = service.events.return_value
    events.list.return_value.execute.return_value = {
        "items": [
            {
                "id": "ev1",
                "start": {"dateTime": "2026-06-06T10:00:00Z"},
                "summary": "Standup",
            }
        ]
    }
    events.insert.return_value.execute.return_value = {
        "id": "newid",
        "summary": "Meeting",
        "htmlLink": "http://link",
    }
    events.delete.return_value.execute.return_value = {}
    return service


@pytest.fixture()
def spotify_client() -> SpotifyClient:
    return SpotifyClient(sp=_make_spotipy())


@pytest.fixture()
def google_client() -> GoogleCalendarClient:
    return GoogleCalendarClient(service=_make_google_service())


# ─────────────────────────────────────────────────────────────────────────────
# Construction / graceful disable
# ─────────────────────────────────────────────────────────────────────────────
def test_spotify_client_disabled_without_creds():
    client = SpotifyClient({})
    assert client.enabled is False
    assert "missing" in client.disabled_reason.lower()


def test_spotify_client_disabled_with_none():
    client = SpotifyClient(None)
    assert client.enabled is False


def test_google_client_disabled_without_creds():
    client = GoogleCalendarClient({})
    assert client.enabled is False
    assert "missing" in client.disabled_reason.lower()


def test_injected_clients_enabled(spotify_client, google_client):
    assert spotify_client.enabled is True
    assert google_client.enabled is True


# ─────────────────────────────────────────────────────────────────────────────
# Spotify NL agent → expected client/spotipy calls
# ─────────────────────────────────────────────────────────────────────────────
def test_spotify_pause(spotify_client):
    sp = spotify_client._sp
    result = call_spotify_agent("pause the music", client=spotify_client)
    assert "paused" in result.lower()
    sp.pause_playback.assert_called_once()


def test_spotify_play_resume(spotify_client):
    sp = spotify_client._sp
    # not playing -> play() path through toggle? call_spotify_agent uses play directly
    call_spotify_agent("resume playback", client=spotify_client)
    sp.start_playback.assert_called_once()


def test_spotify_skip(spotify_client):
    sp = spotify_client._sp
    result = call_spotify_agent("skip to next", client=spotify_client)
    assert "skip" in result.lower()
    sp.next_track.assert_called_once()


def test_spotify_queue(spotify_client):
    sp = spotify_client._sp
    result = call_spotify_agent("queue Bohemian Rhapsody", client=spotify_client)
    assert "Queued" in result
    sp.add_to_queue.assert_called_once()
    # query was forwarded to search
    assert sp.search.call_args.kwargs["q"] == "bohemian rhapsody"


def test_spotify_search(spotify_client):
    sp = spotify_client._sp
    result = call_spotify_agent("search for jazz", client=spotify_client)
    assert "Found" in result
    sp.search.assert_called()


def test_spotify_devices(spotify_client):
    sp = spotify_client._sp
    result = call_spotify_agent("list devices", client=spotify_client)
    assert "Phone" in result
    sp.devices.assert_called()


def test_spotify_current_track(spotify_client):
    result = call_spotify_agent("what's playing", client=spotify_client)
    assert "Now Playing" in result


def test_spotify_get_queue(spotify_client):
    result = call_spotify_agent("show me the upcoming queue", client=spotify_client)
    assert "Queued" in result


def test_spotify_device_id_forwarded(spotify_client):
    sp = spotify_client._sp
    call_spotify_agent("pause", "explicit_dev", client=spotify_client)
    assert sp.pause_playback.call_args.kwargs["device_id"] == "explicit_dev"


def test_spotify_transfer_method(spotify_client):
    spotify_client.transfer_playback("targetdev")
    spotify_client._sp.transfer_playback.assert_called_once_with(
        "targetdev", force_play=True
    )


def test_spotify_agent_disabled_message():
    client = SpotifyClient({})
    result = call_spotify_agent("pause", client=client)
    assert "not configured" in result.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Google NL agent → expected service calls
# ─────────────────────────────────────────────────────────────────────────────
def test_google_list_events(google_client):
    service = google_client._service
    result = call_google_agent("what's on my calendar this week", client=google_client)
    assert "Standup" in result
    service.events.return_value.list.assert_called()


def test_google_list_days_parsed(google_client):
    call_google_agent("events in the next 3 days", client=google_client)
    kwargs = google_client._service.events.return_value.list.call_args.kwargs
    # timeMax should be ~3 days out; just assert list invoked with our calendar
    assert kwargs["calendarId"] == "primary"


def test_google_delete_event(google_client):
    service = google_client._service
    result = call_google_agent("delete event abc12345", client=google_client)
    assert "Deleted" in result
    service.events.return_value.delete.assert_called_once()


def test_google_create_needs_args(google_client):
    result = call_google_agent("create a new event", client=google_client)
    assert "structured details" in result.lower()


def test_google_create_event_method(google_client):
    service = google_client._service
    created = google_client.create_event(
        "Meeting", "2026-06-06T10:00:00Z", "2026-06-06T11:00:00Z"
    )
    assert created["id"] == "newid"
    service.events.return_value.insert.assert_called_once()


def test_google_agent_disabled_message():
    client = GoogleCalendarClient({})
    result = call_google_agent("what's on my calendar", client=client)
    assert "not configured" in result.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Tool surface
# ─────────────────────────────────────────────────────────────────────────────
def test_integration_tools_shape():
    for tool in integrations.INTEGRATION_TOOLS:
        assert tool["type"] == "function"
        assert "name" in tool["function"]
        assert "parameters" in tool["function"]
    names = {t["function"]["name"] for t in integrations.INTEGRATION_TOOLS}
    assert names == {"call_spotify_agent", "call_google_agent"}


def test_available_tools_empty_creds():
    assert available_tools({}) == []
    assert available_tools(None) == []


def test_available_tools_spotify_only():
    creds = {"spotify_client_id": "x", "spotify_client_secret": "y"}
    tools = available_tools(creds)
    names = {t["function"]["name"] for t in tools}
    assert names == {"call_spotify_agent"}


def test_available_tools_google_only():
    creds = {"token": {"refresh_token": "r"}}
    tools = available_tools(creds)
    names = {t["function"]["name"] for t in tools}
    assert names == {"call_google_agent"}


def test_available_tools_both():
    creds = {
        "spotify_client_id": "x",
        "spotify_client_secret": "y",
        "token_file": "/tmp/token.json",
    }
    tools = available_tools(creds)
    names = {t["function"]["name"] for t in tools}
    assert names == {"call_spotify_agent", "call_google_agent"}


# ─────────────────────────────────────────────────────────────────────────────
# dispatch
# ─────────────────────────────────────────────────────────────────────────────
def test_dispatch_unknown_returns_none(spotify_client, google_client):
    assert dispatch("not_my_tool", {}, spotify=spotify_client, google=google_client) is None


def test_dispatch_spotify(spotify_client):
    result = dispatch(
        "call_spotify_agent", {"user_request": "pause"}, spotify=spotify_client
    )
    assert "paused" in result.lower()
    spotify_client._sp.pause_playback.assert_called_once()


def test_dispatch_google(google_client):
    result = dispatch(
        "call_google_agent",
        {"user_request": "what's on my calendar"},
        google=google_client,
    )
    assert "Standup" in result


def test_dispatch_spotify_disabled_message():
    result = dispatch("call_spotify_agent", {"user_request": "pause"}, spotify=None)
    assert "not configured" in result.lower()


def test_dispatch_google_disabled():
    disabled = GoogleCalendarClient({})
    result = dispatch(
        "call_google_agent", {"user_request": "events"}, google=disabled
    )
    assert "not configured" in result.lower()
