"""Tests for ``wheatley_V2.tools``.

HTTP tools are unit-tested with a mocked ``requests.get``. Keyless live calls
to Open-Meteo and the joke API run by default (set ``WHEATLEY_SKIP_LIVE=1`` to
skip them). api-ninjas paths stay mocked because no key is available.
"""

from __future__ import annotations

import importlib
import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

# The shared test ``conftest.py`` may install a minimal ``requests`` stub that
# only provides ``post`` (it does so only when the real package was not yet
# imported). These tools need the real ``requests`` (with ``get``) for the
# keyless live calls, so evict any stub and import the genuine package, then
# (re)load ``tools`` so it binds to the real module.
_real_requests = sys.modules.get("requests")
if _real_requests is not None and not hasattr(_real_requests, "get"):
    del sys.modules["requests"]
    _real_requests = None
if _real_requests is None:
    importlib.import_module("requests")

from wheatley_V2 import tools  # noqa: E402

tools = importlib.reload(tools)

SKIP_LIVE = os.environ.get("WHEATLEY_SKIP_LIVE") == "1"


class FakeResponse:
    """Minimal stand-in for a ``requests.Response``."""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeQueue:
    """A simple synchronous fake queue capturing ``put_nowait`` calls."""

    def __init__(self):
        self.items = []

    def put_nowait(self, item):
        self.items.append(item)


# ---------------------------------------------------------------------------
# get_weather
# ---------------------------------------------------------------------------
def test_get_weather_mock_url_params_and_summary(monkeypatch):
    captured = {}

    def fake_get(url, params=None, headers=None):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse(
            {
                "latitude": 59.9,
                "longitude": 10.75,
                "elevation": 12.0,
                "timezone": "Europe/Oslo",
                "timezone_abbreviation": "CEST",
                "current_weather": {
                    "temperature": 17.3,
                    "time": "2026-06-05T12:00",
                    "weathercode": 3,
                },
            }
        )

    monkeypatch.setattr(tools.requests, "get", fake_get)

    result = tools.get_weather(59.9, 10.75)

    assert captured["url"] == "https://api.open-meteo.com/v1/forecast"
    assert captured["params"]["latitude"] == 59.9
    assert captured["params"]["longitude"] == 10.75
    assert captured["params"]["current_weather"] == "true"
    assert captured["params"]["temperature_unit"] == "celsius"
    assert captured["params"]["wind_speed_unit"] == "kmh"
    assert "hourly" not in captured["params"]
    assert "17.3" in result
    assert "Mainly clear" in result  # weathercode 3
    assert "(Code: 3)" in result


def test_get_weather_with_forecast(monkeypatch):
    captured = {}

    def fake_get(url, params=None, headers=None):
        captured["params"] = params
        return FakeResponse(
            {
                "latitude": 1.0,
                "longitude": 2.0,
                "current_weather": {
                    "temperature": 5.0,
                    "time": "t",
                    "weathercode": 0,
                },
                "hourly": {
                    "time": ["2026-06-05T00:00", "2026-06-05T01:00"],
                    "temperature_2m": [4.0, 4.5],
                    "weathercode": [0, 61],
                },
            }
        )

    monkeypatch.setattr(tools.requests, "get", fake_get)

    result = tools.get_weather(1.0, 2.0, include_forecast=True, forecast_days=2)

    assert captured["params"]["hourly"] == "temperature_2m,weathercode"
    assert captured["params"]["forecast_days"] == 2
    assert "Extended Forecast:" in result
    assert "temperature_2m=4.0" in result
    assert "Rain: Slight intensity" in result  # weathercode 61


# ---------------------------------------------------------------------------
# get_joke
# ---------------------------------------------------------------------------
def test_get_joke_mock(monkeypatch):
    captured = {}

    def fake_get(url, params=None, headers=None):
        captured["url"] = url
        return FakeResponse({"setup": "Why?", "punchline": "Because."})

    monkeypatch.setattr(tools.requests, "get", fake_get)

    result = tools.get_joke()

    assert captured["url"] == "https://official-joke-api.appspot.com/random_joke"
    assert "Why?" in result
    assert "Because." in result


