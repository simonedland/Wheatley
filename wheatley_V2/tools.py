"""Simple everyday tools for Wheatley V2.

This module provides a small, dependency-injected set of "everyday" tools
(weather, jokes, quotes, city coordinates, timers and reminders) plus the
OpenAI chat tool schemas describing them and a :func:`dispatch` router.

Design principles:
    * Only the standard library and :mod:`requests` are imported.
    * Sibling ``wheatley_V2`` modules are never imported.
    * Secrets (e.g. the api-ninjas key) and the event queue are passed in,
      never read from configuration here.
"""

from __future__ import annotations

import re
import threading
from datetime import datetime, timedelta
from typing import Any, Optional

import requests

# ---------------------------------------------------------------------------
# Weather code descriptions (ported from v1 ``llm_client_utils``).
# ---------------------------------------------------------------------------
WEATHER_CODE_DESCRIPTIONS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear, partly cloudy, and overcast",
    2: "Mainly clear, partly cloudy, and overcast",
    3: "Mainly clear, partly cloudy, and overcast",
    45: "Fog and depositing rime fog",
    48: "Fog and depositing rime fog",
    51: "Drizzle: Light intensity",
    53: "Drizzle: Moderate intensity",
    55: "Drizzle: Dense intensity",
    56: "Freezing Drizzle: Light intensity",
    57: "Freezing Drizzle: Dense intensity",
    61: "Rain: Slight intensity",
    63: "Rain: Moderate intensity",
    65: "Rain: Heavy intensity",
    66: "Freezing Rain: Light intensity",
    67: "Freezing Rain: Heavy intensity",
    71: "Snow fall: Slight intensity",
    73: "Snow fall: Moderate intensity",
    75: "Snow fall: Heavy intensity",
    77: "Snow grains",
    80: "Rain showers: Slight intensity",
    81: "Rain showers: Moderate intensity",
    82: "Rain showers: Violent",
    85: "Snow showers: Slight intensity",
    86: "Snow showers: Heavy intensity",
    95: "Thunderstorm: Slight or moderate",
    96: "Thunderstorm with slight hail (Central Europe only)",
    99: "Thunderstorm with heavy hail (Central Europe only)",
}

# Time-string parsing helpers (ported from v1 ``llm_client``).
_TIME_24H = re.compile(r"^(\d{1,2}):(\d{2})$")
_TIME_AMPM = re.compile(r"^(\d{1,2})(am|pm)$", re.I)

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_JOKE_URL = "https://official-joke-api.appspot.com/random_joke"
_QUOTE_URL = "https://api.api-ninjas.com/v1/quotes"
_CITY_URL = "https://api.api-ninjas.com/v1/city"


# ---------------------------------------------------------------------------
# HTTP tools.
# ---------------------------------------------------------------------------
def get_weather(
    latitude: float,
    longitude: float,
    *,
    include_forecast: bool = False,
    forecast_days: int = 7,
    temperature_unit: str = "celsius",
    wind_speed_unit: str = "kmh",
) -> str:
    """Return a concise weather summary for the given coordinates.

    Calls the keyless Open-Meteo forecast API and maps the current weather
    code to a human-readable description.

    Args:
        latitude: Latitude of the location in decimal degrees.
        longitude: Longitude of the location in decimal degrees.
        include_forecast: If ``True``, append an hourly extended forecast.
        forecast_days: Number of forecast days to request (1-14).
        temperature_unit: ``"celsius"`` or ``"fahrenheit"``.
        wind_speed_unit: ``"kmh"``, ``"ms"``, ``"mph"`` or ``"kn"``.

    Returns:
        A multi-line human-readable weather summary string.
    """
    extra_hourly = ["temperature_2m", "weathercode"]
    params: dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
        "current_weather": "true",
        "forecast_days": forecast_days,
        "temperature_unit": temperature_unit,
        "wind_speed_unit": wind_speed_unit,
    }
    if include_forecast:
        params["hourly"] = ",".join(extra_hourly)

    response = requests.get(_OPEN_METEO_URL, params=params)
    data = response.json()
    cw = data.get("current_weather", {})

    summary = (
        f"Weather Details:\n"
        f"Location: ({data.get('latitude')}, {data.get('longitude')})\n"
        f"Temperature: {cw.get('temperature')}°C\n"
        f"Time: {cw.get('time')}\n"
        f"Elevation: {data.get('elevation')} m\n"
        f"Timezone: {data.get('timezone')} ({data.get('timezone_abbreviation')})"
    )

    weather_code = cw.get("weathercode")
    if weather_code is not None:
        weather_code_int = int(weather_code)
        description = WEATHER_CODE_DESCRIPTIONS.get(
            weather_code_int, "Unknown weather condition"
        )
        summary += (
            f"\nWeather Condition: {description} (Code: {weather_code_int})"
        )

    if include_forecast:
        hours_data = data.get("hourly", {})
        times = hours_data.get("time", [])
        forecast_summary = "\nExtended Forecast:\n"
        for i, t in enumerate(times):
            line_info = [t]
            for var_name in extra_hourly:
                var_values = hours_data.get(var_name, [])
                if i < len(var_values):
                    value = var_values[i]
                    if var_name == "weathercode":
                        code_int = int(value)
                        desc = WEATHER_CODE_DESCRIPTIONS.get(code_int, "Unknown")
                        line_info.append(f"{var_name}={value} ({desc})")
                    else:
                        line_info.append(f"{var_name}={value}")
            forecast_summary += ", ".join(line_info) + "\n"
        summary += forecast_summary

    return summary


