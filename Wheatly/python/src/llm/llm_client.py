import openai
import json
import yaml

import os
import logging
import requests
import time

from playsound import playsound
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import tempfile

#from local file google_agent import GoogleCalendarManager
try:
  from llm.google_agent import GoogleCalendarManager
except ImportError:
  from google_agent import GoogleCalendarManager

from llm.google_agent import GoogleAgent
  
logging.basicConfig(level=logging.WARN)

def _load_config():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    config_path = os.path.join(base_dir, "config", "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

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

class TextToSpeech:
    def __init__(self):
        config = _load_config()
        base_dir = os.path.dirname(os.path.dirname(__file__))
        # Get TTS parameters from config
        tts_config = config.get("tts", {})
        self.api_key = config["secrets"]["elevenlabs_api_key"]
        self.voice_id = tts_config.get("voice_id", "4Jtuv4wBvd95o1hzNloV")
        self.voice_settings = VoiceSettings(
            stability=tts_config.get("stability", 0.3),
            similarity_boost=tts_config.get("similarity_boost", 0.1),
            style=tts_config.get("style", 0.0),
            use_speaker_boost=tts_config.get("use_speaker_boost", True),
            speed=tts_config.get("speed", 0.8)
        )
        self.model_id = tts_config.get("model_id", "eleven_flash_v2_5")
        self.output_format = tts_config.get("output_format", "mp3_22050_32")
        # Disable verbose logging from elevenlabs to remove INFO prints
        logging.getLogger("elevenlabs").setLevel(logging.WARNING)
        self.client = ElevenLabs(api_key=self.api_key)
    
    def elevenlabs_generate_audio(self, text):
        start_time = time.time()
        # Generates audio using ElevenLabs TTS with configured parameters
        audio = self.client.text_to_speech.convert(
            text=text,
            voice_id=self.voice_id,
            voice_settings=self.voice_settings,
            model_id=self.model_id,
            output_format=self.output_format
        )
        elapsed = time.time() - start_time
        logging.info(f"TTS audio generation took {elapsed:.3f} seconds.")
        return audio
    
    def generate_and_play_advanced(self, text):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(base_dir, "temp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        audio_chunks = list(self.elevenlabs_generate_audio(text))
        # Use NamedTemporaryFile for cleaner handling
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.mp3', dir=temp_dir, delete=False) as temp_file:
            for chunk in audio_chunks:
                temp_file.write(chunk)
            file_path = temp_file.name
        play_start = time.time()
        try:
            playsound(file_path)
        except Exception as e:
            logging.error(f"Error playing audio file: {e}")
        finally:
            try:
                os.remove(file_path)
            except Exception as e:
                logging.error(f"Error deleting audio file: {e}")
        play_elapsed = time.time() - play_start
        logging.info(f"TTS audio playback took {play_elapsed:.3f} seconds.")

# =================== LLM Client ===================
# This class is responsible for interacting with the OpenAI API

class GPTClient:
    def __init__(self, model="gpt-4o-mini"):
        config = _load_config()
        self.api_key = config["secrets"]["openai_api_key"]
        self.model = model
        self.tts_enabled = config["tts"]["enabled"]
        openai.api_key = self.api_key

    def get_text(self, conversation):
        start_time = time.time()
        completion = openai.responses.create(
            model=self.model,
            input=conversation,
        )
        elapsed = time.time() - start_time
        if not getattr(completion, "output", None):
            raise Exception("No response from GPT")
        first_msg = completion.output[0]
        if hasattr(first_msg, "content"):
            text = "".join(getattr(item, "text", "") for item in first_msg.content)
        elif hasattr(first_msg, "text"):
            text = first_msg.text
        else:
            raise Exception("No text found in the response message")
        return text

    def reply_with_animation(self, conversation):
        start_time = time.time()
        completion = openai.responses.create(
            model=self.model,
            input=conversation,
            tools=set_animation_tool,
            tool_choice={"name": "set_animation", "type": "function"}
        )
        elapsed = time.time() - start_time
        logging.info(f"GPT animation selection took {elapsed:.3f} seconds.")
        choice = completion.output[0]
        animation = ""
        try:
            args = json.loads(choice.arguments)
            animation = args.get("animation", "")
        except Exception:
            if hasattr(choice.arguments, "function_call") and choice.arguments.function_call:
                func_call = choice.arguments.function_call
                try:
                    args = json.loads(func_call.arguments)
                    animation = args.get("animation", "")
                except Exception:
                    animation = ""
        return animation
        
    def get_workflow(self, conversation):
        start_time = time.time()
        completion = openai.responses.create(
            model=self.model,
            input=conversation,
            tools=tools,
            parallel_tool_calls=True
        )
        elapsed = time.time() - start_time
        choice = completion.output
        results = []
        if completion.output[0].type == "web_search_call":
            #add content of completion.output[1]
            for item in completion.output[1].content:
                results.append({
                    "arguments": {"text": item.text},
                    "name": "web_search_call_result",
                    "call_id": getattr(item, "id", "")
                })

        for msg in choice:
            if msg.type == "function_call":
                #print("function_call")
                if hasattr(msg, "arguments"):
                    results.append({
                        "arguments": json.loads(msg.arguments),
                        "name": msg.name,
                        "call_id": msg.call_id
                    })
                else:
                    results.append({
                        "arguments": {},
                        "name": msg.name,
                        "call_id": msg.call_id
                    })
        return results if results else None


set_animation_tool = [
    {
        "type": "function",
        "name": "set_animation",
        "description": "The Wheatley bot should select an animation based on the emotional state it determines from the current context or input. The function will analyze the tone, keywords, and interaction style to decide which emotional state best reflects the bot's current mood or reaction. Depending on the chosen emotion, the corresponding animation should be selected to visually represent that state, ensuring it aligns with the emotional intensity. For example, a more dramatic emotion like \"fearful\" may trigger exaggerated, frantic movements, while a \"neutral\" state might result in subtle, minimal animations. The animation choice should dynamically vary based on the bot's emotional state, adding diversity and depth to its interactions, ensuring that each response feels unique and appropriate.",
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

tools = [
    {"type": "web_search_preview"},
    {
        "type": "function",
        "name": "get_weather",
        "description": "Get current temperature and forecast for provided coordinates.",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "include_forecast": {"type": "boolean"},
                "forecast_days": {"type": "integer"},
                "extra_hourly": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "temperature_unit": {"type": "string", 
                "enum": ["celsius", "fahrenheit"]},
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
        "name": "reverse_text",
        "description": "Reverse the provided text.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"],
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
    }
]

tts_engine = TextToSpeech()


class Functions:
    def __init__(self):
        self.test = GPTClient()
        config = _load_config()
        self.tts_enabled = config["tts"]["enabled"]
        self.google_agent = GoogleAgent()
        

    def execute_workflow(self, workflow):
        results = []
        for item in workflow:
            func_name = item.get("name")
            logging.info(f"\n--- Tool Execution: {func_name} ---")
            tool_start = time.time()
            if self.tts_enabled:
                conversation = [
                    {"role": "system", "content": "Act as Weatly from portal 2. in 10 words summarize the function call as if you are doing what it says. always say numbers out in full. try to enterpet things yourself, so long and lat should be city names. try to be funny but also short. Do not give the result of the function, just explain what you are doing. for example: generating joke. or adding numbers"},
                    {"role": "user", "content": f"Executing function: {func_name} with arguments: {item.get('arguments')}"}
                ]
                text = self.test.get_text(conversation)
                tts_engine.generate_and_play_advanced(text)
            if func_name == "call_google_agent":
                user_request = item.get("arguments", {}).get("user_request", "")
                args = item.get("arguments", {}).get("arguments", {})
                response = self.google_agent.llm_decide_and_dispatch(user_request, args)
                results.append((func_name, response))
            elif func_name == "get_weather":
                get_weather_args = item.get("arguments")
                latitude = get_weather_args.get("latitude")
                longitude = get_weather_args.get("longitude")
                include_forecast = get_weather_args.get("include_forecast", False)
                forecast_days = get_weather_args.get("forecast_days", 7)
                extra_hourly = get_weather_args.get("extra_hourly", ["temperature_2m", "weathercode"])
                temperature_unit = get_weather_args.get("temperature_unit", "celsius")
                wind_speed_unit = get_weather_args.get("wind_speed_unit", "kmh")
                response = self.get_weather(latitude, longitude, include_forecast, forecast_days, extra_hourly, temperature_unit, wind_speed_unit)
                results.append((func_name, response))
            elif func_name == "test_function":
                test_args = item.get("arguments")
                test = test_args.get("test")
                response = f"Test function executed with argument: {test}"
                results.append((func_name, response))
            elif func_name == "get_joke":
                response = self.get_joke()
                results.append((func_name, response))
            elif func_name == "get_quote":
                response = self.get_quote()
                results.append((func_name, response))
            elif func_name == "reverse_text":
                args = item.get("arguments")
                text_val = args.get("text")
                response = self.reverse_text(text_val)
                results.append((func_name, response))
            elif func_name == "get_city_coordinates":
                args = item.get("arguments")
                city = args.get("city")
                response = self.get_city_coordinates(city)
                results.append((func_name, response))
            elif func_name == "get_advice":
                response = self.get_advice()
                results.append((func_name, response))
            tool_elapsed = time.time() - tool_start
            logging.info(f"Tool '{func_name}' execution took {tool_elapsed:.3f} seconds.")
        return results

    def get_weather(self, lat, lon, include_forecast=False, forecast_days=7, extra_hourly=["temperature_2m", "weathercode"], temperature_unit="celsius", wind_speed_unit="kmh"):
        base_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current_weather=true"
            f"&forecast_days={forecast_days}"
            f"&temperature_unit={temperature_unit}"
            f"&wind_speed_unit={wind_speed_unit}"
        )
        if include_forecast and extra_hourly:
            hourly_params = ",".join(extra_hourly)
            base_url += f"&hourly={hourly_params}"
        try:
            response = requests.get(base_url)
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
            # Interpret the current weather code.
            weather_code = cw.get("weathercode")
            if weather_code is not None:
                try:
                    weather_code_int = int(weather_code)
                except Exception:
                    weather_code_int = None
                if weather_code_int is not None:
                    description = WEATHER_CODE_DESCRIPTIONS.get(weather_code_int, "Unknown weather condition")
                    summary += f"\nWeather Condition: {description} (Code: {weather_code_int})"
            # Process extended forecast if requested.
            if include_forecast and extra_hourly:
                hours_data = data.get("hourly", {})
                times = hours_data.get("time", [])
                forecast_summary = "\nExtended Forecast:\n"
                for i, t in enumerate(times):
                    line_info = [t]
                    for var_name in extra_hourly:
                        var_values = hours_data.get(var_name, [])
                        if i < len(var_values):
                            value = var_values[i]
                            # If the variable is weathercode, interpret it.
                            if var_name == "weathercode":
                                try:
                                    code_int = int(value)
                                    desc = WEATHER_CODE_DESCRIPTIONS.get(code_int, "Unknown")
                                    line_info.append(f"{var_name}={value} ({desc})")
                                except Exception:
                                    line_info.append(f"{var_name}={value}")
                            else:
                                line_info.append(f"{var_name}={value}")
                    forecast_summary += ", ".join(line_info) + "\n"
                summary += forecast_summary
            return summary
        except Exception as e:
            return f"Error retrieving weather: {e}"

    def get_joke(self):
        response = requests.get("https://official-joke-api.appspot.com/random_joke")
        data = response.json()
        joke = f"Provide the following joke to the user: {data.get('setup')} - {data.get('punchline')}"
        return joke

    def get_quote(self):
        config = _load_config()
        api_key = config["secrets"].get("api_ninjas_api_key", "")
        headers = {"X-Api-Key": api_key}
        response = requests.get("https://api.api-ninjas.com/v1/quotes", headers=headers)
        data = response.json()
        if data and isinstance(data, list):
            item = data[0]
            return f"Tell the user: {item.get('quote', '')} — {item.get('author', '')}"
        return "No quote available."

    def reverse_text(self, text):
        return text[::-1]

    def get_city_coordinates(self, city):
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

    def get_advice(self):
      config = _load_config()
      api_key = config["secrets"].get("api_ninjas_api_key", "")
      headers = {"X-Api-Key": api_key}
      response = requests.get("https://api.api-ninjas.com/v1/advice", headers=headers)
      data = response.json()
      #print(f"Data: {data}")
      advice = None
      advice = data.get("advice")
      return f"Give the following advice: {advice}"


if __name__ == "__main__":
    manager = GoogleCalendarManager()
    
    # Print calendars
    manager.print_calendars()
    
    # Print upcoming events
    manager.print_upcoming_events()