# ---------------------------------------------------------------------------
# get_quote
# ---------------------------------------------------------------------------
def test_get_quote_no_key_returns_message(monkeypatch):
    def fail_get(*args, **kwargs):  # pragma: no cover - should not be called
        raise AssertionError("requests.get should not be called without a key")

    monkeypatch.setattr(tools.requests, "get", fail_get)

    result = tools.get_quote("")

    assert "api key missing" in result.lower()


def test_get_quote_mock_with_key(monkeypatch):
    captured = {}

    def fake_get(url, params=None, headers=None):
        captured["url"] = url
        captured["headers"] = headers
        return FakeResponse([{"quote": "Be bold.", "author": "Someone"}])

    monkeypatch.setattr(tools.requests, "get", fake_get)

    result = tools.get_quote("KEY123")

    assert captured["url"] == "https://api.api-ninjas.com/v1/quotes"
    assert captured["headers"] == {"X-Api-Key": "KEY123"}
    assert "Be bold." in result
    assert "Someone" in result


# ---------------------------------------------------------------------------
# get_city_coordinates
# ---------------------------------------------------------------------------
def test_get_city_coordinates_no_key_returns_message(monkeypatch):
    def fail_get(*args, **kwargs):  # pragma: no cover - should not be called
        raise AssertionError("requests.get should not be called without a key")

    monkeypatch.setattr(tools.requests, "get", fail_get)

    result = tools.get_city_coordinates("Oslo", "")

    assert "api key missing" in result.lower()
    assert "Oslo" in result


def test_get_city_coordinates_mock_with_key(monkeypatch):
    captured = {}

    def fake_get(url, params=None, headers=None):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        return FakeResponse([{"latitude": 59.91, "longitude": 10.75}])

    monkeypatch.setattr(tools.requests, "get", fake_get)

    result = tools.get_city_coordinates("Oslo", "KEY123")

    assert captured["url"] == "https://api.api-ninjas.com/v1/city"
    assert captured["params"] == {"name": "Oslo"}
    assert captured["headers"] == {"X-Api-Key": "KEY123"}
    assert "59.91" in result
    assert "10.75" in result


def test_get_city_coordinates_empty_data(monkeypatch):
    monkeypatch.setattr(
        tools.requests, "get", lambda *a, **k: FakeResponse([])
    )

    result = tools.get_city_coordinates("Nowhere", "KEY123")

    assert "No data available for Nowhere" in result


# ---------------------------------------------------------------------------
# Time parsing.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "value,expected",
    [
        ("07:30", (7, 30)),
        ("19:30", (19, 30)),
        ("00:00", (0, 0)),
        ("7am", (7, 0)),
        ("7pm", (19, 0)),
        ("12am", (0, 0)),
        ("12pm", (12, 0)),
        ("11PM", (23, 0)),
    ],
)
def test_parse_time_string(value, expected):
    assert tools._parse_time_string(value) == expected


def test_parse_time_string_invalid():
    with pytest.raises(ValueError):
        tools._parse_time_string("not a time")


# ---------------------------------------------------------------------------
# set_timer / set_reminder scheduling.
# ---------------------------------------------------------------------------
def test_set_timer_acknowledges_without_queue():
    result = tools.set_timer(5, "tea")
    assert "5" in result
    assert "tea" in result


def test_set_timer_schedules_on_queue(monkeypatch):
    scheduled = {}

    def fake_schedule(delay, event, event_queue):
        scheduled["delay"] = delay
        scheduled["event"] = event
        scheduled["queue"] = event_queue

    monkeypatch.setattr(tools, "_schedule_event", fake_schedule)

    queue = FakeQueue()
    result = tools.set_timer(10, "stretch", event_queue=queue)

    assert scheduled["delay"] == 10.0
    assert scheduled["event"]["source"] == "timer"
    assert scheduled["event"]["payload"] == "stretch"
    assert scheduled["queue"] is queue
    assert "10" in result