def get_joke() -> str:
    """Return a random joke from the keyless official-joke-api.

    Returns:
        A human-readable joke string.
    """
    response = requests.get(_JOKE_URL)
    data = response.json()
    return f"Joke provided: {data.get('setup')} - {data.get('punchline')}"


def get_quote(api_key: str = "") -> str:
    """Return a random inspirational quote from api-ninjas.

    Args:
        api_key: The api-ninjas API key. If empty, a clear "missing key"
            message is returned instead of making a request.

    Returns:
        A human-readable quote string, or a message explaining that no quote
        is available.
    """
    if not api_key:
        return "No quote available: api key missing."
    headers = {"X-Api-Key": api_key}
    response = requests.get(_QUOTE_URL, headers=headers)
    data = response.json()
    if data and isinstance(data, list):
        item = data[0]
        return f"Tell the user: {item.get('quote', '')} — {item.get('author', '')}"
    return "No quote available."


def get_city_coordinates(city: str, api_key: str = "") -> str:
    """Return latitude/longitude information for ``city`` via api-ninjas.

    Args:
        city: The name of the city to look up.
        api_key: The api-ninjas API key. If empty, a clear "missing key"
            message is returned instead of making a request.

    Returns:
        A human-readable coordinates string, or a message explaining that no
        data (or no api key) is available.
    """
    if not api_key:
        return f"No coordinates available for {city}: api key missing."
    headers = {"X-Api-Key": api_key}
    response = requests.get(_CITY_URL, headers=headers, params={"name": city})
    data = response.json()
    if data and isinstance(data, list) and len(data) > 0:
        item = data[0]
        lat = item.get("latitude")
        lon = item.get("longitude")
        return f"Coordinates for {city}: Latitude {lat}, Longitude {lon}."
    return f"No data available for {city}."


# ---------------------------------------------------------------------------
# Timer / reminder tools.
# ---------------------------------------------------------------------------
def _parse_time_string(time_str: str) -> tuple[int, int]:
    """Return ``(hour, minute)`` parsed from ``'07:30'`` or ``'7pm'``.

    Args:
        time_str: A clock time in 24-hour (``'19:30'``) or am/pm
            (``'7am'``, ``'7pm'``) format.

    Returns:
        A ``(hour, minute)`` tuple.

    Raises:
        ValueError: If ``time_str`` is not in a supported format.
    """
    if m := _TIME_24H.match(time_str):
        return int(m.group(1)), int(m.group(2))
    if m := _TIME_AMPM.match(time_str):
        hour = int(m.group(1)) % 12
        if m.group(2).lower() == "pm":
            hour += 12
        return hour, 0
    raise ValueError(f"Invalid time format: {time_str!r}")


def _seconds_until(target_hour: int, target_min: int) -> float:
    """Return seconds until the next occurrence of ``target_hour:target_min``.

    Args:
        target_hour: Target hour (0-23).
        target_min: Target minute (0-59).

    Returns:
        The number of seconds from now until the next occurrence.
    """
    now = datetime.now()
    target = now.replace(
        hour=target_hour, minute=target_min, second=0, microsecond=0
    )
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def _schedule_event(delay: float, event: dict[str, Any], event_queue: Any) -> None:
    """Schedule ``event`` to be put onto ``event_queue`` after ``delay`` seconds.

    Uses a non-blocking :class:`threading.Timer`. Supports both asyncio-style
    queues (whose ``put`` returns a coroutine) and plain queues. For asyncio
    queues the thread-safe ``put_nowait`` is preferred when available.

    Args:
        delay: Delay in seconds before the event is posted.
        event: The event payload to enqueue.
        event_queue: The queue to put the event onto.
    """

    def _fire() -> None:
        put_nowait = getattr(event_queue, "put_nowait", None)
        if callable(put_nowait):
            try:
                put_nowait(event)
                return
            except Exception:
                pass
        result = event_queue.put(event)
        # If ``put`` returned a coroutine (asyncio.Queue), close it to avoid a
        # "coroutine was never awaited" warning; ``put_nowait`` above is the
        # supported path for asyncio queues.
        if hasattr(result, "close"):
            try:
                result.close()
            except Exception:
                pass

    timer = threading.Timer(delay, _fire)
    timer.daemon = True
    timer.start()


