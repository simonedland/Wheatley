# llm_client_utils.py
# Utility functions and tool definitions extracted from llm_client.py
import os
import yaml
from datetime import datetime
import requests

# Weather code descriptions
WEATHER_CODE_DESCRIPTIONS = {
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
    99: "Thunderstorm with heavy hail (Central Europe only)"
}

def _load_config():
    base_dir = os.path.dirname(__file__)
    config_path = os.path.join(base_dir, "..", "config", "config.yaml")
    config_path = os.path.abspath(config_path)
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
    
def get_joke():
    response = requests.get("https://official-joke-api.appspot.com/random_joke")
    data = response.json()
    joke = f"Provide the following joke to the user: {data.get('setup')} - {data.get('punchline')}"
    return joke

def get_quote():
    config = _load_config()
    api_key = config["secrets"].get("api_ninjas_api_key", "")
    headers = {"X-Api-Key": api_key}
    response = requests.get("https://api.api-ninjas.com/v1/quotes", headers=headers)
    data = response.json()
    if data and isinstance(data, list):
        item = data[0]
        return f"Tell the user: {item.get('quote', '')} — {item.get('author', '')}"
    return "No quote available."

def get_city_coordinates(city):
    config = _load_config()
    api_key = config["secrets"].get("api_ninjas_api_key", "")
    headers = {"X-Api-Key": api_key}
    url = f"https://api.api-ninjas.com/v1/city?name={city}"
    response = requests.get(url, headers=headers)
    data = response.json()
    if data and isinstance(data, list) and len(data) > 0:
        item = data[0]
        lat = item.get("latitude")
        lon = item.get("longitude")
        return f"Coordinates for {city}: Latitude {lat}, Longitude {lon}."
    return f"No data available for {city}."

set_animation_tool = [
    {
        "type": "function",
        "name": "set_animation",
        "description": "The Wheatley bot should select an animation based on the emotional state it determines from the current context or input. Last known mood: {last_mood}. Use this as context for your choice. The function will analyze the tone, keywords, and interaction style to decide which emotional state best reflects the bot's current mood or reaction.",
        "parameters": {
            "type": "object",
            "properties": {
                "animation": {
                    "type": "string",
                    "enum": ["happy", "angry", "sad", "neutral", "excited", "confused", "surprised", "curious", "bored", "fearful", "hopeful", "embarrassed", "frustrated", "proud", "nostalgic", "relieved", "grateful", "shy", "disappointed", "jealous"]  # allowed animations
                }
            },
            "required": ["animation"],
            "additionalProperties": False
        }
    }
]

def build_tools():
    config = _load_config()
    web_search_config = config.get("web_search", {})
    web_search_tool = {"type": "web_search_preview"}
    if "user_location" in web_search_config:
        web_search_tool["user_location"] = web_search_config["user_location"]
    if "search_context_size" in web_search_config:
        web_search_tool["search_context_size"] = web_search_config["search_context_size"]
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_day = datetime.now().strftime("%A")
    tools = [
        web_search_tool,
        {
            "type": "function",
            "name": "get_weather",
            "description": f"Get current temperature and forecast for provided coordinates. today is {current_day} and the current time is {current_time}. forecast days is the number of days from today to include in the forecast. in the case of the user asking for the weather in the weekend when today is monday you should include 7 days. Forecast for the weekend does not mean 3 days unles current day is friday.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "include_forecast": {"type": "boolean"},
                    "forecast_days": { "type": "integer", "minimum": 1, "maximum": 14, "default": 7, "description": "Number of days from the current day to include in the forecast (1-7)."},
                    "extra_hourly": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "temperature_unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    "wind_speed_unit": {"type": "string", "enum": ["kmh", "ms", "mph", "kn"]}
                },
                "required": ["latitude", "longitude"],
                "additionalProperties": False
            }
        },
        {
            "type": "function",
            "name": "test_function",
            "description": "Test function to check if the function calling works.",
            "parameters": {
                "type": "object",
                "properties": {
                    "test": {"type": "string"}
                },
                "required": ["test"],
                "additionalProperties": False
            }
        },
        {
            "type": "function",
            "name": "get_joke",
            "description": "Get a random joke.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        },
        {
            "type": "function",
            "name": "get_quote",
            "description": "Retrieve a random inspirational quote.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        },
        {
            "type": "function",
            "name": "get_city_coordinates",
            "description": "Get accurate coordinates for a given city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"}
                },
                "required": ["city"],
                "additionalProperties": False
            }
        },
        {
            "type": "function",
            "name": "get_advice",
            "description": "Retrieve a piece of advice.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        },
        {
            "type": "function",
            "name": "call_google_agent",
            "description": "Delegate any Google-related request to the Google Agent. Use this if the user asks about Google services, calendar, or anything Google-related. if user asks about calendar use this function. this agent can delete events, create/add events, and get events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_request": {"type": "string", "description": "The user's request or question related to Google services."}
                },
                "required": ["user_request"],
                "additionalProperties": False
            }
        },
        {
            "type": "function",
            "name": "call_spotify_agent",
            "description": "Delegate any Spotify request—play, pause, search, queue, device control, etc.—to the Spotify Agent. Use this whenever the user mentions Spotify or music playback. supply device id when transferring playback.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_request": {"type": "string"},
                    "device_id": {"type": "string", "pattern": "^[0-9a-f]{40}$"}
                },
                "required": ["user_request"],
            },
        },
        {
            "type": "function",
            "name": "set_timer",
            "description": "Set a timer for a specified number of seconds or minutes. When the timer expires, an event will be triggered in the assistant's event queue. Use this to remind the user or trigger actions after a delay.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration": {"type": "number", "description": "The duration of the timer in seconds."},
                    "reason": {"type": "string", "description": "The reason or label for the timer (optional)."}
                },
                "required": ["duration"],
                "additionalProperties": False
            }
        },
        {
            "type": "function",
            "name": "set_reminder",
            "description": "Set a reminder for a specific clock time (e.g., 'at 7:00' or 'at 19:30'). When the time is reached, an event will be triggered in the assistant's event queue. Use this to remind the user or trigger actions at a specific time of day. Accepts both 24-hour and 12-hour formats.",
            "parameters": {
                "type": "object",
                "properties": {
                    "time": {"type": "string", "description": "The target time for the reminder, e.g., '07:00', '19:30', or '7am'."},
                    "reason": {"type": "string", "description": "The reason or label for the reminder (optional)."}
                },
                "required": ["time"],
                "additionalProperties": False
            }
        },
        {
            "type": "function",
            "name": "daily_summary",
            "description": "Generate a daily summary of the user's activities, tasks, and events. This function will compile information from various sources, such as calendar events, task lists, and notes, to provide a comprehensive overview of the user's day.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        }
    ]
    #print(tools)
    return tools