def test_set_reminder_schedules_on_queue(monkeypatch):
    scheduled = {}

    def fake_schedule(delay, event, event_queue):
        scheduled["delay"] = delay
        scheduled["event"] = event

    monkeypatch.setattr(tools, "_schedule_event", fake_schedule)

    queue = FakeQueue()
    result = tools.set_reminder("07:30", "wake up", event_queue=queue)

    assert scheduled["event"]["source"] == "reminder"
    assert scheduled["event"]["payload"] == "wake up"
    assert scheduled["event"]["metadata"]["reminder_time"] == "07:30"
    assert isinstance(scheduled["delay"], float)
    assert "07:30" in result


def test_set_reminder_invalid_time_raises():
    with pytest.raises(ValueError):
        tools.set_reminder("nonsense")


def test_schedule_event_fires_onto_queue():
    """The real ``_schedule_event`` should post to a fake queue after delay."""
    queue = FakeQueue()
    event = {"source": "timer", "payload": "x"}
    tools._schedule_event(0.01, event, queue)
    # Wait for the threading.Timer to fire.
    for _ in range(200):
        if queue.items:
            break
        import time

        time.sleep(0.01)
    assert queue.items == [event]


# ---------------------------------------------------------------------------
# dispatch.
# ---------------------------------------------------------------------------
def test_dispatch_unknown_returns_none():
    assert tools.dispatch("not_a_tool", {}) is None


def test_dispatch_routes_get_joke(monkeypatch):
    monkeypatch.setattr(
        tools, "get_joke", lambda: "JOKE"
    )
    assert tools.dispatch("get_joke", {}) == "JOKE"


def test_dispatch_injects_api_key(monkeypatch):
    captured = {}

    def fake_quote(api_key=""):
        captured["api_key"] = api_key
        return "Q"

    monkeypatch.setattr(tools, "get_quote", fake_quote)

    assert tools.dispatch("get_quote", {}, api_ninjas_key="K") == "Q"
    assert captured["api_key"] == "K"


def test_dispatch_injects_city_key(monkeypatch):
    captured = {}

    def fake_city(city, api_key=""):
        captured["city"] = city
        captured["api_key"] = api_key
        return "C"

    monkeypatch.setattr(tools, "get_city_coordinates", fake_city)

    result = tools.dispatch(
        "get_city_coordinates", {"city": "Oslo"}, api_ninjas_key="K"
    )
    assert result == "C"
    assert captured == {"city": "Oslo", "api_key": "K"}


def test_dispatch_injects_event_queue(monkeypatch):
    captured = {}

    def fake_timer(duration, reason="", *, event_queue=None):
        captured["duration"] = duration
        captured["queue"] = event_queue
        return "T"

    monkeypatch.setattr(tools, "set_timer", fake_timer)

    queue = FakeQueue()
    result = tools.dispatch("set_timer", {"duration": 3}, event_queue=queue)
    assert result == "T"
    assert captured["duration"] == 3
    assert captured["queue"] is queue


def test_dispatch_routes_get_weather(monkeypatch):
    monkeypatch.setattr(
        tools, "get_weather", lambda **kwargs: f"W:{kwargs}"
    )
    result = tools.dispatch("get_weather", {"latitude": 1.0, "longitude": 2.0})
    assert result.startswith("W:")


# ---------------------------------------------------------------------------
# Tool surface sanity.
# ---------------------------------------------------------------------------
def test_simple_tools_schema_shape():
    names = set()
    for tool in tools.SIMPLE_TOOLS:
        assert tool["type"] == "function"
        fn = tool["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn
        names.add(fn["name"])
    assert names == {
        "get_weather",
        "get_joke",
        "get_quote",
        "get_city_coordinates",
        "set_timer",
        "set_reminder",
    }


# ---------------------------------------------------------------------------
# Live keyless tests.
# ---------------------------------------------------------------------------
@pytest.mark.skipif(SKIP_LIVE, reason="WHEATLEY_SKIP_LIVE set")
def test_live_get_weather_oslo():
    result = tools.get_weather(59.91, 10.75)
    assert isinstance(result, str)
    assert "Weather Details:" in result
    assert "Temperature:" in result


@pytest.mark.skipif(SKIP_LIVE, reason="WHEATLEY_SKIP_LIVE set")
def test_live_get_joke():
    result = tools.get_joke()
    assert isinstance(result, str)
    assert result.startswith("Joke provided:")
    assert len(result) > len("Joke provided:  - ")