def set_timer(
    duration: float,
    reason: str = "",
    *,
    event_queue: Any = None,
) -> str:
    """Set a timer that posts an event after ``duration`` seconds.

    Args:
        duration: The timer duration in seconds.
        reason: An optional human-readable label for the timer.
        event_queue: An optional queue to receive the timer event when it
            expires. If ``None``, the timer is simply acknowledged.

    Returns:
        A human-readable acknowledgement string.
    """
    duration = float(duration)
    if event_queue is not None:
        event = {
            "source": "timer",
            "payload": reason or f"Timer for {duration} seconds",
            "metadata": {
                "set_by": "llm_agent",
                "duration": duration,
                "set_at": datetime.now().isoformat(),
            },
        }
        _schedule_event(duration, event, event_queue)
    label = f" ({reason})" if reason else ""
    return f"Timer set for {duration:g} seconds{label}."


def set_reminder(
    time: str,
    reason: str = "",
    *,
    event_queue: Any = None,
) -> str:
    """Set a reminder for a specific clock time.

    Args:
        time: The target time, e.g. ``'07:00'``, ``'19:30'`` or ``'7am'``.
        reason: An optional human-readable label for the reminder.
        event_queue: An optional queue to receive the reminder event when the
            time is reached. If ``None``, the reminder is simply acknowledged.

    Returns:
        A human-readable acknowledgement string.

    Raises:
        ValueError: If ``time`` is not in a supported format.
    """
    hour, minute = _parse_time_string(time)
    delay = _seconds_until(hour, minute)
    if event_queue is not None:
        event = {
            "source": "reminder",
            "payload": reason or time,
            "metadata": {
                "set_by": "llm_agent",
                "reminder_time": time,
                "set_at": datetime.now().isoformat(),
            },
        }
        _schedule_event(delay, event, event_queue)
    label = f" ({reason})" if reason else ""
    return f"Reminder set for {time}{label}."


# ---------------------------------------------------------------------------
# Tool schemas (OpenAI chat tool format).
# ---------------------------------------------------------------------------
SIMPLE_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Get current temperature and forecast for provided "
                "coordinates. forecast_days is the number of days from today "
                "to include in the forecast."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "include_forecast": {"type": "boolean"},
                    "forecast_days": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 14,
                        "default": 7,
                        "description": (
                            "Number of days from the current day to include "
                            "in the forecast (1-14)."
                        ),
                    },
                    "temperature_unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                    },
                    "wind_speed_unit": {
                        "type": "string",
                        "enum": ["kmh", "ms", "mph", "kn"],
                    },
                },
                "required": ["latitude", "longitude"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_joke",
            "description": "Get a random joke.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_quote",
            "description": "Retrieve a random inspirational quote.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_city_coordinates",
            "description": "Get accurate coordinates for a given city.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": (
                "Set a timer for a specified number of seconds. When the timer "
                "expires, an event will be triggered in the assistant's event "
                "queue. Use this to remind the user or trigger actions after a "
                "delay."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "duration": {
                        "type": "number",
                        "description": "The duration of the timer in seconds.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "The reason or label for the timer (optional).",
                    },
                },
                "required": ["duration"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": (
                "Set a reminder for a specific clock time (e.g., 'at 7:00' or "
                "'at 19:30'). When the time is reached, an event will be "
                "triggered in the assistant's event queue. Accepts both "
                "24-hour and 12-hour formats."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "time": {
                        "type": "string",
                        "description": (
                            "The target time for the reminder, e.g., '07:00', "
                            "'19:30', or '7am'."
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": "The reason or label for the reminder (optional).",
                    },
                },
                "required": ["time"],
                "additionalProperties": False,
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Dispatch router.
# ---------------------------------------------------------------------------
def dispatch(
    name: str,
    args: dict,
    *,
    api_ninjas_key: str = "",
    event_queue: Any = None,
) -> Optional[str]:
    """Route a tool call to the matching function in this module.

    Injects ``api_ninjas_key`` and ``event_queue`` where appropriate.

    Args:
        name: The tool name to invoke.
        args: The keyword arguments for the tool.
        api_ninjas_key: API key forwarded to api-ninjas-backed tools.
        event_queue: Event queue forwarded to timer/reminder tools.

    Returns:
        The result string from the tool, or ``None`` if ``name`` is not owned
        by this module.
    """
    if name == "get_weather":
        return get_weather(**args)
    if name == "get_joke":
        return get_joke()
    if name == "get_quote":
        return get_quote(api_key=api_ninjas_key, **args)
    if name == "get_city_coordinates":
        return get_city_coordinates(api_key=api_ninjas_key, **args)
    if name == "set_timer":
        return set_timer(**args, event_queue=event_queue)
    if name == "set_reminder":
        return set_reminder(**args, event_queue=event_queue)
    return None
